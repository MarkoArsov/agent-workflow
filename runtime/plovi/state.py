"""Atomic run journals and OS-held locks; stale PIDs never authorize a kill."""
from __future__ import annotations
import os
import time
from contextlib import contextmanager
from pathlib import Path
from .util import WorkflowError, contained, identifier, read_json, write_json

def directory(project, task):
    return contained(project.root, project.profile["planning"]["evidence_directory"]) / identifier(task)

def read(project, task):
    root = directory(project, task)
    value = read_json(root / "state.json")
    launch = read_json(root / "launch.json", {})
    from .migration import lock_held
    if (launch.get("run_id") and launch.get("at", 0) > (value or {}).get("updated_at", 0)
            and launch.get("run_id") != (value or {}).get("run_id")
            and (lock_held(root / "launch.lock") or lock_held(root / "runner.lock"))):
        return {"task": task, "run_id": launch["run_id"], "status": "starting",
                "completed": (value or {}).get("completed", []), "started_at": launch["at"]}
    if value is None:
        raise WorkflowError("No run state exists for this task")
    if value.get("status") in {"starting", "running", "waiting"}:
        from .migration import lock_held
        if not lock_held(project.config / "local/runner.lock"):
            try:
                with lock(directory(project, task) / "runner.lock"):
                    value = read_json(directory(project, task) / "state.json")
                    if value.get("status") in {"starting", "running", "waiting"}:
                        value["status"] = "interrupted"
                        save(directory(project, task), value)
                        _record_interruption(project, task, value)
            except WorkflowError:
                pass
    live = read_json(directory(project, task) / "live.json", {})
    if live.get("run_id") and live.get("run_id") == value.get("run_id"):
        for key in ("activity", "activity_at", "heartbeat_at", "provider", "model", "repair_round", "tool_active", "tool_started_at", "check", "passed"):
            if key in live: value[key] = live[key]
    return value

def _record_interruption(project, task, value):
    import sys
    from . import ledger
    try:
        ledger.interrupted(project, task, value)
    except (WorkflowError, OSError) as exc:
        print(f"Warning: plovi could not record the interruption in the ledger ({exc}).", file=sys.stderr)


def observe(project, task):
    """Read the compact observer receipt, falling back once for legacy journals."""
    from .migration import lock_held
    from .progress import summary
    root = directory(project, task)
    value = read_json(root / "status.json")
    launch = read_json(root / "launch.json", {})
    if (launch.get("run_id") and launch.get("at", 0) > (value or {}).get("updated_at", 0)
            and launch.get("run_id") != (value or {}).get("run_id")
            and (lock_held(root / "launch.lock") or lock_held(root / "runner.lock"))):
        return summary({"task": task, "run_id": launch["run_id"], "status": "starting",
                        "started_at": launch["at"], "completed": (value or {}).get("completed", [])})
    if value is None or (value.get("status") in {"starting", "running", "waiting"}
                         and not lock_held(root / "runner.lock")
                         and not lock_held(project.config / "local/runner.lock")):
        return summary(read(project, task))
    live = read_json(root / "live.json", {})
    if live.get("run_id") and live.get("run_id") == value.get("run_id"):
        for key in ("activity", "activity_at", "heartbeat_at", "provider", "model", "repair_round", "tool_active", "tool_started_at", "check", "passed"):
            if key in live: value[key] = live[key]
    return value


def save(root, state, *, before_publish=None):
    state["updated_at"] = time.time()
    if state.get('status') in {'cancelled', 'merged', 'closed'}:
        state.setdefault('terminal_at', state['updated_at'])
    if before_publish:
        before_publish()
    publish(root, state)


def publish(root, state):
    from .progress import summary
    write_json(root / "state.json", state)
    write_json(root / "status.json", summary(state))

if os.name == "nt":
    import msvcrt

    def _acquire(handle):
        # Lock one byte far past any PID we write; the OS releases it if we die.
        handle.seek(1 << 30)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

    def _release(handle):
        handle.seek(1 << 30)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _acquire(handle):
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _release(handle):
        fcntl.flock(handle, fcntl.LOCK_UN)

@contextmanager
def lock(path, *, wait=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        deadline = time.monotonic() + 30
        while True:
            try:
                _acquire(handle)
                break
            except OSError as exc:
                if not wait or time.monotonic() >= deadline:
                    raise WorkflowError("A runner owns this project/environment lock") from exc
                time.sleep(0.02)
        handle.seek(0); handle.truncate(); handle.write(str(os.getpid())); handle.flush()
        try:
            yield
        finally:
            _release(handle)

def cancel(project, task):
    root = directory(project, task)
    value = read(project, task)
    write_json(root / "cancel.json", {"requested_at": time.time()})
    return {"task": task, "status": value["status"], "cancel_requested": True,
            "detail": "The owning runner terminates its own child process group."}


from .progress import Reporter, read_events
