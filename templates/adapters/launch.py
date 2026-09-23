#!/usr/bin/env python3
"""Version-selecting launcher; payloads and project extensions remain separate."""
import json
import os
import subprocess
import sys
from pathlib import Path

LOCAL_RUNTIME = None
start = Path.cwd().resolve()
args = sys.argv[1:]
if "--project" in args:
    index = args.index("--project")
    if index + 1 < len(args):
        start = Path(args[index + 1]).expanduser().resolve()
global_root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "agent-workflow"
profile = None
project = None
candidates = []
search = [start, *start.parents]
try:
    common = subprocess.check_output(["git", "rev-parse", "--git-common-dir"], cwd=start, text=True, stderr=subprocess.DEVNULL).strip()
    original = (start / common).resolve().parent
    search += [original, *original.parents]
except (OSError, subprocess.CalledProcessError):
    pass
for parent in search:
    ref = parent / ".agent-workflow/project-ref.json"
    target = (parent / json.loads(ref.read_text())["root"]).resolve() if ref.is_file() else parent
    marker = target / ".agent-workflow/project.json"
    if marker.is_file():
        profile = json.loads(marker.read_text()); project = target; break
if profile:
    version = profile["package"]["version"]
    candidates += [project / ".agent-workflow/runtime/versions" / version, global_root / "versions" / version]
else:
    for root in [LOCAL_RUNTIME, *(p / ".agent-workflow/runtime" for p in search), global_root]:
        if root and (root / "active.json").is_file():
            candidates.append(Path(json.loads((root / "active.json").read_text())["path"]))
if os.environ.get("AGENT_WORKFLOW_PACKAGE"):
    candidates.append(Path(os.environ["AGENT_WORKFLOW_PACKAGE"]))
for candidate in candidates:
    marker = candidate / "workflow-package.json"
    if marker.is_file() and (not profile or json.loads(marker.read_text())["version"] == profile["package"]["version"]):
        sys.path.insert(0, str(candidate / "runtime"))
        from agent_workflow.cli import main
        raise SystemExit(main(args))
raise SystemExit("No matching workflow package. Install the project's pinned version, or install globally before setup.")

