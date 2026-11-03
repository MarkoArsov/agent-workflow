"""The target scenario, end to end, against the provider double, the GitHub fake and local bare remotes.

One method per step in steps.py. A step runs only when every owning issue is done in
owners.json; until then it is skipped with "owned by #N (pending)". A stub fails with
"not implemented", so flipping an owner without writing the test fails loudly.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest.mock
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tests.helpers import PACKAGE, WorkspaceTest, _cache_root, install_script, wait_for
from tests.scenario.steps import APP_SPEC, owned_by
from plovi.util import write_json

RESETS_AT = 1793631600
PLAN_FILES = ["prompt.md", "requirements.md", "implementation.md", "deferred.md"]
BASELINE_TEST = "import unittest\nfrom app import VALUE\nclass Behavior(unittest.TestCase):\n def test_behavior(self): self.assertEqual(VALUE, 1)\n"
CHANGED_TEST = BASELINE_TEST.replace("VALUE, 1", "VALUE, 2")
# Settings each fixture project gets once its owning issue adds the keys to plovi.toml.
# Today plovi.toml rejects them, and the stage list lives in each plan's "stages".
FUTURE_POLICY = {
    "hobby": {"delivery": {"mode": "pull-request"}, "merge": {"mode": "manual"}, "intake": {"max_active": 1}},  # #21, #23
    "product": {"delivery": {"ci": "fix"}, "merge": {"mode": "auto", "shadow": 0}},  # #23
}
STAGES = {"hobby": ["implement", "review"], "product": ["implement-tests", "implement", "review", "docs-check"]}
DOCS_STAGE = {"id": "docs-check", "after": "review", "inputs": [], "outputs": [], "checks": ["docs"],
              "command": {"argv": [sys.executable, "-c", "print('docs-check ran')"]}}
VERIFY = "name: Verify\njobs:\n  smoke:\n    timeout-minutes: 5\n  core:\n    timeout-minutes: 25\n    steps:\n      - name: Tests\n        timeout-minutes: 20\n"
TEMPLATES = {}


class ScenarioTests(WorkspaceTest):
    """Fixture projects are built once per process and copied for each test."""

    def setUp(self):
        super().setUp()
        self.scenario = self.root / "provider-scenario.json"
        write_json(self.scenario, [{}])
        binaries = self.root / "bin"
        binaries.mkdir()
        for name in ("codex", "claude", "agent"):
            install_script(binaries, name, PACKAGE / "tests/fixtures/provider_double.py")
        for environment in (self.env, os.environ):
            environment["PATH"] = str(binaries) + os.pathsep + environment["PATH"]
            environment["WORKFLOW_TEST_SCENARIO"] = str(self.scenario)

    # ---- fixtures -------------------------------------------------------------------------

    def template(self, name):
        """Build the hobby or product project once, with its own throwaway user data."""
        if name in TEMPLATES:
            return TEMPLATES[name]
        root = Path(tempfile.mkdtemp(prefix=f"scenario-{name}-", dir=_cache_root())) / name
        root.mkdir()
        self.git(root, "init", "-b", "main")
        (root / ".gitignore").write_text("__pycache__/\n")
        (root / "README.md").write_text(f"# {name.title()} fixture\n")
        (root / "app.py").write_text("VALUE = 1\n")
        (root / "test_app.py").write_text(BASELINE_TEST)
        data = root.parent / "data"
        with unittest.mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(data)}):
            self.setup_project(root, {"agents": ["codex"], "repositories": [{"id": name, "checkout_strategy": "current-checkout"}],
                                      "pipeline": {"routes": {"default": [{"provider": "codex", "model": "fixture-model"}]}}})
        if name == "product":
            write_json(root / ".plovi/stages.json", [DOCS_STAGE])
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", f"Configure the {name} fixture")
        TEMPLATES[name] = root
        return root

    def project(self, name, copy_as=None):
        from plovi.project import load
        root = self.root / (copy_as or name)
        shutil.copytree(self.template(name), root)
        remote = self.bare_remote(root.name)
        self.git(root, "remote", "add", "origin", str(remote))
        self.git(root, "push", "--quiet", "origin", "main")
        return load(root)

    def plan(self, project, stages, *, task="sample", extra=None, files=None):
        from plovi import manifest
        repository = project.profile["repositories"][0]["id"]
        directory = self.root / f"plans-{project.root.name}-{task}"
        directory.mkdir()
        for name in PLAN_FILES:
            (directory / name).write_text(f"Scenario fixture: {name}\n")
        for name, text in (files or {}).items():
            (directory / name).write_text(text)
        checks = [{"id": "behavior", "repository": repository, "parser": "unittest", "identities": ["test_behavior"],
                   "command": {"argv": [sys.executable, "-m", "unittest", "-v", "test_app"], "timeout_seconds": 20},
                   "phases": ["red", "green"]},
                  {"id": "docs", "repository": repository, "parser": "generic", "success_pattern": "^docs ok$", "phases": ["green"],
                   "command": {"argv": [sys.executable, "-c", "from pathlib import Path; assert Path('README.md').read_text().startswith('#'); print('docs ok')"]}}]
        value = {"schema_version": 1, "task": task, "plan_files": PLAN_FILES,
                 "repositories": [{"id": repository, "access": "write", "paths": ["*.py"], "test_paths": ["test_*.py"]}],
                 "stages": stages, "checks": checks,
                 "outcomes": [{"id": "behavior", "checks": ["behavior"]}, {"id": "docs", "checks": ["docs"]}],
                 "limits": {"attempts_per_route": 1, "timeout_seconds": 20, "inactivity_seconds": 10, "tool_timeout_seconds": 10}}
        value.update(extra or {})
        write_json(directory / "pipeline.json", value)
        return manifest.load(directory / "pipeline.json", project)

    def provider(self, steps):
        write_json(self.scenario, steps)
        self.scenario.with_suffix(".calls.json").unlink(missing_ok=True)

    def calls(self):
        path = self.scenario.with_suffix(".calls.json")
        return json.loads(path.read_text()) if path.exists() else []

    def events(self, project, task="sample"):
        from plovi import ledger
        return ledger.events(project, subject={"kind": "task", "id": task})

    def stages_started(self, project, task="sample"):
        return [e["data"]["stage"] for e in self.events(project, task) if e["type"] == "stage.started"]

    def task_cli(self, project, *args, check=True):
        return self.cli("--project", project.root, *args, check=check)

    def run_in_thread(self, project, plan):
        from plovi import runner
        outcome = {}

        def work():
            try:
                outcome["result"] = runner.run(project, plan, unattended=False)
            except BaseException as exc:  # reported by the caller's assertion
                outcome["error"] = exc
        worker = threading.Thread(target=work)
        worker.start()
        return worker, outcome

    def assert_app_test(self, step_id):
        spec = PACKAGE / APP_SPEC
        self.assertTrue(spec.is_file(), f"{APP_SPEC} is missing")
        self.assertRegex(spec.read_text(encoding="utf-8"), r"""test\(\s*["'`]""" + step_id + " ")

    # ---- U: set up once ----------------------------------------------------------------------

    @owned_by(49)
    def test_U1_setup_once(self):
        # #20 extends this step: setup also writes the built-in schedules, disabled.
        root = self.repo("fresh")
        proposal, answers = self.root / "proposal.json", self.root / "answers.json"
        write_json(answers, {"confirmed_defaults": True})
        preview = json.loads(self.cli_inproc("setup", root, "--answers", answers, "--output", proposal).stdout)
        self.assertFalse((root / ".plovi/project.json").exists(), "the preview changes nothing")
        self.assertIn("plovi.toml", preview["changed_files"])
        self.cli_inproc("setup", "--apply", proposal, "--approve", preview["approval"])
        self.assertTrue((root / ".plovi/project.json").is_file())
        self.assertTrue((root / "plovi.toml").is_file())
        policy = json.loads(self.cli_inproc("--project", root, "policy", "show", "--json").stdout)
        self.assertIn("limits", json.dumps(policy))
        again = json.loads(self.cli_inproc("setup", root, "--answers", answers, "--output", self.root / "again.json").stdout)
        self.assertEqual(again["changed_files"], [], "setting up once is enough")

    @owned_by(49, 23)
    def test_U2_project_settings_apply(self):
        from plovi import runner
        plain = self.project("product", copy_as="product-plain")
        custom = self.project("product", copy_as="product-custom")
        self.provider([{"writes": {"app.py": "VALUE = 1\n"}}, {}, {"writes": {"app.py": "VALUE = 1\n"}}, {}])
        self.assertEqual(runner.run(plain, self.plan(plain, ["implement", "review"], task="plain"), unattended=False)["status"], "complete")
        self.assertEqual(runner.run(custom, self.plan(custom, ["implement", "review", "docs-check"], task="custom"),
                                    unattended=False)["status"], "complete")
        self.assertEqual(self.stages_started(plain, "plain"), ["implement", "review"])
        self.assertEqual(self.stages_started(custom, "custom"), ["implement", "review", "docs-check"])
        # #23: move FUTURE_POLICY into plovi.toml and assert the delivery and merge keys change delivery here.

    # ---- I: intake --------------------------------------------------------------------------

    @owned_by(21)
    def test_I1_only_allowed_labels_count(self):
        self.fail("not implemented")

    @owned_by(21)
    def test_I2_tick_picks_next_issue(self):
        self.fail("not implemented")

    @owned_by(21)
    def test_I3_max_active_one(self):
        self.fail("not implemented")

    @owned_by(21)
    def test_I4_blocked_because(self):
        self.fail("not implemented")

    # ---- P: planning -------------------------------------------------------------------------

    @owned_by(21)
    def test_P1_headless_assumptions_recorded(self):
        self.fail("not implemented")

    @owned_by(21)
    def test_P2_stop_list_asks_once(self):
        self.fail("not implemented")

    @owned_by(48)
    def test_P3_plan_checks_validated(self):
        self.fail("not implemented")

    @owned_by(21)
    def test_P4_auto_approved_plan_builds(self):
        self.fail("not implemented")

    # ---- B: build -----------------------------------------------------------------------------

    @owned_by(49)
    def test_B1_hobby_stages(self):
        from plovi import runner
        project = self.project("hobby")
        self.provider([{"writes": {"app.py": "VALUE = 1  # implemented\n"}}, {}])
        result = runner.run(project, self.plan(project, STAGES["hobby"]), unattended=False)
        self.assertEqual(result["status"], "complete", result.get("error"))
        self.assertEqual(result["completed"], ["implement", "review"])
        self.assertEqual(self.stages_started(project), ["implement", "review"])
        self.assertEqual(len(self.calls()), 2, "one provider session per stage")

    @owned_by(49)
    def test_B2_product_stages_with_custom(self):
        from plovi import runner
        project = self.project("product")
        self.provider([{"writes": {"test_app.py": CHANGED_TEST}}, {"writes": {"app.py": "VALUE = 2\n"}}, {}])
        result = runner.run(project, self.plan(project, STAGES["product"]), unattended=False)
        self.assertEqual(result["status"], "complete", result.get("error"))
        self.assertEqual(self.stages_started(project), STAGES["product"])
        self.assertEqual(len(self.calls()), 3, "the custom command stage starts no provider session")
        self.assertIn("docs-check", result["stage_evidence"])
        started = [e for e in self.events(project) if e["type"] == "run.started"]
        self.assertIs(started[0]["data"]["red_proof"], True)

    @owned_by(47)
    def test_B3_recovers_in_the_middle(self):
        self.fail("not implemented")

    @owned_by(18)
    def test_B4_usage_limit_pause_resume(self):
        from plovi import runner
        project = self.project("hobby")
        self.provider([{"writes": {"partial.py": "PARTIAL = 1\n"}, "usage_limit": RESETS_AT}, {}, {}])
        plan = self.plan(project, STAGES["hobby"])
        paused = runner.run(project, plan, unattended=False)
        self.assertEqual((paused["status"], paused.get("pause_reason"), paused.get("resets_at")), ("paused", "usage_limit", RESETS_AT))
        recorded = [e["data"] for e in self.events(project) if e["type"] == "run.paused"]
        self.assertEqual((recorded[-1].get("reason"), recorded[-1].get("resets_at")), ("usage_limit", RESETS_AT))
        result = runner.run(project, plan, resume=True, unattended=False)
        self.assertEqual(result["status"], "complete", result.get("error"))
        self.assertTrue((project.root / "partial.py").is_file(), "resume keeps the partial edit")
        self.assertEqual(len(self.calls()), 3)

    # ---- D: deliver ---------------------------------------------------------------------------

    @owned_by(49, 48)
    def test_D0_push_and_pr(self):
        # #48 adds: every claim in the PR's verification section matches a check plovi ran.
        from plovi import runner
        project = self.project("hobby")
        self.git(project.root, "switch", "--quiet", "-c", "plovi/sample")
        state_path = self.install_github_fake()
        self.provider([{"writes": {"app.py": "VALUE = 1  # delivered\n"}}])
        plan = self.plan(project, ["implement", "commit-and-push", "draft-pr"], files={"body.md": "Scenario plan body.\n"},
                         extra={"delivery": {"commit_message": "Deliver the scenario change", "title": "Scenario change",
                                             "body_file": "body.md"},
                                "plan_files": PLAN_FILES + ["body.md"],
                                "repositories": [{"id": "hobby", "access": "write", "paths": ["*.py"], "test_paths": ["test_*.py"],
                                                  "branch": "plovi/sample"}]})
        result = runner.run(project, plan, unattended=False)
        self.assertEqual(result["status"], "complete", result.get("error"))
        head = self.git(project.root, "rev-parse", "HEAD")
        self.assertEqual(self.git(self.root / "remotes/hobby.git", "rev-parse", "refs/heads/plovi/sample"), head)
        pulls = json.loads(state_path.read_text())["pulls"]
        self.assertEqual(len(pulls), 1)
        pull = next(iter(pulls.values()))
        self.assertEqual((pull["head"], pull["base"], pull["draft"]), ("plovi/sample", "main", True))
        self.assertIn("## Evidence", pull["body"])
        self.assertIn("behavior", pull["body"])
        self.assertIn("Scenario plan body.", pull["body"])
        opened = [e["data"] for e in self.events(project) if e["type"] == "pr.opened"]
        self.assertEqual(opened[0]["files_changed"], 1)

    @owned_by(23)
    def test_D1_readiness_tracked(self):
        self.fail("not implemented")

    @owned_by(23)
    def test_D2_ci_failure_fixed_same_pr(self):
        self.fail("not implemented")

    @owned_by(23)
    def test_D3_review_comment_fixed(self):
        self.fail("not implemented")

    @owned_by(23)
    def test_D4_auto_merge_policy(self):
        self.fail("not implemented")

    @owned_by(23)
    def test_D5_manual_merge_untouched(self):
        self.fail("not implemented")

    # ---- J: scheduled jobs --------------------------------------------------------------------

    @owned_by(20)
    def test_J1_daily_job_runs(self):
        self.fail("not implemented")

    @owned_by(50)
    def test_J2_tests_merged_changes_on_target(self):
        self.fail("not implemented")

    @owned_by(50)
    def test_J3_files_well_formed_issue(self):
        self.fail("not implemented")

    @owned_by(50)
    def test_J4_dedupe_caps_no_loop(self):
        self.fail("not implemented")

    @owned_by(20)
    def test_J5_budgets_stop_jobs(self):
        self.fail("not implemented")

    # ---- V: see and control --------------------------------------------------------------------

    @owned_by(18)
    def test_V1_status_and_inbox(self):
        project = self.project("hobby")
        self.provider([{"sleep": 2}, {"report": {"status": "needs_input", "question": "Ship the parser change?"}}])
        worker, outcome = self.run_in_thread(project, self.plan(project, STAGES["hobby"]))
        wait_for(lambda: self.calls(), timeout=30)
        running = json.loads(self.task_cli(project, "status", "sample", "--json").stdout)
        self.assertEqual(running["status"], "running")
        waiting = json.loads(self.task_cli(project, "inbox", "--format", "json").stdout)["items"]
        self.assertEqual([item for item in waiting if item["subject"]["id"] == "sample"], [], "a running task waits on nobody")
        worker.join(60)
        self.assertNotIn("error", outcome, outcome.get("error"))
        self.assertEqual(outcome["result"]["status"], "needs_input")
        stopped = json.loads(self.task_cli(project, "status", "sample", "--json").stdout)
        self.assertEqual(stopped["status"], "needs_input")
        items = json.loads(self.task_cli(project, "inbox", "--format", "json").stdout)["items"]
        self.assertEqual([(i["kind"], i["subject"]["id"]) for i in items], [("question", "sample")])
        self.assertIn("Ship the parser change?", items[0]["reason"])
        self.assertIn("answer", [action["operation"] for action in items[0]["actions"]])

    @owned_by(18)
    def test_V2_pause_resume_cancel(self):
        project = self.project("hobby")
        self.provider([{"sleep": 2}, {"report": {"status": "needs_input", "question": "Keep the old parser?"}}])
        worker, outcome = self.run_in_thread(project, self.plan(project, STAGES["hobby"]))
        wait_for(lambda: self.calls(), timeout=30)
        self.task_cli(project, "pause", "sample", "--reason", "Pause before review")
        worker.join(60)
        self.assertNotIn("error", outcome, outcome.get("error"))
        self.assertEqual((outcome["result"]["status"], outcome["result"]["completed"]), ("paused", ["implement"]))
        self.task_cli(project, "resume", "sample", "--reason", "Continue to review", check=False)
        self.assertEqual(json.loads(self.task_cli(project, "status", "sample", "--json").stdout)["status"], "needs_input")
        self.task_cli(project, "cancel", "sample", "--reason", "Superseded")
        types = [(e["type"], e["actor"]["kind"]) for e in self.events(project)
                 if e["type"] in {"pause.requested", "run.paused", "run.resumed", "question.asked", "cancel.requested"}]
        self.assertEqual(types, [("pause.requested", "person"), ("run.paused", "plovi"), ("run.resumed", "person"),
                                 ("question.asked", "plovi"), ("cancel.requested", "person")])
        self.assertEqual(len(self.calls()), 2, "resume ran only the remaining stage")

    @owned_by(19)
    def test_V3_app_board_inbox_actions(self):
        self.assert_app_test("V3")

    @owned_by(22)
    def test_V4_app_settings(self):
        self.assert_app_test("V4")

    @owned_by(25)
    def test_V5_take_over_hand_back(self):
        self.fail("not implemented")

    @owned_by(20, 23)
    def test_V6_pause_all_automation(self):
        self.fail("not implemented")

    @owned_by(47)
    def test_V7_status_explains_stop_and_cost(self):
        self.fail("not implemented")

    # ---- X: measure ------------------------------------------------------------------------------

    @owned_by(49)
    def test_X1_stats_gate(self):
        from plovi import runner
        project = self.project("hobby")
        self.provider([{"writes": {"app.py": "VALUE = 1  # implemented\n"}}, {}])
        self.assertEqual(runner.run(project, self.plan(project, STAGES["hobby"]), unattended=False)["status"], "complete")
        (project.root / ".github/workflows").mkdir(parents=True)
        (project.root / ".github/workflows/verify.yml").write_text(VERIFY)
        start = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        stamp = lambda seconds: (start + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
        runs = [{"id": n, "name": "Verify", "path": ".github/workflows/verify.yml", "head_branch": "main", "status": "completed",
                 "conclusion": "success", "run_attempt": 1} for n in range(30, 20, -1)]
        jobs = {str(n): [{"name": "smoke", "started_at": stamp(0), "completed_at": stamp(40)},
                         {"name": "core (ubuntu-latest, 3.14)", "started_at": stamp(0), "completed_at": stamp(130)}] for n in range(21, 31)}
        steps = {"B1": {"status": "passed", "owners": [49]}, "I1": {"status": "skipped", "owners": [21]}}
        self.install_github_fake({"actions": {"runs": runs, "jobs": jobs,
                                              "artifacts": {"30": {"scenario-results": {"scenario-results.json": {"steps": steps}}}}}})
        result = self.cli_inproc("--project", project.root, "stats", "--gate", "--json", check=False)
        self.assertEqual(result.returncode, 1, "one run cannot meet the gate")
        data = json.loads(result.stdout)
        self.assertEqual([(row["result"], len(row["interventions"]), sum(row["attempts"].values()), row["tokens"]) for row in data["runs"]],
                         [("complete", 0, 2, 30)])
        gate = {item["id"]: item for item in data["gate"]}
        self.assertEqual(sorted(gate), ["G1", "G2", "G3", "G4", "G5"])
        self.assertEqual({key: item["passed"] for key, item in gate.items()},
                         {"G1": True, "G2": False, "G3": False, "G4": False, "G5": True})
        for item in gate.values():
            self.assertRegex(item["detail"], r"\d", f"{item['id']} reports its numbers")
        text = self.cli_inproc("--project", project.root, "stats", "--gate", check=False)
        self.assertEqual(text.returncode, 1)
        self.assertIn("G1 PASS", text.stdout)
        self.assertIn("G3 FAIL", text.stdout)
