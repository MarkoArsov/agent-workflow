"""Claim only what ran (#48): the runner's evidence is the PR's only verification section."""
import json
import re
from tests.helpers import PACKAGE, HardeningTest
from plovi import ledger
from plovi.evidence import evidence_markdown

BODY = ("## What changed\n\nVerified with `mkdocs build --strict` and `python3 -m unittest -v test_app`.\n\n"
        "```bash\nnpm test\n```\n\nThe `VALUE` constant and `app.py` are not commands.\n")


def verified(*commands):
    checks = [{"id": f"check{n}", "passed": True, "command": command, "duration_seconds": 1.25, "skipped": 0,
               "counts": {"tests": 3, "failures": 0, "errors": 0, "skipped": 0}} for n, command in enumerate(commands)]
    return {"green": {"checks": checks, "fingerprint": "f1"}, "completed": [], "attempts": [], "diff": {}}


class ClaimTests(HardeningTest):
    def setUp(self):
        super().setUp()
        self.fixture([])

    def mentioned(self, body):
        match = re.search(r"### Mentioned but not run by plovi\n\n(.*?)\n<!-- plovi:evidence:end -->", body, re.S)
        return re.findall(r"^- `(.+)`$", match[1], re.M) if match else []

    def test_evidence_lists_each_check_command_result_and_duration(self):
        state = verified("/usr/bin/python3 -m unittest -v test_app")
        state["green"]["checks"][0].update(skipped=2, reused=True, approved_skip_reason="Docker is opt-in")
        body = evidence_markdown(state, self.plan)
        self.assertIn("## Verification (from plovi's evidence)", body)
        self.assertIn("- check0: passed, `/usr/bin/python3 -m unittest -v test_app` (1.2 s; skipped: 2, Docker is opt-in; reused)", body)

    def test_body_lists_mentioned_but_unrun_commands(self):
        state = verified("/usr/bin/python3 -m unittest -v test_app")
        body = evidence_markdown(state, self.plan, BODY)
        self.assertEqual(self.mentioned(body), ["mkdocs build --strict", "npm test"])
        self.assertLess(body.index("## Verification"), body.index("### Mentioned but not run by plovi"))

    def test_no_flag_when_all_mentioned_commands_ran(self):
        state = verified("/usr/bin/python3 -m unittest -v test_app", ".venv/bin/python -m mkdocs build --strict", "npm test")
        body = evidence_markdown(state, self.plan, BODY)
        self.assertNotIn("Mentioned but not run", body)
        self.assertEqual(body, evidence_markdown(state, self.plan, BODY), "rendering is stable")

    def test_interpreter_prefix_counts_as_run(self):
        state = verified(".venv/bin/python -m mkdocs build --strict")
        for written in ("mkdocs build", "python -m mkdocs build --strict", "python3.11 -m mkdocs build --strict"):
            with self.subTest(written=written):
                self.assertEqual(self.mentioned(evidence_markdown(state, self.plan, f"Ran `{written}`.")), [])
        # A longer command than the one that ran is still a claim.
        self.assertEqual(self.mentioned(evidence_markdown(state, self.plan, "Ran `mkdocs build --strict --clean`.")),
                         ["mkdocs build --strict --clean"])

    def test_template_has_no_verification_section(self):
        template = (PACKAGE / "templates/pr-body.md").read_text()
        headings = re.findall(r"^#+\s*(.+)$", template, re.M)
        self.assertIn("What changes for your workflow", headings)
        for heading in headings:
            self.assertNotRegex(heading, re.compile(r"verif|testing|tests? run|checks", re.I))


class DeliveredClaimTests(HardeningTest):
    def test_unverified_claims_ledger_event(self):
        from tests.test_recovery import RecoveryTests
        RecoveryTests.delivery_fixture(self)
        (self.manifest_path.parent / "body.md").write_text(BODY)
        done = self.task_cli("run", self.manifest_path)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        body = json.loads((self.root / "gh-state.json").read_text())["prs"][0]["body"]
        self.assertIn("## Verification (from plovi's evidence)", body)
        self.assertIn("### Mentioned but not run by plovi", body)
        events = [e["data"] for e in ledger.events(self.project) if e["type"] == "delivery.unverified_claims"]
        # The fixture's behavior check ran python -m unittest -v test_app, so only two claims are unrun.
        self.assertEqual(events, [{"repository": "app", "count": 2, "commands": ["mkdocs build --strict", "npm test"]}])
