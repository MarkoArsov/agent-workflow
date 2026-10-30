from __future__ import annotations
import json
import os
import time
from pathlib import Path
from unittest.mock import patch
from tests.helpers import WorkspaceTest
from plovi import runner, state
from plovi.util import WorkflowError, digest, json_text, read_json, write_json

class RunnerLifecycleTests(WorkspaceTest):
    def test_binding_is_identical_with_windows_legacy_and_utf8_defaults(self):
        self.fixture([{}])
        text = "Plan caf\u00e9 \u2014 preserve the approved scope.\n"
        plan_file = Path(self.plan["_directory"]) / self.plan["plan_files"][0]
        plan_file.write_bytes(text.encode("utf-8"))
        skill = self.project.config / "skills/implement/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_bytes(("---\nname: implement\ndescription: Implement the approved change.\n---\n" + text).encode("utf-8"))
        (skill.parent / "notes.txt").write_bytes(text.encode("utf-8"))
        reference = self.project.root / self.project.profile["extensions"]["references"] / "scope.md"
        reference.parent.mkdir(parents=True, exist_ok=True)
        reference.write_bytes(text.encode("utf-8"))
        original = Path.read_text
        def with_default(encoding):
            def read(path, *args, **kwargs):
                if not args and kwargs.get("encoding") is None:
                    kwargs["encoding"] = encoding
                return original(path, *args, **kwargs)
            return read
        with patch.object(Path, "read_text", with_default("utf-8")):
            expected = runner.binding(self.project, self.plan)
        saved = self.root / "saved-binding.json"
        write_json(saved, expected)
        with patch.object(Path, "read_text", with_default("cp1252")):
            actual = runner.binding(self.project, self.plan)
            restored = read_json(saved)
        self.assertEqual(digest(json_text(actual)), digest(json_text(expected)))
        self.assertEqual(restored, expected)
        self.assertEqual(actual["plans"][self.plan["plan_files"][0]], text)

    def fixture(self, steps):
        from tests.test_runner import RunnerTests
        return RunnerTests.fixture(self, steps, stages=["implement"])

    def calls(self):
        return json.loads(self.scenario.with_suffix(".calls.json").read_text())

    def wait_status(self, predicate):
        deadline = time.monotonic() + 15
        path = state.directory(self.project, "sample") / "state.json"
        while time.monotonic() < deadline:
            value = read_json(path)
            if value and predicate(value):
                return value
            time.sleep(0.05)
        self.fail("Runner did not reach the expected bounded state")

    def test_detached_cancel_lock_and_resume(self):
        self.fixture([{"sleep": 8}, {}])
        launch = runner.detach(self.project, self.manifest_path)
        self.assertGreater(launch["pid"], 0)
        # Popen can report a PID before Python has consumed the fixture step.
        self.wait_status(lambda value: value.get("child_pid") and self.scenario.with_suffix(".calls.json").exists())
        self.addCleanup(lambda: state.cancel(self.project, "sample"))
        with self.assertRaisesRegex(WorkflowError, "lock"):
            runner.run(self.project, self.plan, resume=True)
        state.cancel(self.project, "sample")
        result = self.wait_status(lambda value: value["status"] == "cancelled")
        self.assertEqual(result["attempts"][0]["classification"], "cancelled")
        result = runner.run(self.project, self.plan, resume=True)
        self.assertEqual(result["status"], "complete")
        self.assertNotEqual(self.calls()[0]["pid"], self.calls()[1]["pid"])

    def test_interrupted_verified_stage_reuses_current_evidence(self):
        self.fixture([{}])
        completed = runner.run(self.project, self.plan)
        completed["completed"] = []
        completed["status"] = "running"
        completed["active_stage"] = "implement"
        completed["stage_before"] = completed["baseline"]
        state.save(state.directory(self.project, "sample"), completed)
        result = runner.run(self.project, self.plan, resume=True)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(self.calls()), 1)

    def test_rebind_invalidates_passed_evidence_for_changed_plan(self):
        self.fixture([{}, {}])
        self.assertEqual(runner.run(self.project, self.plan)["status"], "complete")
        self.plan["outcomes"][0]["description"] = "Revised acceptance explanation"
        skill = self.project.config / "skills/implement/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: implement\ndescription: Revised project procedure.\n---\nREVISED_SKILL\n")
        result = runner.run(self.project, self.plan, resume=True, rebind=True)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(self.calls()), 2)
        self.assertIn("REVISED_SKILL", self.calls()[-1]["prompt"])

    def test_interrupted_red_verification_restores_frozen_tests_before_implementation(self):
        from tests.test_runner import RunnerTests
        RunnerTests.fixture(self, [
            {"writes": {"test_app.py": "import unittest\nfrom app import VALUE\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertEqual(VALUE, 2)\n"}},
            {"writes": {"test_app.py": "import unittest\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertTrue(True)\n"}}])
        with patch.object(runner, "accept_evidence", side_effect=KeyboardInterrupt):
            interrupted = runner.run(self.project, self.plan)
        self.assertNotIn("red_test_files", interrupted)
        self.assertTrue(interrupted["stage_evidence"]["implement-tests"]["passed"])
        with self.assertRaisesRegex(WorkflowError, "frozen by implement-tests"):
            runner.run(self.project, self.plan, resume=True)
        self.assertEqual(len(self.calls()), 2)

    def test_final_fingerprint_is_rechecked_after_custom_stage(self):
        from tests.test_runner import RunnerTests
        root = RunnerTests.fixture(self, [{}], stages=["implement"])
        import sys
        write_json(self.project.config / "stages.json", [{"id": "mutation", "after": "implement", "inputs": [],
            "outputs": [{"repository": "app", "path": "app.py"}],
            "command": {"argv": [sys.executable, "-c", "from pathlib import Path; Path('app.py').write_text('VALUE = 999\\n')"]},
            "checks": ["custom-check"]}])
        self.plan["stages"].append("mutation")
        self.plan["checks"].append({"id": "custom-check", "repository": "app", "parser": "generic",
             "success_pattern": "^custom done$", "command": {"argv": [sys.executable, "-c", "print('custom done')"]}})
        with self.assertRaisesRegex(WorkflowError, "passing verification"):
            runner.run(self.project, self.plan)
        self.assertEqual(state.read(self.project, "sample")["status"], "failed")

