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
    value = read_json(directory(project, task) / "state.json")
    if value is None:
        raise WorkflowError("No run state exists for this task")
    return value

def save(root, state):
    state["updated_at"] = time.time()
    write_json(root / "state.json", state)

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
def lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            _acquire(handle)
        except OSError as exc:
            raise WorkflowError("A runner owns this project/environment lock") from exc
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

