from __future__ import annotations
import json
import os
import shutil
import sys
from pathlib import Path
from tests.helpers import PACKAGE, WorkspaceTest
from agent_workflow import runner, manifest, state
from agent_workflow.util import WorkflowError, write_json

class RunnerTests(WorkspaceTest):
    def fixture(self, steps, *, stages=None):
        root = self.repo("app")
        (root / ".gitignore").write_text("__pycache__/\n")
        (root / "app.py").write_text("VALUE = 1\n")
        (root / "test_app.py").write_text("import unittest\nfrom app import VALUE\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertEqual(VALUE, 1)\n")
        self.project = self.setup_project(root, {"agents": ["codex"], "pipeline": {"routes": {"default": [{"provider": "codex", "model": "fixture-model"}]}}})
        self.git(root, "add", "."); self.git(root, "commit", "-m", "Configure fixture")
        self.scenario = self.root / "scenario.json"
        write_json(self.scenario, steps)
        os.environ["WORKFLOW_TEST_SCENARIO"] = str(self.scenario)
        self.env["WORKFLOW_TEST_SCENARIO"] = str(self.scenario)
        binaries = self.root / "bin"; binaries.mkdir()
        for name in ("codex", "claude", "agent"):
            shutil.copy(PACKAGE / "tests/fixtures/provider_double.py", binaries / name)
            (binaries / name).chmod(0o755)
        os.environ["PATH"] = str(binaries) + os.pathsep + self.env["PATH"]
        self.env["PATH"] = os.environ["PATH"]
        plan_dir = self.root / "plans"; plan_dir.mkdir()
        plan_files = ["prompt.md", "requirements.md", "implementation.md", "deferred.md"]
        for name in plan_files:
            (plan_dir / name).write_text("Fixture behavior. " + ("PRIVATE_IMPLEMENTATION_REASONING" if name == "implementation.md" else name))
        value = {"schema_version": 1, "task": "sample", "plan_files": plan_files,
                 "repositories": [{"id": "app", "access": "write", "paths": ["*.py"], "test_paths": ["test_*.py"]}],
                 "stages": stages or ["implement-tests", "implement", "review"],
                 "checks": [{"id": "behavior", "repository": "app", "parser": "unittest",
                             "command": {"argv": [sys.executable, "-m", "unittest", "-v", "test_app"], "timeout_seconds": 10},
                             "identities": ["test_behavior"], "phases": ["red", "green"]}],
                 "outcomes": [{"id": "behavior", "checks": ["behavior"]}],
                 "limits": {"attempts_per_route": 1, "timeout_seconds": 10, "inactivity_seconds": 5, "tool_timeout_seconds": 5}}
        self.manifest_path = plan_dir / "pipeline.json"; write_json(self.manifest_path, value)
        self.plan = manifest.load(self.manifest_path, self.project)
        return root

    def calls(self):
        return json.loads(self.scenario.with_suffix(".calls.json").read_text())

    def test_full_red_green_review_and_fresh_sessions(self):
        root = self.fixture([
            {"writes": {"test_app.py": "import unittest\nfrom app import VALUE\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertEqual(VALUE, 2)\n"}},
            {"writes": {"app.py": "VALUE = 2\n"}}, {}])
        result = runner.run(self.project, self.plan)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["completed"], self.plan["stages"])
        self.assertEqual(len({c["pid"] for c in self.calls()}), 3)
        self.assertNotIn("PRIVATE_IMPLEMENTATION_REASONING", self.calls()[2]["prompt"])
        self.assertIn("ACTUAL DIFF", self.calls()[2]["prompt"])
        self.assertTrue(result["stage_evidence"]["implement-tests"]["checks"][0]["passed"])
        self.assertIsNone(result["attempts"][0]["cost_usd"])
        self.assertEqual(self.git(root, "log", "-1", "--format=%s"), "Configure fixture")

    def test_exact_session_input_resume(self):
        self.fixture([{"session": "asking-session", "report": {"status": "needs_input", "question": "Keep the existing behavior?"}}, {}],
                     stages=["implement"])
        result = runner.run(self.project, self.plan)
        self.assertEqual(result["status"], "needs_input")
        with self.assertRaisesRegex(WorkflowError, "needs input"):
            runner.run(self.project, self.plan, resume=True)
        result = runner.run(self.project, self.plan, resume=True, answer="Yes, keep it.")
        self.assertEqual(result["status"], "complete")
        self.assertIn("asking-session", self.calls()[1]["argv"])
        self.assertIn("resume", self.calls()[1]["argv"])
        self.assertEqual(self.calls()[1]["prompt"], "Yes, keep it.")

    def test_permanent_failure_uses_approved_fallback_fresh(self):
        self.fixture([{"error": "model not available"}, {}], stages=["implement"])
        self.plan["routes"] = {"default": [{"provider": "codex", "model": "unavailable"},
                                           {"provider": "codex", "model": "fallback"}]}
        result = runner.run(self.project, self.plan)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["attempts"][0]["classification"], "model")
        self.assertIn("fallback", self.calls()[1]["argv"])
        self.assertNotIn("resume", self.calls()[1]["argv"])

    def test_out_of_scope_write_blocks_and_retains_evidence(self):
        root = self.fixture([{"writes": {"unapproved.txt": "retained"}}], stages=["implement"])
        with self.assertRaisesRegex(WorkflowError, "Scope violation"):
            runner.run(self.project, self.plan)
        self.assertEqual((root / "unapproved.txt").read_text(), "retained")
        self.assertEqual(state.read(self.project, "sample")["status"], "failed")

    def test_implementation_cannot_rewrite_assertion_proven_tests(self):
        self.fixture([{"writes": {"test_app.py": "import unittest\nfrom app import VALUE\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertEqual(VALUE, 2)\n"}},
                      {"writes": {"test_app.py": "import unittest\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertTrue(True)\n"}}])
        with self.assertRaisesRegex(WorkflowError, "Assertion-proven"):
            runner.run(self.project, self.plan)

    def test_profile_change_requires_explicit_rebind(self):
        self.fixture([{"report": {"status": "blocked", "reason": "fixture"}}, {}], stages=["implement"])
        self.assertEqual(runner.run(self.project, self.plan)["status"], "failed")
        self.project.profile["tracking"] = {"provider": "github"}
        with self.assertRaisesRegex(WorkflowError, "rebind"):
            runner.run(self.project, self.plan, resume=True)
        result = runner.run(self.project, self.plan, resume=True, rebind=True)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["revisions"]), 1)

    def test_inactivity_and_stalled_inner_tool_are_bounded(self):
        for behavior, expected in (({"sleep": 3}, "inactive"), ({"tool_stall": True}, "tool-stalled")):
            # Separate tests share this instance; create the fixture once then rewrite state/scenario.
            if not hasattr(self, "project"):
                self.fixture([behavior], stages=["implement"])
            else:
                shutil.rmtree(state.directory(self.project, "sample"))
                self.scenario.with_suffix(".calls.json").unlink()
                write_json(self.scenario, [behavior])
            self.plan["limits"]["inactivity_seconds"] = 1
            self.plan["limits"]["tool_timeout_seconds"] = 1
            result = runner.run(self.project, self.plan)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["attempts"][0]["classification"], expected)

    def test_custom_stage_executes_and_uses_project_override(self):
        self.fixture([{}], stages=["implement"])
        skill = self.project.config / "skills/implement/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: implement\ndescription: Fixture override.\n---\nCUSTOM_PROJECT_SKILL\n")
        write_json(self.project.config / "stages.json", [{"id": "receipt", "after": "implement", "inputs": [],
            "outputs": [{"repository": "app", "path": "receipt.py"}],
            "command": {"argv": [sys.executable, "-c", "from pathlib import Path; Path('receipt.py').write_text('DONE = True\\n')"]},
            "checks": ["behavior"]}])
        self.plan["stages"].append("receipt")
        self.assertEqual(runner.run(self.project, self.plan)["status"], "complete")
        self.assertIn("CUSTOM_PROJECT_SKILL", self.calls()[0]["prompt"])

    def test_manifest_rejects_missing_outcome_check_and_stage_order(self):
        self.fixture([{}], stages=["implement"])
        self.plan["outcomes"][0]["checks"] = ["missing"]
        with self.assertRaisesRegex(WorkflowError, "existing checks"):
            manifest.validate(self.plan, self.project)

