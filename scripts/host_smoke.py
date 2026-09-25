#!/usr/bin/env python3
"""Optional installed-host checks in a disposable home. No model generation or account actions."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
from scorebook.install import files_in

def main():
    results = []
    with tempfile.TemporaryDirectory(prefix="workflow-host-smoke-") as temporary:
        root = Path(temporary)
        home = root / "home"; home.mkdir()
        source = root / "package"
        for file in files_in(ROOT):
            target = source / file.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target)
        env = {"PATH": os.environ["PATH"], "HOME": str(home), "CLAUDE_CONFIG_DIR": str(home / "claude"),
               "CODEX_HOME": str(home / "codex"), "XDG_CONFIG_HOME": str(home / "config"),
               "XDG_DATA_HOME": str(home / "data"), "XDG_CACHE_HOME": str(home / "cache"),
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        def run(label, argv):
            try:
                result = subprocess.run(argv, cwd=root, env=env, text=True, capture_output=True, timeout=40)
                results.append({"check": label, "exit_code": result.returncode,
                                "output": (result.stdout + result.stderr).replace(str(root), "<temporary>")})
                return result.returncode == 0
            except subprocess.TimeoutExpired:
                results.append({"check": label, "exit_code": None, "output": "timed out"})
                return False
        for binary, args in (("codex", ["exec", "--help"]), ("claude", ["--help"]), ("agent", ["--help"])):
            if shutil.which(binary):
                run(binary + " command interface", [binary, *args])
            else:
                results.append({"check": binary + " command interface", "exit_code": None, "output": "not installed"})
        if shutil.which("claude"):
            run("marketplace strict validation", ["claude", "plugin", "validate", "--strict", str(source / ".claude-plugin/marketplace.json")])
            run("plugin strict validation", ["claude", "plugin", "validate", "--strict", str(source / ".claude-plugin/plugin.json")])
            added = run("local marketplace add", ["claude", "plugin", "marketplace", "add", str(source)])
            if added:
                installed = run("native install", ["claude", "plugin", "install", "scorebook@scorebook", "--scope", "user"])
                if installed:
                    run("native list", ["claude", "plugin", "list", "--json"])
                    run("native details", ["claude", "plugin", "details", "scorebook@scorebook"])
                    run("native update", ["claude", "plugin", "update", "scorebook@scorebook", "--scope", "user"])
                    run("native uninstall", ["claude", "plugin", "uninstall", "scorebook@scorebook", "--scope", "user"])
        print(json.dumps(results, indent=2))
    return 1 if any(row["exit_code"] not in (0, None) for row in results) else 0

if __name__ == "__main__":
    raise SystemExit(main())
