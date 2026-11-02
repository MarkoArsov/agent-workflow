"""Append-only ledger: envelope, type table, concurrency, torn lines, months, import and location."""
from __future__ import annotations
import contextlib
import io
import json
import multiprocessing
import os
import warnings
from pathlib import Path
from tests.helpers import PACKAGE, HardeningTest, WorkspaceTest
from tests.fixtures.control_plane import RUNNER, TIMESTAMP, ULID, ControlPlaneMixin, rows
from plovi import runner, state
from plovi.util import WorkflowError

RUN = "fixture-run"
PERSON = {"kind": "person", "name": "Fixture Person"}
# type: (sample data, fields whose absence must be rejected). Taken from requirements L3.
SAMPLES = {
    "task.created": ({"branches": {"app": "codex/sample"}, "issue": "example/repo#12", "title": "Fix the parser"}, ["branches"]),
    "task.claimed": ({"run_id": RUN}, ["run_id"]),
    "run.started": ({"run_id": RUN, "manifest": "plans/pipeline.json", "plan_sha256": "a" * 64},
                    ["run_id", "manifest", "plan_sha256"]),
    "stage.started": ({"run_id": RUN, "stage": "implement"}, ["run_id", "stage"]),
    "attempt.finished": ({"run_id": RUN, "stage": "implement", "attempt": 0, "classification": "complete",
                          "path": "attempts/0000.json"}, ["run_id", "stage", "attempt", "classification", "path"]),
    "stage.finished": ({"run_id": RUN, "stage": "implement", "result": "passed"}, ["run_id", "stage", "result"]),
    "question.asked": ({"run_id": RUN, "stage": "implement", "question": "Keep the parser?"}, ["run_id", "stage", "question"]),
    "question.answered": ({"run_id": RUN}, ["run_id"]),
    "plan.proposed": ({"plan_sha256": "a" * 64, "manifest": "plans/pipeline.json"}, ["plan_sha256", "manifest"]),
    "plan.approved": ({"plan_sha256": "a" * 64, "auto": False}, ["plan_sha256", "auto"]),
    "approval.requested": ({"run_id": RUN, "kind": "size", "fingerprint": "b" * 64}, ["run_id", "kind", "fingerprint"]),
    "approval.granted": ({"run_id": RUN, "kind": "size", "fingerprint": "b" * 64}, ["run_id", "kind", "fingerprint"]),
    "escalation.raised": ({"run_id": RUN, "stage": "implement", "kind": "blocked", "detail": "A person decides"},
                          ["run_id", "stage", "kind", "detail"]),
    "run.paused": ({"run_id": RUN, "status": "paused"}, []),
    "run.resumed": ({"run_id": RUN, "status": "running"}, []),
    "run.interrupted": ({"run_id": RUN, "status": "interrupted"}, []),
    "run.cancelled": ({"run_id": RUN, "status": "cancelled"}, []),
    "run.finished": ({"run_id": RUN, "status": "complete"}, ["run_id", "status"]),
    "delivery.committed": ({"repository": "app", "commit": "c" * 40}, ["repository", "commit"]),
    "delivery.pushed": ({"repository": "app", "branch": "codex/sample"}, ["repository", "branch"]),
    "pr.opened": ({"repository": "app", "url": "https://example.invalid/pull/1"}, ["repository", "url"]),
    "policy.changed": ({"diff": "-max_changed_files = 40\n+max_changed_files = 10\n"}, ["diff"]),
    "project.registered": ({"root": "/fixture/app"}, ["root"]),
    "state.checkpoint": ({"run_id": RUN, "state_sha256": "d" * 64, "keys": {"status": "e" * 64}},
                         ["run_id", "state_sha256", "keys"]),
    "pause.requested": ({"run_id": RUN}, []),
    "cancel.requested": ({"run_id": RUN}, []),
    "project.unregistered": ({"root": "/fixture/app"}, []),
}


def _subject(kind, project_id):
    if kind == "policy.changed":
        return {"kind": "policy", "id": project_id}
    if kind.startswith("project."):
        return {"kind": "project", "id": project_id}
    return {"kind": "task", "id": "sample"}


def _append_many(root, environment, worker, count):
    """Spawned child: append count events through the public API."""
    os.environ.clear(); os.environ.update(environment)
    from plovi.project import load
    from plovi import ledger
    project = load(Path(root), migrate=False)
    for number in range(count):
        ledger.append(project, {"subject": {"kind": "task", "id": "sample"}, "type": "stage.started",
                                "actor": dict(RUNNER), "reason": "Concurrency fixture",
                                "data": {"run_id": f"w{worker}-{number:04d}", "stage": "implement"}})


