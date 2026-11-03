"""plovi stats: logical runs and interventions from the ledger, and the stable-enough gate."""
import json
from datetime import datetime, timedelta, timezone
from tests.helpers import WorkspaceTest

PERSON = {"kind": "person", "name": "Dana"}
OTHER = {"kind": "person", "name": "Sam"}
AGENT = {"kind": "agent", "name": "fixture-agent", "via": "cli"}
RUNNER = {"kind": "plovi", "name": "runner"}
START = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
VERIFY = """name: Verify
on:
  push:
jobs:
  smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo smoke
  core:
    name: core (${{ matrix.os }}, ${{ matrix.python }})
    timeout-minutes: 25
    steps:
      - name: Run isolated unit tests
        timeout-minutes: 20
        run: echo tests
"""


class Ledger:
    """Build an in-memory event list in ledger order, one minute apart."""

    def __init__(self):
        self.events, self.minute = [], 0

    def add(self, task, kind, data=None, actor=RUNNER, reason="Fixture event"):
        at = START + timedelta(minutes=self.minute)
        self.minute += 1
        self.events.append({"v": 1, "id": f"{len(self.events):026d}", "at": at.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                            "project": "fixture", "subject": {"kind": "task", "id": task}, "type": kind, "actor": actor,
                            "reason": reason, "data": data or {}})
        return self

    def run(self, task, run_id, *, red=False, provider="codex", tokens=None, cost=None, kind=None):
        self.add(task, "run.started", {"run_id": run_id, "manifest": "pipeline.json", "plan_sha256": "a" * 64, "red_proof": red})
        data = {"run_id": run_id, "stage": "implement", "attempt": 0, "classification": "complete", "path": "a.json", "provider": provider}
        if tokens:
            data["usage"] = {"input_tokens": tokens[0], "output_tokens": tokens[1]}
        if cost is not None:
            data["cost_usd"] = cost
        if kind:
            data["kind"] = kind
        return self.add(task, "attempt.finished", data)

    def pr(self, task, files=3):
        return self.add(task, "pr.opened", {"repository": "app", "url": f"https://example.invalid/pull/{task}", "files_changed": files})


def six_runs():
    """The issue's fixture: answer, retry after escalation, clean, clean with plan approval, foreign commit, own pause."""
    book = Ledger()
    book.run("answer", "r1").add("answer", "question.asked", {"run_id": "r1", "stage": "implement", "question": "Keep it?"})
    book.add("answer", "run.finished", {"run_id": "r1", "status": "needs_input"})
    book.add("answer", "question.answered", {"run_id": "r1"}, actor=PERSON)
    book.add("answer", "run.resumed", {"run_id": "r1", "status": "needs_input"}, actor=PERSON)
    book.run("answer", "r1b").add("answer", "run.finished", {"run_id": "r1b", "status": "complete"})

    book.run("retry", "r2").add("retry", "escalation.raised", {"run_id": "r2", "stage": "implement", "kind": "blocked", "detail": "Unclear"})
    book.add("retry", "run.finished", {"run_id": "r2", "status": "escalated"})
    book.add("retry", "run.resumed", {"run_id": "r2", "status": "escalated", "retry": True}, actor=PERSON)
    book.run("retry", "r2b").pr("retry")

    book.run("clean", "r3").pr("clean")

    book.add("approved", "plan.approved", {"plan_sha256": "a" * 64, "auto": False}, actor=PERSON)
    book.run("approved", "r4").pr("approved")

    book.run("foreign", "r5").add("foreign", "commits.adopted", {"run_id": "r5", "author": "Sam"}, actor=RUNNER)
    book.pr("foreign")

    book.run("paused", "r6").add("paused", "pause.requested", {"run_id": "r6"}, actor=PERSON)
    book.add("paused", "run.paused", {"run_id": "r6", "status": "paused"})
    book.add("paused", "run.resumed", {"run_id": "r6", "status": "paused"}, actor=PERSON)
    book.run("paused", "r6b").pr("paused")
    return book.events


