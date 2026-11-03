"""Append-only, per-project event ledger kept outside every repository and worktree."""
from __future__ import annotations
import json
import os
import re
import secrets
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from .util import WorkflowError, atomic_write, contained, digest, identifier, json_text, package_root, read_json, redact, user_data, write_json

VERSION = 1
MAX_LINE = 64 * 1024
TEXT_LIMIT = 4000
SUBJECTS = ("task", "schedule", "execution", "pr", "policy", "project")
ACTORS = ("person", "agent", "plovi")
RUNNER = {"kind": "plovi", "name": "runner"}
IMPORTER = {"kind": "plovi", "name": "import"}
# Event type -> (required data fields, optional data fields). docs/ledger.md mirrors this table.
TYPES = {
    "task.created": (("branches",), ("issue", "title")),
    "task.claimed": (("run_id",), ()),
    "run.started": (("run_id", "manifest", "plan_sha256"), ("red_proof",)),
    "stage.started": (("run_id", "stage"), ()),
    "attempt.finished": (("run_id", "stage", "attempt", "classification", "path"), ("kind", "provider", "usage", "cost_usd")),
    "stage.finished": (("run_id", "stage", "result"), ()),
    "question.asked": (("run_id", "stage", "question"), ("next",)),
    "question.answered": (("run_id",), ()),
    "plan.proposed": (("plan_sha256", "manifest"), ()),
    "plan.approved": (("plan_sha256", "auto"), ("manifest",)),
    "approval.requested": (("run_id", "kind", "fingerprint"), ("next",)),
    "approval.granted": (("run_id", "kind", "fingerprint"), ()),
    "escalation.raised": (("run_id", "stage", "kind", "detail"), ("next",)),
    "run.paused": ((), ("run_id", "status", "reason", "resets_at", "next")),
    "run.resumed": ((), ("run_id", "status", "retry")),
    "run.interrupted": ((), ("run_id", "status")),
    "run.cancelled": ((), ("run_id", "status")),
    "run.finished": (("run_id", "status"), ("error",)),
    "delivery.committed": (("repository", "commit"), ()),
    "delivery.pushed": (("repository", "branch"), ()),
    "pr.opened": (("repository", "url"), ("files_changed",)),
    "policy.changed": (("diff",), ()),
    "project.registered": (("root",), ()),
    "state.checkpoint": (("run_id", "state_sha256", "keys"), ()),
    "pause.requested": ((), ("run_id",)),
    "cancel.requested": ((), ("run_id",)),
    "project.unregistered": ((), ("root",)),
    "checkpoint.migrated": (("binding_sha256",), ()),
    "plan.rebound": (("run_id", "old", "new"), ()),
    "commits.adopted": (("repository", "commits"), ("author",)),
    "limits.exceeded": (("run_id", "files", "lines", "limit"), ()),
    "receipt.rederived": (("repository",), ("path",)),
    "provider.circuit_open": (("run_id", "provider", "classification"), ()),
}
# Free text that may carry provider output or person input: redacted and bounded.
TEXT_FIELDS = {"question": TEXT_LIMIT, "detail": TEXT_LIMIT, "title": 300, "error": TEXT_LIMIT, "diff": 16000}
# Live or process-local fields; a change in these alone is not a new checkpoint.
VOLATILE = {"updated_at", "pid", "child_pid", "heartbeat_at", "activity", "activity_at", "tool_active", "tool_started_at"}
_ULID = re.compile(r"[0-9A-HJKMNP-TV-Z]{26}")
_SHA = re.compile(r"[0-9a-f]{64}")
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ids = threading.Lock()
_last = [0, 0]
_imported = set()
_schema = None


# ---- identifiers and validation -------------------------------------------------

def new_id(now_ms=None):
    """48-bit millisecond time plus 80 random bits; monotonic within this process."""
    with _ids:
        ms = time.time_ns() // 1_000_000 if now_ms is None else now_ms
        if ms <= _last[0]:
            ms, rand = _last[0], _last[1] + 1
            if rand >= 1 << 80:
                ms, rand = ms + 1, secrets.randbits(79)
        else:
            rand = secrets.randbits(80)
        _last[:] = [ms, rand]
    value = (ms << 80) | rand
    return "".join(_ALPHABET[(value >> shift) & 31] for shift in range(125, -1, -5))