class DeliveryBindingRecoveryTests(WorkspaceTest):
    def test_completed_delivery_accepts_only_verified_task_owned_reference_changes(self):
        root = self.repo('app')
        project = self.setup_project(root, {'repositories': [{'id': 'app', 'path': '.', 'checkout_strategy': 'current-checkout'}]})
        (root / 'references').mkdir()
        (root / 'references' / 'pipeline-contract.md').write_text('old')
        self.git(root, 'add', '.')
        self.git(root, 'commit', '-m', 'Configure')
        from plovi import git_ops
        before = git_ops.snapshot(project, {'app': str(root)})
        (root / 'references' / 'pipeline-contract.md').write_text('new')
        self.git(root, 'add', 'references/pipeline-contract.md')
        self.git(root, 'commit', '-m', 'Change approved task output')
        head = self.git(root, 'rev-parse', 'HEAD')
        current = git_ops.snapshot(project, {'app': str(root)})
        manifest = {'repositories': [{'id': 'app', 'access': 'write', 'branch': 'main', 'paths': ['references/**']}],
                    'stages': ['implement', 'review', 'commit-and-push', 'draft-pr']}
        saved = {'stage': 'draft-pr', 'completed': ['implement', 'review', 'commit-and-push'],
                 'baseline': before, 'checkouts': {'app': str(root)},
                 'delivery': {'app': {'commit': head, 'pushed': True}},
                 'green': {'fingerprint': git_ops.fingerprint(current)}}
        old = {'profile': {'x': 1}, 'package_references': {'pipeline-contract.md': 'old'}, 'skills': {}}
        new = {'profile': {'x': 1}, 'package_references': {'pipeline-contract.md': 'new'}, 'skills': {}}
        with patch.object(runner, 'package_root', return_value=root):
            self.assertTrue(runner.owned_delivery_binding(project, manifest, saved, old, new))
            changed = dict(new, profile={'x': 2})
            self.assertFalse(runner.owned_delivery_binding(project, manifest, saved, old, changed))
            unverified = dict(saved, green={'fingerprint': 'wrong'})
            self.assertFalse(runner.owned_delivery_binding(project, manifest, unverified, old, new))
            incomplete = dict(saved, completed=['implement'])
            self.assertFalse(runner.owned_delivery_binding(project, manifest, incomplete, old, new))
            foreign = dict(saved, delivery={'app': {'commit': 'wrong', 'pushed': True}})
            self.assertFalse(runner.owned_delivery_binding(project, manifest, foreign, old, new))
            (root / 'references' / 'pipeline-contract.md').write_text('foreign edit')
            self.assertFalse(runner.owned_delivery_binding(project, manifest, saved, old, new))
