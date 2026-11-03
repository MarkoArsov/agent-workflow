"""The stateful GitHub CLI fake: scripted state, logged calls and loud failure on anything unmapped."""
import json
import shutil
import subprocess
import sys
import unittest
from tests.helpers import PACKAGE, WorkspaceTest, windows_launcher


class GithubFakeTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.state_path = self.install_github_fake({"repo": "octo/sample", "viewer": {"login": "maintainer", "type": "User"}})

    def gh(self, *args, check=True):
        return subprocess.run([shutil.which("gh", path=self.env["PATH"]), *args], env=self.env, cwd=self.root,
                              text=True, capture_output=True, check=check)

    def state(self):
        return json.loads(self.state_path.read_text())

    def script(self, **values):
        saved = json.loads(self.state_path.read_text())
        saved.update(values)
        self.state_path.write_text(json.dumps(saved))

    def calls(self):
        return json.loads(self.state_path.with_suffix(".calls.json").read_text())

    def test_windows_launcher_passes_ampersands_and_newlines_intact(self):
        launcher = windows_launcher(PACKAGE / "tests/fixtures/github_fake.py")
        if launcher is None:
            raise unittest.SkipTest("pip's script launchers are not installed")
        # Python runs the launcher's zip payload directly; on Windows the .exe hands it the same argv.
        (self.root / "gh.exe").write_bytes(launcher)
        query = "query {\n  viewer\n}"
        subprocess.run([sys.executable, str(self.root / "gh.exe"), "api", "graphql", "-f", f"query={query}"],
                       env=self.env, cwd=self.root, capture_output=True, check=False)
        subprocess.run([sys.executable, str(self.root / "gh.exe"), "api", "repos/octo/sample/issues?labels=a&state=open"],
                       env=self.env, cwd=self.root, capture_output=True, check=True)
        self.assertEqual([c["argv"] for c in self.calls()],
                         [["api", "graphql", "-f", f"query={query}"], ["api", "repos/octo/sample/issues?labels=a&state=open"]])

    def test_unmapped_call_exits_99_with_its_argv(self):
        result = self.gh("release", "list", check=False)
        self.assertEqual(result.returncode, 99)
        self.assertIn('["release", "list"]', result.stderr)
        result = self.gh("api", "repos/octo/sample/branches", check=False)
        self.assertEqual(result.returncode, 99)
        self.assertEqual([c["argv"][0] for c in self.calls()], ["release", "api"])

    def test_every_call_is_logged_with_its_body(self):
        body = self.root / "body.md"
        body.write_text("Fixes the parser.")
        self.gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
        self.gh("pr", "create", "--repo", "octo/sample", "--head", "fix", "--base", "main", "--draft",
                "--title", "Fix", "--body-file", str(body))
        self.assertEqual([c["argv"][:2] for c in self.calls()], [["repo", "view"], ["pr", "create"]])
        self.assertEqual(self.calls()[1]["body"], "Fixes the parser.")

    def test_repo_view(self):
        self.assertEqual(self.gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner").stdout.strip(), "octo/sample")
        self.assertEqual(json.loads(self.gh("repo", "view", "--json", "nameWithOwner").stdout), {"nameWithOwner": "octo/sample"})

    def test_pull_request_lifecycle(self):
        body = self.root / "body.md"
        body.write_text("First body")
        url = self.gh("pr", "create", "--repo", "octo/sample", "--head", "feature", "--base", "main", "--draft",
                      "--title", "Feature", "--body-file", str(body)).stdout.strip()
        self.assertEqual(url, "https://example.invalid/octo/sample/pull/1")
        listed = json.loads(self.gh("pr", "list", "--repo", "octo/sample", "--head", "feature", "--base", "main",
                                    "--state", "open", "--json", "url,isDraft,body").stdout)
        self.assertEqual(listed, [{"url": url, "isDraft": True, "body": "First body"}])
        self.assertEqual(json.loads(self.gh("pr", "list", "--head", "other", "--json", "url").stdout), [])
        body.write_text("Second body")
        self.gh("pr", "edit", url, "--repo", "octo/sample", "--body-file", str(body))
        self.gh("pr", "ready", "1")
        view = json.loads(self.gh("pr", "view", url, "--json", "body,isDraft,autoMergeRequest").stdout)
        self.assertEqual(view, {"body": "Second body", "isDraft": False, "autoMergeRequest": None})
        self.gh("pr", "ready", "1", "--undo")
        self.assertTrue(self.state()["pulls"]["1"]["draft"])

    def test_auto_merge_toggles(self):
        self.script(pulls={"7": {"head": "feature", "base": "main", "draft": False, "state": "open"}})
        self.gh("pr", "merge", "7", "--auto", "--squash")
        self.assertTrue(self.state()["pulls"]["7"]["auto_merge"])
        self.assertIsNotNone(json.loads(self.gh("pr", "view", "7", "--json", "autoMergeRequest").stdout)["autoMergeRequest"])
        self.gh("pr", "merge", "7", "--disable-auto")
        self.assertFalse(self.state()["pulls"]["7"]["auto_merge"])
        self.assertEqual(self.gh("pr", "merge", "7", check=False).returncode, 99)

    def test_issue_create_comment_label_and_view(self):
        url = self.gh("issue", "create", "--title", "Parser drops tabs", "--body", "Steps", "--label", "qa").stdout.strip()
        self.assertEqual(url, "https://example.invalid/octo/sample/issues/1")
        self.gh("issue", "comment", "1", "--body", "Seen again")
        self.gh("issue", "edit", "1", "--add-label", "plovi,ready")
        view = json.loads(self.gh("issue", "view", "1", "--repo", "octo/sample", "--json", "title,body,url,labels,state").stdout)
        self.assertEqual(view, {"title": "Parser drops tabs", "body": "Steps", "url": url, "state": "OPEN",
                                "labels": [{"name": "qa"}, {"name": "plovi"}, {"name": "ready"}]})
        self.assertEqual(self.state()["issues"]["1"]["comments"], [{"body": "Seen again", "author": "maintainer"}])
        self.assertEqual(self.gh("issue", "view", "9", check=False).returncode, 1)

    def test_label_events_record_actor_and_bot_type(self):
        self.script(issues={"4": {"title": "Bot labelled", "labels": ["plovi"], "events": [
            {"event": "labeled", "label": {"name": "plovi"}, "actor": {"login": "ci-helper[bot]", "type": "Bot"}}]}})
        self.gh("issue", "edit", "4", "--add-label", "plovi")
        events = json.loads(self.gh("api", "repos/octo/sample/issues/4/events").stdout)
        self.assertEqual([(e["actor"]["login"], e["actor"]["type"]) for e in events],
                         [("ci-helper[bot]", "Bot"), ("maintainer", "User")])

    def test_labelled_open_issues_paginate_and_slurp(self):
        self.script(issues={"1": {"title": "One", "labels": ["plovi"]}, "2": {"title": "Two", "labels": ["other"]},
                            "3": {"title": "Three", "labels": ["plovi"], "state": "closed"}})
        pages = json.loads(self.gh("api", "--paginate", "--slurp", "repos/octo/sample/issues?labels=plovi&state=open").stdout)
        self.assertEqual([[issue["number"] for issue in page] for page in pages], [[1]])
        plain = json.loads(self.gh("api", "--paginate", "repos/octo/sample/issues?labels=plovi&state=all").stdout)
        self.assertEqual([issue["number"] for issue in plain], [1, 3])

    def test_collaborator_permission(self):
        self.script(collaborators={"maintainer": "admin", "visitor": "read"})
        self.assertEqual(json.loads(self.gh("api", "repos/octo/sample/collaborators/visitor/permission").stdout)["permission"], "read")
        self.assertEqual(self.gh("api", "repos/octo/sample/collaborators/stranger/permission", check=False).returncode, 1)

    def test_check_runs_follow_their_scripted_order(self):
        sha = "abc123"
        self.script(checks={sha: [{"name": "verify", "sequence": ["pending", "failure"]},
                                  {"name": "lint", "sequence": ["pending", "pending", "success"]}]})
        seen = []
        for _ in range(4):
            runs = json.loads(self.gh("api", f"repos/octo/sample/commits/{sha}/check-runs").stdout)["check_runs"]
            seen.append([(r["name"], r["status"], r["conclusion"]) for r in runs])
        self.assertEqual(seen[0], [("verify", "in_progress", None), ("lint", "in_progress", None)])
        self.assertEqual(seen[1], [("verify", "completed", "failure"), ("lint", "in_progress", None)])
        self.assertEqual(seen[3], [("verify", "completed", "failure"), ("lint", "completed", "success")])

    def test_commit_statuses_combine_and_accept_posts(self):
        sha = "def456"
        self.assertEqual(json.loads(self.gh("api", f"repos/octo/sample/commits/{sha}/status").stdout)["state"], "pending")
        self.gh("api", f"repos/octo/sample/statuses/{sha}", "-f", "state=success", "-f", "context=plovi/evidence")
        self.assertEqual(json.loads(self.gh("api", f"repos/octo/sample/commits/{sha}/status").stdout)["state"], "success")
        self.gh("api", "-X", "POST", f"repos/octo/sample/statuses/{sha}", "-f", "state=failure", "-f", "context=ci")
        status = json.loads(self.gh("api", f"repos/octo/sample/commits/{sha}/status").stdout)
        self.assertEqual((status["state"], status["total_count"]), ("failure", 2))

    def test_workflow_runs_jobs_logs_and_artifacts(self):
        runs = [{"id": 11, "name": "Verify", "path": ".github/workflows/verify.yml", "head_branch": "main", "head_sha": "a1",
                 "status": "completed", "conclusion": "success", "run_attempt": 1, "html_url": "https://example.invalid/r/11"},
                {"id": 12, "name": "Verify", "path": ".github/workflows/verify.yml", "head_branch": "fix", "head_sha": "b2",
                 "status": "completed", "conclusion": "failure", "run_attempt": 2}]
        self.script(actions={"runs": runs, "jobs": {"11": [{"name": "smoke", "started_at": "2026-11-01T10:00:00Z",
                                                             "completed_at": "2026-11-01T10:01:00Z"}]},
                             "logs": {"12": "core\tRun tests\tFAIL: test_parser"},
                             "artifacts": {"11": {"scenario-results": {"scenario-results.json": {"U1": "passed"}}}}})
        listed = json.loads(self.gh("api", "repos/octo/sample/actions/workflows/verify.yml/runs?branch=main&per_page=20").stdout)
        self.assertEqual([r["id"] for r in listed["workflow_runs"]], [11])
        jobs = json.loads(self.gh("api", "repos/octo/sample/actions/runs/11/jobs").stdout)
        self.assertEqual(jobs["jobs"][0]["name"], "smoke")
        cli_runs = json.loads(self.gh("run", "list", "--branch", "fix", "--json", "databaseId,conclusion,headSha").stdout)
        self.assertEqual(cli_runs, [{"databaseId": 12, "conclusion": "failure", "headSha": "b2"}])
        self.assertIn("FAIL: test_parser", self.gh("run", "view", "12", "--log-failed").stdout)
        target = self.root / "download"
        self.gh("run", "download", "11", "--name", "scenario-results", "--dir", str(target))
        self.assertEqual(json.loads((target / "scenario-results.json").read_text()), {"U1": "passed"})
        self.gh("run", "download", "11", "--pattern", "scenario-*", "--dir", str(self.root / "matched"))
        self.assertEqual(json.loads((self.root / "matched/scenario-results/scenario-results.json").read_text()), {"U1": "passed"})
        self.assertEqual(self.gh("run", "download", "11", "--pattern", "tests-*", "--dir", str(target), check=False).returncode, 1)
        self.assertEqual(self.gh("run", "download", "11", "--name", "other", "--dir", str(target), check=False).returncode, 1)

    def test_integration_reads_work_against_the_fake(self):
        from plovi.integrations import github
        self.script(pulls={"5": {"head": "feature", "base": "main", "comments": [{"body": "Looks fine", "author": "coderabbitai[bot]"}],
                                 "reviews": [{"state": "COMMENTED", "user": {"login": "reviewer"}}],
                                 "review_threads": [{"id": "T1", "path": "app.py", "line": 3,
                                                     "comments": [{"body": "Rename this", "author": "reviewer"}]}]}},
                    issues={"9": {"title": "Parser", "body": "Details", "labels": ["plovi"]}})
        repo = {"base_branch": "main"}
        data = github.comments(self.root, repo, 5)
        self.assertEqual(data["issue_comments"][0]["user"]["login"], "coderabbitai[bot]")
        self.assertEqual(data["reviews"][0]["user"]["login"], "reviewer")
        self.assertEqual(data["threads"][0]["comments"]["nodes"][0]["body"], "Rename this")
        self.assertEqual(github.issue(self.root, repo, 9)["labels"], [{"name": "plovi"}])
        url = github.draft_pr(self.root, repo, "feature-2", "Feature", "Body")
        self.assertEqual(github.draft_pr(self.root, repo, "feature-2", "Feature", "Body"), url)
        self.assertEqual(sum(1 for c in self.calls() if c["argv"][:2] == ["pr", "create"]), 1)