def id_time(event_id):
    value = 0
    for char in event_id:
        value = value * 32 + _ALPHABET.index(char)
    return value >> 80


def timestamp(ms):
    moment = datetime.fromtimestamp(ms / 1000, timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms % 1000:03d}Z"


def schema():
    global _schema
    if _schema is None:
        _schema = json.loads((package_root() / "schemas/event.schema.json").read_text(encoding="utf-8"))
    return _schema


def _check(value, rule, where):
    """Validate the JSON-schema subset the event schema uses."""
    if "const" in rule and value != rule["const"]:
        raise WorkflowError(f"Ledger event {where} must be {rule['const']!r}")
    if "enum" in rule and value not in rule["enum"]:
        raise WorkflowError(f"Ledger event {where} is not one of: {', '.join(map(str, rule['enum']))}")
    kind = rule.get("type")
    types = {"object": dict, "string": str, "array": list, "boolean": bool}
    if kind in types and (type(value) is not types[kind]):
        raise WorkflowError(f"Ledger event {where} must be a {kind}")
    if isinstance(value, str):
        if len(value) < rule.get("minLength", 0) or len(value) > rule.get("maxLength", 1 << 30):
            raise WorkflowError(f"Ledger event {where} has an invalid length")
        if "pattern" in rule and not re.search(rule["pattern"], value):
            raise WorkflowError(f"Ledger event {where} has an invalid format")
    if isinstance(value, dict):
        for key in rule.get("required", []):
            if key not in value:
                raise WorkflowError(f"Ledger event {where} needs {key}")
        properties = rule.get("properties", {})
        for key, item in value.items():
            if key in properties:
                _check(item, properties[key], f"{where}.{key}" if where != "event" else key)
            elif rule.get("additionalProperties") is False:
                raise WorkflowError(f"Ledger event {where} has an unknown field: {key}")


def _text(value, limit):
    if not isinstance(value, str):
        return value
    value = redact(value)
    return value if len(value) <= limit else value[:limit - 1] + "…"


def _clean_data(kind, data):
    if not isinstance(data, dict):
        raise WorkflowError("Ledger event data must be an object")
    required, _ = TYPES.get(kind, ((), ()))
    missing = [field for field in required if field not in data]
    if missing:
        raise WorkflowError(f"Ledger event {kind} needs data fields: {', '.join(missing)}")
    return {key: _text(value, TEXT_FIELDS[key]) if key in TEXT_FIELDS else value for key, value in data.items()}


def _record(project_id, event, event_id, at):
    if not isinstance(event, dict):
        raise WorkflowError("A ledger event must be an object")
    record = {"v": VERSION, "id": event_id, "at": at, "project": project_id}
    for key in ("subject", "type", "actor", "reason", "data"):
        if key in event:
            record[key] = event[key]
    if isinstance(record.get("reason"), str):
        record["reason"] = _text(record["reason"], 2000)
    _check(record, schema(), "event")
    if record["type"] not in TYPES:
        raise WorkflowError(f"Unknown ledger event type: {record['type']}")
    if not record["reason"].strip():
        raise WorkflowError("A ledger event needs a reason")
    record["data"] = _clean_data(record["type"], record["data"])
    return record


# ---- location ------------------------------------------------------------------

def _protected(project):
    roots = [Path(project.root)]
    profile = getattr(project, "profile", {}) or {}
    for repo in profile.get("repositories", []):
        try:
            roots.append(project.repo_path(repo["id"]))
        except (WorkflowError, AttributeError, KeyError):
            pass
    worktrees = profile.get("git", {}).get("worktree_directory")
    if worktrees:
        try:
            roots.append(contained(Path(project.root), worktrees))
        except WorkflowError:
            pass
    return roots


def directory(project):
    """The per-project ledger root under user data; never inside the project."""
    from .factory import safe
    project_id = identifier(project.profile["project"]["id"])
    path = safe(user_data().resolve(), "projects", project_id, "ledger")
    resolved = path.resolve()
    for root in _protected(project):
        if resolved.is_relative_to(Path(root).resolve()):
            raise WorkflowError(f"The plovi ledger would be written inside {root}. "
                                "Point XDG_DATA_HOME at a folder outside the project, its repositories and worktrees.")
    return path


