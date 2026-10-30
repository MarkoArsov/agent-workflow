import json
import tomllib
from tests.helpers import WorkspaceTest
from plovi.setup import apply, propose
from plovi.util import WorkflowError


class PolicyTests(WorkspaceTest):
    def project_fixture(self):
        root = self.repo("app")
        return self.setup_project(root)

    def test_documented_defaults_and_independent_values(self):
        from plovi import policy
        value = policy.defaults()
        self.assertEqual(value, {
            "limits": {"running_tasks": 2, "waiting_for_review": 3, "attempts_per_stage": 2,
                       "max_changed_files": 40, "max_changed_lines": 1500,
                       "size_exempt": ["**/package-lock.json", "**/*.lock"]},
            "paths": {"protected": [".github/workflows/**", "**/migrations/**"]},
            "execution": {"unattended_permission_mode": "restricted"},
            "autonomy": {"level": "assisted"}, "grants": {}})
        value["limits"]["size_exempt"].append("other")
        self.assertNotIn("other", policy.defaults()["limits"]["size_exempt"])

    def test_validation_reports_dotted_unknown_key_and_suggestion(self):
        from plovi import policy
        with self.assertRaisesRegex(WorkflowError, r"limits\.max_changed_file.*max_changed_files"):
            policy.validate({"limits": {"max_changed_file": 41}})

    def test_exact_types_bounds_globs_and_reserved_grants(self):
        from plovi import policy
        cases = [
            {"limits": {"max_changed_files": x}} for x in (True, False, 0, -1, 1.5, "40", 10**20)
        ] + [
            {"limits": {"size_exempt": "*.lock"}},
            {"paths": {"protected": [1]}}, {"paths": {"protected": ["../outside"]}},
            {"paths": {"protected": ["/outside/**"]}},
            {"execution": {"unattended_permission_mode": "anything"}},
            {"autonomy": {"level": "unbounded"}}, {"grants": {"shell": True}},
        ]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(WorkflowError):
                policy.validate(value)
        for level in ("assisted", "ready", "auto"):
            policy.validate({"autonomy": {"level": level}})

    def test_malformed_toml_names_file(self):
        from plovi import policy
        project = self.project_fixture()
        (project.root / "plovi.toml").write_text("[limits\n")
        with self.assertRaisesRegex(WorkflowError, "plovi.toml"):
            policy.load(project)

    def test_policy_show_reports_effective_value_and_source(self):
        project = self.project_fixture()
        (project.root / "plovi.toml").write_text("[limits]\nmax_changed_files = 12\n")
        response = self.cli("--project", project.root, "policy", "show", "--json", check=False)
        self.assertEqual(response.returncode, 0, response.stderr)
        value = json.loads(response.stdout)
        self.assertIn("12", str(value))
        self.assertIn("plovi.toml", str(value))

    def test_set_requires_review_and_preserves_unrelated_crlf_comments(self):
        project = self.project_fixture(); path = project.root / "plovi.toml"
        original = b'# retain this comment\r\n[limits]\r\nmax_changed_files = 40 # reviewed\r\nsize_exempt = ["a#b.lock", "quote\\\".lock"]\r\n'
        path.write_bytes(original)
        args = ("--project", project.root, "policy", "set", "limits.max_changed_files", "41")
        refused = self.cli(*args, check=False)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(path.read_bytes(), original)
        changed = self.cli(*args, "--yes", check=False)
        self.assertEqual(changed.returncode, 0, changed.stderr)
        self.assertIn("-max_changed_files = 40", changed.stdout)
        self.assertIn("+max_changed_files = 41", changed.stdout)
        self.assertEqual(path.read_bytes(), original.replace(b"files = 40", b"files = 41"))
        self.assertEqual(tomllib.loads(path.read_text())["limits"]["max_changed_files"], 41)
        before = path.read_bytes()
        self.assertEqual(self.cli(*args, "--yes", check=False).returncode, 0)
        self.assertEqual(path.read_bytes(), before)

    def test_invalid_edit_leaves_original_bytes(self):
        project = self.project_fixture(); path = project.root / "plovi.toml"
        path.write_text("# reviewed\n[limits]\nmax_changed_files = 40\n")
        before = path.read_bytes()
        result = self.cli("--project", project.root, "policy", "set", "limits.max_changed_files", "true", "--yes", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_bytes(), before)

    def test_setup_reviews_policy_and_preserves_user_edits(self):
        root = self.repo("app")
        proposal = propose(root, {"confirmed_defaults": True})
        self.assertIn("plovi.toml", str(proposal["changes"]))
        apply(proposal, proposal["approval"])
        path = root / "plovi.toml"
        self.assertTrue(path.is_file())
        custom = "# My reviewed policy\n[limits]\nmax_changed_files = 17\n"
        path.write_text(custom)
        again = propose(root); apply(again, again["approval"])
        self.assertEqual(path.read_text(), custom)

    def test_unsupported_inline_table_edit_refuses_without_rewriting(self):
        project = self.project_fixture(); path = project.root / "plovi.toml"
        original = b"# keep inline syntax\nlimits = {max_changed_files = 40}\n"
        path.write_bytes(original)
        result = self.cli("--project", project.root, "policy", "set", "limits.max_changed_files", "41", "--yes", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_bytes(), original)

    def test_policy_change_requires_explicit_running_task_rebind(self):
        from tests.helpers import HardeningTest
        from plovi import runner
        # Use the common isolated provider fixture while keeping policy tests independent.
        root = HardeningTest.fixture(self, [{"session": "policy-question", "report": {
            "status": "needs_input", "question": "Proceed?"}}, {}])
        self.assertEqual(runner.run(self.project, self.plan)["status"], "needs_input")
        (root / "plovi.toml").write_text("[limits]\nmax_changed_files = 12\n")
        with self.assertRaisesRegex(WorkflowError, "rebind"):
            runner.run(self.project, self.plan, resume=True, answer="Proceed")
