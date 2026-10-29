"""Portable native-host entry points; all delegate to one project resolver."""
from __future__ import annotations
from pathlib import Path
import json
from .extensions import catalog
from .project import Project
from .util import WorkflowError, identifier, package_root, read_json, user_data

def entry_name(name, package=None):
    """Public skill names are presentation; canonical skill IDs remain stable."""
    marker = read_json((package or package_root()) / "workflow-package.json", {})
    discovery = marker.get("discovery", {})
    prefix = discovery.get("prefix", "plovi")
    alias = discovery.get("aliases", {}).get(name, name)
    value = identifier(f"{prefix}-{alias}")
    if any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in value):
        raise WorkflowError("Discovery names must use lowercase letters, digits, and hyphens")
    return value

def interface_metadata(name, package=None):
    """Use an explicit label so hosts do not title-case the namespace acronym."""
    marker = read_json((package or package_root()) / "workflow-package.json", {})
    prefix = marker.get("discovery", {}).get("prefix", "plovi")
    words = entry_name(name, package)[len(prefix) + 1:].split("-")
    title = " ".join(word.upper() if word in {"ci", "e2e", "pr", "rfc"} else word.capitalize()
                     for word in words)
    return f"interface:\n  display_name: {json.dumps(prefix + ' ' + title)}\n"

def discovery_file(relative):
    parts = Path(relative).parts
    return any(parts[i:i + 2] in ((".agents", "skills"), (".claude", "skills"))
               for i in range(len(parts) - 1))

def project_files(root: Path, profile: dict) -> dict[str, str]:
    project = Project(root, profile)
    skills = catalog(project)
    files = {}
    receipt = read_json(user_data(migrate=False) / "receipt.json", {})
    # A live global install already resolves each project's overrides. Repeating
    # bundled adapters in projects would leave stale names/scripts after a sync.
    linked = (receipt.get("backend") == "linked"
              and Path(receipt.get("source", "")).resolve() == package_root()
              and not (root / ".plovi/runtime/active.json").exists())
    bundled = catalog() if linked else {}
    locations = []
    for repo in profile["repositories"]:
        prefix = Path(repo["path"])
        if set(profile["agents"]) & {"codex", "cursor"}:
            locations.append(prefix / ".agents/skills")
        if "claude" in profile["agents"]:
            locations.append(prefix / ".claude/skills")
    for location in locations:
        for name, info in skills.items():
            hosts = set(profile["agents"]) & ({"claude"} if location.parent.name == ".claude" else {"codex", "cursor"})
            if name in bundled and hosts <= set(receipt.get("agents", [])):
                continue
            for public in entry_names(name):
                for relative, content in skill_files(name, info, public).items():
                    files[(location / public / relative).as_posix()] = content
    validate_names(skills)
    return files


def entry_names(name, package=None):
    public = entry_name(name, package)
    # TODO(1.0): remove compatibility aliases. They apply to the default plovi namespace.
    return (public, "af-" + public[len("plovi-"):]) if public.startswith("plovi-") else (public,)


def validate_names(skills, package=None):
    names = [public for name in skills for public in entry_names(name, package)]
    if len(names) != len(set(names)):
        raise WorkflowError("Discovery aliases produce duplicate skill names")


def adapter_source(name, package=None):
    root = package or package_root()
    if not (root / "templates/adapters/bootstrap.py").is_file():
        root = package_root()  # One-release legacy source compatibility uses the current bootstrap.
    text = (root / "templates/adapters" / name).read_text()
    return text.replace("# bootstrap:include", (root / "templates/adapters/bootstrap.py").read_text())


def skill_files(name, info, public, package=None):
    canonical = entry_name(name, package)
    note = f"{public} is now {canonical}; use {canonical} (alias available until 1.0)." if public != canonical else None
    template = adapter_source("dispatch.py", package)
    template = template.replace("SKILL_NAME = None", f"SKILL_NAME = {name!r}").replace("ALIAS_NOTE = None", f"ALIAS_NOTE = {note!r}")
    description = (f"Deprecated alias of {canonical}. " if note else "") + info["description"]
    text = f"---\nname: {public}\ndescription: {json.dumps(description)}\n---\n\nRun this skill folder's scripts/dispatch.py with the current project as its working directory. Read the returned effective skill file, then follow its procedure. Project overrides take precedence. Do not use defaults from another project.\n"
    if note:
        text += f"\nDeprecated alias of {canonical}. Use {canonical} for new work.\n"
    return {"SKILL.md": text, "scripts/dispatch.py": template,
            "agents/openai.yaml": interface_metadata(name, package)}
