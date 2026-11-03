"""The inbox: what needs a person, derived from the ledger on every call."""
from __future__ import annotations
import sys
from datetime import datetime
from pathlib import Path
from .. import ledger
from ..util import WorkflowError
from . import Text, register
from .tasks import local_time, one_line

KINDS = ("question", "plan", "approval", "escalation", "failed", "interrupted", "usage_limit")
CLOSES_ALL = {"run.cancelled", "cancel.requested"}
RESTARTS = {"run.started", "run.resumed"}


def _cancel(task):
    return {"label": "Cancel task", "operation": "cancel", "args": {"task": task}}


def _items(project):
    """Fold one project's task events into open items."""
    project_id = project.profile["project"]["id"]
    open_items, titles, approved, started = {}, {}, set(), set()
    proposals = {}
    for event in ledger.events(project):
        if event["subject"]["kind"] != "task":
            continue
        task, kind, data = event["subject"]["id"], event["type"], event["data"]
        items = open_items.setdefault(task, {})
        if kind == "task.created" and data.get("title"):
            titles[task] = data["title"]
        elif kind == "plan.approved":
            approved.add((task, data.get("plan_sha256")))
        elif kind == "run.started":
            started.add((task, data.get("plan_sha256")))
        elif kind == "plan.proposed":
            proposals[task] = event
        if kind in CLOSES_ALL or (kind == "run.finished" and data.get("status") == "complete"):
            items.clear()
            proposals.pop(task, None)
            continue
        if kind in RESTARTS:
            for name in ("escalation", "failed", "interrupted", "usage_limit"):
                items.pop(name, None)
        if kind == "question.asked":
            items["question"] = (event, "The task asks: " + one_line(data["question"]),
                                 [{"label": "Answer the question", "operation": "answer", "args": {"task": task}}])
        elif kind == "question.answered":
            items.pop("question", None)
        elif kind == "approval.requested":
            flag = "size" if data["kind"] == "size" else "paths"
            what = "size limits" if flag == "size" else "protected paths"
            items["approval:" + data["kind"]] = (event, f"The diff crossed the {what} and needs your approval.",
                                                 [{"label": "Approve the diff", "operation": "approve",
                                                   "args": {"task": task, flag: True, "approve": data["fingerprint"]}}])
        elif kind == "approval.granted":
            items.pop("approval:" + data["kind"], None)
        elif kind == "escalation.raised":
            items["escalation"] = (event, one_line(data["detail"]) or "The run stopped for your decision.",
                                   [{"label": "Retry with a note", "operation": "retry", "args": {"task": task}}])
        elif kind == "run.finished" and data.get("status") == "failed":
            items["failed"] = (event, one_line(data.get("error") or "The run failed."),
                               [{"label": "Resume the task", "operation": "resume", "args": {"task": task}}])
        elif kind == "run.paused" and data.get("reason") == "usage_limit":
            when = data.get("resets_at")
            reset = datetime.fromtimestamp(when).strftime("%Y-%m-%d %H:%M") if type(when) in (int, float) else None
            reason = "The provider usage limit was reached." + (f" It resets at {reset}." if reset else "")
            items["usage_limit"] = (event, reason + " Resume the task after that.",
                                    [{"label": "Resume the task", "operation": "resume", "args": {"task": task}}])
        elif kind == "run.interrupted":
            items["interrupted"] = (event, "The runner stopped without recording a result.",
                                    [{"label": "Resume the task", "operation": "resume", "args": {"task": task}}])
    for task, event in proposals.items():
        sha = event["data"]["plan_sha256"]
        if (task, sha) in approved or (task, sha) in started:
            continue
        open_items.setdefault(task, {})["plan"] = (event, "A new plan is ready for your approval.",
            [{"label": "Approve the plan", "operation": "approve",
              "args": {"task": task, "plan": True, "manifest": event["data"]["manifest"], "approve": sha}}])
    result = []
    for task, items in open_items.items():
        for name, (event, reason, actions) in items.items():
            result.append({"id": event["id"], "kind": name.split(":")[0], "project": project_id, "subject": {"kind": "task", "id": task},
                           "title": titles.get(task, task), "reason": reason, "created_at": event["at"],
                           "actions": actions + [_cancel(task)]})
    return result


def _projects(args):
    from .. import registry
    from ..project import load, resolve
    projects, warnings, seen = [], [], set()
    try:
        current = resolve(Path(args.get("project") or "."))
        projects.append(current)
        seen.add((current.profile["project"]["id"], str(current.root.resolve())))
    except WorkflowError:
        if args.get("project"):
            raise
    for entry in registry.entries():
        root = Path(entry["root"])
        key = (entry["id"], str(root.resolve()))
        if key in seen:
            continue
        seen.add(key)
        if not root.is_dir():
            warnings.append(f"Project {entry['id']} is registered at {entry['root']}, but that folder is missing. "
                            f"Run plovi projects remove {entry['id']} to forget it.")
            continue
        try:
            projects.append(load(root, migrate=False))
        except WorkflowError as exc:
            warnings.append(f"Project {entry['id']} at {entry['root']} could not be read: {exc}")
    return projects, warnings


def collect(args):
    projects, warnings = _projects(args)
    items = []
    for project in projects:
        try:
            items.extend(_items(project))
        except WorkflowError as exc:
            warnings.append(f"Project {project.profile['project']['id']}: {exc}")
    items.sort(key=lambda item: (item["created_at"], item["id"]))
    return items, warnings


def render(items):
    if not items:
        return "Nothing needs you.\n"
    header = "1 item needs you." if len(items) == 1 else f"{len(items)} items need you."
    blocks = []
    for item in items:
        task = item["subject"]["id"]
        head = f"{local_time(item['created_at'])}  {item['kind']}  {task}"
        if item["title"] != task:
            head += f"  {item['title']}"
        blocks.append("\n".join([head, "  " + item["reason"], "  Next: " + "; ".join(a["label"] for a in item["actions"])]))
    return header + "\n\n" + "\n\n".join(blocks) + "\n"


@register("inbox", "List what needs you across registered projects, oldest first", "plovi inbox [--format text|json]",
          arguments={"format": {"enum": ["text", "json"]}}, mutates=False, risk="none")
def inbox(args):
    items, warnings = collect(args)
    for warning in warnings:
        print("Warning: " + warning, file=sys.stderr)
    if args.get("format") == "text":
        return Text(render(items))
    return {"items": items, "warnings": warnings}
