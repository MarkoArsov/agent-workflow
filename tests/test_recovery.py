import json
import os
from tests.helpers import HardeningTest
from plovi import runner, state


class RecoveryTests(HardeningTest):
    def delivery_fixture(self):
        root = self.fixture([{"writes": {"owned.py": "# approved content\n"}}])
        self.plan["stages"] = ["implement", "commit-and-push", "draft-pr"]
        self.git(root, "switch", "-c", "feature/sample")
        remote = self.root / "remote.git"; remote.mkdir(); self.git(remote, "init", "--bare")
        self.git(remote, "config", "core.logAllRefUpdates", "true")
        self.git(root, "remote", "add", "origin", str(remote))
        self.plan["repositories"][0]["branch"] = "feature/sample"
        self.plan["delivery"] = {"commit_message": "Deliver approved fixture", "title": "Fixture", "body_file": "body.md"}
        (self.manifest_path.parent / "body.md").write_text("Approved fixture plan.\n")
        self.plan["plan_files"].append("body.md")
        # Trace actual child Git invocations: a duplicate no-op push leaves no reflog entry.
        self.git_trace = self.root / "git-trace.jsonl"
        self.env["GIT_TRACE2_EVENT"] = str(self.git_trace)
        gh = self.install_gh_double(); self.save_plan()
        return root, remote, gh

    def test_status_reconciles_abandoned_running_state_without_pid_signals(self):
        self.fixture([{}]); directory = state.directory(self.project, "sample")
        state.save(directory, {"schema_version": 1, "task": "sample", "status": "running",
                               "pid": os.getpid(), "completed": ["implement-tests"]})
        response = self.task_cli("status", "sample")
        self.assertEqual(response.returncode, 0, response.stderr)
        self.assertEqual(json.loads(response.stdout)["status"], "interrupted")
        self.assertEqual(state.read(self.project, "sample")["status"], "interrupted")
        self.assertEqual(state.read(self.project, "sample")["completed"], ["implement-tests"])

    def test_retained_verified_output_does_not_repeat_provider(self):
        self.fixture([{}]); completed = runner.run(self.project, self.plan)
        completed.update(completed=[], status="running", active_stage="implement", stage_before=completed["baseline"])
        state.save(state.directory(self.project, "sample"), completed)
        self.assertEqual(runner.run(self.project, self.plan, resume=True)["status"], "complete")
        self.assertEqual(len(self.calls()), 1)

    def crash_and_resume(self, point):
        root, remote, gh = self.delivery_fixture()
        baseline = self.git(root, "rev-parse", "HEAD")
        self.env.update(PLOVI_TESTING="1", PLOVI_TEST_CRASH_AFTER=point)
        crashed = self.task_cli("run", self.manifest_path)
        self.assertNotEqual(crashed.returncode, 0, "Testing fault hook must abruptly stop the child")
        self.env.pop("PLOVI_TEST_CRASH_AFTER")
        status = self.task_cli("status", "sample")
        self.assertEqual(json.loads(status.stdout)["status"], "interrupted")
        resumed = self.task_cli("resume", "sample")
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        saved = state.read(self.project, "sample")
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(self.git(root, "rev-list", "--count", f"{baseline}..HEAD"), "1")
        head = self.git(root, "rev-parse", "HEAD")
        self.assertEqual(self.git(remote, "rev-parse", "refs/heads/feature/sample"), head)
        self.assertEqual(len(self.git(remote, "reflog", "show", "--format=%H", "refs/heads/feature/sample").splitlines()), 1)
        commands = [json.loads(line) for line in self.git_trace.read_text().splitlines()]
        self.assertEqual(sum(event.get("event") == "start" and "push" in event.get("argv", [])
                             for event in commands), 1)
        journal = json.loads(gh.read_text())
        self.assertEqual(sum(c["argv"][:2] == ["pr", "create"] for c in journal["calls"]), 1)
        self.assertIn("Evidence", journal["prs"][0]["body"])
        self.assertEqual(saved["delivery"]["app"]["pr"], journal["prs"][0]["url"])

    def test_abrupt_exit_after_commit_adopts_exact_commit(self):
        self.crash_and_resume("commit")

    def test_abrupt_exit_after_push_adopts_remote_branch(self):
        self.crash_and_resume("push")

    def test_abrupt_exit_after_pr_reuses_remote_pr(self):
        self.crash_and_resume("pr")

    def test_fault_hook_is_inert_without_testing_opt_in(self):
        self.delivery_fixture()
        self.env["PLOVI_TEST_CRASH_AFTER"] = "commit"
        response = self.task_cli("run", self.manifest_path)
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        self.assertEqual(state.read(self.project, "sample")["status"], "complete")

    def test_crash_commit_with_altered_content_is_not_adopted(self):
        root, _, _ = self.delivery_fixture()
        self.env.update(PLOVI_TESTING="1", PLOVI_TEST_CRASH_AFTER="commit")
        crashed = self.task_cli("run", self.manifest_path)
        self.assertNotEqual(crashed.returncode, 0)
        (root / "owned.py").write_text("# foreign content\n")
        self.git(root, "add", "owned.py")
        self.git(root, "commit", "--amend", "--no-edit")
        unexpected = self.git(root, "rev-parse", "HEAD")
        self.env.pop("PLOVI_TEST_CRASH_AFTER")
        resumed = self.task_cli("resume", "sample")
        self.assertNotEqual(resumed.returncode, 0)
        self.assertEqual(self.git(root, "rev-parse", "HEAD"), unexpected)
        self.assertEqual((root / "owned.py").read_text(), "# foreign content\n")
        self.assertEqual(len(self.calls()), 1)

    def test_crash_commit_with_changed_message_is_not_adopted(self):
        root, _, _ = self.delivery_fixture()
        self.env.update(PLOVI_TESTING="1", PLOVI_TEST_CRASH_AFTER="commit")
        self.assertNotEqual(self.task_cli("run", self.manifest_path).returncode, 0)
        self.git(root, "commit", "--amend", "-m", "Foreign message")
        unexpected = self.git(root, "rev-parse", "HEAD")
        self.env.pop("PLOVI_TEST_CRASH_AFTER")
        self.assertNotEqual(self.task_cli("resume", "sample").returncode, 0)
        self.assertEqual(self.git(root, "rev-parse", "HEAD"), unexpected)

    def test_remote_divergence_is_never_force_pushed(self):
        root, remote, _ = self.delivery_fixture()
        self.env.update(PLOVI_TESTING="1", PLOVI_TEST_CRASH_AFTER="push")
        self.assertNotEqual(self.task_cli("run", self.manifest_path).returncode, 0)
        peer = self.root / "peer"
        self.git(self.root, "clone", "-b", "feature/sample", str(remote), str(peer))
        (peer / "foreign.py").write_text("# remote owner\n")
        self.git(peer, "add", "."); self.git(peer, "commit", "-m", "Remote owner change")
        self.git(peer, "push", "origin", "feature/sample")
        expected = self.git(peer, "rev-parse", "HEAD")
        self.env.pop("PLOVI_TEST_CRASH_AFTER")
        self.assertNotEqual(self.task_cli("resume", "sample").returncode, 0)
        self.assertEqual(self.git(remote, "rev-parse", "refs/heads/feature/sample"), expected)

    def test_crash_commit_with_extra_path_is_not_adopted(self):
        root, _, _ = self.delivery_fixture()
        self.env.update(PLOVI_TESTING="1", PLOVI_TEST_CRASH_AFTER="commit")
        self.assertNotEqual(self.task_cli("run", self.manifest_path).returncode, 0)
        (root / "foreign.txt").write_text("Other owner\n")
        self.git(root, "add", "foreign.txt"); self.git(root, "commit", "--amend", "--no-edit")
        unexpected = self.git(root, "rev-parse", "HEAD")
        self.env.pop("PLOVI_TEST_CRASH_AFTER")
        self.assertNotEqual(self.task_cli("resume", "sample").returncode, 0)
        self.assertEqual(self.git(root, "rev-parse", "HEAD"), unexpected)

    def test_crash_commit_with_extra_parent_is_not_adopted(self):
        root, _, _ = self.delivery_fixture()
        baseline = self.git(root, "rev-parse", "HEAD")
        self.env.update(PLOVI_TESTING="1", PLOVI_TEST_CRASH_AFTER="commit")
        self.assertNotEqual(self.task_cli("run", self.manifest_path).returncode, 0)
        tree = self.git(root, "rev-parse", "HEAD^{tree}")
        # A second distinct parent makes a merge with the same message and contents.
        extra = self.git(root, "commit-tree", tree, "-p", baseline, "-m", "Unrelated parent")
        merge = self.git(root, "commit-tree", tree, "-p", baseline, "-p", extra, "-m", "Deliver approved fixture")
        self.git(root, "reset", "--hard", merge)
        self.env.pop("PLOVI_TEST_CRASH_AFTER")
        self.assertNotEqual(self.task_cli("resume", "sample").returncode, 0)
        self.assertEqual(self.git(root, "rev-parse", "HEAD"), merge)

    def test_foreign_staged_content_survives_rejected_recovery(self):
        root, _, _ = self.delivery_fixture()
        self.env.update(PLOVI_TESTING="1", PLOVI_TEST_CRASH_AFTER="commit")
        self.assertNotEqual(self.task_cli("run", self.manifest_path).returncode, 0)
        (root / "foreign.txt").write_text("Other owner\n"); self.git(root, "add", "foreign.txt")
        expected = self.git(root, "ls-files", "--stage", "-z")
        self.env.pop("PLOVI_TEST_CRASH_AFTER")
        self.assertNotEqual(self.task_cli("resume", "sample").returncode, 0)
        self.assertEqual(self.git(root, "ls-files", "--stage", "-z"), expected)
