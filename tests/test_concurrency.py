import json
import socket
import subprocess
import sys
from pathlib import Path
from tests.helpers import HardeningTest, PACKAGE
from plovi import state
from plovi.util import write_json


class ConcurrencyTests(HardeningTest):
    def launch(self, path, *flags):
        process = subprocess.Popen([sys.executable, str(PACKAGE / "bin/plovi"), "--project", str(self.project.root),
                                    "run", str(path), *flags], env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=20)
        self.addCleanup(cleanup)
        return process

    def barrier(self):
        server = socket.socket(); server.bind(("127.0.0.1", 0)); server.listen(2); server.settimeout(10)
        self.addCleanup(server.close)
        return server

    def accept(self, server):
        try:
            connection, _ = server.accept()
        except TimeoutError:
            self.fail("Both providers must become active before either is released")
        connection.settimeout(10)
        self.addCleanup(connection.close)
        connection.recv(4096)
        return connection

    def test_two_detached_worktree_tasks_overlap_and_complete(self):
        server = self.barrier(); port = server.getsockname()[1]
        root = self.fixture([{"barrier_port": port}])
        self.project.profile["repositories"][0]["checkout_strategy"] = "worktree"
        write_json(self.project.config / "project.json", self.project.profile)
        self.git(root, "add", "."); self.git(root, "commit", "-m", "Select task worktrees")
        scenarios, plans = {}, []
        for task, pattern in (("first", "first_*.py"), ("second", "second_*.py")):
            plan = {k: v for k, v in self.plan.items() if not k.startswith("_")}
            plan = json.loads(json.dumps(plan)); plan["task"] = task
            plan["repositories"][0].update(branch=f"feature/{task}", paths=[pattern])
            path = self.manifest_path.parent / f"{task}.json"; write_json(path, plan); plans.append(path)
            scenario = self.root / f"{task}-scenario.json"; write_json(scenario, [{"barrier_port": port}])
            checkout = root / self.project.profile["git"]["worktree_directory"] / task / "app"
            scenarios[str(checkout)] = str(scenario)
        self.env["WORKFLOW_TEST_SCENARIOS"] = json.dumps(scenarios)
        # Exercise the actual detach path with separate provider journals.
        for task in ("first", "second"):
            self.addCleanup(lambda task=task: self.task_cli("cancel", task))
        first = self.task_cli("run", plans[0], "--detach")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        one = self.accept(server)
        second = self.task_cli("run", plans[1], "--detach")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        two = self.accept(server)
        for task in ("first", "second"):
            self.assertEqual(state.read(self.project, task)["status"], "running")
        one.sendall(b"x"); two.sendall(b"x")
        for task in ("first", "second"):
            watched = self.task_cli("watch", task, "--seconds", "20")
            self.assertEqual(watched.returncode, 0, watched.stdout + watched.stderr)
            self.assertEqual(state.read(self.project, task)["status"], "complete")
        self.assertEqual(self.git(root, "branch", "--show-current"), "main")
        self.assertEqual(self.git(root, "status", "--porcelain"), "")

    def test_same_task_and_current_checkout_conflicts_fail_without_waiting(self):
        server = self.barrier()
        self.fixture([{"barrier_port": server.getsockname()[1]}]); self.save_plan()
        first = self.launch(self.manifest_path); connection = self.accept(server)
        same = self.task_cli("run", self.manifest_path, "--no-wait")
        self.assertNotEqual(same.returncode, 0)
        self.assertRegex(same.stdout + same.stderr, r"lock|owns|active|conflict")
        other = json.loads(self.manifest_path.read_text()); other["task"] = "other"
        path = self.manifest_path.parent / "other.json"; write_json(path, other)
        conflict = self.task_cli("run", path, "--no-wait")
        self.assertNotEqual(conflict.returncode, 0)
        self.assertRegex(conflict.stdout + conflict.stderr, r"sample|current-checkout|conflict")
        connection.sendall(b"x")
        first.communicate(timeout=20)

    def test_live_task_lock_prevents_false_interrupted_status(self):
        self.fixture([{}])
        path = state.directory(self.project, "sample")
        state.save(path, {"schema_version": 1, "task": "sample", "status": "running", "completed": [], "pid": 99999999})
        with state.lock(path / "runner.lock"):
            response = self.task_cli("status", "sample")
            self.assertEqual(response.returncode, 0, response.stderr)
            self.assertEqual(json.loads(response.stdout)["status"], "running")
        response = self.task_cli("status", "sample")
        self.assertEqual(json.loads(response.stdout)["status"], "interrupted")

    def test_legacy_project_lock_retains_ownership_meaning(self):
        self.fixture([{}]); self.save_plan()
        with state.lock(self.project.config / "local/runner.lock"):
            response = self.task_cli("run", self.manifest_path, "--no-wait")
        self.assertNotEqual(response.returncode, 0)
        self.assertRegex(response.stdout + response.stderr, r"lock|owns|active|legacy")
        self.assertEqual(self.calls(), [])

    def test_input_pause_releases_task_lock(self):
        from plovi import runner
        self.fixture([{"session": "pause", "report": {"status": "needs_input", "question": "Proceed?"}}])
        self.assertEqual(runner.run(self.project, self.plan)["status"], "needs_input")
        with state.lock(state.directory(self.project, "sample") / "runner.lock"):
            pass

    def test_migration_refuses_a_live_task_lock(self):
        from plovi import migration
        from plovi.util import WorkflowError
        root = self.fixture([{}])
        legacy = root / ".agentflow"
        self.project.config.rename(legacy)
        task_dir = legacy / "local/evidence/sample"
        state.save(task_dir, {"schema_version": 1, "task": "sample", "status": "running"})
        with state.lock(task_dir / "runner.lock"):
            with self.assertRaisesRegex(WorkflowError, r"active|lock|Finish|cancel"):
                migration.migrate(root)
        self.assertTrue(legacy.is_dir())
