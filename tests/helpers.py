from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "runtime"))

class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="workflow-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.home), "XDG_DATA_HOME": str(self.home / "data"),
                    "XDG_CONFIG_HOME": str(self.home / "config"), "XDG_CACHE_HOME": str(self.home / "cache"),
                    "CODEX_HOME": str(self.home / "codex"), "CLAUDE_CONFIG_DIR": str(self.home / "claude"),
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                    "PYTHONDONTWRITEBYTECODE": "1", "STAGEWAY_PACKAGE": str(PACKAGE)}
        self.patch = unittest.mock.patch.dict(os.environ, self.env, clear=True)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def git(self, root, *args, check=True):
        return subprocess.run(["git", "-C", str(root), *args], env=self.env, text=True, capture_output=True, check=check).stdout.strip()

    def repo(self, name):
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        self.git(path, "init", "-b", "main")
        (path / "README.md").write_text("# Fixture\n")
        self.git(path, "add", ".")
        self.git(path, "commit", "-m", "Initialize fixture")
        return path

    def setup_project(self, path, patch=None):
        from stageway.setup import apply, propose
        p = propose(path, {"confirmed_defaults": True, "profile": patch or {}})
        apply(p, p["approval"])
        from stageway.project import load
        return load(path)

    def cli(self, *args, cwd=None, check=True):
        return subprocess.run([sys.executable, str(PACKAGE / "bin/stageway"), *map(str, args)],
                              cwd=cwd or PACKAGE, env=self.env, text=True, capture_output=True, check=check)

import unittest.mock
