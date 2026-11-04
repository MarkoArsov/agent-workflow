---
title: Evidence and checks
description: What counts as proof: red and green evidence, frozen tests, parsers, and the diff fingerprint.
question: What counts as proof?
---

# Evidence and checks

!!! summary "In one minute"
    - An agent's response is a proposal, not a completion. The orchestrator runs the named checks itself and examines the files.
    - Red evidence means the expected tests failed on assertions, not on a setup error. Those tests are then frozen.
    - Green evidence is parsed from real output and bound to a fingerprint of the files it describes.
    - Any later change makes that evidence stale. Delivery re-runs the checks first.
    - Exit codes decide green. A success pattern is an optional extra assertion, and skips are advisory unless a planned test is skipped.
    - `validate-plan --run-checks` runs every check once when the plan is written, so a check that can never pass is caught before any agent time is spent.

## A proposal, not a completion

When a stage's agent reports `complete`, the orchestrator treats it as a request to finish the stage.
It then checks the changed files against the stage's contract and runs every named check itself.
The agent's own summary is kept in the attempt record, but it never counts as evidence.

<!-- diagram: evidence-flow -->

## Red evidence

Test-first stages need expected test identities and observed assertion failures.
The orchestrator rejects output that shows a setup or compile failure, such as `ModuleNotFoundError`, `ImportError`, `SyntaxError`, `command not found`, a C# compiler error, or a collection error.
Those failures do not prove a behavior is missing.

For unittest and pytest, each expected identity must itself appear as a failed test. For other parsers, the output must show an assertion failure.
Generic checks need an explicit `failure_pattern` for red.

### When the test slice cannot fail yet

Some test slices pass against current behavior, such as moving existing tests or adding a denial that already holds, and the behavioral red only appears once product or configuration changes land.
Record that in the plan as `approved_no_red_reason`, stating where red is demonstrated instead, and declare no check with a red phase; the two cannot be combined.
`implement-tests` then runs the green checks, which must pass with no setup failure, and the task diff must change at least one file under `test_paths`.
Files written before an input pause, an earlier attempt, or a plan rebind still count, because the comparison uses the task's starting snapshot.

### Frozen tests

After `implement-tests` is verified, the orchestrator records the hashes of every file under the plan's `test_paths`.
Implementation and review cannot rewrite, add, or delete those tests to make them pass; a change stops the run.
A wrong requirement or test needs a complete plan revision, `resume --rebind`, and renewed red proof.

## Frozen scope and test edits

After implement-tests, plovi freezes only the test files it wrote that contain a red
identity, such as `test_behavior`. When none matches, it freezes every test file that
stage wrote. Implement and review may change other files under `test_paths`: helpers,
fixtures and other tests. Those edits are listed as `test_edits` in the stage evidence,
and review is asked to check they don't weaken any assertion.

A check that runs fewer tests than it did before the stage fails closed: a test was
deleted. `unittest` and `pytest` output report test counts; other parsers have none, so
their frozen red files are the guard. In the same way, a check that skips more tests than it
did before the stage fails closed: a test was skipped to get green. Skips that were already
there, such as a test that needs Docker, stay advisory.

## Green evidence

Every required outcome maps to at least one named check with a green phase.
The orchestrator executes each check with its argv, working directory, and timeout, then parses the output:

| Parser | Green when | Red (assertion) when |
|---|---|---|
| `unittest` | `Ran N tests` with N ≥ 1, and `OK` | A `FAIL:` with `AssertionError`, and no `ERROR:` |
| `pytest` | `N passed` with N ≥ 1, and no failures or errors | `FAILED … - assert…` or `AssertionError`, and no errors |
| `dotnet` | `Passed!` with `Failed: 0` and at least one pass | A failed test with an `Assert…`, `AssertionException`, or `Expected:` line |
| `jest` | `Tests: … N passed`, and none failed | `Tests: … N failed`, with `Expected:` or `expect(` |
| `tap` | A plan line `1..N`, and no `not ok` | `not ok` with `expected:` or `operator:` |
| `generic` | Exit code 0 | Your `failure_pattern` matches |

The exit code is authoritative. A green check needs exit code 0, no failures or errors from its
parser, and every declared identity in the output. `success_pattern` is optional for every parser;
when you set it, it must match as well. Set one only when the tool's exit code can't be trusted.

Skipped, pending and todo tests are counted and shown as `skipped: N` in the evidence. They fail
a check only when a declared identity was skipped, when the check sets `skips = "fail"`, or when a
stage skips more tests than before (see above). A skipped identity is found from per-test lines,
so give checks with identities verbose output (`unittest -v`, `pytest -v`). `approved_skip_reason`
is still accepted and shown in the evidence.

## When checks run

A check's optional `when` says where it runs: `["loop"]`, `["final"]`, or both (the default).

