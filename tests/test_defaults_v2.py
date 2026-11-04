"""New-task defaults (#47): permission mode, checkouts, runtime pin, state version, task base and the account guard."""
from tests.helpers import HardeningTest, WorkspaceTest
from plovi import state
from plovi.util import WorkflowError


class StateVersionTests(WorkspaceTest):
    def test_state_version_migrates_forward(self):
        old = {"schema_version": 1, "task": "sample", "status": "failed", "completed": ["implement"]}
        migrated = state.migrate(old)
        self.assertEqual(migrated["state_version"], state.STATE_VERSION)
        self.assertEqual((migrated["attempts"], migrated["delivery"], migrated["stage_evidence"]), ([], {}, {}))
        self.assertEqual(migrated["completed"], ["implement"])
        self.assertIs(state.migrate(migrated), migrated)
        with self.assertRaisesRegex(WorkflowError, "state version 9.*newer plovi"):
            state.migrate({"state_version": 9})


class PermissionDefaultTests(HardeningTest):
    def run_child(self, restricted=False):
        self.default_policy()  # plovi's own defaults: the task's current checkout, no factory.
        if restricted:
            self.policy("execution.unattended_permission_mode", '"restricted"')
        self.save_plan()
        response = self.task_cli("run", self.manifest_path)
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        return state.read(self.project, "sample")

    def test_unattended_uses_profile_permission_mode(self):
        self.fixture([{}])
        saved = self.run_child()
        self.assertEqual((saved["execution"]["permission_mode"], saved["execution"]["permission_source"]),
                         ("trusted", "unattended default (profile)"))
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", self.calls()[0]["argv"])

    def test_restricted_still_selectable(self):
        self.fixture([{}])
        saved = self.run_child(restricted=True)
        self.assertEqual((saved["execution"]["permission_mode"], saved["execution"]["permission_source"]), ("restricted", "policy"))
        self.assertIn("workspace-write", self.calls()[0]["argv"])


class CheckoutAndPinTests(HardeningTest):
    def worktree_task(self):
        self.fixture([{}])
        self.default_policy()
        self.project.profile["repositories"][0]["checkout_strategy"] = "worktree"
        from plovi.util import write_json
        write_json(self.project.config / "project.json", self.project.profile)
        self.git(self.project.root, "add", "."); self.git(self.project.root, "commit", "-m", "Select task worktrees")
        self.plan["repositories"][0]["branch"] = "feature/sample"
        self.save_plan()

    def test_unattended_uses_task_worktree_by_default(self):
        from plovi import factory
        self.worktree_task()
        strategies = factory.strategies(self.project, self.plan, unattended=True)
        self.assertEqual(strategies, {"app": "worktree"})

    def test_factory_opt_in_still_works(self):
        from plovi import factory
        self.worktree_task()
        self.policy("isolation.checkout", '"factory"')
        self.assertEqual(factory.strategies(self.project, self.plan, unattended=True), {"app": "factory"})

    def test_container_requires_factory_checkout(self):
        from plovi import policy
        self.fixture([{}])
        self.default_policy()
        (self.project.root / "plovi.toml").write_text('[isolation]\nmode = "container"\nimage = "plovi/runner:test"\n')
        with self.assertRaisesRegex(WorkflowError, 'Container mode needs isolation.checkout = "factory"'):
            policy.load(self.project)

    def test_new_tasks_unpinned_existing_pins_kept(self):
        from plovi import runtime_pin
        from tests.helpers import PACKAGE
        self.fixture([{}, {}])
        self.plan["repositories"][0]["branch"] = "feature/sample"
        self.save_plan()
        response = self.task_cli("run", self.manifest_path)
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        root = state.directory(self.project, "sample")
        self.assertFalse((root / "runtime.json").exists())
        pinned = runtime_pin.freeze(PACKAGE, self.root / "runtimes")
        from plovi.util import write_json
        write_json(root / "runtime.json", pinned)
        self.assertIsNotNone(runtime_pin.dispatch(self.project, "sample", ["--version"], source=self.root / "elsewhere"))
        self.assertEqual(state.directory(self.project, "sample").joinpath("runtime.json").read_text(),
                         (root / "runtime.json").read_text())

    def test_unpinned_task_follows_installed_runtime(self):
        from unittest.mock import patch
        from plovi import runner
        self.fixture([{"session": "s", "report": {"status": "needs_input", "question": "Keep it?"}}, {}])
        self.assertEqual(runner.run(self.project, self.plan, unattended=False)["status"], "needs_input")
        with patch.object(runner, "__version__", "99.0.0"):
            saved = runner.run(self.project, self.plan, resume=True, answer="Yes", unattended=False)
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(saved["runtime_updates"][0]["to"], "99.0.0")


class TaskBaseTests(WorkspaceTest):
    def configured(self):
        root = self.repo("app")
        self.setup_project(root, {"repositories": [{"id": "app", "path": "."}]})
        self.git(root, "add", "."); self.git(root, "commit", "-m", "Configure fixture")
        return root

    def test_task_start_uses_remote_base(self):
        root = self.configured()
        remote = self.bare_remote("task-base")
        self.git(root, "remote", "add", "origin", str(remote)); self.git(root, "push", "origin", "main")
        pushed = self.git(root, "rev-parse", "HEAD")
        (root / "local.txt").write_text("unpushed\n"); self.git(root, "add", "local.txt"); self.git(root, "commit", "-m", "Unpushed")
        result = self.cli("task", "start", "first", cwd=root)
        import json
        checkout = json.loads(result.stdout)["checkouts"]["app"]
        self.assertEqual(self.git(checkout, "rev-parse", "HEAD"), pushed)
        self.assertFalse((__import__("pathlib").Path(checkout) / "local.txt").exists())

    def test_task_start_falls_back_to_local_base_with_message(self):
        root = self.configured()
        local = self.git(root, "rev-parse", "HEAD")
        result = self.cli("task", "start", "first", cwd=root)
        self.assertIn("Could not fetch origin/main; starting from local main.", result.stderr)
        import json
        self.assertEqual(self.git(json.loads(result.stdout)["checkouts"]["app"], "rev-parse", "HEAD"), local)


class AccountGuardTests(WorkspaceTest):
    def guarded(self):
        import json
        root = self.repo("app")
        project = self.setup_project(root)
        account = self.root / "personal"; account.mkdir()
        (project.config / "local").mkdir(parents=True, exist_ok=True)
        (project.config / "local" / "claude-account.json").write_text(json.dumps({"config_dir": str(account), "email": "me@example.invalid"}))
        return project, root

    def test_account_guard_warns_interactive_blocks_unattended(self):
        import contextlib, io, json, os
        from types import SimpleNamespace
        from unittest.mock import patch
        from plovi import providers
        project, root = self.guarded()
        status = {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "email": "me@example.invalid"}
        os.environ["ANTHROPIC_BASE_URL"] = "https://example.invalid"
        with patch.object(providers, "run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(status))):
            with patch.object(providers, "is_interactive", return_value=False), \
                    self.assertRaisesRegex(WorkflowError, "cannot use credential or backend overrides"):
                providers.claude_environment(project, root)
            warning = io.StringIO()
            with patch.object(providers, "is_interactive", return_value=True), contextlib.redirect_stderr(warning):
                env = providers.claude_environment(project, root)
        self.assertIn("cannot use credential or backend overrides", warning.getvalue())
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], str(self.root / "personal"))
