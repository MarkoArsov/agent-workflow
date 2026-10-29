"""CI batches must execute the complete suite and propagate real failures."""
import json
import subprocess
import sys
from tests.helpers import PACKAGE, WorkspaceTest


class CITestRunnerTests(WorkspaceTest):
    def fixture(self, *, fail=False):
        suite = self.root / "suite"
        suite.mkdir()
        source = 'import unittest\nclass Example(unittest.TestCase):\n'
        for number in range(7):
            source += f'    def test_{number}(self): self.assertEqual({number}, {99 if fail and number == 6 else number})\n'
        (suite / "test_sample.py").write_text(source, encoding="utf-8")
        return suite

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(PACKAGE / "scripts/run_tests.py"), *map(str, args)],
                              cwd=self.root, env=self.env, text=True, capture_output=True, timeout=30)

    def test_batches_execute_every_case_once_with_timings(self):
        suite = self.fixture()
        ids = []
        for shard in (1, 2, 3):
            timings = self.root / f"timings-{shard}.json"
            result = self.invoke("--start-directory", suite, "--shard", shard, "--shards", 3, "--timings", timings)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(timings.read_text())
            self.assertTrue(data["successful"])
            self.assertEqual(data["discovered"], 7)
            self.assertEqual(data["tests_run"], data["selected"])
            self.assertEqual(len(data["tests"]), data["tests_run"])
            self.assertTrue(all(item["seconds"] >= 0 for item in data["tests"]))
            ids.extend(item["test"] for item in data["tests"])
        self.assertEqual(sorted(ids), [f"test_sample.Example.test_{number}" for number in range(7)])

    def test_failure_still_fails_the_process_and_writes_timings(self):
        suite = self.fixture(fail=True)
        timings = self.root / "failed-timings.json"
        result = self.invoke("--start-directory", suite, "--timings", timings)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("FAIL: test_6", result.stderr)
        data = json.loads(timings.read_text())
        self.assertFalse(data["successful"])
        self.assertEqual(data["tests_run"], 7)
        self.assertEqual(len(data["tests"]), 7)

    def test_invalid_or_empty_batch_cannot_report_success(self):
        suite = self.fixture()
        for shard, count in ((0, 3), (4, 3), (1, 0), (8, 8)):
            with self.subTest(shard=shard, count=count):
                result = self.invoke("--start-directory", suite, "--shard", shard, "--shards", count)
                self.assertEqual(result.returncode, 2, result.stderr)

    def test_repository_partition_is_complete_disjoint_and_stable(self):
        full = self.invoke("--list")
        self.assertEqual(full.returncode, 0, full.stderr)
        expected = json.loads(full.stdout)
        self.assertGreater(len(expected), 170)
        observed = []
        for shard in (1, 2, 3):
            args = ("--list", "--shard", shard, "--shards", 3)
            first = self.invoke(*args)
            repeated = self.invoke(*args)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(first.stdout, repeated.stdout)
            observed.extend(json.loads(first.stdout))
        self.assertEqual(sorted(observed), expected)
        self.assertEqual(len(set(observed)), len(observed))

    def test_discovery_error_is_not_silently_dropped(self):
        suite = self.fixture()
        (suite / "test_broken.py").write_text('raise RuntimeError("fixture import failure")\n')
        result = self.invoke("--start-directory", suite)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("fixture import failure", result.stderr)
