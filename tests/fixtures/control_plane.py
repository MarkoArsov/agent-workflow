"""Shared helpers for control-plane tests.

Product modules that do not exist before the change (plovi.ledger, plovi.operations)
are imported inside helper methods, never at module level, so missing behavior is an
assertion failure rather than an import error.

Contract choices these helpers encode (requirements leave them open):
- Task-related ledger events use the subject {"kind": "task", "id": <task>}.
- JSON listings may be a bare list or an object holding the list under a named key
  ("items" for inbox, "events" for events, "projects" for projects list,
  "operations" for commands).
- High-risk previews expose their digest under "digest"; plan previews expose
  "plan_sha256" and "plan_files".
"""
from __future__ import annotations
import json
import re
import time

ULID = re.compile(r"[0-9A-HJKMNP-TV-Z]{26}")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")
RUNNER = {"kind": "plovi", "name": "runner"}
AGENT = {"kind": "agent", "name": "helper", "via": "plovi-factory"}
AGENT_FLAGS = ("--actor-agent", "helper", "--via", "plovi-factory")


def rows(value, key):
    """Accept a bare JSON list or an object that holds the list under key."""
    if isinstance(value, dict) and isinstance(value.get(key), list):
        return value[key]
    return value


class ControlPlaneMixin:
    def ledger_directory(self, project=None):
        from plovi.util import user_data
        project = project or self.project
        return user_data() / "projects" / project.profile["project"]["id"] / "ledger"

    def month_files(self, project=None):
        return sorted(self.ledger_directory(project).glob("events-*.jsonl"))

    def ledger_events(self, project=None, **filters):
        from plovi import ledger
        return ledger.events(project or self.project, **filters)

    def task_events(self, task="sample", project=None):
        return [e for e in self.ledger_events(project) if e["subject"] == {"kind": "task", "id": task}]

    def task_types(self, task="sample", project=None):
        return [e["type"] for e in self.task_events(task, project)]

    def of_type(self, kind, task="sample", project=None):
        return [e for e in self.task_events(task, project) if e["type"] == kind]

    def ok(self, response):
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        return response

    def cli_json(self, *args):
        return json.loads(self.ok(self.task_cli(*args)).stdout)

    def inbox(self):
        return rows(self.cli_json("inbox"), "items")

    def task_inbox(self, task="sample"):
        return [item for item in self.inbox() if item["subject"] == {"kind": "task", "id": task}]

    def factory_ready(self):
        """Non-TTY CLI launches use factory checkouts, which need an approved feature branch."""
        self.plan["repositories"][0]["branch"] = "codex/sample"
        self.save_plan()

    def plan_preview(self, task="sample"):
        return self.cli_json("approve", task, "--plan", "--manifest", self.manifest_path)

    def assert_subsequence(self, observed, expected):
        position = 0
        for value in observed:
            if position < len(expected) and value == expected[position]:
                position += 1
        self.assertEqual(position, len(expected), f"{expected} is not an ordered subsequence of {observed}")

    def wait_for(self, predicate, timeout=60, message="condition"):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                return value
            time.sleep(0.1)
        self.fail(f"Timed out waiting for {message}")