class RunTests(WorkspaceTest):
    def test_interventions_in_the_six_run_fixture(self):
        from plovi import stats
        rows = stats.runs(six_runs())
        self.assertEqual([row["task"] for row in rows], ["answer", "retry", "clean", "approved", "foreign", "paused"])
        self.assertEqual([len(row["interventions"]) for row in rows], [1, 1, 0, 0, 1, 0])
        self.assertEqual([i["type"] for i in rows[0]["interventions"]], ["question.answered"])
        self.assertEqual([i["type"] for i in rows[1]["interventions"]], ["run.resumed"])
        self.assertEqual([i["type"] for i in rows[4]["interventions"]], ["commits.adopted"])

    def test_a_resumed_run_is_one_logical_run_with_its_stops_and_attempts(self):
        from plovi import stats
        row = stats.runs(six_runs())[1]
        self.assertEqual((row["result"], row["attempts"]), ("pull-request", {"attempt": 2}))
        self.assertEqual([stop["type"] for stop in row["stops"]], ["escalation.raised"])
        self.assertEqual(row["duration_seconds"], 7 * 60)

    def test_cancel_then_restart_counts_on_the_cancelled_run(self):
        from plovi import stats
        book = Ledger()
        book.run("redo", "c1").add("redo", "cancel.requested", {"run_id": "c1"}, actor=PERSON)
        book.add("redo", "run.cancelled", {"run_id": "c1", "status": "cancelled"})
        book.run("redo", "c2").pr("redo")
        book.run("dropped", "c3").add("dropped", "run.cancelled", {"run_id": "c3", "status": "cancelled"})
        rows = stats.runs(book.events)
        self.assertEqual([(r["task"], r["result"], len(r["interventions"])) for r in rows],
                         [("redo", "cancelled", 1), ("redo", "pull-request", 0), ("dropped", "cancelled", 0)])

    def test_resume_after_failure_counts_unless_the_same_person_paused(self):
        from plovi import stats
        book = Ledger()
        book.run("failed", "f1").add("failed", "run.finished", {"run_id": "f1", "status": "failed", "error": "boom"})
        book.add("failed", "run.resumed", {"run_id": "f1", "status": "failed"}, actor=PERSON)
        book.run("failed", "f2").add("failed", "run.finished", {"run_id": "f2", "status": "complete"})
        book.run("mine", "m1").add("mine", "pause.requested", {"run_id": "m1"}, actor=PERSON)
        book.add("mine", "run.interrupted", {"run_id": "m1", "status": "interrupted"})
        book.add("mine", "run.resumed", {"run_id": "m1", "status": "interrupted"}, actor=PERSON)
        book.run("mine", "m2").add("mine", "run.finished", {"run_id": "m2", "status": "complete"})
        book.run("theirs", "t1").add("theirs", "pause.requested", {"run_id": "t1"}, actor=PERSON)
        book.add("theirs", "run.interrupted", {"run_id": "t1", "status": "interrupted"})
        book.add("theirs", "run.resumed", {"run_id": "t1", "status": "interrupted"}, actor=OTHER)
        book.run("theirs", "t2").add("theirs", "run.finished", {"run_id": "t2", "status": "complete"})
        self.assertEqual([len(r["interventions"]) for r in stats.runs(book.events)], [1, 0, 1])

    def test_person_actor_events_count_and_agent_or_plan_approvals_do_not(self):
        from plovi import stats
        book = Ledger()
        book.run("mixed", "x1")
        book.add("mixed", "question.answered", {"run_id": "x1"}, actor=AGENT)
        book.add("mixed", "approval.granted", {"run_id": "x1", "kind": "size", "fingerprint": "b" * 64}, actor=PERSON)
        book.add("mixed", "approval.granted", {"run_id": "x1", "kind": "plan", "fingerprint": "c" * 64}, actor=PERSON)
        book.add("mixed", "plan.approved", {"plan_sha256": "a" * 64, "auto": False}, actor=PERSON)
        book.add("mixed", "plan.rebound", {"run_id": "x1"}, actor=PERSON)
        book.add("mixed", "checkpoint.migrated", {"binding_sha256": "d" * 64}, actor=PERSON)
        book.add("mixed", "handoff.started", {"run_id": "x1"}, actor=PERSON)
        book.add("mixed", "commits.adopted", {"run_id": "x1", "author": "plovi"})
        book.pr("mixed")
        row = stats.runs(book.events)[0]
        self.assertEqual([i["type"] for i in row["interventions"]],
                         ["approval.granted", "plan.rebound", "checkpoint.migrated", "handoff.started"])

    def test_attempt_kinds_tokens_and_cost(self):
        from plovi import stats
        book = Ledger()
        book.run("known", "k1", tokens=(100, 40), cost=0.5)
        book.add("known", "attempt.finished", {"run_id": "k1", "stage": "review", "attempt": 1, "classification": "complete",
                                               "path": "b.json", "kind": "challenge", "usage": {"input_tokens": 7, "output_tokens": 3}})
        book.add("known", "attempt.finished", {"run_id": "k1", "stage": "implement", "attempt": 2, "classification": "complete",
                                               "path": "c.json", "kind": "fix"})
        book.pr("known")
        book.run("unknown", "u1").pr("unknown")
        known, unknown = stats.runs(book.events)
        self.assertEqual(known["attempts"], {"attempt": 1, "challenge": 1, "fix": 1})
        self.assertEqual((known["challenges"], known["fix_rounds"]), (1, 1))
        self.assertEqual((known["tokens"], known["cost_usd"]), (150, 0.5))
        self.assertEqual((unknown["tokens"], unknown["cost_usd"]), (None, None))

    def test_open_runs_report_their_last_stop(self):
        from plovi import stats
        book = Ledger()
        book.run("open", "o1").add("open", "run.paused", {"run_id": "o1", "status": "paused", "reason": "usage_limit", "next": "plovi resume open"})
        row = stats.runs(book.events)[0]
        self.assertEqual((row["result"], row["finished"]), ("paused", None))
        self.assertEqual(row["stops"][0]["next"], "plovi resume open")

    def test_totals(self):
        from plovi import stats
        rows = stats.runs(six_runs())
        totals = stats.totals(rows)
        self.assertEqual((totals["runs"], totals["interventionless"]), (6, 3))
        self.assertIsNone(totals["tokens_per_run"])
        self.assertGreater(totals["median_duration_seconds"], 0)

    def test_since_accepts_a_date_or_a_duration(self):
        from plovi import stats
        rows = stats.runs(six_runs())
        later = stats.since(rows, "2026-10-01T09:20:00Z")
        self.assertEqual([r["task"] for r in later], ["approved", "foreign", "paused"])
        self.assertEqual(stats.since(rows, "1d", now=START + timedelta(days=3)), [])
        self.assertEqual(len(stats.since(rows, "3d", now=START + timedelta(days=2))), 6)
        with self.assertRaises(Exception):
            stats.since(rows, "yesterday")