def _month_files(root):
    return sorted(root.glob("events-[0-9][0-9][0-9][0-9]-[0-9][0-9].jsonl")) if root.is_dir() else []


def _prepare(project):
    root = directory(project)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    _ensure_imported(project, root)
    return root


# ---- writing -------------------------------------------------------------------

def _repair_tail(path):
    """Drop a crash-truncated trailing record before appending after it."""
    size = path.stat().st_size
    if not size:
        return
    with path.open("rb+") as stream:
        stream.seek(-1, os.SEEK_END)
        if stream.read(1) == b"\n":
            return
        stream.seek(max(0, size - MAX_LINE * 2))
        data = stream.read()
        end = data.rfind(b"\n")
        stream.truncate(size - len(data) + end + 1 if end >= 0 else max(0, size - len(data)))


def _write(root, project_id, event):
    """Validate and append one event; the caller holds the ledger lock."""
    ms = time.time_ns() // 1_000_000
    event_id = new_id(ms)
    record = _record(project_id, event, event_id, timestamp(id_time(event_id)))
    line = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    if len(line) > MAX_LINE:
        raise WorkflowError(f"Ledger event {record['type']} is {len(line)} bytes; the limit is {MAX_LINE}. "
                            "Store large payloads in a file and record its path.")
    files = _month_files(root)
    if files:
        _repair_tail(files[-1])
    target = root / f"events-{record['at'][:7]}.jsonl"
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0)
    handle = os.open(target, flags, 0o600)
    try:
        view = memoryview(line)
        while view:
            written = os.write(handle, view)
            view = view[written:]
        os.fsync(handle)
    finally:
        os.close(handle)
    return record


def append(project, event):
    """Validate the envelope and type table, then append exactly one line."""
    from .state import lock
    root = _prepare(project)
    with lock(root / "ledger.lock", wait=True):
        return _write(root, project.profile["project"]["id"], event)


# ---- reading -------------------------------------------------------------------

def _since(value):
    if value is None:
        return None
    if _ULID.fullmatch(value):
        return ("id", value)
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise WorkflowError(f"Use an ISO timestamp or an event ID for since, not {value!r}") from None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    ms = int(moment.timestamp() * 1000)
    return ("at", timestamp(ms))


def events(project, subject=None, since=None):
    """Read every month file in order; skip only a torn last line of the newest file."""
    root = _prepare(project)
    cutoff = _since(since)
    files = _month_files(root)
    result = []
    warned = False
    for number, path in enumerate(files):
        data = path.read_bytes()
        chunks = data.split(b"\n")
        complete = data.endswith(b"\n")
        if complete:
            chunks.pop()
        newest = number == len(files) - 1
        for index, chunk in enumerate(chunks):
            last = index == len(chunks) - 1
            if not chunk.strip():
                continue
            torn = last and not complete
            try:
                value = None if torn and newest else json.loads(chunk)
            except ValueError:
                value = None
            if not isinstance(value, dict) or not isinstance(value.get("data"), dict):
                if newest and last:
                    if not warned:
                        print(f"Warning: plovi skipped an incomplete last ledger line in {path.name}; "
                              "a writer stopped mid-append.", file=sys.stderr)
                        warned = True
                    continue
                raise WorkflowError(f"Ledger file {path.name} line {index + 1} is not a valid event. "
                                    "Restore the file from a backup or move the damaged line aside.")
            if subject is not None and value.get("subject") != subject:
                continue
            if cutoff and str(value.get(cutoff[0], "")) < cutoff[1]:
                continue
            result.append(value)
    return result


# ---- import of runs that predate the ledger --------------------------------------

def _ensure_imported(project, root):
    key = str(root)
    if key in _imported:
        return
    marker = root / "imported.json"
    saved = read_json(marker)
    if not (isinstance(saved, dict) and saved.get("complete")):
        from .state import lock
        with lock(root / "ledger.lock", wait=True):
            saved = read_json(marker)
            if not isinstance(saved, dict):
                saved = {"schema_version": 1, "complete": False, "runs": []}
            if not saved.get("complete"):
                _import_runs(project, root, saved)
                saved["complete"] = True
                write_json(marker, saved)
    _imported.add(key)


