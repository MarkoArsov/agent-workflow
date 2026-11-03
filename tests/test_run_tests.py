"""Parallel workers, per-test timeouts, tiers and change-based selection in scripts/run_tests.py."""
import json
import subprocess
import sys
import time
from tests.helpers import PACKAGE, WorkspaceTest


class RunTestsTests(WorkspaceTest):
    def suite(self, modules):
        suite = self.root / "suite"
        suite.mkdir(exist_ok=True)
        for name, body in modules.items():
            (suite / f"{name}.py").write_text("import unittest\nclass Case(unittest.TestCase):\n" + body, encoding="utf-8")
        return suite

    def invoke(self, *args, cwd=None, timeout=60):
        return subprocess.run([sys.executable, str(PACKAGE / "scripts/run_tests.py"), *map(str, args)],
                              cwd=cwd or self.root, env=self.env, text=True, capture_output=True, timeout=timeout)

    def test_parallel_aggregates_pass_fail_error_and_exit_code(self):
        suite = self.suite({
            "test_ok": "    def test_passes(self): self.assertTrue(True)\n",
            "test_fail": "    def test_fails(self): self.assertEqual(1, 2, 'distinct-assertion-marker')\n",
            "test_err": "    def test_raises(self): raise RuntimeError('distinct-error-marker')\n",
        })
        timings = self.root / "timings.json"
        result = self.invoke("--start-directory", suite, "--jobs", 2, "--timings", timings)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr.count("FAIL: test_fails (test_fail.Case.test_fails)"), 1, result.stderr)
        self.assertEqual(result.stderr.count("ERROR: test_raises (test_err.Case.test_raises)"), 1, result.stderr)
        self.assertEqual(result.stderr.count("AssertionError: 1 != 2 : distinct-assertion-marker"), 1, result.stderr)
        self.assertEqual(result.stderr.count("RuntimeError: distinct-error-marker"), 1, result.stderr)
        self.assertNotIn("test_ok.Case.test_passes)\n", result.stderr.split("Slowest tests:")[0].split("FAIL:")[-1])
        data = json.loads(timings.read_text())
        self.assertEqual((data["tests_run"], data["selected"], data["jobs"], data["successful"]), (3, 3, 2, False))
        self.assertEqual(sorted(item["test"] for item in data["tests"]),
                         ["test_err.Case.test_raises", "test_fail.Case.test_fails", "test_ok.Case.test_passes"])

    def test_parallel_success_exits_zero(self):
        suite = self.suite({f"test_m{number}": "    def test_passes(self): pass\n" for number in range(4)})
        result = self.invoke("--start-directory", suite, "--jobs", "auto")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ran 4 tests", result.stderr)

    def test_worker_crash_is_a_failure(self):
        suite = self.suite({
            "test_ok": "    def test_passes(self): pass\n",
            "test_crash": "    def test_exits(self):\n        import os\n        os._exit(3)\n",
        })
        result = self.invoke("--start-directory", suite, "--jobs", 2)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("WORKER CRASH", result.stderr)
        self.assertIn("modules: test_crash", result.stderr)

    def test_hanging_test_dumps_stacks_and_fails(self):
        suite = self.suite({
            "test_hang": "    def test_sleeps(self):\n        import time\n        time.sleep(30)\n",
            "test_ok": "    def test_passes(self): pass\n",
        })
        started = time.monotonic()
        result = self.invoke("--start-directory", suite, "--jobs", 2, "--per-test-timeout", 2, timeout=30)
        self.assertLess(time.monotonic() - started, 15, result.stderr)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Thread", result.stderr)
        self.assertRegex(result.stderr, r'test_hang\.py", line \d+ in test_sleeps')
        self.assertIn("ERROR: test_sleeps (test_hang.Case.test_sleeps)", result.stderr)
        self.assertIn("TimeoutError: test exceeded 2 s", result.stderr)
        self.assertIn("test_passes (test_ok.Case.test_passes) ... ok", result.stderr)

    def test_timeout_reports_tests_the_worker_did_not_reach(self):
        suite = self.suite({
            "test_hang": ("    def test_a_sleeps(self):\n        import time\n        time.sleep(30)\n"
                          "    def test_b_after(self): pass\n"),
        })
        result = self.invoke("--start-directory", suite, "--per-test-timeout", 1, timeout=30)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("NOT RUN", result.stderr)
        self.assertIn("test_hang.Case.test_b_after", result.stderr)

    def test_timeout_from_environment(self):
        suite = self.suite({"test_hang": "    def test_sleeps(self):\n        import time\n        time.sleep(30)\n"})
        self.env["PLOVI_TEST_TIMEOUT"] = "1"
        started = time.monotonic()
        result = self.invoke("--start-directory", suite, timeout=30)
        self.assertLess(time.monotonic() - started, 15, result.stderr)
        self.assertIn("TimeoutError: test exceeded 1 s", result.stderr)

    def changed_repo(self):
        repo = self.repo("changed")
        (repo / "runtime/plovi").mkdir(parents=True)
        (repo / "runtime/plovi/__init__.py").write_text("")
        (repo / "runtime/plovi/foo.py").write_text("VALUE = 1\n")
        (repo / "runtime/plovi/bar.py").write_text("VALUE = 2\n")
        (repo / "docs").mkdir()
        (repo / "docs/x.md").write_text("# Docs\n")
        tests = repo / "tests"
        tests.mkdir()
        header = "import sys, pathlib\nsys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'runtime'))\n"
        (tests / "test_foo_user.py").write_text(header + "import unittest\nimport plovi.foo\nclass Case(unittest.TestCase):\n"
                                                "    def test_uses(self): pass\n")
        (tests / "test_from_user.py").write_text(header + "import unittest\nfrom plovi import foo\nclass Case(unittest.TestCase):\n"
                                                 "    def test_uses(self): pass\n")
        (tests / "test_other.py").write_text(header + "import unittest\nfrom plovi.bar import VALUE\nclass Case(unittest.TestCase):\n"
                                             "    def test_other(self): pass\n")
        (tests / "test_basic.py").write_text(header + "import unittest\nclass Case(unittest.TestCase):\n    def test_basic(self): pass\n")
        (tests / "tiers.json").write_text(json.dumps({"smoke": ["test_basic"], "slow": []}))
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-m", "Add modules")
        return repo

    def test_changed_selects_importing_tests(self):
        repo = self.changed_repo()
        (repo / "runtime/plovi/foo.py").write_text("VALUE = 3\n")
        result = self.invoke("--start-directory", repo / "tests", "--changed", "--list", cwd=repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        listing = json.loads(result.stdout[result.stdout.index("["):])
        self.assertEqual(listing, ["test_basic.Case.test_basic", "test_foo_user.Case.test_uses",
                                   "test_from_user.Case.test_uses"])
        self.assertIn("plovi.foo", result.stdout)
        ran = self.invoke("--start-directory", repo / "tests", "--changed", "--timings", self.root / "t.json", cwd=repo)
        self.assertEqual(ran.returncode, 0, ran.stderr)
        self.assertEqual(json.loads((self.root / "t.json").read_text())["tests_run"], 3)

        self.git(repo, "checkout", "--", "runtime/plovi/foo.py")
        (repo / "docs/x.md").write_text("# Changed docs\n")
        docs = self.invoke("--start-directory", repo / "tests", "--changed", cwd=repo)
        self.assertEqual(docs.returncode, 0, docs.stderr)
        self.assertIn("No tests affected; run the docs checks.", docs.stdout)
        self.assertNotIn("Ran ", docs.stderr)

    def test_changed_selects_nested_test_modules(self):
        repo = self.changed_repo()
        header = "import sys, pathlib\nsys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'runtime'))\n"
        (repo / "tests/nested").mkdir()
        (repo / "tests/nested/__init__.py").write_text("")
        (repo / "tests/nested/test_deep.py").write_text(header + "import unittest\nfrom plovi import foo\nclass Case(unittest.TestCase):\n"
                                                        "    def test_deep(self): pass\n")
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-m", "Add a nested module")
        (repo / "runtime/plovi/foo.py").write_text("VALUE = 4\n")
        listing = self.invoke("--start-directory", repo / "tests", "--changed", "--list", cwd=repo)
        self.assertIn("nested.test_deep.Case.test_deep", json.loads(listing.stdout[listing.stdout.index("["):]))
        self.git(repo, "checkout", "--", "runtime/plovi/foo.py")
        (repo / "tests/nested/test_deep.py").write_text((repo / "tests/nested/test_deep.py").read_text() + "# edited\n")
        direct = self.invoke("--start-directory", repo / "tests", "--changed", "--list", cwd=repo)
        self.assertEqual(json.loads(direct.stdout[direct.stdout.index("["):]),
                         ["nested.test_deep.Case.test_deep", "test_basic.Case.test_basic"])

    def test_changed_helper_or_fixture_selects_every_test(self):
        repo = self.changed_repo()
        (repo / "tests/helpers.py").write_text("HELPER = 1\n")
        result = self.invoke("--start-directory", repo / "tests", "--changed", "--list", cwd=repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout[result.stdout.index("["):])), 4)

    def test_changed_ignores_plans_and_maps_named_files(self):
        repo = self.changed_repo()
        header = "import sys, pathlib\nsys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'runtime'))\n"
        (repo / "tests/test_script_user.py").write_text(header + "import unittest\nclass Case(unittest.TestCase):\n"
                                                        "    def test_names(self): self.assertTrue('scripts/tool.py')\n")
        self.git(repo, "add", "tests/test_script_user.py")
        self.git(repo, "commit", "-m", "Add script test")
        (repo / "ai-plans/task").mkdir(parents=True)
        (repo / "ai-plans/task/plan.md").write_text("# Plan\n")
        (repo / "ai-plans/task/facts.json").write_text("{}\n")
        plans = self.invoke("--start-directory", repo / "tests", "--changed", cwd=repo)
        self.assertEqual(plans.returncode, 0, plans.stderr)
        self.assertIn("No tests affected; run the docs checks.", plans.stdout)
        (repo / "scripts").mkdir()
        (repo / "scripts/tool.py").write_text("print(1)\n")
        result = self.invoke("--start-directory", repo / "tests", "--changed", "--list", cwd=repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        listing = json.loads(result.stdout[result.stdout.index("["):])
        self.assertEqual(listing, ["test_basic.Case.test_basic", "test_script_user.Case.test_names"])
        (repo / "scripts/other.py").write_text("print(2)\n")
        unnamed = self.invoke("--start-directory", repo / "tests", "--changed", "--list", cwd=repo)
        self.assertIn("scripts/other.py changed; selecting every test.", unnamed.stdout)
        self.assertEqual(len(json.loads(unnamed.stdout[unnamed.stdout.index("["):])), 5)

    def test_tiers_file_lists_existing_modules(self):
        tiers = json.loads((PACKAGE / "tests/tiers.json").read_text())
        self.assertEqual(set(tiers), {"smoke", "slow"})
        self.assertTrue(tiers["smoke"])
        for name in tiers["smoke"] + tiers["slow"]:
            # Nested packages such as tests/scenario use dotted module names.
            self.assertTrue((PACKAGE / "tests" / (name.replace(".", "/") + ".py")).is_file(), name)
        self.assertFalse(set(tiers["smoke"]) & set(tiers["slow"]))

    def test_smoke_tier_selects_only_listed_modules(self):
        result = self.invoke("--tier", "smoke", "--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        smoke = set(json.loads((PACKAGE / "tests/tiers.json").read_text())["smoke"])
        modules = {name.split(".")[0] for name in json.loads(result.stdout)}
        self.assertEqual(modules, smoke)

    def test_shards_are_deterministic(self):
        suite = self.suite({f"test_m{number}": "".join(f"    def test_{case}(self): pass\n" for case in range(3))
                            for number in range(4)})
        runs = [self.invoke("--start-directory", suite, "--shard", 2, "--shards", 3, "--list") for _ in range(2)]
        self.assertEqual(runs[0].returncode, 0, runs[0].stderr)
        self.assertEqual(runs[0].stdout, runs[1].stdout)
        timed = [self.root / f"shard-{number}.json" for number in range(2)]
        for path in timed:
            result = self.invoke("--start-directory", suite, "--shard", 2, "--shards", 3, "--jobs", 2, "--timings", path)
            self.assertEqual(result.returncode, 0, result.stderr)
        selections = [sorted(item["test"] for item in json.loads(path.read_text())["tests"]) for path in timed]
        self.assertEqual(selections[0], selections[1])
        self.assertEqual(selections[0], json.loads(runs[0].stdout))

    def test_invalid_jobs_and_timeout_are_rejected(self):
        suite = self.suite({"test_ok": "    def test_passes(self): pass\n"})
        for args in (("--jobs", 0), ("--jobs", "many"), ("--per-test-timeout", 0)):
            with self.subTest(args=args):
                self.assertEqual(self.invoke("--start-directory", suite, *args).returncode, 2)

    def test_summary_lists_failures_and_slowest(self):
        suite = self.suite({"test_fail": "    def test_fails(self): self.fail('marker')\n"})
        summary = self.root / "summary.md"
        result = self.invoke("--start-directory", suite, "--summary", summary)
        self.assertEqual(result.returncode, 1, result.stderr)
        text = summary.read_text()
        self.assertIn("FAIL `test_fail.Case.test_fails`", text)
        self.assertIn("Slowest tests", text)

    def test_record_writes_the_local_suite_time_only_after_a_full_passing_run(self):
        suite = self.suite({"test_ok": "    def test_passes(self): pass\n"})
        record = self.root / "stats/local-suite.json"
        result = self.invoke("--start-directory", suite, "--jobs", 2, "--record", record)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(record.read_text())
        self.assertEqual((data["tests_run"], data["jobs"]), (1, 1))
        self.assertGreater(data["cpu_count"], 0)
        self.assertGreaterEqual(data["seconds"], 0)
        self.assertRegex(data["date"], r"^\d{4}-\d{2}-\d{2}$")
        record.unlink()
        failing = self.suite({"test_bad": "    def test_fails(self): self.fail('no')\n"})
        result = self.invoke("--start-directory", failing, "--record", record)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(record.exists())
        self.assertIn("Not recorded", result.stderr)
        partial = self.invoke("--start-directory", suite, "--tier", "smoke", "--record", record)
        self.assertEqual(partial.returncode, 2)
        self.assertIn("--record needs a full run", partial.stderr)

    def test_scenario_results_map_each_step_to_its_result_and_owners(self):
        suite = self.suite({"test_other": "    def test_passes(self): pass\n"})
        scenario = suite / "scenario"
        scenario.mkdir()
        (scenario / "__init__.py").write_text("")
        (scenario / "steps.py").write_text(
            "SCENARIO_STEPS = [\n"
            " {'id': 'A1', 'text': 'Passes', 'owners': [49], 'test': 'ScenarioTests.test_A1_passes'},\n"
            " {'id': 'A2', 'text': 'Skips', 'owners': [21], 'test': 'ScenarioTests.test_A2_skips'},\n"
            " {'id': 'A3', 'text': 'Fails', 'owners': [49, 48], 'test': 'ScenarioTests.test_A3_fails'},\n"
            " {'id': 'A4', 'text': 'Missing', 'owners': [50], 'test': 'ScenarioTests.test_A4_missing'},\n]\n")
        (scenario / "test_target_scenario.py").write_text(
            "import unittest\nclass ScenarioTests(unittest.TestCase):\n"
            "    def test_A1_passes(self): pass\n"
            "    @unittest.skip('owned by #21 (pending)')\n    def test_A2_skips(self): pass\n"
            "    def test_A3_fails(self): self.fail('not implemented')\n")
        output = self.root / "scenario-results.json"
        result = self.invoke("--start-directory", suite, "--jobs", 2, "--scenario-results", output)
        self.assertEqual(result.returncode, 1, result.stderr)
        steps = json.loads(output.read_text())["steps"]
        self.assertEqual({key: (value["status"], value["owners"]) for key, value in steps.items()},
                         {"A1": ("passed", [49]), "A2": ("skipped", [21]), "A3": ("failed", [49, 48]), "A4": ("not-run", [50])})