- **The implement loop** runs `loop` checks after each attempt and each fix round, cheapest first,
  and stops at the first failure. Order comes from `expected_seconds`, then the check's last
  recorded duration, then the plan's order. Checks not reached are listed as `not_run`.
- **Final verification** runs `final` checks once every loop check passes. A check in both sets
  runs once.

Use focused loop checks, such as one test module, and put the full suite in a final check. Set
`expected_seconds` for checks that take more than 30 s.

Passing results are reused for the same check, command, phase and diff fingerprint. A review that
changes nothing reuses the implement stage's results instead of running the suite again, and
reused rows say `reused`. Failed results always run again.

### Red runs only the planned tests

A red-only check (its phases don't include `green`) with identities runs just those tests. unittest
gets one `-k IDENTITY` per identity, which also works with `discover`; pytest gets
`-k "name or name"`. If an identity is missing from the narrowed output, the whole command runs
once instead. A check with both red and green phases runs its whole command in red, because that
run is the baseline the removed-test and skip guards compare against. Other parsers always run the
whole command.

## Validate checks when you plan

```sh
plovi validate-plan ai-plans/csv-export/pipeline.json --run-checks
```

`--run-checks` runs every named check once in the task checkout from `plovi task start`, never in
your main checkout. Each check gets one result:

| Result | Meaning |
|---|---|
| `ran` | The tool ran and its parser understood the output, whatever the test result. A missing test module counts: the plan's tests are written later. |
| `missing-tool` | The command isn't on `PATH` or in the checkout, or `python -m X` has no module `X`. |
| `bad-cwd` | The check's `cwd` doesn't exist in the repository. |
| `unparseable` | The parser found no result line, or exit 0 but `success_pattern` never matched. |
| `timeout` | The check ran past its `timeout_seconds`. |
| `modifies-files` | The check changed files in the checkout. plovi reports it and doesn't clean up. |

Every result except `ran` prints one fix line, for example:

```text
docs-build: missing-tool: python3 has no mkdocs. Use the project's documented interpreter (for example .venv/bin/python) or a named command that has it.
```

The results are saved to `planning-checks.json` beside the manifest and added to `plan_files`, so
the plan hash, and so your approval, covers them. The command exits 0 when every check ran, 1 when
one can't, and 2 for invalid input such as a pattern that doesn't compile. A plan whose checks
fail isn't proposed in your inbox. Add `--json` for machine-readable output.

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
  "problems": [],
  "rules": []
}
~~~

In each check, `problems` lists every reason it did not pass; the top-level `problems` lists stage-level failures, such as a test stage that changed no test files. `reason` records a timeout, inactivity, or cancellation. `rules` holds blocking and advisory findings. Output and commands are redacted before they are saved.

## Current artifacts

Edits outside the stage's declared paths, or to a read-only repository, fail the stage and stay in place for inspection.
A stage may not change Git HEAD, the branch, or the index, and may not touch changes that existed before the run started.

Verification commands must not change repository files; if they do, their evidence is rejected.
Ignored build output is fine; configure cleanup and ignore files so checks leave the checkout unchanged.

Every verified stage records the fingerprint of the files it checked. Review and custom stages that change files produce new evidence.
Before delivery, the orchestrator compares the latest green fingerprint with the current files. If they differ, it re-runs the loop and final checks and stops if they fail. It also re-runs the secret detector and blocking rules on the whole task diff.

## Behavior beyond unit tests

Run local end-to-end checks against [disposable environments](environments.md) with named scenarios and observed readiness.
For deployed behavior, use the separate `test-on-staging` skill and its configured data and cleanup boundaries.

<!-- checkpoints: VER-1, VER-2, VER-5, REV-2 -->

## See also

[Principles](principles.md#stop-or-flag) · [When a task stops](recovery.md) · [Rules and references](rules.md)

## Fixture health and independent correction

A check can declare `phases: ["setup"]` or `["setup", "green"]`. Setup has green
semantics and runs before assertion-red proof in test authoring. Exercise the
helpers directly so broken setup is visible even before a new product API exists.

During implementation/review, a provider can return `test_fixture_repair` with a
reason, explicit repository/path test files, and declared setup check IDs. The
runner reproduces the failure, invokes a fresh approved test-author route, guards
paths and test/assertion identities, and obtains a separate review decision. It
saves original files, diff, review and command evidence under `test-repairs/`.
After accepted review and passing setup it renews red proof before product edits,
or runs green checks against existing implementation, then refreezes test hashes.
A green failure feeds the implementation correction loop; it cannot prove success.

The default budget is two fixture rounds per implementation/review stage. Set
`corrections.fixture_rounds` to 0–5 in the manifest. Rejected mechanical corrections
are saved and only their owned files are restored before reauthoring. Changes to
assertions/cases, foreign edits or product requirements stop for inspection.
Optional `corrections.max_known_cost_usd` stops another request once reported usage
reaches the limit. Unknown costs remain unknown, so this is not a total-spend cap.
