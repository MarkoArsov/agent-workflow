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
    prefix = discovery.get("prefix", "aw")
    alias = discovery.get("aliases", {}).get(name, name)
    value = identifier(f"{prefix}-{alias}")
    if any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in value):
        raise WorkflowError("Discovery names must use lowercase letters, digits, and hyphens")
    return value

def interface_metadata(name, package=None):
    """Use an explicit label so hosts do not title-case the namespace acronym."""
    marker = read_json((package or package_root()) / "workflow-package.json", {})
    prefix = marker.get("discovery", {}).get("prefix", "aw")
    words = entry_name(name, package)[len(prefix) + 1:].split("-")
    title = " ".join(word.upper() if word in {"ci", "e2e", "pr", "rfc"} else word.capitalize()
                     for word in words)
    return f"interface:\n  display_name: {json.dumps(prefix.upper() + ' ' + title)}\n"

def discovery_file(relative):
    parts = Path(relative).parts
    return any(parts[i:i + 2] in ((".agents", "skills"), (".claude", "skills"))
               for i in range(len(parts) - 1))

def project_files(root: Path, profile: dict) -> dict[str, str]:
    project = Project(root, profile)
    skills = catalog(project)
    template = (package_root() / "templates/adapters/dispatch.py").read_text()
    files = {}
    receipt = read_json(user_data() / "receipt.json", {})
    # A live global install already resolves each project's overrides. Repeating
    # bundled adapters in projects would leave stale names/scripts after a sync.
    linked = (receipt.get("backend") == "linked"
              and Path(receipt.get("source", "")).resolve() == package_root()
              and not (root / ".agent-workflow/runtime/active.json").exists())
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
            public = entry_name(name)
            entry = location / public
            text = f"---\nname: {public}\ndescription: {json.dumps(info['description'])}\n---\n\nRun this skill folder's scripts/dispatch.py with the current project as its working directory. Read the returned effective skill file, then follow its procedure. Project overrides take precedence. Do not use defaults from another project.\n"
            files[(entry / "SKILL.md").as_posix()] = text
            files[(entry / "agents/openai.yaml").as_posix()] = interface_metadata(name)
            files[(entry / "scripts/dispatch.py").as_posix()] = template.replace("SKILL_NAME = None", f"SKILL_NAME = {name!r}")
    return files