def _import_runs(project, root, saved):
    try:
        evidence = contained(project.root, project.profile["planning"]["evidence_directory"])
    except (WorkflowError, KeyError, TypeError):
        return
    if not evidence.is_dir():
        return
    project_id = project.profile["project"]["id"]
    for folder in sorted(evidence.iterdir()):
        path = folder / "state.json"
        try:
            value = read_json(path) if path.is_file() else None
        except WorkflowError:
            value = None
        if not isinstance(value, dict):
            continue
        task = value.get("task") or folder.name
        try:
            identifier(task)
        except WorkflowError:
            continue
        run_id = str(value.get("run_id") or "imported")
        key = f"{task}:{run_id}"
        if key in saved["runs"]:
            continue
        for event_type, data in _imported_events(value, run_id):
            _write(root, project_id, {"subject": {"kind": "task", "id": task}, "type": event_type, "actor": dict(IMPORTER),
                                      "reason": "Imported from run state that predates the ledger",
                                      "data": dict(data, imported=True)})
        _write(root, project_id, {"subject": {"kind": "task", "id": task}, "type": "state.checkpoint",
                                  "actor": dict(IMPORTER), "reason": "Imported from run state that predates the ledger",
                                  "data": dict(_store(root, value), imported=True)})
        saved["runs"].append(key)
        write_json(root / "imported.json", saved)


def _imported_events(value, run_id):
    status = value.get("status")
    yield "task.created", {"branches": {}}
    yield "run.started", {"run_id": run_id, "manifest": str(value.get("manifest_path", "")),
                          "plan_sha256": str(value.get("plan_sha256", ""))}
    for stage in value.get("completed", []):
        yield "stage.finished", {"run_id": run_id, "stage": stage, "result": "passed"}
    pending = value.get("pending_input") or {}
    escalation = value.get("escalation") or {}
    if status == "needs_input" and pending.get("question"):
        yield "question.asked", {"run_id": run_id, "stage": value.get("stage") or "", "question": pending["question"]}
    elif status == "needs_approval" and value.get("pending_approvals"):
        for item in value["pending_approvals"]:
            yield "approval.requested", {"run_id": run_id, "kind": item.get("kind", ""), "fingerprint": item.get("fingerprint", "")}
    elif status == "escalated" and escalation:
        yield "escalation.raised", {"run_id": run_id, "stage": escalation.get("stage") or "", "kind": escalation.get("kind", ""),
                                    "detail": str(escalation.get("reason", ""))}
    elif status == "cancelled":
        yield "run.cancelled", {"run_id": run_id, "status": status}
    elif status == "paused":
        yield "run.paused", {"run_id": run_id, "status": status}
    elif status in {"starting", "running", "waiting", "interrupted"}:
        yield "run.interrupted", {"run_id": run_id, "status": "interrupted"}
    else:
        yield "run.finished", {"run_id": run_id, "status": str(status or "unknown"),
                               **({"error": value["error"]} if value.get("error") else {})}


# ---- state checkpoints and the blob store --------------------------------------

def _blob(root, sha):
    if not _SHA.fullmatch(str(sha)):
        raise WorkflowError("A state checkpoint names an invalid blob hash")
    return root / "blobs" / sha[:2] / (sha + ".json")


def _store(root, state):
    keys = {}
    for key, value in state.items():
        text = json_text(value)
        sha = digest(text.encode("utf-8"))
        path = _blob(root, sha)
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            atomic_write(path, text, 0o600)
        keys[key] = sha
    return {"run_id": str(state.get("run_id") or ""), "state_sha256": digest(json_text(state)), "keys": keys}


def content_sha(state):
    return digest(json_text({key: value for key, value in state.items() if key not in VOLATILE}))


def checkpoint(project, task, state, *, actor=None, reason="The runner saved task state"):
    root = _prepare(project)
    data = _store(root, state)
    return append(project, {"subject": {"kind": "task", "id": task}, "type": "state.checkpoint",
                            "actor": dict(actor or RUNNER), "reason": reason, "data": data})


