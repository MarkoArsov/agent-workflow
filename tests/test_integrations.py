from __future__ import annotations
import json
from types import SimpleNamespace
from unittest.mock import patch
from tests.helpers import WorkspaceTest
from scorebook.integrations import connectors, github
from scorebook import rules
from scorebook.util import WorkflowError, write_json

class IntegrationTests(WorkspaceTest):
    def test_connector_patch_preserves_other_settings_and_rejects_stale_approval(self):
        path = self.home / "host.json"
        write_json(path, {"theme": "light", "mcpServers": {"existing": {"command": "fixture"}}})
        proposal = connectors.patch_proposal(path, "tracker", {"command": "tracker-cli", "args": ["mcp"]})
        connectors.apply_patch(proposal, proposal["approval"])
        result = json.loads(path.read_text())
        self.assertEqual(result["theme"], "light")
        self.assertIn("existing", result["mcpServers"])
        self.assertIn("tracker", result["mcpServers"])
        with self.assertRaisesRegex(WorkflowError, "changed"):
            connectors.apply_patch(proposal, proposal["approval"])
        with self.assertRaisesRegex(WorkflowError, "environment"):
            connectors.patch_proposal(path, "bad", {"token": "literal"})
        with self.assertRaisesRegex(WorkflowError, "environment"):
            connectors.patch_proposal(path, "bad", {"env": {"TRACKER_API_KEY": "literal"}})
        with self.assertRaisesRegex(WorkflowError, "environment"):
            connectors.patch_proposal(path, "bad", {"headers": {"Authorization": "literal"}})

    def test_connector_headless_availability_is_provider_specific(self):
        root = self.repo("app"); project = self.setup_project(root)
        write_json(project.config / "connectors/tracker.json", {"id": "tracker", "transport": "host", "capabilities": ["read:issue"],
                   "providers": {"claude": {"headless": True}, "codex": {"headless": False}}})
        plan = {"connectors": ["tracker"], "stages": ["implement"], "routes": {"default": [{"provider": "codex", "model": "fixture"}]}}
        with self.assertRaisesRegex(WorkflowError, "headless codex"):
            connectors.preflight(project, plan)
        plan["routes"]["default"][0]["provider"] = "claude"
        self.assertEqual(connectors.preflight(project, plan)[0]["id"], "tracker")
        data = connectors.catalog(project)["tracker"]; data["enabled"] = False
        write_json(project.config / "connectors/tracker.json", data)
        with self.assertRaisesRegex(WorkflowError, "no-tracker"):
            connectors.preflight(project, plan)

    def test_repeated_prose_rule_proposes_review_without_forced_detector(self):
        project = self.setup_project(self.repo("app"))
        path = project.config / "rules/clarity.json"
        write_json(path, {"id": "clarity", "enforcement": "prose", "guidance": "Explain consequential choices.", "review_after": 3})
        for i in range(3):
            result = rules.record(project, "clarity", f"Example {i + 1}")
        self.assertEqual(result["corrective_review"]["enforcement_change"], "none; requires a reviewed rule edit")
        self.assertEqual(json.loads(path.read_text())["enforcement"], "prose")

    def test_github_paginates_threads_and_nested_comments(self):
        calls = []
        def response(argv, cwd):
            calls.append(argv)
            if "--paginate" in argv:
                self.assertIn("--slurp", argv)
                return SimpleNamespace(stdout='[[{"body":"first"}],[{"body":"second"}]]')
            if any(str(x).startswith("id=") for x in argv):
                body = {"data": {"node": {"comments": {"nodes": [{"id": "comment-2"}], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}
            elif any(str(x).startswith("cursor=") for x in argv):
                body = {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}}
            else:
                body = {"data": {"repository": {"pullRequest": {"reviewThreads": {
                    "nodes": [{"id": "thread-1", "comments": {"nodes": [{"id": "comment-1"}], "pageInfo": {"hasNextPage": True, "endCursor": "inner"}}}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "outer"}}}}}}
            return SimpleNamespace(stdout=json.dumps(body))
        with patch("scorebook.integrations.github.run", side_effect=response):
            data = github.comments(self.root, {"github": "example/project"}, 1)
        self.assertEqual(len(data["issue_comments"]), 2)
        self.assertEqual(len(data["threads"][0]["comments"]["nodes"]), 2)
        self.assertTrue(any("cursor=outer" in argv for argv in calls))

    def test_bot_ready_transition_restores_draft_even_on_fetch_failure(self):
        calls = []
        def command(argv, cwd):
            calls.append(argv)
            return SimpleNamespace(stdout='{"isDraft":true}' if "view" in argv else "")
        with patch("scorebook.integrations.github.run", side_effect=command), \
             patch("scorebook.integrations.github.comments", side_effect=WorkflowError("fixture failure")):
            with self.assertRaisesRegex(WorkflowError, "fixture"):
                github.wait_bots(self.root, {"github": "example/project"}, 1, temporary_ready=True, authorized=True)
        self.assertIn("--undo", calls[-1])
        self.assertEqual(github.bot_kind("coderabbitai[bot]"), "coderabbit")
        self.assertEqual(github.bot_kind("cursor[bot]"), "bugbot")