class LedgerTests(ControlPlaneMixin, WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.app = self.repo("app")
        self.project = self.setup_project(self.app)
        self.project_id = self.project.profile["project"]["id"]

    def append(self, kind, data, *, actor=None, reason="Fixture event", subject=None):
        from plovi import ledger
        return ledger.append(self.project, {"subject": subject or _subject(kind, self.project_id), "type": kind,
                                            "actor": actor or dict(PERSON), "reason": reason, "data": data})

    def test_append_read_round_trip(self):
        data = {"branches": {"app": "codex/sample"}, "title": "Fix the parser"}
        self.append("task.created", data, reason="Task started for the parser fix")
        self.append("task.claimed", {"run_id": RUN}, actor=dict(RUNNER), reason="Runner claimed the task")
        events = self.task_events()
        self.assertEqual([e["type"] for e in events], ["task.created", "task.claimed"])
        first, second = events
        self.assertEqual(first["v"], 1)
        self.assertRegex(first["id"], ULID.pattern + "$")
        self.assertRegex(first["at"], TIMESTAMP.pattern + "$")
        self.assertEqual(first["project"], self.project_id)
        self.assertEqual(first["subject"], {"kind": "task", "id": "sample"})
        self.assertEqual(first["actor"], PERSON)
        self.assertEqual(first["reason"], "Task started for the parser fix")
        self.assertEqual(first["data"]["branches"], data["branches"])
        self.assertEqual(first["data"]["title"], "Fix the parser")
        self.assertEqual(second["actor"], RUNNER)
        self.assertLess(first["id"], second["id"], "IDs sort in append order within one process")
        self.assertLessEqual(first["at"], second["at"])
        files = self.month_files()
        self.assertEqual([f.name for f in files], [f"events-{first['at'][:4]}-{first['at'][5:7]}.jsonl"])
        raw = files[0].read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        stored = [json.loads(line) for line in raw.splitlines()]
        self.assertIn(first, stored)
        self.assertIn(second, stored)
        self.assertNotIn(first["id"], [e["id"] for e in self.ledger_events(since=second["id"])])
        self.assertIn(second["id"], [e["id"] for e in self.ledger_events(since=first["at"])])
        self.assertEqual(self.ledger_events(since="2999-01-01T00:00:00.000Z"), [])

    def test_every_event_type_validates_against_schema(self):
        from plovi import ledger
        schema = json.loads((PACKAGE / "schemas/event.schema.json").read_text())
        self.assertLessEqual({"v", "id", "at", "project", "subject", "type", "actor", "reason", "data"},
                             set(schema.get("required", [])))
        enums = []
        def collect(node):
            if isinstance(node, dict):
                if isinstance(node.get("enum"), list):
                    enums.append(set(node["enum"]))
                for value in node.values(): collect(value)
            elif isinstance(node, list):
                for value in node: collect(value)
        collect(schema)
        self.assertIn(set(SAMPLES), enums, "the schema enumerates exactly the ledger event types")
        self.assertIn({"task", "schedule", "execution", "pr", "policy", "project"}, enums)
        self.assertIn({"person", "agent", "plovi"}, enums)
        tables = [value for value in vars(ledger).values() if isinstance(value, dict) and set(value) == set(SAMPLES)]
        self.assertTrue(tables, "ledger.py keeps a type table covering every event type")
        docs = (PACKAGE / "docs/ledger.md").read_text()
        for kind, (data, required) in SAMPLES.items():
            with self.subTest(kind=kind):
                self.assertIn(kind, docs)
                self.append(kind, dict(data))
                self.assertEqual(self.ledger_events()[-1]["type"], kind)
                for field in required:
                    with self.assertRaises(WorkflowError, msg=f"{kind} without {field}"):
                        self.append(kind, {k: v for k, v in data.items() if k != field})
        count = len(self.ledger_events())
        invalid = [
            {"subject": {"kind": "task", "id": "sample"}, "type": "task.exploded", "actor": dict(PERSON), "reason": "x", "data": {}},
            {"subject": {"kind": "galaxy", "id": "sample"}, "type": "task.claimed", "actor": dict(PERSON), "reason": "x", "data": {"run_id": RUN}},
            {"subject": {"kind": "task", "id": "sample"}, "type": "task.claimed", "actor": {"kind": "robot", "name": "x"}, "reason": "x", "data": {"run_id": RUN}},
            {"subject": {"kind": "task", "id": "sample"}, "type": "task.claimed", "actor": dict(PERSON), "reason": "", "data": {"run_id": RUN}},
            {"subject": {"kind": "task", "id": "sample"}, "type": "task.claimed", "actor": dict(PERSON), "data": {"run_id": RUN}},
        ]
        for event in invalid:
            with self.subTest(event=event), self.assertRaises(WorkflowError):
                ledger.append(self.project, event)
        self.assertEqual(len(self.ledger_events()), count, "rejected events append nothing")
        self.append("question.asked", {"run_id": RUN, "stage": "implement", "question": "Use token=abcdef1234567890 here?"},
                    reason="Provider asked with password=hunter2secret")
        stored = self.ledger_events()[-1]
        self.assertNotIn("abcdef1234567890", stored["data"]["question"])
        self.assertNotIn("hunter2secret", stored["reason"])

    def test_concurrent_processes_never_interleave(self):
        context = multiprocessing.get_context("spawn")
        workers = [context.Process(target=_append_many, args=(str(self.project.root), dict(os.environ), worker, 1000))
                   for worker in (0, 1)]
        for process in workers: process.start()
        for process in workers: process.join(300)
        self.assertEqual([p.exitcode for p in workers], [0, 0])
        raw = b"".join(path.read_bytes() for path in self.month_files())
        self.assertTrue(raw.endswith(b"\n"))
        events = [json.loads(line) for line in raw.split(b"\n")[:-1]]
        appended = [e for e in events if e["type"] == "stage.started"]
        self.assertEqual(len(appended), 2000)
        self.assertEqual({e["data"]["run_id"] for e in appended},
                         {f"w{w}-{n:04d}" for w in (0, 1) for n in range(1000)})
        self.assertEqual(len({e["id"] for e in events}), len(events))

    def test_torn_last_line_skipped_with_one_warning(self):
        self.append("task.claimed", {"run_id": RUN})
        self.append("stage.started", {"run_id": RUN, "stage": "implement"})
        newest = self.month_files()[-1]
        with newest.open("ab") as stream:
            stream.write(b'{"v": 1, "id": "01TORN')
        for _ in range(2):
            stderr = io.StringIO()
            with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stderr(stderr):
                warnings.simplefilter("always")
                events = self.ledger_events()
            self.assertEqual([e["type"] for e in events][-2:], ["task.claimed", "stage.started"])
            self.assertEqual(len(caught) + len([line for line in stderr.getvalue().splitlines() if line.strip()]), 1,
                             "exactly one warning per read call")
        lines = newest.read_bytes().split(b"\n")
        lines.insert(0, b"not json")
        newest.write_bytes(b"\n".join(lines))
        with self.assertRaises(WorkflowError):
            self.ledger_events()

    def test_month_rollover_reads_across_files(self):
        for number in range(3):
            self.append("stage.started", {"run_id": f"month-{number}", "stage": "implement"})
        current = self.month_files()[-1]
        lines = current.read_bytes().splitlines()
        events = [json.loads(line) for line in lines]
        moved = [e for e in events if e["type"] == "stage.started"]
        kept = [line for line, e in zip(lines, events) if e not in moved[:2]]
        directory = self.ledger_directory()
        for event, month in zip(moved[:2], ("2001-01", "2001-02")):
            older = dict(event, at=f"{month}-15T12:00:00.000Z")
            (directory / f"events-{month}.jsonl").write_bytes(json.dumps(older).encode() + b"\n")
        current.write_bytes(b"".join(line + b"\n" for line in kept))
        read = [e for e in self.ledger_events() if e["type"] == "stage.started"]
        self.assertEqual([e["data"]["run_id"] for e in read], ["month-0", "month-1", "month-2"])
        self.assertEqual([e["at"][:7] for e in read][:2], ["2001-01", "2001-02"])
        since = [e["data"]["run_id"] for e in self.ledger_events(since="2001-02-01T00:00:00.000Z") if e["type"] == "stage.started"]
        self.assertEqual(since, ["month-1", "month-2"])

    def test_state_import_is_idempotent(self):
        # Evidence predates the project's first ledger use, including any setup registration.
        legacy = {"legacy-failed": ("failed", ["implement-tests"]),
                  "legacy-done": ("complete", ["implement-tests", "implement", "review"])}
        app = self.repo("legacy-app")
        for task, (status, completed) in legacy.items():
            state.save(app / ".plovi/local/evidence" / task, {
                "schema_version": 1, "task": task, "run_id": task + "-run", "status": status,
                "completed": completed, "attempts": [], "started_at": 1_700_000_000.0,
                "manifest_path": str(app / "plans/pipeline.json")})
        self.project = self.setup_project(app)
        for task in legacy:
            self.assertTrue((state.directory(self.project, task) / "state.json").is_file(), "fixture evidence location")
        first = self.ledger_events()
        for task, (status, completed) in legacy.items():
            with self.subTest(task=task):
                events = [e for e in first if e["subject"] == {"kind": "task", "id": task}]
                types = [e["type"] for e in events]
                for kind in ("task.created", "run.started", "stage.finished", "run.finished", "state.checkpoint"):
                    self.assertIn(kind, types)
                self.assertTrue(all(e["data"].get("imported") is True for e in events))
                self.assertEqual([e["data"]["stage"] for e in events if e["type"] == "stage.finished"], completed)
                self.assertEqual([e["data"]["status"] for e in events if e["type"] == "run.finished"], [status])
        self.assertTrue((self.ledger_directory() / "imported.json").is_file())
        self.assertEqual(self.ledger_events(), first)
        self.append("task.claimed", {"run_id": "after-import"})
        self.assertEqual(self.ledger_events()[:len(first)], first)
        self.assertEqual(len(self.ledger_events()), len(first) + 1)

    def test_ledger_lives_outside_repository_and_worktrees(self):
        before = sorted(p.relative_to(self.app).as_posix() for p in self.app.rglob("*") if ".git" not in p.parts)
        self.append("task.claimed", {"run_id": RUN})
        from plovi.util import user_data
        directory = self.ledger_directory()
        self.assertTrue(self.month_files(), "events were written under the per-project user data root")
        self.assertTrue(directory.resolve().is_relative_to(user_data().resolve()))
        self.assertFalse(directory.resolve().is_relative_to(self.app.resolve()))
        after = sorted(p.relative_to(self.app).as_posix() for p in self.app.rglob("*") if ".git" not in p.parts)
        self.assertEqual(before, after, "the ledger writes nothing inside the project")
        for inside in (self.app / "data", self.app / ".plovi/local/worktrees/data"):
            with self.subTest(inside=inside):
                os.environ["XDG_DATA_HOME"] = str(inside)
                with self.assertRaises(WorkflowError):
                    self.append("task.claimed", {"run_id": RUN})
                self.assertFalse(list(inside.rglob("events-*.jsonl")))

    def test_oversized_event_rejected(self):
        self.append("task.claimed", {"run_id": RUN})
        size = sum(len(p.read_bytes()) for p in self.month_files())
        large = {f"repository-{n:04d}": "b" * 100 for n in range(700)}
        with self.assertRaises(WorkflowError):
            self.append("task.created", {"branches": large})
        self.assertEqual(sum(len(p.read_bytes()) for p in self.month_files()), size)


class LedgerCliTests(ControlPlaneMixin, HardeningTest):
    def test_runner_transitions_are_listed_by_events(self):
        self.fixture([{}], stages=["implement"])
        result = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(result["status"], "complete")
        response = self.task_cli("events", "--task", "sample")
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        events = rows(json.loads(response.stdout), "events")
        self.assertTrue(events)
        self.assertTrue(all(e["subject"] == {"kind": "task", "id": "sample"} for e in events))
        types = [e["type"] for e in events]
        self.assert_subsequence(types, ["task.claimed", "run.started", "stage.started", "attempt.finished",
                                        "stage.finished", "run.finished"])
        self.assertIn("state.checkpoint", types)
        runner_events = [e for e in events if e["type"] in {"task.claimed", "run.started", "stage.started",
                                                            "attempt.finished", "stage.finished", "run.finished"}]
        self.assertTrue(all(e["actor"] == RUNNER for e in runner_events))
        self.assertTrue(all(e["data"]["run_id"] == result["run_id"] for e in runner_events))
        by_type = {e["type"]: e for e in events}
        self.assertEqual(by_type["stage.started"]["data"]["stage"], "implement")
        self.assertEqual(by_type["run.finished"]["data"]["status"], "complete")
        attempt = Path(by_type["attempt.finished"]["data"]["path"])
        if not attempt.is_absolute():
            attempt = state.directory(self.project, "sample") / attempt
        self.assertTrue(attempt.is_file(), "attempt.finished references the retained attempt file")
        started = by_type["run.started"]["id"]
        later = rows(self.cli_json("events", "--task", "sample", "--since", started), "events")
        self.assertTrue(later)
        self.assertTrue(all(e["id"] >= started for e in later))
        text = self.ok(self.task_cli("events", "--task", "sample", "--format", "text")).stdout
        self.assertTrue(text.strip())
        with self.assertRaises(ValueError):
            json.loads(text)
