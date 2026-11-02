"""Task operations: status, events, answer, approve, retry, pause, resume, cancel and rebuild-state."""
from __future__ import annotations
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from .. import ledger, manifest as contracts, state
from ..util import WorkflowError, identifier, read_json, write_json
from . import Text, actor, plans, record, register, suppressed, task_subject

TASK = {"task": {"type": "string", "description": "Task ID"}}
CONTINUE = {"rebind": {"type": "boolean", "description": "Accept a reviewed plan revision"},
            "upgrade_runtime": {"type": "boolean", "description": "Move the task to the current runtime; needs rebind"}}
FORMAT = {"format": {"enum": ["text", "json"], "description": "Output format"}}


def project_for(args):
    from ..project import resolve
    return resolve(Path(args.get("project") or "."))


def local_time(at, seconds=False):
    moment = datetime.fromisoformat(at.replace("Z", "+00:00")).astimezone()
    return moment.strftime("%Y-%m-%d %H:%M:%S" if seconds else "%Y-%m-%d %H:%M")


def one_line(text, limit=300):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def saved_state(project, task):
    identifier(task)
    value = read_json(state.directory(project, task) / "state.json")
    if not value:
        raise WorkflowError("No saved task to continue")
    return value


# ---- read-only ---------------------------------------------------------------------

def rebuild(project, task):
    value, latest = ledger.restore(project, task)
    root = state.directory(project, task)
    root.mkdir(parents=True, exist_ok=True)
    from ..progress import summary
    with state.lock(root / "runner.lock"):
        write_json(root / "state.json", value)
        write_json(root / "status.json", summary(value))
    return value, latest


def _has_history(project, task):
    return any(e["type"] == "state.checkpoint" for e in ledger.events(project, subject=task_subject(task)))


@register("status", "Show one task's progress, or every task the ledger knows", "plovi status [TASK] [--json] [--format text|json]",
          arguments={"task": {"type": "string", "description": "Task ID; omit to list every task"},
                     "json": {"type": "boolean"}, "verbose": {"type": "boolean"}, **FORMAT},
          mutates=False, risk="none")
def status(args):
    project = project_for(args)
    task = args.get("task")
    machine = args.get("json") or args.get("format") == "json"
    if not task:
        rows = ledger.tasks(project)
        if machine:
            return {"tasks": rows}
        if not rows:
            return Text("No tasks recorded yet.\n")
        lines = [f"{row['task']}: {row['status']} | {row['stage'] or 'preparing'}" + (f" | {row['title']}" if row.get("title") else "")
                 for row in rows]
        return Text("\n".join(lines) + "\n")
    identifier(task)
    root = state.directory(project, task)
    from ..migration import lock_held
    if not (root / "state.json").exists() and not lock_held(root / "runner.lock") and _has_history(project, task):
        rebuild(project, task)
    verbose = args.get("verbose")
    result = state.read(project, task) if verbose else state.observe(project, task)
    if not verbose:
        from ..progress import summary
        result = summary(result)
    return result


@register("events", "List ledger events, optionally for one task or after a time or event ID",
          "plovi events [--task ID] [--since TIME|EVENT_ID] [--format text|json]",
          arguments={"task": {"type": "string"}, "since": {"type": "string", "description": "ISO timestamp or event ID"}, **FORMAT},
          mutates=False, risk="none")
def events(args):
    project = project_for(args)
    subject = task_subject(identifier(args["task"])) if args.get("task") else None
    rows = ledger.events(project, subject=subject, since=args.get("since"))
    if args.get("format") != "text":
        return {"events": rows}
    if not rows:
        return Text("No events recorded.\n")
    return Text("".join(f"{local_time(e['at'], True)}  {e['type']}  {e['subject']['id']}  {e['actor']['name']}  {one_line(e['reason'], 160)}\n"
                        for e in rows))


# ---- continuing a run -----------------------------------------------------------------

def _resumed(project, saved, args, command, *, retry=False):
    """Clear a pause request; record that the run continues."""
    root = state.directory(project, saved["task"])
    (root / "pause.json").unlink(missing_ok=True)
    data = {"run_id": str(saved.get("run_id") or ""), "status": str(saved.get("status") or "")}
    if retry:
        data["retry"] = True
    if retry or command == "resume" or saved.get("status") == "paused":
        record(project, task_subject(saved["task"]), "run.resumed", data, args=args, command=command)


def _plan(project, saved):
    return contracts.load(saved["manifest_path"], project)


@register("answer", "Answer the question a stopped task asked, then continue it",
          "plovi answer TASK (--text TEXT | --file FILE) [--reason TEXT]",
          arguments={**TASK, "text": {"type": "string"}, "file": {"type": "string", "description": "Path to the answer"}, **CONTINUE},
          required=("task",), mutates=True, risk="low")
