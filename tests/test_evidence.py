import copy
import json
from tests.helpers import HardeningTest
from plovi import runner
from plovi.integrations import github
from plovi.util import write_json


class EvidenceTests(HardeningTest):
    def verified(self):
        self.fixture([{"report": {"status": "complete", "summary": "Fixture",
                                  "assumptions": ["Use offline fixtures"]}}])
        return runner.run(self.project, self.plan)

    def test_pure_stable_evidence_uses_verified_results(self):
        from plovi.evidence import evidence_markdown
        saved = self.verified(); before = copy.deepcopy(saved)
        body = evidence_markdown(saved, self.plan)
        self.assertEqual(body, evidence_markdown(saved, self.plan))
        self.assertEqual(saved, before)
        for expected in ("Evidence", "behavior", "implement", "codex", "fixture-model", "Use offline fixtures"):
            self.assertIn(expected, body)
        # A report summary is not proof of a test count.
        self.assertNotIn("1000 tests passed", body)

    def test_all_rendered_strings_are_redacted_and_markdown_escaped(self):
        from plovi.evidence import evidence_markdown
        saved = self.verified()
        saved["attempts"][0]["report"]["assumptions"] = ["token=fixture-secret-value", "\n# forged heading", "[click](https://example.invalid)"]
        self.plan["outcomes"][0]["id"] = "\n# forged outcome"
        body = evidence_markdown(saved, self.plan)
        self.assertNotIn("fixture-secret-value", body)
        self.assertNotIn("\n# forged", body)
        self.assertNotIn("[click](https://example.invalid)", body)

    def test_existing_pr_body_is_synchronized_once_and_unrelated_content_survives(self):
        from plovi.evidence import evidence_markdown
        saved = self.verified(); gh_path = self.install_gh_double()
        evidence = evidence_markdown(saved, self.plan)
        url = "https://example.invalid/pull/1"
        write_json(gh_path, {"prs": [{"url": url, "isDraft": True, "body": "Reviewer notes stay here.\n\nPlan body.\n"}], "calls": []})
        repo = {"github": "example/fixture", "base_branch": "main"}
        body = evidence + "\n\nPlan body.\n"
        self.assertEqual(github.draft_pr(self.project.root, repo, "feature/sample", "Fixture", body), url)
        first = json.loads(gh_path.read_text())
        self.assertIn("Reviewer notes stay here.", first["prs"][0]["body"])
        self.assertIn("Plan body.", first["prs"][0]["body"])
        self.assertEqual(first["prs"][0]["body"].count("## Evidence"), 1)
        github.draft_pr(self.project.root, repo, "feature/sample", "Fixture", body)
        calls = json.loads(gh_path.read_text())["calls"]
        self.assertEqual(sum(c["argv"][:2] == ["pr", "edit"] for c in calls), 1)
        self.assertFalse(any(c["argv"][:2] == ["pr", "create"] for c in calls))

    def test_final_pr_body_redacts_plan_secrets(self):
        self.fixture([{}]); path = self.install_gh_double()
        github.draft_pr(self.project.root, {"github": "example/fixture", "base_branch": "main"},
                        "feature/sample", "Fixture", "Plan token=fixture-body-secret")
        body = json.loads(path.read_text())["prs"][0]["body"]
        self.assertNotIn("fixture-body-secret", body)

    def test_changed_evidence_edits_existing_pr_exactly_once(self):
        from plovi.evidence import evidence_markdown
        saved = self.verified(); gh_path = self.install_gh_double()
        repo = {"github": "example/fixture", "base_branch": "main"}
        body = evidence_markdown(saved, self.plan) + "\n\nPlan body.\n"
        github.draft_pr(self.project.root, repo, "feature/sample", "Fixture", body)
        saved["attempts"][0]["report"]["assumptions"] = ["A revised verified fixture assumption"]
        changed = evidence_markdown(saved, self.plan) + "\n\nPlan body.\n"
        self.assertNotEqual(body, changed)
        github.draft_pr(self.project.root, repo, "feature/sample", "Fixture", changed)
        github.draft_pr(self.project.root, repo, "feature/sample", "Fixture", changed)
        journal = json.loads(gh_path.read_text())
        self.assertEqual(sum(c["argv"][:2] == ["pr", "create"] for c in journal["calls"]), 1)
        self.assertEqual(sum(c["argv"][:2] == ["pr", "edit"] for c in journal["calls"]), 1)
        self.assertIn("A revised verified fixture assumption", journal["prs"][0]["body"])
