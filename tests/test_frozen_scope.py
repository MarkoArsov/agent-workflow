"""Narrow frozen tests (#47): only red-identity files freeze; other test edits are listed; removed or skipped tests fail closed."""
import sys
from tests.helpers import HardeningTest
from plovi import runner

RED = "import unittest\nfrom app import VALUE\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertEqual(VALUE, 2)\n"
EXTRA = "import unittest\nclass Extra(unittest.TestCase):\n def test_other(self): self.assertTrue(True)\n"
SKIPPED = "import unittest\nclass Extra(unittest.TestCase):\n @unittest.skip('later')\n def test_other(self): self.assertTrue(True)\n"


class FrozenScopeTests(HardeningTest):
    def run_plan(self, steps, *, discover=False):
        self.fixture(steps, stages=["implement-tests", "implement", "review"])
        if discover:
            self.plan["checks"][0]["command"]["argv"] = [sys.executable, "-m", "unittest", "discover", "-v", "-p", "test_*.py"]
        self.plan["corrections"] = {"same_session_rounds": 0}
        return runner.run(self.project, self.plan, unattended=False)

    def test_only_red_identity_files_are_frozen(self):
        saved = self.run_plan([{"writes": {"test_app.py": RED, "test_support.py": "HELPER = 1\n"}},
                               {"writes": {"app.py": "VALUE = 2\n", "test_support.py": "HELPER = 2\n"}}, {}])
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(set(saved["frozen_tests"]["app"]), {"test_app.py"})

    def test_helper_edits_are_allowed_and_listed_in_evidence(self):
        saved = self.run_plan([{"writes": {"test_app.py": RED, "test_support.py": "HELPER = 1\n"}},
                               {"writes": {"app.py": "VALUE = 2\n", "test_support.py": "HELPER = 2\n"}}, {}])
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(saved["stage_evidence"]["implement"]["test_edits"], {"app": ["test_support.py"]})
        review = self.calls()[2]["prompt"]
        self.assertIn("Check that these test edits did not weaken any assertion.", review)
        self.assertIn("app/test_support.py", review)

    def test_editing_a_frozen_test_still_stops(self):
        with self.assertRaisesRegex(Exception, "Tests frozen by implement-tests changed"):
            self.run_plan([{"writes": {"test_app.py": RED}},
                           {"writes": {"app.py": "VALUE = 2\n", "test_app.py": RED.replace("2)", "VALUE)")}}, {}])

    def test_removing_a_test_fails_closed(self):
        saved = self.run_plan([{"writes": {"test_app.py": RED, "test_extra.py": EXTRA}},
                               {"writes": {"app.py": "VALUE = 2\n"}, "deletes": ["test_extra.py"]}, {}], discover=True)
        self.assertEqual(saved["status"], "failed")
        problems = saved["stage_evidence"]["implement"]["problems"]
        self.assertTrue(any("fewer tests" in problem for problem in problems), problems)

    def test_skipping_a_test_fails_closed(self):
        saved = self.run_plan([{"writes": {"test_app.py": RED, "test_extra.py": EXTRA}},
                               {"writes": {"app.py": "VALUE = 2\n", "test_extra.py": SKIPPED}}, {}], discover=True)
        self.assertEqual(saved["status"], "failed")
        self.assertNotIn("implement", saved["completed"])


class CountTests(HardeningTest):
    def test_pytest_output_reports_test_counts(self):
        from plovi.verification import parse
        output = "test_app.py::test_behavior PASSED\n=== 3 passed, 1 skipped in 0.12s ==="
        evidence = parse({"id": "behavior", "parser": "pytest", "approved_skip_reason": "platform"}, output, 0)
        self.assertEqual(evidence["counts"], {"tests": 4, "failures": 0, "errors": 0, "skipped": 1})
