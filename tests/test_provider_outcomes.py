"""Provider outcomes: usage limits pause cleanly and reports may follow prose (G4, G5)."""
from __future__ import annotations
import json
from tests.helpers import HardeningTest, WorkspaceTest

RESETS_AT = 1793631600
NOISE = {"type": "assistant", "message": {"content": [{"type": "text", "text": "Fixing authentication: unauthorized tokens are rejected."}]}}
LIMIT = {"type": "result", "subtype": "success", "is_error": True, "api_error_status": 429,
         "api_error": "usage_limit_reached", "result": "You've hit your 5-hour limit",
         "rate_limit_info": {"status": "rejected", "resetsAt": RESETS_AT, "rateLimitType": "five_hour"}}


def feed(lines):
    from plovi import providers
    events = providers.Events()
    for line in lines:
        events.line(json.dumps(line))
    return events


def outcome(lines, exit_code=1):
    from plovi import providers
    events = feed(lines)
    output = "\n".join(json.dumps(line) for line in lines)
    return providers.classify({"reason": None, "exit_code": exit_code, "output": output}, events), events


def result_text(text):
    return {"type": "result", "subtype": "success", "is_error": False, "result": text}


class UsageLimitTests(HardeningTest):
    def limited_run(self):
        self.fixture([{"writes": {"partial.py": "PARTIAL = 1\n"}, "usage_limit": RESETS_AT}, {}], stages=["implement"])
        self.plan["routes"] = {"implement": [{"provider": "codex", "model": "fixture-a"},
                                             {"provider": "codex", "model": "fixture-b"}]}
        self.save_plan()
        from plovi import manifest, runner
        self.plan = manifest.load(self.manifest_path, self.project)
        return runner.run(self.project, self.plan, unattended=False)

    def test_usage_limit_classified_from_structured_result_not_transcript(self):
        classification, events = outcome([NOISE, LIMIT])
        self.assertEqual(classification, "usage_limit")
        self.assertEqual(getattr(events, "resets_at", None), RESETS_AT)
        # Words in the transcript alone never decide the failure kind.
        plain, _ = outcome([NOISE])
        self.assertEqual(plain, "transient")

    def test_usage_limit_skips_same_provider_fallback_and_pauses(self):
        result = self.limited_run()
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result.get("pause_reason"), "usage_limit")
        self.assertEqual(result.get("resets_at"), RESETS_AT)
        self.assertEqual(len(self.calls()), 1, "the fallback on the same provider shares the limit")
        from plovi import ledger
        paused = [e for e in ledger.events(self.project) if e["type"] == "run.paused"]
        self.assertEqual(paused[-1]["data"].get("reason"), "usage_limit")

    def test_resume_after_usage_limit_keeps_partial_edits(self):
        self.assertEqual(self.limited_run()["status"], "paused")
        from plovi import runner
        result = runner.run(self.project, self.plan, resume=True, unattended=False)
        self.assertEqual(result["status"], "complete", result.get("error"))
        self.assertTrue((self.project.root / "partial.py").exists(), "the interrupted attempt's edit is kept")
        self.assertEqual(len(self.calls()), 2)

    def test_usage_limit_appears_in_inbox_with_resume_action(self):
        self.assertEqual(self.limited_run()["status"], "paused")
        from plovi.operations import inbox
        items, _ = inbox.collect({"project": str(self.project.root)})
        limited = [i for i in items if i["kind"] == "usage_limit"]
        self.assertEqual(len(limited), 1, items)
        self.assertIn("resume", [a["operation"] for a in limited[0]["actions"]])


class ReportParsingTests(WorkspaceTest):
    def test_prose_then_bare_json_report_is_accepted(self):
        events = feed([result_text("I could not fix the two failing checks.\n\n"
                                   '{"status": "blocked", "reason": "mkdocs is not installed"}')])
        report = events.report()
        self.assertIsNotNone(report)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["reason"], "mkdocs is not installed")

    def test_invalid_trailing_json_is_still_rejected(self):
        for tail in ('{"status": "done"}', '{"status": "blocked"}', '{"status": "blocked", "reason": '):
            with self.subTest(tail=tail):
                self.assertIsNone(feed([result_text("Some prose first.\n" + tail)]).report())