def gate_runs(*, intervention=None, missing_next=False):
    """Five interventionless pipeline runs: two large, one with red proof, both providers."""
    book = Ledger()
    plan = [("g1", 12, False, "claude"), ("g2", 15, True, "codex"), ("g3", 3, False, "codex"),
            ("g4", 4, False, "claude"), ("g5", 5, False, "codex")]
    for task, files, red, provider in plan:
        book.run(task, task + "-run", red=red, provider=provider)
        book.add(task, "run.paused", {"run_id": task + "-run", "status": "paused", "reason": "budget",
                                      **({} if missing_next and task == "g4" else {"next": f"plovi resume {task}"})})
        if task == intervention:
            book.add(task, "question.answered", {"run_id": task + "-run"}, actor=PERSON)
        book.run(task, task + "-run2", provider=provider).pr(task, files)
    return book.events


class GateTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        root = self.repo("app")
        (root / ".github/workflows").mkdir(parents=True)
        (root / ".github/workflows/verify.yml").write_text(VERIFY)
        self.project = self.setup_project(root, {"repositories": [{"id": "app", "github": "octo/sample"}]})
        self.local = root / ".plovi/local/stats/local-suite.json"
        self.local.parent.mkdir(parents=True, exist_ok=True)
        self.local.write_text(json.dumps({"cpu_count": 4, "jobs": 4, "seconds": 200, "date": "2026-11-01"}))
        self.state = self.install_github_fake(self.actions())

    def actions(self, *, rerun=None, slow_ubuntu=False, scenario=None):
        runs, jobs = [], {}
        for number in range(110, 100, -1):
            runs.append({"id": number, "name": "Verify", "path": ".github/workflows/verify.yml", "head_branch": "main",
                         "head_sha": f"{number:040x}", "status": "completed", "conclusion": "success",
                         "run_attempt": 2 if number == rerun else 1})
            ubuntu = 200 if slow_ubuntu else 120
            jobs[str(number)] = [self.job("smoke", 60), self.job("core (ubuntu-latest, 3.14)", ubuntu),
                                 self.job("core (windows-latest, 3.14)", 600)]
        steps = scenario or {"U1": {"status": "passed", "owners": [49]}, "B3": {"status": "passed", "owners": [47]},
                             "I1": {"status": "skipped", "owners": [21]}, "D0": {"status": "passed", "owners": [49, 48]}}
        return {"repo": "octo/sample", "actions": {"runs": runs, "jobs": jobs, "logs": {},
                                                   "artifacts": {"110": {"scenario-results": {"scenario-results.json": {"steps": steps}}}}}}

    @staticmethod
    def job(name, seconds):
        start = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        end = start + timedelta(seconds=seconds)
        return {"name": name, "status": "completed", "conclusion": "success",
                "started_at": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "completed_at": end.strftime("%Y-%m-%dT%H:%M:%SZ")}

    def script(self, **values):
        self.state.write_text(json.dumps(self.actions(**values)))

    def evaluate(self, events=None):
        from plovi import stats
        return {item["id"]: item for item in stats.gate(self.project, stats.runs(events if events is not None else gate_runs()))}

    def test_all_criteria_pass(self):
        result = self.evaluate()
        self.assertEqual({key: value["passed"] for key, value in result.items()},
                         {"G1": True, "G2": True, "G3": True, "G4": True, "G5": True}, json.dumps(result, indent=1))
        self.assertIn("10 of the last 10", result["G1"]["detail"])
        self.assertIn("20 min", result["G1"]["detail"])

    def test_g1_fails_on_a_rerun(self):
        self.script(rerun=105)
        result = self.evaluate()
        self.assertFalse(result["G1"]["passed"])
        self.assertIn("9 of the last 10", result["G1"]["detail"])
        self.assertTrue(result["G2"]["passed"])

    def test_g2_fails_on_slow_ubuntu_suite_or_local_suite(self):
        self.script(slow_ubuntu=True)
        result = self.evaluate()
        self.assertFalse(result["G2"]["passed"])
        self.assertIn("200 s", result["G2"]["detail"])
        self.script()
        self.local.write_text(json.dumps({"cpu_count": 4, "jobs": 4, "seconds": 300, "date": "2026-11-01"}))
        result = self.evaluate()
        self.assertFalse(result["G2"]["passed"])
        self.assertIn("300 s", result["G2"]["detail"])
        self.local.unlink()
        self.assertIn("--record", self.evaluate()["G2"]["detail"])

    def test_g3_fails_when_an_intervention_restarts_the_count(self):
        result = self.evaluate(gate_runs(intervention="g2"))
        self.assertFalse(result["G3"]["passed"])
        self.assertIn("3 consecutive", result["G3"]["detail"])

    def test_g3_needs_large_runs_red_proof_and_both_providers(self):
        from plovi import stats
        rows = stats.runs(gate_runs())
        for row in rows:
            row["providers"] = ["codex"]
        result = {item["id"]: item for item in stats.gate(self.project, rows)}
        self.assertFalse(result["G3"]["passed"])
        self.assertIn("claude", result["G3"]["detail"])

    def test_g4_fails_when_a_stop_has_no_next_command(self):
        result = self.evaluate(gate_runs(missing_next=True))
        self.assertTrue(result["G3"]["passed"])
        self.assertFalse(result["G4"]["passed"])
        self.assertIn("4 of 5 stops", result["G4"]["detail"])

    def test_g5_fails_when_a_done_step_fails(self):
        self.script(scenario={"U1": {"status": "failed", "owners": [49]}, "I1": {"status": "skipped", "owners": [21]}})
        result = self.evaluate()
        self.assertFalse(result["G5"]["passed"])
        self.assertIn("U1", result["G5"]["detail"])

    def test_missing_github_data_is_a_failure_not_a_crash(self):
        self.state.write_text(json.dumps({"repo": "octo/sample"}))
        result = self.evaluate([])
        self.assertEqual({key: value["passed"] for key, value in result.items()},
                         {"G1": False, "G2": False, "G3": False, "G4": False, "G5": False})
        self.assertIn("0 of the last 10", result["G1"]["detail"])

    def test_cli_prints_every_criterion_and_exits_by_the_gate(self):
        from plovi import ledger
        for event in gate_runs():
            ledger.append(self.project, {key: event[key] for key in ("subject", "type", "actor", "reason", "data")})
        passed = self.cli_inproc("--project", self.project.root, "stats", "--gate", check=False)
        self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
        for name in ("G1 PASS", "G2 PASS", "G3 PASS", "G4 PASS", "G5 PASS"):
            self.assertIn(name, passed.stdout)
        self.script(rerun=101)
        failed = self.cli_inproc("--project", self.project.root, "stats", "--gate", "--json", check=False)
        self.assertEqual(failed.returncode, 1)
        data = json.loads(failed.stdout)
        self.assertEqual((data["gate"][0]["id"], data["gate"][0]["passed"], data["passed"]), ("G1", False, False))
        self.assertEqual(len(data["runs"]), 5)
        table = self.cli_inproc("--project", self.project.root, "stats", "--task", "g1")
        self.assertIn("g1", table.stdout)
        self.assertNotIn("g2", table.stdout)
        self.assertIn("Runs: 1", table.stdout)