def restore(project, task):
    """Rebuild a task's saved state from its latest checkpoint, verifying every blob."""
    latest = None
    for event in events(project, subject={"kind": "task", "id": task}):
        if event["type"] == "state.checkpoint":
            latest = event
    if latest is None:
        raise WorkflowError(f"No recorded state history exists for {task}, so plovi cannot rebuild its state. "
                            "Check the task ID, or start the task again.")
    root = directory(project)
    state = {}
    for key, sha in latest["data"]["keys"].items():
        path = _blob(root, sha)
        if not path.is_file():
            raise WorkflowError(f"The saved state of {task} is incomplete: the value of {key} is missing from the ledger blob store. "
                                "Restore the ledger from a backup before rebuilding.")
        raw = path.read_bytes()
        if digest(raw) != sha:
            raise WorkflowError(f"The saved state of {task} was changed after it was recorded: the value of {key} "
                                "does not match its hash. Restore the ledger from a backup before rebuilding.")
        state[key] = json.loads(raw.decode("utf-8"))
    if digest(json_text(state)) != latest["data"]["state_sha256"]:
        raise WorkflowError(f"The saved state of {task} does not match its recorded hash. Restore the ledger from a backup before rebuilding.")
    return state, latest


# ---- runner transitions ----------------------------------------------------------

def red_proof(manifest):
    """True when the plan demonstrates a failing test before the change (implement-tests without a waiver)."""
    return "implement-tests" in manifest.get("stages", []) and not manifest.get("approved_no_red_reason")


def usage(value):
    """Input and output token counts from a provider usage report, or None when it reports neither."""
    if not isinstance(value, dict):
        return None
    tokens = {key: value[key] for key in ("input_tokens", "output_tokens")
              if type(value.get(key)) is int and value[key] >= 0}
    return tokens or None


