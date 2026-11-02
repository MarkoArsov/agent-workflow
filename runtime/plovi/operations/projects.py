"""The projects registry: add, list and remove; files on disk are never touched."""
from __future__ import annotations
from pathlib import Path
from .. import registry
from ..util import WorkflowError
from . import Text, record, register


@register("projects.add", "Register a configured project so the inbox covers it", "plovi projects add PATH [--reason TEXT]",
          arguments={"path": {"type": "string", "description": "Project root"}}, required=("path",), mutates=True, risk="low")
def add(args):
    from ..project import load
    project = load(Path(args["path"]), migrate=False)
    return registry.register(project, args=args, command="projects.add")


@register("projects.list", "List registered projects and whether each root still exists", "plovi projects list [--format text|json]",
          arguments={"format": {"enum": ["text", "json"]}}, mutates=False, risk="none")
def listing(args):
    rows = [dict(entry, exists=Path(entry["root"]).is_dir()) for entry in registry.entries()]
    if args.get("format") == "text":
        return Text("".join(f"{row['id']}  {row['root']}" + ("" if row["exists"] else "  missing") + "\n" for row in rows))
    return {"projects": rows}


@register("projects.remove", "Unregister a project; its files stay on disk", "plovi projects remove ID [--reason TEXT]",
          arguments={"id": {"type": "string", "description": "Registered project ID"}}, required=("id",), mutates=True, risk="low")
def remove(args):
    from ..project import load
    removed = registry.remove(args["id"])
    root = Path(removed["root"])
    try:
        project = load(root, migrate=False)
        if project.profile["project"]["id"] != removed["id"]:
            raise WorkflowError("project ID changed")
    except WorkflowError:
        project = registry.stand_in(removed["id"], root)
    record(project, {"kind": "project", "id": removed["id"]}, "project.unregistered", {"root": removed["root"]},
           args=args, command="projects.remove")
    return {"id": removed["id"], "root": removed["root"], "removed": True,
            "detail": "plovi forgot this project. Its files stay on disk."}
