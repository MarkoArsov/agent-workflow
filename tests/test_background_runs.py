"""Background runs keep the plan branch, preflight never allocates, and plans can name commands (G1-G3)."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from tests.helpers import HardeningTest


class BackgroundRunTests(HardeningTest):
    def factory_project(self, name):
        bare = self.bare_remote(name)
        self.seed_remote(bare)
        working = self.clone_repo(bare, "app")
        project = self.setup_project(working, patch={
            "repositories": [{"id": "app", "path": ".", "checkout_strategy": "worktree", "base_branch": "main"}]})
        self.git(working, "add", ".")
        self.git(working, "commit", "-m", "Configure project")
        self.git(working, "push", "origin", "main")
        return project, working

    def start_task(self, project, task):
        from plovi import tasks
        started = tasks.start(project, task)
        checkout = Path(started["checkouts"]["app"])
        plan = checkout / project.profile["planning"]["directory"] / task / "pipeline.json"
        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text('{"task": "%s"}\n' % task)
        return checkout, plan

    def commit_plan(self, checkout):
        self.git(checkout, "add", ".")
        self.git(checkout, "commit", "-m", "Plan the task")
        return self.git(checkout, "rev-parse", "HEAD")

    def factory_root(self, project):
        from plovi.util import user_data
        return user_data() / "projects" / project.profile["project"]["id"]

    def test_factory_branch_includes_task_branch_plan_commits(self):
        from plovi import factory
        project, _ = self.factory_project("plan-branch")
        checkout, plan = self.start_task(project, "plan-task")
        head = self.commit_plan(checkout)
        (checkout / "scratch.txt").write_text("not committed\n")
        result = factory.allocate(project, "plan-task", unattended=True)
        allocated = Path(result["app"])
        self.assertEqual(self.git(allocated, "rev-parse", "HEAD"), head, "the factory branch starts at the task branch")
        self.assertTrue((allocated / plan.relative_to(checkout)).exists(), "planning commits reach the factory branch")
        self.assertFalse((allocated / "scratch.txt").exists(), "uncommitted files are never copied")
        row = json.loads(factory.receipt_path(project, "plan-task").read_text())["repositories"][0]
        self.assertEqual(row.get("task_head"), head)
        self.assertEqual(row.get("source"), "task-branch")

    def test_factory_refuses_task_branch_not_descending_from_base(self):
        from plovi import factory
        from plovi.util import WorkflowError
        project, working = self.factory_project("local-base")
        self.git(working, "commit", "--allow-empty", "-m", "Local commit that was never pushed")
        checkout, _ = self.start_task(project, "local-task")
        self.commit_plan(checkout)
        with self.assertRaises(WorkflowError) as raised:
            factory.allocate(project, "local-task", unattended=True)
        self.assertIn("origin/main", str(raised.exception))
        self.assertFalse(factory.receipt_path(project, "local-task").exists())

    def test_factory_refuses_uncommitted_plan(self):
        from plovi import factory
        from plovi.util import WorkflowError
        project, _ = self.factory_project("dirty-plan")
        self.start_task(project, "dirty-task")
        with self.assertRaises(WorkflowError) as raised:
            factory.allocate(project, "dirty-task", unattended=True)
        self.assertIn("commit the plan", str(raised.exception).lower())

    def test_preflight_and_dry_run_never_allocate(self):
        self.fixture([{}], stages=["implement"])
        self.plan["repositories"][0]["branch"] = "feature/sample"
        self.save_plan()
        allocations = self.factory_root(self.project)
        for args in (("preflight", self.manifest_path), ("run", self.manifest_path, "--dry-run")):
            with self.subTest(command=args[0]):
                response = self.task_cli(*args)
                self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
                self.assertFalse((allocations / "allocations" / "sample.json").exists(), "no receipt is written")
                self.assertFalse((allocations / "worktrees" / "sample").exists(), "no worktree is created")
                self.assertIn("factory", response.stdout, "the report names the strategy a run would use")

    def test_receipt_root_mismatch_names_recorded_root(self):
        from plovi import factory
        from plovi.util import WorkflowError
        project, _ = self.factory_project("root-mismatch")
        factory.allocate(project, "moved", unattended=True)
        path = factory.receipt_path(project, "moved")
        saved = json.loads(path.read_text())
        recorded = str(self.root / "elsewhere" / "project")
        saved["configuration_root"] = recorded
        path.write_text(json.dumps(saved))
        with self.assertRaises(WorkflowError) as raised:
            factory.receipt(project, "moved")
        self.assertIn(recorded, str(raised.exception))
        self.assertIn("--project", str(raised.exception))

    def test_restricted_mode_allows_plan_named_commands(self):
        from plovi import manifest, policy
        self.fixture([{}], stages=["implement"])
        self.plan["allowed_commands"] = [{"argv": ["python3", "scripts/generate_docs.py"]},
                                         {"argv": ["python3", "scripts/generate_plugin_skills.py"], "cwd": "."}]
        self.save_plan()
        loaded = manifest.load(self.manifest_path, self.project)
        self.assertEqual(len(loaded["allowed_commands"]), 2)
        with_claude = copy.deepcopy(loaded)
        with_claude["routes"] = {"default": [{"provider": "claude", "model": "fixture"}]}
        execution = policy.execution(self.project, with_claude, unattended=True)
        self.assertEqual(execution["permission_mode"], "restricted")
        tools = execution["provider_settings"]["claude"]["allowed_tools"]
        self.assertIn("Bash(python3 scripts/generate_docs.py)", tools)
        self.assertIn("Bash(python3 scripts/generate_plugin_skills.py)", tools)
        trusted = policy.execution(self.project, with_claude, trusted=True)
        self.assertNotIn("allowed_tools", trusted.get("provider_settings", {}).get("claude", {}))

    def test_allowed_commands_rejects_unsafe_argv(self):
        from plovi import manifest
        from plovi.util import WorkflowError
        self.fixture([{}], stages=["implement"])
        for value in ([{"argv": ["sh", "-c", "rm -rf build"]}], [{"argv": []}], [{"cwd": "."}],
                      [{"argv": ["python3", "x.py"], "cwd": "../outside"}], {"argv": ["python3"]}):
            with self.subTest(value=value):
                plan = copy.deepcopy({k: v for k, v in self.plan.items() if not k.startswith("_")})
                plan["allowed_commands"] = value
                with self.assertRaises(WorkflowError):
                    manifest.validate(plan, self.project)

    def test_resumed_worker_never_republishes_previous_stop(self):
        """A launcher waits for the new run ID; the first save carrying it must not show the old stop."""
        from unittest import mock
        from plovi import runner, state
        self.fixture([{}], stages=["implement"])
        saved = runner.run(self.project, self.plan, unattended=False)
        saved.update(status="interrupted", completed=[], active_stage="implement",
                     stage_before=saved["baseline"], stage_evidence={}, run_id="previous-run")
        state.save(state.directory(self.project, "sample"), saved)
        seen = []
        original = state.save
        def record(root, value, **kwargs):
            seen.append((value.get("run_id"), value.get("status")))
            return original(root, value, **kwargs)
        with mock.patch.object(state, "save", record):
            result = runner.run(self.project, self.plan, resume=True, unattended=False)
        self.assertEqual(result["status"], "complete")
        first = next(status for run_id, status in seen if run_id != "previous-run")
        self.assertNotEqual(first, "interrupted")

    def test_stop_status_is_published_after_the_ledger(self):
        """state.json is the last write of a run: anyone who sees its stop status sees the whole run."""
        from unittest import mock
        from plovi import ledger, runner, state
        self.fixture([{}], stages=["implement"])
        seen = []
        original = state.publish
        def record(root, value):
            seen.append((value.get("status"), [e["type"] for e in ledger.events(self.project)]))
            return original(root, value)
        with mock.patch.object(state, "publish", record):
            result = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(result["status"], "complete")
        status, recorded = seen[-1]
        self.assertEqual(status, "complete")
        self.assertIn("run.finished", recorded, "the ledger records the stop before state.json shows it")
        self.assertEqual(recorded[-1], "state.checkpoint", "the final checkpoint precedes state.json")
