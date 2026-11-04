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


RECORD = ("import os, sys; open(os.environ['CHECK_LOG'], 'a').write(sys.argv[1] + '\\n'); "
          "sys.exit(int(sys.argv[2]) if len(sys.argv) > 2 else 0)")
RED_MODULE = ("import unittest\nclass Red(unittest.TestCase):\n"
              " def test_target(self):\n  '''Target behaviour'''\n  self.assertEqual(1, 2)\n"
              " def test_other(self): self.assertEqual(1, 1)\n")


class SelectionTests(HardeningTest):
    def setUp(self):
        super().setUp()
        import os
        self.root = self.fixture([])
        self.log = self.root.parent / "checks.log"
        os.environ["CHECK_LOG"] = str(self.log)
        self.addCleanup(os.environ.pop, "CHECK_LOG", None)

    def recorded(self, name, *, code=0, **fields):
        import sys
        return {"id": name, "repository": "app", "parser": "generic", "phases": ["green"],
                "command": {"argv": [sys.executable, "-c", RECORD, name, str(code)], "timeout_seconds": 10}} | fields

    def ran(self):
        return self.log.read_text().split() if self.log.exists() else []

    def use(self, *checks):
        self.plan["checks"] = list(checks)
        self.plan["outcomes"] = [{"id": "behavior", "checks": [checks[0]["id"]]}]

    def green(self, **options):
        from plovi.verification import run_green
        return run_green(self.project, self.plan, {"app": str(self.root)}, **options)

    def test_loop_and_final_selection(self):
        self.use(self.recorded("quick", when=["loop"]), self.recorded("full", when=["final"]), self.recorded("both"))
        rows, not_run = self.green(cache={}, fingerprint="f1")
        self.assertEqual(self.ran(), ["quick", "both", "full"])
        self.assertEqual(not_run, [])
        # "both" ran once, in the loop; the final pass reused that run instead of repeating it.
        self.assertEqual({row["id"]: row.get("reused", False) for row in rows}, {"quick": False, "both": False, "full": False})
        from plovi.autonomy import loop_checks
        self.assertEqual([c["id"] for c in loop_checks(self.plan)], ["quick", "both"])

    def test_loop_checks_ordered_by_expected_seconds(self):
        self.use(self.recorded("slow", expected_seconds=30), self.recorded("unmeasured"),
                 self.recorded("measured"), self.recorded("fast", expected_seconds=1))
        self.green(durations={"measured": 5.0})
        self.assertEqual(self.ran(), ["fast", "measured", "slow", "unmeasured"])

    def test_loop_stops_at_first_failure_and_final_waits(self):
        self.use(self.recorded("broken", code=1, when=["loop"], expected_seconds=1),
                 self.recorded("later", when=["loop"], expected_seconds=2), self.recorded("full", when=["final"]))
        rows, not_run = self.green()
        self.assertEqual(self.ran(), ["broken"])
        self.assertEqual([row["id"] for row in rows], ["broken"])
        self.assertEqual(not_run, ["later", "full"])

    def test_same_argv_and_fingerprint_reused(self):
        from plovi.verification import run_checks
        self.use(self.recorded("quick"))
        cache = {}
        first = run_checks(self.project, self.plan, {"app": str(self.root)}, cache=cache, fingerprint="f1")
        again = run_checks(self.project, self.plan, {"app": str(self.root)}, cache=cache, fingerprint="f1")
        self.assertEqual(self.ran(), ["quick"])
        self.assertTrue(again[0]["reused"])
        self.assertEqual((again[0]["passed"], again[0]["command"]), (first[0]["passed"], first[0]["command"]))
        run_checks(self.project, self.plan, {"app": str(self.root)}, cache=cache, fingerprint="f2")
        self.plan["checks"][0]["command"]["argv"].append("extra")
        run_checks(self.project, self.plan, {"app": str(self.root)}, cache=cache, fingerprint="f2")
        self.assertEqual(self.ran(), ["quick", "quick", "quick"])

    def test_failed_result_not_reused(self):
        from plovi.verification import run_checks
        self.use(self.recorded("broken", code=1))
        cache = {}
        for _ in range(2):
            self.assertFalse(run_checks(self.project, self.plan, {"app": str(self.root)}, cache=cache, fingerprint="f1")[0]["passed"])
        self.assertEqual(self.ran(), ["broken", "broken"])

    def red_check(self, argv, identities):
        import sys
        (self.root / "test_red.py").write_text(RED_MODULE)
        return {"id": "red", "repository": "app", "parser": "unittest", "phases": ["red"], "identities": identities,
                "command": {"argv": [sys.executable, "-m", "unittest", *argv], "timeout_seconds": 30}}

    def red(self, check):
        from plovi.verification import run_checks
        self.use(check)
        return run_checks(self.project, self.plan, {"app": str(self.root)}, phase="red")[0]

    def test_red_runs_only_identities_for_unittest(self):
        result = self.red(self.red_check(["-v", "test_red"], ["test_target"]))
        self.assertTrue(result["passed"], result["problems"])
        self.assertTrue(result["filtered"])
        self.assertIn("-k test_target", result["command"])
        self.assertIn("Ran 1 test", result["output"])
        self.assertNotIn("test_other", result["output"])

    def test_red_filter_works_with_discover(self):
        result = self.red(self.red_check(["discover", "-v", "-p", "test_red*.py"], ["test_target"]))
        self.assertTrue(result["passed"], result["problems"])
        self.assertTrue(result["filtered"])
        self.assertIn("Ran 1 test", result["output"])

    def test_red_identity_filter_falls_back_to_whole_command(self):
        # The docstring line names the test in verbose output, but -k matches test IDs only.
        result = self.red(self.red_check(["-v", "test_red"], ["Target behaviour"]))
        self.assertFalse(result["filtered"])
        self.assertNotIn("-k", result["command"])
        self.assertIn("Ran 2 tests", result["output"])

    def test_checks_with_green_phase_run_whole_in_red(self):
        # Their red run is the test-count and skip baseline #47's guards compare against.
        check = self.red_check(["-v", "test_red"], ["test_target"]) | {"phases": ["red", "green"]}
        result = self.red(check)
        self.assertFalse(result["filtered"])
        self.assertIn("Ran 2 tests", result["output"])


class RunnerReuseTests(HardeningTest):
    def test_review_reuses_implement_results_for_the_same_diff(self):
        from plovi import runner
        self.fixture([{"writes": {"app.py": "VALUE = 1  # implemented\n"}}, {}], stages=["implement", "review"])
        saved = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(saved["status"], "complete", saved.get("error"))
        implement, review = (saved["stage_evidence"][stage]["checks"][0] for stage in ("implement", "review"))
        self.assertFalse(implement.get("reused", False))
        self.assertTrue(review["reused"])
        self.assertIn("behavior", saved["check_durations"])
