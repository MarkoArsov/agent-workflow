"""Verification v2 (#48): exit codes decide, skips are advisory, checks declare when they run."""
import copy
from tests.helpers import HardeningTest
from plovi import manifest
from plovi.util import WorkflowError
from plovi.verification import parse

UNITTEST_SKIP = ("test_behavior (test_app.Behavior.test_behavior) ... ok\n"
                 "test_docker (test_app.Behavior.test_docker) ... skipped 'needs PLOVI_TEST_DOCKER=1'\n\n"
                 "Ran 2 tests in 0.01s\n\nOK (skipped=1)\n")


class ParseTests(HardeningTest):
    def test_exit_code_authoritative_without_pattern(self):
        check = {"parser": "generic"}
        self.assertTrue(parse(check, "", 0)["passed"])
        self.assertTrue(parse(check, "anything at all", 0)["passed"])
        failed = parse(check, "anything at all", 2)
        self.assertFalse(failed["passed"])
        self.assertIn("check did not produce successful evidence", failed["problems"])

    def test_pattern_is_extra_assertion(self):
        check = {"parser": "generic", "success_pattern": r"Checked [1-9]\d* links; 0 failures"}
        self.assertTrue(parse(check, "Checked 12 links; 0 failures", 0)["passed"])
        self.assertFalse(parse(check, "Checked 12 links; 3 failures", 0)["passed"])
        self.assertFalse(parse(check, "Checked 12 links; 0 failures", 1)["passed"])

    def test_environment_skip_is_advisory(self):
        # The #18 full-suite check: an opt-in Docker test skips outside its environment.
        evidence = parse({"parser": "unittest", "identities": ["test_behavior"]}, UNITTEST_SKIP, 0)
        self.assertTrue(evidence["passed"], evidence["problems"])
        self.assertEqual(evidence["skipped"], 1)
        pytest = parse({"parser": "pytest"}, "1 passed, 1 skipped in 0.04s", 0)
        self.assertTrue(pytest["passed"], pytest["problems"])
        self.assertEqual(pytest["skipped"], 1)

    def test_skipped_identity_fails(self):
        evidence = parse({"parser": "unittest", "identities": ["test_docker"]}, UNITTEST_SKIP, 0)
        self.assertFalse(evidence["passed"])
        self.assertIn("planned test test_docker was skipped", evidence["problems"])
        pytest = "test_app.py::test_behavior PASSED\ntest_app.py::test_docker SKIPPED (no docker)\n1 passed, 1 skipped in 0.04s"
        self.assertFalse(parse({"parser": "pytest", "identities": ["test_docker"]}, pytest, 0)["passed"])
        # A longer test name that only starts with the identity is not the identity.
        self.assertTrue(parse({"parser": "unittest", "identities": ["test_dock"]},
                              UNITTEST_SKIP.replace("test_behavior", "test_dock"), 0)["passed"])

    def test_skips_fail_when_check_says_so(self):
        evidence = parse({"parser": "unittest", "skips": "fail"}, UNITTEST_SKIP, 0)
        self.assertFalse(evidence["passed"])
        self.assertIn("1 skipped; this check sets skips = \"fail\"", evidence["problems"])
        reason = parse({"parser": "unittest", "approved_skip_reason": "Docker is opt-in"}, UNITTEST_SKIP, 0)
        self.assertTrue(reason["passed"])
        self.assertEqual(reason["approved_skip_reason"], "Docker is opt-in")


class ContractFieldTests(HardeningTest):
    def validate(self, **check):
        plan = copy.deepcopy({k: v for k, v in self.plan.items() if not k.startswith("_")})
        plan["checks"][0].update(check)
        return manifest.validate(plan, self.project)

    def test_generic_checks_need_no_success_pattern(self):
        self.fixture([])
        self.validate(parser="generic", phases=["green"], identities=[])

    def test_when_expected_seconds_and_skips_validated(self):
        self.fixture([])
        self.validate(when=["loop"], expected_seconds=5, skips="fail")
        self.validate(when=["final"], skips="advisory")
        for bad in ({"when": []}, {"when": ["sometimes"]}, {"when": "loop"}, {"expected_seconds": 0},
                    {"expected_seconds": 1.5}, {"expected_seconds": True}, {"skips": "never"}):
            with self.subTest(bad=bad), self.assertRaises(WorkflowError):
                self.validate(**bad)

    def test_patterns_must_compile(self):
        self.fixture([])
        with self.assertRaisesRegex(WorkflowError, "success_pattern does not compile"):
            self.validate(parser="generic", phases=["green"], identities=[], success_pattern="Checked (")
        with self.assertRaisesRegex(WorkflowError, "failure_pattern does not compile"):
            self.validate(parser="generic", failure_pattern="[unclosed")
