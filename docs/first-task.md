---
title: Your first task
description: One task end to end, from plan to evidence, with the real command output format.
question: What does one task look like end to end?
footer: docs
footer_order: 3
---

# Your first task

!!! summary "In one minute"
    - This walkthrough adds CSV export to a reports endpoint in a repository called `app`.
    - `specify` writes a plan in which one outcome, `exports-report-as-csv`, maps to one check, `csv-export-behavior`.
    - The manual lane implements it in your session. The full lane runs fresh stages and keeps evidence on disk.
    - Every command below exists; output blocks show the real format, trimmed.

Before you start, [install](install.md) Stagecoach and [set up your project](setup.md).

## 1. Specify

In your agent, invoke `aw-specify` (or `agent-workflow:specify` in the native Claude plugin):

~~~text
aw-specify Add CSV export to the reports endpoint.
~~~

It reads the project workflow, repository instructions, and the nearest working examples, then asks only what it can't find out.
For this task it might ask whether the export must match the on-screen column order, and whether the existing JSON endpoint stays unchanged.

For the full lane it writes the plan folder:

~~~text
ai-plans/csv-export/
├── prompt.md            # the original request and decisions
├── requirements.md      # outcomes and acceptance criteria
├── implementation.md    # approach, existing patterns, scope
├── deferred.md          # what is deliberately left out, and why
└── pipeline.json        # the contract the runner enforces
~~~

The heart of `pipeline.json` is small. One writable repository with its paths, one check with its command and expected test identity, and one outcome mapped to it:

~~~json
{
  "schema_version": 1,
  "task": "csv-export",
  "plan_files": ["prompt.md", "requirements.md", "implementation.md", "deferred.md"],
  "repositories": [
    {"id": "app", "access": "write", "branch": "feature/csv-export",
     "paths": ["src/**", "tests/**"], "test_paths": ["tests/**"]},
    {"id": "checks", "access": "read"}
  ],
  "stages": ["implement-tests", "implement", "review"],
  "checks": [
    {
      "id": "csv-export-behavior",
      "repository": "app",
      "command": {"argv": ["python3", "-m", "unittest", "-v", "tests.test_reports"], "cwd": ".", "timeout_seconds": 300},
      "parser": "unittest",
      "identities": ["test_exports_csv"],
      "phases": ["red", "green"]
    }
  ],
  "outcomes": [{"id": "exports-report-as-csv", "checks": ["csv-export-behavior"]}]
}
~~~

`checks` is a read-only companion repository: it can supply context and checks, and it never gets a branch. The full contract is in the [plan reference](https://github.com/MarkoArsov/agent-workflow/blob/main/references/pipeline-contract.md).

## 2. Confirm the plan

Approve when another engineer could implement it without inventing behavior:

- no product or implementation choice is left open;
- every outcome maps to a named check with a command, parser, and test identity;
- writable paths, the read-only repository, and deferred work are explicit;
- risky areas are named;
- stages, routes, and delivery actions are what you expect.

## 3. Manual lane

For a change this small you could stop here and implement in the same session:

~~~text
aw-implement
~~~

`implement` follows the plan's path boundaries, writes the test and the code, runs `csv-export-behavior`, fixes what fails, and inspects the final diff.
It reports what it observed and what remains. It doesn't commit or push.

## 4. Full lane

Validate the plan and check readiness:

~~~sh
agent-workflow validate-plan ai-plans/csv-export/pipeline.json
~~~

Example output
{: .code-label }

~~~json
{
  "task": "csv-export",
  "valid": true
}
~~~

~~~sh
agent-workflow preflight ai-plans/csv-export/pipeline.json
~~~

Example output, trimmed
{: .code-label }

~~~json
{
  "binding_sha256": "d0ea11d3…",
  "boundary": "Provider controls plus post-stage path/evidence guards; trusted mode is not an OS sandbox.",
  "permission_mode": "trusted",
  "routes": [
    {
      "model": "your-model",
      "model_validation": "passed to provider; account availability is verified on first request",
      "permission_mode": "trusted",
      "provider": "codex"
    }
  ],
  "side_effects": "Stage selection authorizes only the named delivery actions.",
  "stages": ["implement-tests", "implement", "review"],
  "task": "csv-export"
}
~~~

`run --dry-run` prints the same report and stops. When you're ready, start the run in the background:

~~~sh
agent-workflow run ai-plans/csv-export/pipeline.json --detach
~~~

Example output
{: .code-label }

~~~json
{
  "log": "/path/to/project/.agent-workflow/local/evidence/csv-export/runner.log",
  "next": "agent-workflow --project /path/to/project status csv-export",
  "pid": 48213,
  "task": "csv-export"
}
~~~

Follow it:

~~~sh
agent-workflow watch csv-export --seconds 300
~~~

Example output
{: .code-label }

~~~text
{"status": "running", "stage": "implement-tests", "completed": [], "pending_input": null, "error": null}
{"status": "running", "stage": "implement", "completed": ["implement-tests"], "pending_input": null, "error": null}
{"status": "running", "stage": "review", "completed": ["implement-tests", "implement"], "pending_input": null, "error": null}
{"status": "complete", "stage": "review", "completed": ["implement-tests", "implement", "review"], "pending_input": null, "error": null}
~~~

In the `implement-tests` stage the runner accepted the red state only because the expected test failed on an assertion:

Example output from the red check
{: .code-label }

~~~text
FAIL: test_exports_csv (tests.test_reports.Csv.test_exports_csv)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "tests/test_reports.py", line 6, in test_exports_csv
    self.assertEqual(export([["a", 1]]), "a,1\r\n")
AssertionError: None != 'a,1\r\n'
~~~

A `ModuleNotFoundError` or a syntax error in the same place would have been rejected as a setup failure.

## 5. Read the evidence

Everything the runner observed stays in the project's evidence directory, by default `.agent-workflow/local/evidence/csv-export/`:

~~~text
.agent-workflow/local/evidence/csv-export/
├── state.json           # the run journal: status, stages, attempts, delivery
├── binding.json         # the plan, profile, skills, and rules this run is bound to
├── attempts/0000.json   # each agent attempt: route, session, usage, output
├── evidence/            # each verified stage: checks, rules, fingerprint
└── runner.log           # output of a detached runner
~~~

A green record contains the command the runner ran, its parsed result, the rule findings, the changed paths, and the fingerprint of the files:

Example: evidence/implement-0001.json, trimmed
{: .code-label }

~~~json
{
  "changes": {"app": ["src/reports.py"]},
  "checks": [
    {
      "command": "python3 -m unittest -v tests.test_reports",
      "exit_code": 0,
      "id": "csv-export-behavior",
      "identities": ["test_exports_csv"],
      "output": "test_exports_csv (tests.test_reports.Csv.test_exports_csv) ... ok\n\nRan 1 test in 0.000s\n\nOK",
      "parser": "unittest",
      "passed": true,
      "phase": "green",
      "problems": [],
      "repository": "app"
    }
  ],
  "fingerprint": "c0045111…",
  "passed": true,
  "rules": []
}
~~~

Each attempt also records `usage` and `cost_usd` exactly as the provider reported them. A provider that reports no cost leaves `cost_usd` as `null`, never zero.

## Next steps

- Add `commit-and-push` and `draft-pr` to the stages, with an approved commit message, title, and body file, to let the runner deliver. See [review and delivery](review.md).
- Learn what to do when a run pauses: [when a task stops](recovery.md).
- Read how the evidence is judged: [evidence and checks](verification.md).

<!-- checkpoints: IN-1, VER-1, VER-2, VER-5 -->
