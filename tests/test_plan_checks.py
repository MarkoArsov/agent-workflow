"""validate-plan --run-checks (#48): every named check runs once in the task checkout before approval."""
import json
import sys
from tests.helpers import HardeningTest
from plovi import manifest
from plovi.util import write_json

FAILING = "import unittest\nclass Failing(unittest.TestCase):\n def test_wrong(self): self.assertEqual(1, 2)\n"


def printing(text, code=0):
    return [sys.executable, "-c", f"import sys; sys.stdout.write({text!r}); sys.exit({code})"]


class PlanCheckTests(HardeningTest):
    def setUp(self):
        super().setUp()
        self.app = self.fixture([])
        self.receipt(self.app)

    def receipt(self, path):
        write_json(self.project.config / "local/tasks/sample.json",
                   {"schema_version": 1, "task": "sample", "complete": True,
                    "repositories": [{"repository": "app", "path": str(path), "branch": "main", "strategy": "current-checkout"}]})

    def checks(self, *rows):
        self.plan["checks"] = [{"id": name, "repository": "app", "phases": ["green"]} | fields for name, fields in rows]
        self.plan["outcomes"] = [{"id": "behavior", "checks": [rows[0][0]]}]
        self.save_plan()

    def validate(self, *extra, check=False):
        return self.cli_inproc("--project", self.project.root, "validate-plan", self.manifest_path, *extra, check=check)

    def results(self, *rows):
        self.checks(*rows)
        done = self.validate("--run-checks", "--json")
        self.assertIn(done.returncode, (0, 1), done.stderr)
        return {row["id"]: row for row in json.loads(done.stdout)["checks"]}

    def one(self, fields, name="check"):
        return self.results((name, fields))[name]

    def unittest(self, *modules, **fields):
        return {"parser": "unittest", "command": {"argv": [sys.executable, "-m", "unittest", "-v", *modules], "timeout_seconds": 30}} | fields

    # ---- one test per classification -------------------------------------------------------

    def test_ran_passing_unittest(self):
        self.assertEqual(self.one(self.unittest("test_app"))["result"], "ran")

    def test_ran_failing_assertion(self):
        (self.app / "test_fail.py").write_text(FAILING)
        self.assertEqual(self.one(self.unittest("test_fail"))["result"], "ran")

    def test_ran_missing_test_module(self):
        # The plan's tests are written later; a missing module is expected at plan time.
        row = self.one(self.unittest("test_written_later"))
        self.assertEqual(row["result"], "ran", row["detail"])

    def test_missing_tool_unknown_executable(self):
        row = self.one({"command": {"argv": ["plovi-no-such-tool-48", "--check"]}})
        self.assertEqual(row["result"], "missing-tool")
        self.assertEqual(row["fix"], "check: missing-tool: plovi-no-such-tool-48 is not on PATH. Install it, "
                                     "or use a named repository command that has it.")

    def test_missing_tool_python_module(self):
        # The #18 docs-build check: the system python3 had no mkdocs.
        row = self.one({"command": {"argv": [sys.executable, "-m", "plovi_missing_mkdocs", "build", "--strict"]}}, "docs-build")
        self.assertEqual(row["result"], "missing-tool")
        program = __import__("pathlib").Path(sys.executable).name
        self.assertEqual(row["fix"], f"docs-build: missing-tool: {program} has no plovi_missing_mkdocs. Use the project's "
                                     "documented interpreter (for example .venv/bin/python) or a named command that has it.")

    def test_bad_cwd(self):
        row = self.one({"command": {"argv": printing("ok"), "cwd": "no-such-dir"}})
        self.assertEqual(row["result"], "bad-cwd")
        self.assertIn("no-such-dir does not exist in app", row["fix"])

    def test_unparseable_unittest_without_result_line(self):
        row = self.one({"parser": "unittest", "command": {"argv": printing("all good")}})
        self.assertEqual(row["result"], "unparseable")
        self.assertIn("the unittest parser found no result line", row["fix"])

    def test_unparseable_generic_pattern_never_matches(self):
        # The #18 links check: a success_pattern that the tool never prints.
        row = self.one({"parser": "generic", "success_pattern": "All links OK",
                        "command": {"argv": printing("Checked 3 internal links/assets; 0 failures.\n")}}, "links")
        self.assertEqual(row["result"], "unparseable")
        self.assertEqual(row["fix"], 'links: unparseable: exit 0 but success_pattern "All links OK" never appeared. '
                                     "Remove the pattern (exit code is authoritative) or match the tool's real output.")

    def test_timeout(self):
        row = self.one({"command": {"argv": [sys.executable, "-c", "import time; time.sleep(10)"], "timeout_seconds": 1}})
        self.assertEqual(row["result"], "timeout")
        self.assertLess(row["seconds"], 8)

    def test_modifies_files(self):
        row = self.one({"command": {"argv": [sys.executable, "-c", "open('made.txt', 'w').write('x')"]}})
        self.assertEqual(row["result"], "modifies-files")
        self.assertIn("made.txt", row["fix"])
        self.assertTrue((self.app / "made.txt").exists(), "a check that changes files is reported, not cleaned")

    # ---- recognised output for planned tests that don't exist yet ----------------------------

    def test_dotnet_compile_error_is_ran(self):
        output = "Tests.cs(3,7): error CS0246: The type or namespace name 'Planned' could not be found\nBuild FAILED.\n"
        self.assertEqual(self.one({"parser": "dotnet", "command": {"argv": printing(output, 1)}})["result"], "ran")

    def test_pytest_missing_file_is_ran(self):
        output = "ERROR: file or directory not found: tests/test_new.py\n\nno tests ran in 0.01s\n"
        self.assertEqual(self.one({"parser": "pytest", "command": {"argv": printing(output, 4)}})["result"], "ran")

    def test_generic_without_pattern_ran_whatever_the_exit_code(self):
        self.assertEqual(self.one({"command": {"argv": printing("broken", 3)}})["result"], "ran")

    # ---- plan binding, output and exit codes -------------------------------------------------

    def test_results_bound_into_plan_hash(self):
        self.checks(("check", self.unittest("test_app")))
        self.assertEqual(self.validate("--run-checks").returncode, 0)
        plan = manifest.load(self.manifest_path, self.project)
        self.assertEqual(plan["plan_files"][-1], "planning-checks.json")
        saved = json.loads((self.manifest_path.parent / "planning-checks.json").read_text())
        self.assertEqual((saved["version"], [row["id"] for row in saved["checks"]]), (1, ["check"]))
        self.assertEqual(set(saved["checks"][0]), {"id", "result", "seconds", "detail"})
        before = manifest.plan_sha256(plan)
        saved["checks"][0]["result"] = "timeout"
        write_json(self.manifest_path.parent / "planning-checks.json", saved)
        self.assertNotEqual(manifest.plan_sha256(plan), before)
        self.validate("--run-checks")
        self.assertEqual(manifest.load(self.manifest_path, self.project)["plan_files"].count("planning-checks.json"), 1)

    def test_validate_without_flag_unchanged(self):
        self.checks(("check", {"command": {"argv": [sys.executable, "-c", "open('made.txt', 'w').write('x')"]}}))
        done = self.validate()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout), {"task": "sample", "valid": True})
        self.assertFalse((self.app / "made.txt").exists())
        self.assertFalse((self.manifest_path.parent / "planning-checks.json").exists())

    def test_exit_codes(self):
        self.checks(("check", self.unittest("test_app")))
        passed = self.validate("--run-checks")
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertIn("check", passed.stdout)
        self.assertIn("ran", passed.stdout)
        self.checks(("check", self.unittest("test_app")), ("links", {"parser": "generic", "success_pattern": "All links OK",
                                                                      "command": {"argv": printing("Checked 3 links")}}))
        failed = self.validate("--run-checks")
        self.assertEqual(failed.returncode, 1)
        self.assertIn('links: unparseable: exit 0 but success_pattern "All links OK" never appeared.', failed.stdout)
        self.plan["checks"][1]["success_pattern"] = "All links ("
        self.save_plan()
        self.assertEqual(self.validate("--run-checks").returncode, 2)

    def test_bad_pattern_is_invalid_input(self):
        self.checks(("links", {"parser": "generic", "success_pattern": "Checked (", "command": {"argv": printing("ok")}}))
        done = self.validate("--run-checks")
        self.assertEqual(done.returncode, 2)
        self.assertIn("links: success_pattern does not compile", done.stderr)

    def test_no_receipt_refuses(self):
        (self.project.config / "local/tasks/sample.json").unlink()
        self.checks(("check", self.unittest("test_app")))
        done = self.validate("--run-checks")
        self.assertEqual(done.returncode, 2)
        self.assertIn("No task checkout for sample. Run plovi task start sample, then validate again.", done.stderr)

    def test_runs_in_task_checkout(self):
        worktree = self.root / "task-checkout"
        self.git(self.app, "worktree", "add", "--quiet", "-b", "task", str(worktree))
        self.receipt(worktree)
        script = f"import os, sys; sys.stdout.write('Ran 1 test\\n\\nOK\\n' if os.path.samefile(os.getcwd(), {str(worktree)!r}) else '')"
        self.assertEqual(self.one({"parser": "unittest", "command": {"argv": [sys.executable, "-c", script]}})["result"], "ran")

    def test_failed_validation_records_no_proposal(self):
        def proposals():
            from plovi import ledger
            return [e for e in ledger.events(self.project) if e["type"] == "plan.proposed"]
        self.checks(("check", {"command": {"argv": ["plovi-no-such-tool-48"]}}))
        self.assertEqual(self.validate("--run-checks").returncode, 1)
        self.assertEqual(proposals(), [], "a plan whose checks can't run never reaches the inbox")
        self.checks(("check", self.unittest("test_app")))
        self.assertEqual(self.validate("--run-checks").returncode, 0)
        self.assertEqual(len(proposals()), 1)

    def test_operation_registered_for_headless_planning(self):
        from plovi import operations
        operations._load()
        operation = operations.REGISTRY["validate-plan"]
        self.assertEqual(operation.arguments["properties"]["run_checks"]["type"], "boolean")
        self.checks(("check", self.unittest("test_app")))
        result = operations.call("validate-plan", {"project": str(self.project.root), "manifest": str(self.manifest_path),
                                                   "run_checks": True, "json": True})
        self.assertEqual((result["valid"], [row["result"] for row in result["checks"]]), (True, ["ran"]))
