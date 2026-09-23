from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path
from tests.helpers import PACKAGE, WorkspaceTest
from agent_workflow.project import resolve
from agent_workflow.setup import propose, apply
from agent_workflow.util import WorkflowError

class ResolutionTests(WorkspaceTest):
    def test_spaces_symlink_moved_parent_and_committed_worktree_reference(self):
        app = self.repo("workspace with spaces/app")
        checks = self.repo("workspace with spaces/checks")
        project = self.setup_project(app.parent)
        for repo in (app, checks):
            self.git(repo, "add", "."); self.git(repo, "commit", "-m", "Configure project")
        moved = self.root / "moved project"
        app.parent.rename(moved)
        app = moved / "app"
        nested = app / "nested"; nested.mkdir()
        link = self.root / "alias"; link.symlink_to(moved, target_is_directory=True)
        self.assertEqual(resolve(link / "app/nested").root, moved)
        worktree = self.root / "external task checkout"
        self.git(app, "worktree", "add", "-b", "feature/sample", str(worktree))
        self.assertEqual(resolve(worktree).root, moved)
        result = subprocess.run([sys.executable, str(worktree / ".agents/skills/aw-review/scripts/dispatch.py")],
                                cwd=worktree, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), PACKAGE / "skills/review/SKILL.md")

    def test_setup_refuses_unowned_adapter_and_removes_only_unchanged_disabled_host_entries(self):
        root = self.repo("app")
        collision = root / ".agents/skills/aw-review/SKILL.md"
        collision.parent.mkdir(parents=True); collision.write_text("unrelated user-owned skill")
        p = propose(root, {"confirmed_defaults": True})
        self.assertTrue(p["conflicts"])
        with self.assertRaisesRegex(WorkflowError, "conflicts"):
            apply(p, p["approval"])
        self.assertEqual(collision.read_text(), "unrelated user-owned skill")
        collision.unlink()
        project = self.setup_project(root)
        modified = root / ".claude/skills/aw-review/SKILL.md"
        modified.write_text("custom adapter")
        p = propose(root, {"confirmed_defaults": True, "profile": {"agents": ["codex"]}})
        apply(p, p["approval"])
        self.assertFalse((root / ".claude/skills/aw-specify/SKILL.md").exists())
        self.assertEqual(modified.read_text(), "custom adapter")