def answer(args):
    if (args.get("text") is None) == (args.get("file") is None):
        raise WorkflowError("Give exactly one answer: --text TEXT or --file FILE")
    text = args["text"] if args.get("text") is not None else Path(args["file"]).read_text(encoding="utf-8")
    project = project_for(args)
    saved = saved_state(project, args["task"])
    if not saved.get("pending_input"):
        raise WorkflowError("There is no pending input session to answer")
    plan = _plan(project, saved)
    plans.self_approve(project, plan, args, "answer")
    record(project, task_subject(saved["task"]), "question.answered", {"run_id": str(saved.get("run_id") or "")},
           args=args, command="answer")
    _resumed(project, saved, args, "answer")
    handle, temporary = tempfile.mkstemp(prefix="plovi-answer-", suffix=".txt")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        return _continue(project, saved, args, ["answer", saved["task"], "--file", temporary], answer=text)
    finally:
        os.unlink(temporary)


def _approve_preview(args):
    from .plans import describe, locate
    project = project_for(args)
    return describe(project, locate(project, args["task"], args.get("manifest")))


@register("approve", "Approve a plan, or a diff that crossed the size or protected-path limits",
          "plovi approve TASK (--plan | --size | --paths) [--approve DIGEST] [--manifest PATH] [--actor NAME] [--reason TEXT]",
          arguments={**TASK, "plan": {"type": "boolean"}, "size": {"type": "boolean"}, "paths": {"type": "boolean"},
                     "approve": {"type": "string", "description": "Digest from the preview; required for --plan and for agents"},
                     "manifest": {"type": "string"}, "actor": {"type": "string", "description": "Person name override"}, **CONTINUE},
          required=("task",), mutates=True, risk="high", preview=_approve_preview)
def approve(args):
    project = project_for(args)
    task = identifier(args["task"])
    if args.get("plan"):
        preview = _approve_preview(args)
        if not args.get("approve"):
            return preview
        if args["approve"] != preview["plan_sha256"]:
            raise WorkflowError(f"The digest does not match the current plan for {task}; the plan changed or the digest is wrong. "
                                f"Preview it again with plovi approve {task} --plan.")
        if preview["approved"]:
            return dict(preview, approved=True, recorded=False)
        record(project, task_subject(task), "plan.approved",
               {"plan_sha256": preview["plan_sha256"], "auto": False, "manifest": preview["manifest"]}, args=args, command="approve")
        return dict(preview, approved=True, recorded=True)
    kind = "size" if args.get("size") else "protected_paths"
    saved = saved_state(project, task)
    pending = next((p for p in saved.get("pending_approvals") or [] if p.get("kind") == kind), None)
    agent = bool(args.get("actor_agent"))
    if not saved.get("approval"):
        raise WorkflowError("There is no pending diff approval")
    fingerprint = (pending or saved["approval"])["fingerprint"]
    if agent and not args.get("approve"):
        flag = "--size" if kind == "size" else "--paths"
        return {"operation": "approve", "kind": kind, "task": task, "digest": fingerprint, "fingerprint": fingerprint,
                "pending": pending, "next": f"plovi approve {task} {flag} --approve {fingerprint}",
                "detail": "Show this diff approval to the person before applying it."}
    if args.get("approve") and args["approve"] != fingerprint:
        raise WorkflowError(f"The digest does not match the pending {kind.replace('_', ' ')} approval for {task}; "
                            "the diff changed or the digest is wrong. Preview it again.")
    who = actor(args, project.root)
    legacy_reason = args.get("reason") or ("Explicit --size approval" if kind == "size" else "Explicit --paths approval")
    plans.self_approve(project, _plan(project, saved), args, "approve")
    record(project, task_subject(task), "approval.granted",
           {"run_id": str(saved.get("run_id") or ""), "kind": kind, "fingerprint": fingerprint}, args=args, command="approve")
    _resumed(project, saved, args, "approve")
    legacy = ["approve", task, "--size" if kind == "size" else "--paths", "--actor", who["name"]]
    if args.get("reason"):
        legacy += ["--reason", args["reason"]]
    return _continue(project, saved, args, legacy, approval=(kind, who["name"], legacy_reason))


def _continue(project, saved, args, legacy, **runner_kwargs):
    from .. import runner, runtime_pin
    from ..util import package_root
    from . import WORKER
    task = saved["task"]
    argv = ["--project", str(project.root), *legacy, *(["--rebind"] if args.get("rebind") else [])]
    code = runtime_pin.dispatch(project, task, argv, source=package_root(), create=True,
                                upgrade=bool(args.get("upgrade_runtime")))
    if code is not None:
        return code
    plan = contracts.load(saved["manifest_path"], project)
    gate = WORKER and plans.worker_gate(project, plan)
    return runner.run(project, plan, resume=True, rebind=bool(args.get("rebind")), require_plan_approval=gate, **runner_kwargs)


@register("retry", "Retry an escalated task, optionally with a note for the agent", "plovi retry TASK [--note FILE] [--reason TEXT]",
          arguments={**TASK, "note": {"type": "string", "description": "Path to a note the next attempt reads"}, **CONTINUE},
          required=("task",), mutates=True, risk="low")
