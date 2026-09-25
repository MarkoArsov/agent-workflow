from __future__ import annotations
from pathlib import Path
from tests.helpers import WorkspaceTest
from scorebook import git_ops
from scorebook.util import WorkflowError

class GitTests(WorkspaceTest):
    def configured(self, multiple=False, worktrees=False):
        roots = [self.repo("workspace/app"), self.repo("workspace/checks")] if multiple else [self.repo("app")]
        root = roots[0].parent if multiple else roots[0]
        project = self.setup_project(root)
        for repo in project.profile["repositories"]:
            repo["checkout_strategy"] = "worktree" if worktrees and repo["id"] == "app" else "current-checkout"
        for path in roots:
            self.git(path, "add", "."); self.git(path, "commit", "-m", "Configure fixture")
        return project, roots

    def test_selected_worktree_leaves_parked_and_read_only_companion_unchanged(self):
        project, roots = self.configured(multiple=True, worktrees=True)
        heads = [self.git(root, "rev-parse", "HEAD") for root in roots]
        plan = {"task": "sample", "repositories": [
            {"id": "app", "access": "write", "branch": "feature/sample", "paths": ["file.txt"]},
            {"id": "checks", "access": "read"}]}
        paths = git_ops.prepare(project, plan)
        self.assertNotEqual(Path(paths["app"]), roots[0])
        self.assertEqual(Path(paths["checks"]), roots[1])
        from scorebook.project import resolve
        self.assertEqual(resolve(Path(paths["app"])).root, project.root)
        for index, root in enumerate(roots):
            self.assertEqual(self.git(root, "branch", "--show-current"), "main")
            self.assertEqual(self.git(root, "rev-parse", "HEAD"), heads[index])
        before = git_ops.snapshot(project, paths)
        (roots[1] / "unexpected.txt").write_text("read-only write")
        with self.assertRaisesRegex(WorkflowError, "Scope violation"):
            git_ops.guard(before, git_ops.snapshot(project, paths), plan, "implement")

    def test_partial_delivery_resume_and_base_guard_with_local_bare_remotes(self):
        project, roots = self.configured(multiple=True)
        for root in roots:
            self.git(root, "switch", "-c", "feature/sample")
        remote = self.root / "app-remote.git"; remote.mkdir()
        self.git(remote, "init", "--bare")
        self.git(roots[0], "remote", "add", "origin", str(remote))
        plan = {"task": "sample", "_directory": str(self.root),
                "repositories": [{"id": name, "access": "write", "branch": "feature/sample", "paths": ["file.txt"]}
                                 for name in ("app", "checks")],
                "delivery": {"commit_message": "Add verified fixture behavior"}}
        paths = {name: str(root) for name, root in zip(("app", "checks"), roots)}
        state = {"baseline": git_ops.snapshot(project, paths), "checkouts": paths,
                 "initial_dirty": {"app": [], "checks": []}, "delivery": {}}
        for root in roots:
            (root / "file.txt").write_text("new behavior\n")
        saves = []
        with self.assertRaises(WorkflowError):
            git_ops.deliver(project, plan, state, lambda: saves.append(True))
        first = state["delivery"]["app"]["commit"]
        second = state["delivery"]["checks"]["commit"]
        self.assertTrue(state["delivery"]["app"]["pushed"])
        self.assertNotIn("pushed", state["delivery"]["checks"])
        remote2 = self.root / "checks-remote.git"; remote2.mkdir()
        self.git(remote2, "init", "--bare")
        self.git(roots[1], "remote", "add", "origin", str(remote2))
        git_ops.deliver(project, plan, state, lambda: saves.append(True))
        self.assertEqual(state["delivery"]["app"]["commit"], first)
        self.assertEqual(state["delivery"]["checks"]["commit"], second)
        self.assertEqual(self.git(remote, "rev-parse", "refs/heads/feature/sample"), first)
        self.assertEqual(self.git(remote2, "rev-parse", "refs/heads/feature/sample"), second)
        self.git(roots[0], "switch", "main")
        with self.assertRaisesRegex(WorkflowError, "base branch"):
            git_ops.deliver(project, plan, state, lambda: None)

    def test_base_sync_fast_forward_and_dirty_guard(self):
        project, roots = self.configured()
        root = roots[0]
        remote = self.root / "remote.git"; remote.mkdir(); self.git(remote, "init", "--bare")
        self.git(root, "remote", "add", "origin", str(remote))
        self.git(root, "push", "origin", "main")
        peer = self.root / "peer"
        self.git(self.root, "clone", "-b", "main", str(remote), str(peer))
        (peer / "new.txt").write_text("upstream")
        self.git(peer, "add", "."); self.git(peer, "commit", "-m", "Upstream change"); self.git(peer, "push", "origin", "main")
        git_ops.sync_base(project, ["app"])
        self.assertEqual(self.git(root, "rev-parse", "HEAD"), self.git(peer, "rev-parse", "HEAD"))
        (root / "README.md").write_text("user edit")
        with self.assertRaisesRegex(WorkflowError, "clean"):
            git_ops.sync_base(project, ["app"])

    def test_provider_cannot_stage_changes_behind_runner_delivery(self):
        project, roots = self.configured()
        plan = {"repositories": [{"id": "app", "access": "write", "paths": ["file.txt"]}]}
        before = git_ops.snapshot(project)
        (roots[0] / "file.txt").write_text("within file scope")
        self.git(roots[0], "add", "file.txt")
        with self.assertRaisesRegex(WorkflowError, "Git index"):
            git_ops.guard(before, git_ops.snapshot(project), plan, "implement")
