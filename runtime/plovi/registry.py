"""The user-level projects registry, shared with project.resolve."""
from __future__ import annotations
import time
from pathlib import Path
from types import SimpleNamespace
from .util import WorkflowError, identifier, read_json, user_data, write_json


def path():
    return user_data() / "projects.json"


def entries():
    value = read_json(path(), [])
    if not isinstance(value, list):
        raise WorkflowError(f"{path()} must hold a list of projects. Fix or remove the file, then add projects again.")
    return [e for e in value if isinstance(e, dict) and isinstance(e.get("id"), str) and isinstance(e.get("root"), str)]


def _now():
    ms = time.time_ns() // 1_000_000
    from .ledger import timestamp
    return timestamp(ms)


def add(project):
    """Register a loaded project; the same ID and root is a no-op."""
    from .state import lock
    project_id = identifier(project.profile["project"]["id"])
    root = Path(project.root).resolve()
    with lock(user_data() / "projects.lock", wait=True):
        rows = read_json(path(), [])
        if not isinstance(rows, list):
            raise WorkflowError(f"{path()} must hold a list of projects. Fix or remove the file, then add projects again.")
        for row in rows:
            if isinstance(row, dict) and row.get("id") == project_id:
                if Path(row.get("root", "")).resolve() == root:
                    return {"id": project_id, "root": row["root"], "added": False}
                raise WorkflowError(f"Project ID {project_id} is already registered at {row.get('root')}. "
                                    f"Run plovi projects remove {project_id} first, or give this project its own ID.")
        entry = {"id": project_id, "root": str(root), "added_at": _now()}
        write_json(path(), rows + [entry])
    return dict(entry, added=True)


def remove(project_id):
    from .state import lock
    with lock(user_data() / "projects.lock", wait=True):
        rows = read_json(path(), [])
        if not isinstance(rows, list):
            raise WorkflowError(f"{path()} must hold a list of projects. Fix or remove the file.")
        kept = [row for row in rows if not (isinstance(row, dict) and row.get("id") == project_id)]
        if len(kept) == len(rows):
            raise WorkflowError(f"No registered project has the ID {project_id}. Run plovi projects list to see the IDs.")
        removed = next(row for row in rows if isinstance(row, dict) and row.get("id") == project_id)
        write_json(path(), kept)
    return removed


def stand_in(project_id, root):
    """A minimal project for ledger writes when its root cannot be loaded."""
    return SimpleNamespace(root=Path(root), profile={"project": {"id": project_id}, "repositories": []})


def register(project, *, args=None, command="projects.add"):
    """Register and record project.registered once for a newly added entry."""
    from .operations import record
    result = add(project)
    if result["added"]:
        record(project, {"kind": "project", "id": result["id"]}, "project.registered", {"root": result["root"]},
               args=args or {}, command=command)
    return result
