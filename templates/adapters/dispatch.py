#!/usr/bin/env python3
"""Owned discovery wrapper. Project skill bodies are never stored here."""
from pathlib import Path
import json
import os
import subprocess
import sys

SKILL_NAME = None
start = Path.cwd().resolve()
project = None
for parent in [start, *start.parents]:
    ref = parent / ".agentflow/project-ref.json"
    profile = parent / ".agentflow/project.json"
    if ref.is_file():
        target = (parent / json.loads(ref.read_text())["root"]).resolve()
        if (target / ".agentflow/project.json").is_file():
            project = target
            break
    if profile.is_file():
        project = parent
        break
if project is None:
    try:
        common = subprocess.check_output(["git", "rev-parse", "--git-common-dir"], cwd=start, text=True, stderr=subprocess.DEVNULL).strip()
        original = (start / common).resolve().parent
        for parent in [original, *original.parents]:
            if (parent / ".agentflow/project.json").is_file():
                project = parent
                break
    except (OSError, subprocess.CalledProcessError):
        pass
version = None
if project:
    data = json.loads((project / ".agentflow/project.json").read_text())
    version = data["package"]["version"]
global_root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "agentflow"
legacy_root = global_root.with_name("agent-workflow")
if not (global_root / "active.json").exists() and (legacy_root / "active.json").is_file():
    legacy_active = json.loads((legacy_root / "active.json").read_text())
    if legacy_active.get("backend") == "linked":
        global_root = legacy_root
candidates = []
if project and version:
    candidates.append(project / ".agentflow/runtime/versions" / version)
active = global_root / "active.json"
active_data = json.loads(active.read_text()) if active.is_file() else {}
linked = Path(active_data["path"]) if active_data.get("backend") == "linked" else None
if not version:
    for parent in [start, *start.parents]:
        local_active = parent / ".agentflow/runtime/active.json"
        if local_active.is_file():
            candidates.append(Path(json.loads(local_active.read_text())["path"]))
if linked:
    candidates.append(linked)
if version:
    candidates.append(global_root / "versions" / version)
if not version and active.is_file():
    candidates.append(Path(json.loads(active.read_text())["path"]))
# An explicitly provided package is useful for development and native plugin entry points.
if os.environ.get("AGENTFLOW_PACKAGE"):
    candidates.append(Path(os.environ["AGENTFLOW_PACKAGE"]))
for candidate in candidates:
    marker = candidate / "workflow-package.json"
    package = json.loads(marker.read_text()) if marker.is_file() else {}
    compatible_link = candidate == linked and package.get("schema_version") == (data["schema_version"] if project else 1)
    if package and (compatible_link or (candidate != linked and (not version or package["version"] == version))):
        sys.path.insert(0, str(candidate / "runtime"))
        from agentflow.project import resolve
        from agentflow.extensions import resolve_skill
        from agentflow.util import WorkflowError
        try:
            context = resolve(start)
        except WorkflowError:
            if SKILL_NAME not in {"project-setup", "setup", "update-models", "publish-workflow"}:
                raise
            context = None
        print(resolve_skill(SKILL_NAME, context, candidate))
        break
else:
    raise SystemExit("No matching workflow runtime. Install the project's pinned version or run project-setup after a global installation.")
