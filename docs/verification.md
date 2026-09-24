---
title: Evidence and checks
description: What counts as proof: red and green evidence, frozen tests, parsers, and the diff fingerprint.
question: What counts as proof?
---

# Evidence and checks

!!! summary "In one minute"
    - An agent's response is a proposal, not a completion. The runner runs the named checks itself and examines the files.
    - Red evidence means the expected tests failed on assertions, not on a setup error. Those tests are then frozen.
    - Green evidence is parsed from real output and bound to a fingerprint of the files it describes.
    - Any later change makes that evidence stale. Delivery re-runs the checks first.

## A proposal, not a completion

When a stage's agent reports `complete`, the runner treats it as a request to finish the stage.
It then checks the changed files against the stage's contract and runs every named check itself.
The agent's own summary is kept in the attempt record, but it never counts as evidence.

<!-- diagram: evidence-flow -->

## Red evidence

Test-first stages need expected test identities and observed assertion failures.
The runner rejects output that shows a setup or compile failure, such as `ModuleNotFoundError`, `ImportError`, `SyntaxError`, `command not found`, a C# compiler error, or a collection error.
Those failures do not prove a behavior is missing.

For unittest and pytest, each expected identity must itself appear as a failed test. For other parsers, the output must show an assertion failure.
Generic checks need an explicit `failure_pattern` for red.

After meaningful red evidence, the runner records the hashes of every file under the plan's `test_paths`.
Implementation and review cannot rewrite, add, or delete those tests to make them pass; a change stops the run.
A wrong requirement or test needs a complete plan revision, `resume --rebind`, and renewed red proof.

## Green evidence

Every required outcome maps to at least one named check with a green phase.
The runner executes each check with its argv, working directory, and timeout, then parses the output:

| Parser | Green when | Red (assertion) when |
|---|---|---|
| `unittest` | `Ran N tests` with N ≥ 1, and `OK` | A `FAIL:` with `AssertionError`, and no `ERROR:` |
| `pytest` | `N passed` with N ≥ 1, and no failures or errors | `FAILED … - assert…` or `AssertionError`, and no errors |
| `dotnet` | `Passed!` with `Failed: 0` and at least one pass | A failed test with an `Assert…`, `AssertionException`, or `Expected:` line |
| `jest` | `Tests: … N passed`, and none failed | `Tests: … N failed`, with `Expected:` or `expect(` |
| `tap` | A plan line `1..N`, and no `not ok` | `not ok` with `expected:` or `operator:` |
| `generic` | Your `success_pattern` matches | Your `failure_pattern` matches |

A green check also needs exit code 0 and no assertion failure in its output.
Skipped, pending, or todo tests fail a check unless the plan records `approved_skip_reason`.
If the check declares `identities`, each must appear in the output.

For generic checks, use a precise marker tied to the check's outcome. A broad word such as "passed" is poor evidence.

## What an evidence record contains

Example: evidence/implement-0001.json, trimmed
{: .code-label }

~~~json
{
  "changes": {"app": ["src/reports.py"]},
  "checks": [
    {
      "command": "python3 -m unittest -v tests.test_reports",
      "duration_seconds": 0.05,
      "exit_code": 0,
      "id": "csv-export-behavior",
      "identities": ["test_exports_csv"],
      "output": "test_exports_csv (tests.test_reports.Csv.test_exports_csv) ... ok\n\nRan 1 test in 0.000s\n\nOK",
      "parser": "unittest",
      "passed": true,
      "phase": "green",
      "problems": [],
      "reason": null,
      "repository": "app"
    }
  ],
  "fingerprint": "c0045111…",
  "passed": true,
  "rules": []
}
~~~

`problems` lists every reason a check did not pass. `reason` records a timeout, inactivity, or cancellation. `rules` holds blocking and advisory findings. Output and commands are redacted before they are saved.

## Current artifacts

Edits outside the stage's declared paths, or to a read-only repository, fail the stage and stay in place for inspection.
A stage may not change Git HEAD, the branch, or the index, and may not touch changes that existed before the run started.

Verification commands must not change repository files; if they do, their evidence is rejected.
Ignored build output is fine; configure cleanup and ignore files so checks leave the checkout unchanged.

Every verified stage records the fingerprint of the files it checked. Review and custom stages that change files produce new evidence.
Before delivery, the runner compares the latest green fingerprint with the current files. If they differ, it re-runs the checks and stops if they fail. It also re-runs the secret detector and blocking rules on the whole task diff.

## Behavior beyond unit tests

Run local end-to-end checks against [disposable environments](environments.md) with named scenarios and observed readiness.
For deployed behavior, use the separate `test-on-staging` skill and its configured data and cleanup boundaries.

<!-- checkpoints: VER-1, VER-2, VER-5, REV-2 -->

## See also

[Principles](principles.md#stop-or-flag) · [When a task stops](recovery.md) · [Rules and references](rules.md)