def retry(args):
    project = project_for(args)
    saved = saved_state(project, args["task"])
    if not saved.get("escalation"):
        raise WorkflowError("Only an escalated task can be retried")
    note = Path(args["note"]).resolve() if args.get("note") else None
    text = note.read_text(encoding="utf-8") if note else None
    plans.self_approve(project, _plan(project, saved), args, "retry")
    _resumed(project, saved, args, "retry", retry=True)
    legacy = ["retry", saved["task"], *(["--note", str(note)] if note else [])]
    return _continue(project, saved, args, legacy, retry=True, note=text)


@register("resume", "Continue a paused, failed or interrupted task without repeating finished stages",
          "plovi resume TASK [--rebind] [--reason TEXT]", arguments={**TASK, **CONTINUE},
          required=("task",), mutates=True, risk="low")
def resume(args):
    project = project_for(args)
    saved = saved_state(project, args["task"])
    plans.self_approve(project, _plan(project, saved), args, "resume")
    _resumed(project, saved, args, "resume")
    return _continue(project, saved, args, ["resume", saved["task"]])


def _supports_pause(project, task):
    from ..util import package_root
    receipt = read_json(state.directory(project, task) / "runtime.json")
    if not receipt or Path(receipt.get("path", "")).resolve() == package_root().resolve():
        return True
    return (Path(receipt["path"]) / "runtime/plovi/ledger.py").is_file()


@register("pause", "Stop a running task before its next stage starts", "plovi pause TASK [--reason TEXT]",
          arguments=TASK, required=("task",), mutates=True, risk="low")
def pause(args):
    project = project_for(args)
    task = identifier(args["task"])
    value = state.read(project, task)
    if value.get("status") not in {"starting", "running", "waiting"}:
        raise WorkflowError(f"{task} is {value.get('status')}, so there is nothing to pause. Only a starting or running task can pause.")
    if not _supports_pause(project, task):
        raise WorkflowError(f"{task} runs on an older pinned runtime that cannot pause. Cancel it, or move it to this runtime with "
                            f"plovi resume {task} --upgrade-runtime --rebind after it stops.")
    root = state.directory(project, task)
    who = actor(args, project.root)
    write_json(root / "pause.json", {"requested_at": time.time(), "actor": who})
    record(project, task_subject(task), "pause.requested", {"run_id": str(value.get("run_id") or "")}, args=args, command="pause")
    return {"task": task, "status": value.get("status"), "pause_requested": True,
            "detail": "plovi pauses before the next stage starts. Continue with plovi resume " + task + "."}


@register("cancel", "Ask the runner to stop a task and its child processes", "plovi cancel TASK [--reason TEXT]",
          arguments=TASK, required=("task",), mutates=True, risk="low")
def cancel(args):
    project = project_for(args)
    task = identifier(args["task"])
    result = state.cancel(project, task)
    saved = read_json(state.directory(project, task) / "state.json", {})
    record(project, task_subject(task), "cancel.requested", {"run_id": str(saved.get("run_id") or "")}, args=args, command="cancel")
    return result


@register("rebuild-state", "Rebuild a task's state.json and status.json from the ledger", "plovi rebuild-state TASK [--reason TEXT]",
          arguments=TASK, required=("task",), mutates=True, risk="low")
def rebuild_state(args):
    project = project_for(args)
    task = identifier(args["task"])
    value, latest = rebuild(project, task)
    record(project, task_subject(task), "state.checkpoint", dict(latest["data"], rebuilt=True), args=args, command="rebuild-state")
    return {"task": task, "rebuilt": True, "run_id": value.get("run_id"), "task_status": value.get("status"),
            "checkpoint": latest["id"], "state": str(state.directory(project, task) / "state.json")}


# ---- hooks for commands outside the registry --------------------------------------------

def before_launch(project, args):
    """Explicit run and pipeline launches approve the plan they start."""
    if suppressed():
        return
    command = args.get("command")
    if command == "run":
        if args.get("unattended") or args.get("dry_run"):
            return
        plan = contracts.load(args["manifest"], project)
        if read_json(state.directory(project, plan["task"]) / "state.json"):
            return
        plans.self_approve(project, plan, args, "run")
        return
    target = Path(args["target"])
    plan = contracts.load(target, project) if target.is_file() else None
    saved = read_json(state.directory(project, plan["task"] if plan else identifier(str(args["target"]))) / "state.json", {})
    if not plan and not saved:
        return
    if saved.get("status") in {"complete", "cancelled"} or saved.get("pending_input") or saved.get("pending_approvals") or saved.get("escalation"):
        return
    plans.self_approve(project, plan or contracts.load(saved["manifest_path"], project), args, "pipeline")
    if saved:
        _resumed(project, saved, args, "pipeline")


def after_validation(project, plan, args):
    plans.propose(project, plan, args)


def task_started(project, result, args):
    branches = result.get("branches") or {name: project.profile["git"]["branch_template"].format(task=result["task"])
                                          for name in result.get("checkouts", {})}
    data = {"branches": branches}
    for key in ("issue", "title"):
        if args.get(key):
            data[key] = args[key]
    record(project, task_subject(result["task"]), "task.created", data, args=args, command="task.start")
