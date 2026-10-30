# Implementation evidence: runner hardening

Implementation is ready for independent review. No delivery actions were performed in this checkout. Tests and manual scenarios used isolated child configuration, temporary repositories/remotes and provider/GitHub doubles.

## Regression before and after

Assertion-red evidence is retained in `tests/fixtures/runner_hardening_red.json` at starting revision `3bc42c754456e7bd07860ced728faea93374dd99`. The red checks were rerun through `plovi verify --phase red` before product edits: all five expected assertion failures were observed, without import/build failures. The starting checkout HEAD remains `3bc42c754456e7bd07860ced728faea93374dd99`; the runner owns commits.

- `test_blocked_stops_after_one_attempt`, `test_spec_conflict_stops_after_one_attempt` and `test_impossible_stops_after_one_attempt`: two calls before; one call and retained escalation after.
- `test_41_files_need_approval`: complete before; needs_approval with 41 files/41 lines after.
- `test_new_project_defaults_to_worktree`: current-checkout before; worktree after.

## Named green checks

Executed with `python3 bin/plovi --project . verify ai-plans/runner-hardening/pipeline.json --phase green`. A disposable documentation environment provided MkDocs on PATH; runtime remains standard-library-only. Every configured check ran in its configured working directory.

| Check | Observed result |
|---|---|
| stop-regressions | Passed. Ran 3 tests in 3.051s |
| size-regression | Passed. Ran 1 test in 1.381s |
| planning-default-regression | Passed. Ran 1 test in 0.154s |
| outcomes | Passed. Ran 10 tests in 10.297s |
| limits | Passed. Ran 14 tests in 26.854s |
| policy | Passed. Ran 10 tests in 3.436s |
| permissions | Passed. Ran 9 tests in 10.780s |
| concurrency | Passed. Ran 6 tests in 7.126s |
| recovery | Passed. Ran 12 tests in 24.520s |
| evidence | Passed. Ran 5 tests in 6.270s |
| task-planning | Passed. Ran 5 tests in 2.789s |
| full-suite | Passed. Ran 249 tests in 212.744s |
| generated-docs | Passed. Exit 0; expected empty output |
| docs-build | Passed. Documentation built in 0.16 seconds |
| links | Passed. Checked 4135 internal links/assets; 0 failures. |
| public-content | Passed. Scanned 2753 items; 0 findings; private denylist not supplied. |

The final source correction only changes legacy empty-policy detection. After that correction, the exact full-suite command `python3 -m unittest discover -s tests -v` was rerun: **249 tests passed in 215.078s**, no skips. Named focused suites also passed (59 tests), and the detached cancellation/resume lifecycle check passed separately.

## Acceptance mappings

| Outcome | Evidence |
|---|---|
| stop-outcomes-and-retry | stop-regressions, outcomes |
| diff-bound-size-and-path-approvals | size-regression, limits |
| pr-evidence | evidence, recovery |
| reviewed-policy | policy, full-suite, generated-docs |
| restricted-unattended-permissions | permissions |
| concurrent-worktree-tasks | concurrency, full-suite |
| crash-safe-delivery | recovery, evidence |
| docs-and-portable-regressions | full-suite, generated-docs, docs-build, links, public-content |
| worktree-defaults-and-complete-planning-commits | planning-default-regression, task-planning, full-suite, generated-docs, docs-build, links |

## Repeatable isolated manual scenarios

- Followed the specify/worktree-start procedure for two task IDs before manifest creation. Each created and reused its own actual branch/worktree. Nine complete-contract/evaluator/quality/evidence artifacts were committed and verified with git ls-tree on each task branch. The parked checkout HEAD, branch and status stayed unchanged. Explicit canonical project resolution accepted both checkouts. This is a manual skill walkthrough using real Git fixtures, not live agent execution.
- A legacy binding with no policy/execution fields resumed its exact asking session without rebind when policy contained only empty commented-template tables.
- A size approval followed by an exact-session question resumed safely; approval did not answer the question or replay the completed call.
- A changed retained diff, once explicitly approved, was verified without another provider call.
- An authentication failure that wrote 41 files stopped at the diff gate before a fallback call.
- A report assumption containing a fixture secret was redacted without corrupting structured JSON state.

## Boundaries and limitations

- All source/test changes remain within the approved path contract. Frozen regression assertions were preserved. No real user agent configuration, read-only companion, branch or tracker state was changed.
- Local macOS/Python 3.14 verification only. Hosted Linux/Windows/macOS CI and account-authenticated provider inference were not run. Existing platform fixtures are not a claim of a hosted cross-platform run.
- Policy scheduling/review-slot fields, autonomy levels and grants remain reserved as planned. Unversioned multi-repository plan ownership is resolved through reviewed setup guidance; no Git parent is initialized.
- Private denylist was not supplied. Final public source/history audit: 2,754 items scanned, zero findings.
- No commit, push, PR creation or comment was performed outside disposable test/scenario repositories.
