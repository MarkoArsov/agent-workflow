"""Factory checkout tests: isolated mirrors, unattended runs, delivery, and cleanup.

All tests use guarded factory imports so import failures produce FAIL/AssertionError,
not ImportError. No network, real accounts, or real container engines.
"""
from __future__ import annotations
import subprocess
import sys
import time
from pathlib import Path
from tests.helpers import PACKAGE, WorkspaceTest


class FactoryCheckoutTests(WorkspaceTest):

    # ---- helpers -----------------------------------------------------------

    def _require_factory(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec("plovi.factory"), "plovi.factory module not yet implemented")
        from plovi import factory
        return factory

    def _bare_remote(self, name):
        return self.bare_remote(name)

    def _seed_remote(self, bare, filename="README.md", content="# Fixture\n"):
        return self.seed_remote(bare, filename, content)

    def _clone(self, bare, name):
        return self.clone_repo(bare, name)

    def _setup_with_remote(self, bare):
        """Create a project whose repository has origin pointing at bare."""
        # Clone directory is named "app" so repository auto-detection assigns the
        # same id as the patched repository, instead of registering it twice
        # under two ids with the same path.
        working = self._clone(bare, "app")
        project = self.setup_project(working, patch={
            "repositories": [{"id": "app", "path": ".", "checkout_strategy": "worktree", "base_branch": "main"}],
        })
        # Commit project config back to the clone (not required by all tests but harmless)
        self.git(working, "add", ".", check=False)
        self.git(working, "commit", "-m", "Configure project", check=False)
        return project, working

    def _advance_remote(self, bare, message="New remote commit"):
        """Advance the bare remote's default branch through a writable clone and push.

        Bare repositories have no working tree, so committing directly against one
        fails; this clones, commits, and pushes back instead.
        """
        tmp = self.root / f"tmp-advance-{bare.stem}"
        subprocess.run(
            ["git", "clone", str(bare), str(tmp)],
            env=self.env, check=True, capture_output=True, text=True,
        )
        self.git(tmp, "commit", "--allow-empty", "-m", message)
        self.git(tmp, "push", "origin", "HEAD")
        import shutil
        shutil.rmtree(tmp)
        return self.git(bare, "rev-parse", "refs/heads/main")

    def _checkout_path(self, result, repo_id="app"):
        if isinstance(result, dict):
            return Path(result[repo_id])
        return Path(result)

    def _record_state(self, project, task, status):
        from plovi import state as state_mod
        state_root = state_mod.directory(project, task)
        state_root.mkdir(parents=True, exist_ok=True)
        state_mod.save(state_root, {"status": status, "task": task})

    # ---- red check ---------------------------------------------------------

    def test_unattended_ignores_dirty_user_clone(self):
        """Unattended factory allocation must not fail when the user clone is dirty."""
        factory = self._require_factory()
        bare = self._bare_remote("ign-dirty")
        self._seed_remote(bare)
        project, working = self._setup_with_remote(bare)

        # Make the user clone dirty (uncommitted changes and branch switch)
        (working / "unsaved.txt").write_text("work in progress")
        self.git(working, "checkout", "-b", "feature/user-work")

        # Factory allocation for an unattended run must succeed despite the dirty clone
        self.assertTrue(hasattr(factory, "allocate"), "factory.allocate must be implemented")
        result = factory.allocate(project, "task-alpha", unattended=True)
        self.assertIsNotNone(result, "Factory allocation must return a checkout path or mapping")

        # Factory checkout must track remote HEAD, not dirty user clone state
        checkout = self._checkout_path(result)
        remote_head = self.git(bare, "rev-parse", "refs/heads/main")
        factory_head = self.git(checkout, "rev-parse", "HEAD")
        self.assertEqual(factory_head, remote_head,
                         "Factory checkout must be at remote HEAD, ignoring user clone state")

        # Dirty user-clone file must not appear in the factory worktree
        self.assertFalse((checkout / "unsaved.txt").exists(),
                         "Dirty user-clone file must not appear in factory checkout")

    # ---- green checks ------------------------------------------------------

    def test_user_clone_can_change_mid_run(self):
        """User clone branch and content changes during a run must not affect the factory run."""
        factory = self._require_factory()
        bare = self._bare_remote("midrun")
        self._seed_remote(bare)
        project, working = self._setup_with_remote(bare)

        result = factory.allocate(project, "task-midrun", unattended=True)
        checkout = self._checkout_path(result)
        factory_head_before = self.git(checkout, "rev-parse", "HEAD")

        # Simulate user editing the clone mid-run
        (working / "mid-run.txt").write_text("user edit mid-run")
        self.git(working, "add", ".")
        self.git(working, "commit", "-m", "User mid-run commit")
        self.git(working, "checkout", "-b", "user/feature")

        # Factory checkout must be unaffected
        factory_head_after = self.git(checkout, "rev-parse", "HEAD")
        self.assertEqual(factory_head_before, factory_head_after,
                         "Factory checkout HEAD must not change when user clone changes mid-run")
        self.assertFalse((checkout / "mid-run.txt").exists(),
                         "User mid-run file must not appear in factory checkout")

    def test_next_task_refreshes_remote_base(self):
        """Factory mirror must be refreshed with new remote commits before each new task."""
        factory = self._require_factory()
        bare = self._bare_remote("refresh-base")
        self._seed_remote(bare)
        project, _ = self._setup_with_remote(bare)

        # First allocation
        factory.allocate(project, "task-one", unattended=True)
        first_remote = self.git(bare, "rev-parse", "refs/heads/main")

        # Add a new commit to the remote (bypassing user clone), advanced through
        # a writable clone since the bare remote has no working tree of its own.
        second_remote = self._advance_remote(bare, "New remote commit")
        self.assertNotEqual(first_remote, second_remote)

        # Second allocation must start from the refreshed remote base
        result_two = factory.allocate(project, "task-two", unattended=True)
        checkout_two = self._checkout_path(result_two)
        self.assertEqual(
            self.git(checkout_two, "rev-parse", "HEAD"), second_remote,
            "Second task allocation must start from refreshed remote HEAD",
        )

    def test_factory_pushes_real_remote(self):
        """Factory push must target the real remote URL, not the mirror's origin."""
        factory = self._require_factory()
        bare = self._bare_remote("push-target")
        self._seed_remote(bare)
        project, _ = self._setup_with_remote(bare)

        result = factory.allocate(project, "task-push", unattended=True)
        checkout = self._checkout_path(result)
        branch = "codex/task-push"
        self.git(checkout, "checkout", "-b", branch)
        (checkout / "change.txt").write_text("delivered")
        self.git(checkout, "add", ".")
        self.git(checkout, "commit", "-m", "Deliver task change")
        task_commit = self.git(checkout, "rev-parse", "HEAD")

        self.assertTrue(hasattr(factory, "push"), "factory.push must be implemented")
        factory.push(project, "task-push", "app", branch)

        # Commit must now be visible in the real remote
        pushed = self.git(bare, "rev-parse", f"refs/heads/{branch}")
        self.assertEqual(pushed, task_commit, "factory.push must deliver to the real remote")

    def test_read_companion_uses_factory_base(self):
        """Read-only companion checkout must come from the factory mirror, not the user clone."""
        factory = self._require_factory()
        primary_bare = self._bare_remote("primary")
        companion_bare = self._bare_remote("companion")
        self._seed_remote(primary_bare)
        self._seed_remote(companion_bare, filename="docs.txt", content="Docs fixture\n")

        # Clone both repositories under a shared parent so the explicit "primary"/
        # "companion" ids and paths match what repository auto-detection assigns
        # from the directory names, instead of colliding with a second detected
        # entry at the same path or registering a path outside the project root.
        (self.root / "multi").mkdir()
        primary_working = self._clone(primary_bare, "multi/primary")
        # User has a companion clone with local edits not in the remote
        companion_user = self._clone(companion_bare, "multi/companion")
        (companion_user / "user-only.txt").write_text("user local edit")

        project = self.setup_project(primary_working.parent, patch={
            "repositories": [
                {"id": "primary", "path": "primary", "checkout_strategy": "worktree", "base_branch": "main"},
                {"id": "companion", "path": "companion", "checkout_strategy": "worktree",
                 "base_branch": "main"},
            ],
        })
        result = factory.allocate(project, "task-multi", unattended=True)
        checkouts = result if isinstance(result, dict) else {"primary": result}

        companion_checkout = Path(checkouts.get("companion", ""))
        if companion_checkout.is_dir():
            self.assertFalse(
                (companion_checkout / "user-only.txt").exists(),
                "Companion factory checkout must not contain user-only local edits",
            )
            remote_head = self.git(companion_bare, "rev-parse", "refs/heads/main")
            companion_head = self.git(companion_checkout, "rev-parse", "HEAD")
            self.assertEqual(companion_head, remote_head,
                             "Companion checkout must be at the remote HEAD, not user clone HEAD")

    def test_clean_keeps_active_dirty_and_unfinished(self):
        """clean must not remove active, dirty, or non-terminal worktrees."""
        factory = self._require_factory()
        bare = self._bare_remote("clean-safe")
        self._seed_remote(bare)
        project, _ = self._setup_with_remote(bare)

        result = factory.allocate(project, "task-active", unattended=True)
        checkout = self._checkout_path(result)

        # Make the checkout dirty (uncommitted changes, no terminal state recorded)
        (checkout / "wip.txt").write_text("work in progress")

        self.assertTrue(hasattr(factory, "clean"), "factory.clean must be implemented")
        removed = factory.clean(project) or []

        self.assertTrue(checkout.is_dir(), "Dirty in-progress checkout must not be removed")
        self.assertNotIn(str(checkout), [str(r) for r in removed],
                         "Active dirty checkout must not appear in clean removal list")

    def test_clean_removes_owned_terminal_worktrees(self):
        """clean must remove owned, unlocked, clean worktrees of cancelled tasks."""
        factory = self._require_factory()
        bare = self._bare_remote("clean-terminal")
        self._seed_remote(bare)
        project, _ = self._setup_with_remote(bare)

        result = factory.allocate(project, "task-cancelled", unattended=True)
        checkout = self._checkout_path(result)

        # Record task as cancelled in state
        self._record_state(project, "task-cancelled", "cancelled")

        removed = factory.clean(project) or []

        # Cancelled owned worktree should be removed
        removed_strs = [str(r) for r in removed]
        self.assertTrue(
            not checkout.is_dir() or str(checkout) in removed_strs,
            f"Cancelled task worktree must be removed by clean; still exists at {checkout}",
        )

    def test_remote_identity_mismatch_refused(self):
        """Factory must refuse allocation if the project's remote URL changed since registration."""
        factory = self._require_factory()
        bare_a = self._bare_remote("id-remote-a")
        bare_b = self._bare_remote("id-remote-b")
        self._seed_remote(bare_a)
        self._seed_remote(bare_b)
        project, _ = self._setup_with_remote(bare_a)

        # First allocation registers bare_a as the canonical remote for this project+repo
        factory.allocate(project, "task-first", unattended=True)

        # Simulate remote URL change by modifying the profile in-memory
        project.profile["repositories"][0]["path"] = str(bare_b)

        from plovi.util import WorkflowError
        with self.assertRaises(WorkflowError,
                               msg="Changed remote URL must be refused before allocation"):
            factory.allocate(project, "task-second", unattended=True)

    def test_refresh_preserves_active_task_branch(self):
        """Mirror refresh must not overwrite task branches in active worktrees."""
        factory = self._require_factory()
        bare = self._bare_remote("refresh-safe")
        self._seed_remote(bare)
        project, _ = self._setup_with_remote(bare)

        result = factory.allocate(project, "task-refresh", unattended=True)
        checkout = self._checkout_path(result)

        # Establish a task branch with a commit
        self.git(checkout, "checkout", "-b", "codex/task-refresh")
        (checkout / "task-work.txt").write_text("task progress")
        self.git(checkout, "add", ".")
        self.git(checkout, "commit", "-m", "Task progress commit")
        task_commit = self.git(checkout, "rev-parse", "HEAD")

        # Add a new commit to remote and refresh, advanced through a writable
        # clone since the bare remote has no working tree of its own.
        self._advance_remote(bare, "New remote commit")
        self.assertTrue(hasattr(factory, "refresh"), "factory.refresh must be implemented")
        factory.refresh(project, "app")

        # Task branch commit in the worktree must survive the mirror refresh
        checkout_head = self.git(checkout, "rev-parse", "HEAD")
        self.assertEqual(checkout_head, task_commit,
                         "Task branch commit must survive factory mirror refresh")

    def test_resume_reuses_factory_allocation(self):
        """Resuming an existing task must reuse its allocation, not create a new worktree."""
        factory = self._require_factory()
        bare = self._bare_remote("resume")
        self._seed_remote(bare)
        project, _ = self._setup_with_remote(bare)

        first = self._checkout_path(factory.allocate(project, "task-resume", unattended=True))
        second = self._checkout_path(factory.allocate(project, "task-resume", unattended=True))

        self.assertEqual(str(first), str(second),
                         "Resuming the same task must reuse the existing factory allocation")

    def test_interactive_preserves_profile_strategy(self):
        """Interactive runs must use the profile's configured strategy, not factory mirrors."""
        factory = self._require_factory()
        bare = self._bare_remote("interactive")
        self._seed_remote(bare)
        project, _ = self._setup_with_remote(bare)

        factory_result = factory.allocate(project, "task-factory", unattended=True)
        interactive_result = factory.allocate(project, "task-interactive", unattended=False)

        factory_path = str(self._checkout_path(factory_result))
        interactive_path = str(self._checkout_path(interactive_result))

        # Factory path is under user_data; interactive path is under project worktree dir
        from plovi.util import user_data
        self.assertTrue(
            factory_path.startswith(str(user_data())),
            f"Factory allocation must be under user_data: {factory_path}",
        )
        self.assertFalse(
            interactive_path.startswith(str(user_data())),
            f"Interactive allocation must use profile strategy (not factory): {interactive_path}",
        )
