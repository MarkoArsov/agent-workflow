# Windows CI duration — 29 October 2026

Requested outcome: fix the long and cancelled Windows checks in PR #39 while
preserving its test coverage. The user authorized the correction in this PR.
Work remains in the current checkout, using the standard library; no delegation,
real agent configuration changes, security exclusions or disabled checks.

## Observed failure

Run: https://github.com/MarkoArsov/agent-workflow/actions/runs/40904664885
Head: 6888dc68d15a42b7c58f34ce6d2b34df1118ec70, matching the local starting revision.
Windows Python 3.11 passed all 172 tests in 801.595 seconds. Windows Python 3.14
was cancelled at the 15-minute job deadline after reaching 148 tests. Complete
logs for both jobs were inspected; the cancelled job started its last logged test
immediately before cancellation. There is no assertion failure in that job.

The completed job spent approximately 164 seconds in installation tests, 159 in
migration, 95 in runner tests and 58 in Git operations. This is cumulative suite
cost rather than evidence of one hung test. Round-robin assignment of its observed
test durations projects three batches of roughly 248, 285 and 269 seconds, before
new tests and runner/setup variation. These are estimates, not hosted results.

## Correction and boundaries

- Preserve complete Linux/macOS runs and both Windows Python versions. Split
  each Windows suite into three independently scheduled, deterministic batches.
  This reduces critical-path duration; it does not claim less total runner work.
- A standard-library runner discovers the same unittest suite, sorts stable test
  IDs and distributes cases without duplication. Invalid/empty batches fail;
  assertion and discovery failures preserve unsuccessful process status.
- Print the slowest cases and retain per-test JSON timings plus the full log for
  every job, including successful jobs. Artifact names include the batch number.
- Bound the test step at 12 minutes within the existing 15-minute job budget,
  leaving time for failure summaries/artifact upload. No global timeout increase.
- Update developer instructions. The runtime, installer, fixtures, real user agent
  settings, concurrency cancellation policy and required test assertions stay intact.

## Checks

Before implementation, the new workflow contract assertion failed because the
Windows matrix had no batches. New runner regressions verify actual execution of
all seven disposable fixture cases exactly once across three batches; failure
and discovery-error exit codes; timings on failure; invalid/empty batch rejection;
and complete, disjoint, repeatable partitioning of the repository's real suite.

The expanded matrix was parsed and evaluated locally: four complete Linux/macOS
jobs plus all six Windows version/batch combinations. CI workflow and runner
regressions: 11 passed. Actual batch 1 executed 60 of 178 discovered repository
tests, passed and wrote a JSON timing artifact; its local duration was 29.604s.

Full isolated suite: `python3 -m unittest discover -s tests -v` — 178 passed in
85.562 seconds. Strict MkDocs build and 3964 internal links/assets passed.
Generated documentation/native wrappers/design checks, source/site rename audits,
source/history/site public-content scans and whitespace checks passed. No private
denylist was supplied. The generated search-index compatibility fingerprint was
refreshed solely for the developer documentation update.

All three actual local batch runs passed: 1: 60 tests in 29.604s, 2: 59 tests in 33.098s, 3: 59 tests in 28.013s.
Their timing manifests contain all 178 distinct test IDs exactly once. Native
Windows timing confirmation follows the normal PR-triggered hosted run.