class Recorder:
    """Turn runner state transitions into ledger events and checkpoints.

    A ledger failure never stops a run: plovi reports it once and keeps the
    existing state.json behavior.
    """

    STOPS = {"complete", "failed", "escalated", "needs_input", "needs_approval"}

    def __init__(self, project, manifest):
        self.project = project
        self.manifest = manifest
        self.task = manifest["task"]
        self.subject = {"kind": "task", "id": self.task}
        self.previous = None
        self.content = None
        self.disabled = False

    def _append(self, kind, data):
        if self.disabled:
            return None
        try:
            return append(self.project, {"subject": dict(self.subject), "type": kind, "actor": dict(RUNNER),
                                         "reason": REASONS.get(kind, "The runner recorded a transition"), "data": data})
        except (WorkflowError, OSError) as exc:
            self._disable(exc)
            return None

    def _disable(self, exc):
        self.disabled = True
        print(f"Warning: plovi could not write the ledger ({exc}); the run continues with state.json only.", file=sys.stderr)

    def _snapshot(self, state):
        return {"status": state.get("status"), "completed": list(state.get("completed", [])),
                "pending_input": json_text(state.get("pending_input")) if state.get("pending_input") else None,
                "approvals": {(a.get("kind"), a.get("fingerprint")) for a in state.get("pending_approvals") or []},
                "escalation": json_text(state.get("escalation")) if state.get("escalation") else None,
                "delivery": json.loads(json.dumps(state.get("delivery") or {})),
                "advisory": (state.get("diff_advisory") or {}).get("fingerprint")}

    def started(self, state, *, resumed=False):
        run_id = state["run_id"]
        self._append("task.claimed", {"run_id": run_id})
        self._append("run.started", {"run_id": run_id, "manifest": str(state.get("manifest_path", "")),
                                     "plan_sha256": state.get("plan_sha256", ""), "red_proof": red_proof(self.manifest)})
        self.previous = self._snapshot(state)

    def stage_started(self, state, stage):
        self._append("stage.started", {"run_id": state["run_id"], "stage": stage})

    def attempt(self, state, entry, path):
        data = {"run_id": state["run_id"], "stage": entry["stage"], "attempt": entry["id"],
                "classification": entry["classification"], "path": path}
        if entry.get("failure_kind"):
            data["kind"] = entry["failure_kind"]
        provider = (entry.get("route") or {}).get("provider")
        if provider:
            data["provider"] = provider
        tokens = usage(entry.get("usage"))
        if tokens:
            data["usage"] = tokens
        if entry.get("cost_usd") is not None:
            data["cost_usd"] = entry["cost_usd"]
        self._append("attempt.finished", data)

    @staticmethod
    def _next(state, data):
        from .progress import next_command
        command = next_command(state)
        return dict(data, next=command) if command else data

    def event(self, kind, data, reason=None, actor=None):
        """Record a runner decision that is not a state transition, such as an automatic rebind."""
        if self.disabled:
            return None
        try:
            return append(self.project, {"subject": dict(self.subject), "type": kind, "actor": dict(actor or RUNNER),
                                         "reason": reason or REASONS.get(kind, "The runner recorded a decision"), "data": data})
        except (WorkflowError, OSError) as exc:
            self._disable(exc)
            return None

    def saved(self, state):
        if self.disabled:
            return
        if self.previous is None:
            self.previous = self._snapshot(state)
        before, now = self.previous, self._snapshot(state)
        run_id = state.get("run_id", "")
        for stage in now["completed"]:
            if stage not in before["completed"]:
                self._append("stage.finished", {"run_id": run_id, "stage": stage, "result": "passed"})
        if now["pending_input"] and now["pending_input"] != before["pending_input"]:
            self._append("question.asked", self._next(state, {"run_id": run_id, "stage": state.get("stage") or "",
                                                              "question": state["pending_input"].get("question", "")}))
        for kind, fingerprint in sorted(now["approvals"] - before["approvals"], key=str):
            self._append("approval.requested", self._next(state, {"run_id": run_id, "kind": kind, "fingerprint": fingerprint}))
        if now["escalation"] and now["escalation"] != before["escalation"]:
            escalation = state["escalation"]
            self._append("escalation.raised", self._next(state, {"run_id": run_id, "stage": escalation.get("stage") or state.get("stage") or "",
                                               "kind": escalation.get("kind", ""), "detail": str(escalation.get("reason", ""))}))
        if now["advisory"] and now["advisory"] != before.get("advisory"):
            advisory = state["diff_advisory"]
            self._append("limits.exceeded", {"run_id": run_id, "files": advisory["files"], "lines": advisory["lines"],
                                             "limit": advisory["limit"]})
        for name, progress in now["delivery"].items():
            old = before["delivery"].get(name, {})
            if progress.get("commit") and progress.get("commit") != old.get("commit"):
                self._append("delivery.committed", {"repository": name, "commit": progress["commit"]})
            if progress.get("pushed") and not old.get("pushed"):
                branch = next((r.get("branch") for r in self.manifest.get("repositories", []) if r["id"] == name), None)
                self._append("delivery.pushed", {"repository": name, "branch": branch or ""})
            if progress.get("pr") and progress.get("pr") != old.get("pr"):
                url = progress["pr"].get("url", "") if isinstance(progress["pr"], dict) else str(progress["pr"])
                data = {"repository": name, "url": url}
                if (progress.get("intent") or {}).get("paths") is not None:
                    data["files_changed"] = len(progress["intent"]["paths"])
                self._append("pr.opened", data)
        status = now["status"]
        if status != before["status"]:
            if status in {"failed", "escalated", "cancelled"} and state.get("stage") and state["stage"] not in now["completed"]:
                self._append("stage.finished", {"run_id": run_id, "stage": state["stage"], "result": status})
            if status == "paused":
                data = {"run_id": run_id, "status": status}
                if state.get("pause_reason"):
                    data["reason"] = state["pause_reason"]
                if state.get("resets_at") is not None:
                    data["resets_at"] = state["resets_at"]
                self._append("run.paused", self._next(state, data))
            elif status == "cancelled":
                self._append("run.cancelled", {"run_id": run_id, "status": status})
            elif status in self.STOPS:
                data = {"run_id": run_id, "status": status}
                if state.get("error"):
                    data["error"] = str(state["error"])
                self._append("run.finished", data)
        self.previous = now
        sha = content_sha(state)
        if sha != self.content and not self.disabled:
            try:
                checkpoint(self.project, self.task, state)
                self.content = sha
            except (WorkflowError, OSError) as exc:
                self._disable(exc)


