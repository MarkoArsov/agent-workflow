"""Embedded read-only bootstrap; select a payload before importing its runtime."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys


def bootstrap_read(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def bootstrap_common(path):
    try:
        value = subprocess.check_output(["git", "rev-parse", "--git-common-dir"], cwd=path,
                                        text=True, stderr=subprocess.DEVNULL).strip()
        return (path / value).resolve()
    except (OSError, subprocess.CalledProcessError):
        return None


def bootstrap(start):
    common = bootstrap_common(start)
    search = [start, *start.parents]
    if common:
        original = common.parent
        search += [original, *original.parents]
    base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    global_root = base / "plovi"
    # Legacy state is not moved; receipts and their owned files remain valid.
    if not (global_root / "receipt.json").is_file():
        for name in ("agentflow", "agent-workflow"):
            if (base / name / "receipt.json").is_file():
                global_root = base / name
                break
    project = profile = None
    config = None
    if common:
        for entry in bootstrap_read(global_root / "projects.json", []):
            if str(common) in entry.get("common_dirs", []):
                search.append(Path(entry["root"]))
    for parent in dict.fromkeys(search):
        for folder in (".plovi", ".agentflow"):
            ref = bootstrap_read(parent / folder / "project-ref.json")
            target = (parent / ref["root"]).resolve() if ref else parent
            for target_folder in (".plovi", ".agentflow", ".plovi"):
                data = bootstrap_read(target / target_folder / "project.json")
                if not data:
                    continue
                member = start == target or any(
                    bootstrap_common(target / repo["path"]) == common if common else
                    start.is_relative_to((target / repo["path"]).resolve())
                    for repo in data.get("repositories", []))
                if member:
                    project, profile, config = target, data, target / target_folder
                    break
            if project:
                break
        if project:
            break
    candidates = []
    version = profile["package"]["version"] if profile else None
    if profile:
        candidates.append(config / "runtime/versions" / version)
    active = bootstrap_read(global_root / "active.json", {})
    linked = Path(active["path"]) if active.get("backend") == "linked" else None
    if not profile:
        for parent in search:
            for folder in (".plovi", ".agentflow"):
                local = bootstrap_read(parent / folder / "runtime/active.json", {})
                if local:
                    candidates.append(Path(local["path"]))
    if linked:
        candidates.append(linked)
    if version:
        candidates.append(global_root / "versions" / version)
    elif active:
        candidates.append(Path(active["path"]))
    override = os.environ.get("PLOVI_PACKAGE") or os.environ.get("AGENTFLOW_PACKAGE")
    if override:
        candidates.append(Path(override))
    return project, profile, candidates, linked


def bootstrap_runtime(candidate, profile, linked):
    marker = bootstrap_read(candidate / "workflow-package.json", {})
    if marker.get("name") not in {"plovi", "agentflow"}:
        return None
    compatible_link = candidate == linked and marker.get("schema_version") == (profile["schema_version"] if profile else 1)
    if not (compatible_link or (candidate != linked and (not profile or marker.get("version") == profile["package"]["version"]))):
        return None
    sys.path.insert(0, str(candidate / "runtime"))
    return "agentflow" if marker["name"] == "agentflow" else "plovi"
