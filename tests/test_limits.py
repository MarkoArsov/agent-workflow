from tests.helpers import HardeningTest
from plovi import runner, state


class LimitTests(HardeningTest):
    def changed_files(self, count, *, lines=1):
        self.fixture([{"writes": {f"change_{n}.py": "# change\n" * lines for n in range(count)}}])
        return runner.run(self.project, self.plan)

    def test_41_files_need_approval(self):
        result = self.changed_files(41)
        self.assertEqual(result["status"], "needs_approval")
        self.assertEqual(result["approval"]["kind"], "size")
        self.assertEqual(result["approval"]["files"], 41)
        self.assertEqual(result["approval"]["lines"], 41)
        self.assertEqual(len(self.calls()), 1)

    def test_40_files_are_within_default_limit(self):
        self.assertEqual(self.changed_files(40)["status"], "complete")

    def test_1500_lines_are_within_default_limit(self):
        self.assertEqual(self.changed_files(1, lines=1500)["status"], "complete")

    def test_1501_lines_need_approval(self):
        result = self.changed_files(1, lines=1501)
        self.assertEqual(result["status"], "needs_approval")
        self.assertEqual(result["approval"]["lines"], 1501)

    def test_cumulative_changes_gate_before_review(self):
        self.fixture([{"writes": {f"first_{n}.py": "# first\n" for n in range(21)}},
                      {"writes": {f"second_{n}.py": "# second\n" for n in range(20)}}, {}],
                     stages=["implement", "review"])
        result = runner.run(self.project, self.plan)
        self.assertEqual(result["status"], "needs_approval")
        self.assertEqual(result["approval"]["files"], 41)
        self.assertEqual(len(self.calls()), 2)

    def test_root_and_nested_lockfiles_are_exempt_from_size_only(self):
        writes = {name: "entry\n" * 1600 for name in
                  ("package-lock.json", "nested/package-lock.json", "poetry.lock", "nested/deps.lock")}
        self.fixture([{"writes": writes}])
        self.plan["repositories"][0]["paths"] = ["**"]
        self.assertEqual(runner.run(self.project, self.plan)["status"], "complete")

    def test_approval_resumes_retained_output_without_provider_replay(self):
        self.assertEqual(self.changed_files(41)["status"], "needs_approval")
        self.save_plan()
        response = self.task_cli("approve", "sample", "--size", "--actor", "Fixture")
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        self.assertEqual(state.read(self.project, "sample")["status"], "complete")
        self.assertEqual(len(self.calls()), 1)

    def test_resume_cannot_bypass_size_gate(self):
        self.assertEqual(self.changed_files(41)["status"], "needs_approval")
        self.save_plan()
        self.task_cli("resume", "sample")
        self.assertEqual(state.read(self.project, "sample")["status"], "needs_approval")
        self.assertEqual(len(self.calls()), 1)

    def test_exempt_lockfile_still_requires_protected_path_approval(self):
        self.fixture([{"writes": {"db/migrations/poetry.lock": "entry\n" * 1600}}])
        self.plan["repositories"][0]["paths"] = ["**"]
        result = runner.run(self.project, self.plan)
        self.assertEqual(result["status"], "needs_approval")
        self.assertEqual(result["approval"]["kind"], "protected_paths")
        self.assertIn("db/migrations/poetry.lock", str(result["approval"]))

    def test_binary_changes_count_one_line_each(self):
        self.fixture([{"binary_writes": {f"image_{i}.bin": "00010200" for i in range(41)}}])
        self.plan["repositories"][0]["paths"] = ["*.bin"]
        result = runner.run(self.project, self.plan)
        self.assertEqual(result["status"], "needs_approval")
        self.assertEqual((result["approval"]["files"], result["approval"]["lines"]), (41, 41))

    def test_deleted_tracked_lines_count_against_limit(self):
        root = self.fixture([{"deletes": ["old.py"]}])
        (root / "old.py").write_text("# old\n" * 1501)
        self.git(root, "add", "old.py"); self.git(root, "commit", "-m", "Add deletion fixture")
        result = runner.run(self.project, self.plan)
        self.assertEqual(result["status"], "needs_approval")
        self.assertEqual(result["approval"]["lines"], 1501)

    def test_rename_to_protected_path_is_checked(self):
        root = self.fixture([{"renames": {"old.py": "db/migrations/new.py"}}])
        (root / "db/migrations").mkdir(parents=True)
        (root / "old.py").write_text("# unchanged content\n")
        self.git(root, "add", "old.py"); self.git(root, "commit", "-m", "Add rename fixture")
        self.plan["repositories"][0]["paths"] = ["**"]
        result = runner.run(self.project, self.plan)
        self.assertEqual(result["status"], "needs_approval")
        self.assertIn("db/migrations/new.py", str(result["approval"]))

    def test_both_gates_require_both_approvals(self):
        writes = {f"db/migrations/change_{i}.py": "# migration\n" for i in range(41)}
        self.fixture([{"writes": writes}])
        self.plan["repositories"][0]["paths"] = ["**"]
        self.save_plan()
        self.assertEqual(runner.run(self.project, self.plan)["status"], "needs_approval")
        approved = self.task_cli("approve", "sample", "--size", "--actor", "Fixture")
        self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
        self.assertEqual(state.read(self.project, "sample")["status"], "needs_approval")
        approved = self.task_cli("approve", "sample", "--paths", "--actor", "Fixture")
        self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
        self.assertEqual(state.read(self.project, "sample")["status"], "complete")
        self.assertEqual(len(self.calls()), 1)

    def test_diff_change_invalidates_prior_size_approval(self):
        writes = {f"db/migrations/change_{i}.py": "# migration\n" for i in range(41)}
        root = self.fixture([{"writes": writes}])
        self.plan["repositories"][0]["paths"] = ["**"]; self.save_plan()
        self.assertEqual(runner.run(self.project, self.plan)["status"], "needs_approval")
        self.assertEqual(self.task_cli("approve", "sample", "--size", "--actor", "Fixture").returncode, 0)
        (root / "db/migrations/change_0.py").write_text("# changed after approval\n")
        self.task_cli("approve", "sample", "--paths", "--actor", "Fixture")
        self.assertEqual(state.read(self.project, "sample")["status"], "needs_approval")
        self.assertEqual(len(self.calls()), 1)