REASONS = {
    "task.claimed": "The runner claimed the task",
    "run.started": "The runner started a run",
    "stage.started": "The runner started a stage",
    "attempt.finished": "A provider attempt finished",
    "stage.finished": "A stage finished",
    "question.asked": "The provider asked a question",
    "approval.requested": "The diff needs a person's approval",
    "escalation.raised": "The run stopped for a person's decision",
    "run.paused": "The runner paused before the next stage",
    "run.cancelled": "The run was cancelled",
    "run.finished": "The run stopped",
    "run.interrupted": "The runner stopped without recording a result",
    "delivery.committed": "The runner committed the task changes",
    "delivery.pushed": "The runner pushed the task branch",
    "pr.opened": "The runner opened a pull request",
    "plan.rebound": "The runner continued with the approved plan revision",
    "commits.adopted": "The runner adopted commits on the task branch",
    "limits.exceeded": "The diff passed the size limit but stayed under the ceiling",
    "receipt.rederived": "The runner rewrote the task's allocation receipt from the ledger",
    "provider.circuit_open": "The runner skips this provider for the rest of the run",
}


def interrupted(project, task, value):
    """Record one run.interrupted per run ID from observer interruption detection."""
    run_id = str(value.get("run_id") or "")
    subject = {"kind": "task", "id": task}
    if any(e["type"] == "run.interrupted" and e["data"].get("run_id") == run_id for e in events(project, subject=subject)):
        return None
    event = append(project, {"subject": subject, "type": "run.interrupted", "actor": dict(RUNNER),
                             "reason": REASONS["run.interrupted"], "data": {"run_id": run_id, "status": "interrupted"}})
    checkpoint(project, task, value)
    return event


# ---- task views ------------------------------------------------------------------

def _fold(view, event):
    data, kind = event["data"], event["type"]
    view["updated_at"] = event["at"]
    if kind == "task.created":
        for key in ("issue", "title"):
            if data.get(key):
                view[key] = data[key]
    elif kind == "run.started":
        view.update(run_id=data["run_id"], status="running", escalation=None)
    elif kind == "stage.started":
        view.update(stage=data["stage"], status="running")
    elif kind == "stage.finished" and data.get("result") == "passed":
        if data["stage"] not in view["completed"]:
            view["completed"].append(data["stage"])
    elif kind == "question.asked":
        view.update(pending_question=data["question"], status="needs_input")
    elif kind == "question.answered":
        view["pending_question"] = None
    elif kind == "approval.requested":
        view["pending_approvals"] = [a for a in view["pending_approvals"] if a["kind"] != data["kind"]]
        view["pending_approvals"].append({"kind": data["kind"], "fingerprint": data["fingerprint"]})
    elif kind == "approval.granted":
        view["pending_approvals"] = [a for a in view["pending_approvals"] if a["fingerprint"] != data["fingerprint"] or a["kind"] != data["kind"]]
    elif kind == "escalation.raised":
        view.update(escalation={"stage": data["stage"], "kind": data["kind"], "detail": data["detail"]}, status="escalated")
    elif kind == "plan.approved":
        if data["plan_sha256"] not in view["approved_plans"]:
            view["approved_plans"].append(data["plan_sha256"])
    elif kind in {"run.paused", "run.interrupted", "run.cancelled"}:
        view["status"] = kind.split(".")[1]
    elif kind == "run.finished":
        view["status"] = data["status"]
        if data["status"] == "complete":
            view.update(pending_question=None, pending_approvals=[], escalation=None)


def tasks(project):
    views = {}
    for event in events(project):
        if event["subject"]["kind"] != "task":
            continue
        task = event["subject"]["id"]
        view = views.setdefault(task, {"task": task, "issue": None, "title": None, "status": "created", "stage": None,
                                       "completed": [], "run_id": None, "pending_question": None, "escalation": None,
                                       "pending_approvals": [], "approved_plans": [], "updated_at": None})
        _fold(view, event)
    return sorted(views.values(), key=lambda v: (v["updated_at"] or "", v["task"]))


def task(project, task_id):
    return next((view for view in tasks(project) if view["task"] == task_id), None)
