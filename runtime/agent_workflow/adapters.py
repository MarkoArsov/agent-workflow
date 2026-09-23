"""Portable native-host entry points; all delegate to one project resolver."""
from __future__ import annotations
from pathlib import Path
import json
from .extensions import catalog
from .project import Project
from .util import contained, package_root

def project_files(root: Path, profile: dict) -> dict[str, str]:
    project = Project(root, profile)
    skills = catalog(project)
    template = (package_root() / "templates/adapters/dispatch.py").read_text()
    files = {}
    locations = []
    for repo in profile["repositories"]:
        prefix = Path(repo["path"])
        if set(profile["agents"]) & {"codex", "cursor"}:
            locations.append(prefix / ".agents/skills")
        if "claude" in profile["agents"]:
            locations.append(prefix / ".claude/skills")
    for location in locations:
        for name, info in skills.items():
            entry = location / ("aw-" + name)
            text = f"---\nname: aw-{name}\ndescription: {json.dumps(info['description'])}\n---\n\nRun this skill folder's scripts/dispatch.py with the current project as its working directory. Read the returned effective skill file, then follow its procedure. Project overrides take precedence. Do not use defaults from another project.\n"
            files[(entry / "SKILL.md").as_posix()] = text
            files[(entry / "scripts/dispatch.py").as_posix()] = template.replace("SKILL_NAME = None", f"SKILL_NAME = {name!r}")
    return files
