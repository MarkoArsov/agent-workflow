---
title: Stability gate
description: Five measured criteria that say when the pipeline lane is stable enough to be the default.
question: When can the pipeline lane replace the manual lane?
---

# Stability gate

!!! summary "In one minute"
    - `plovi stats --gate` checks five criteria, G1 to G5, and prints each with its numbers and PASS or FAIL.
    - All five must pass at the same time. The command exits 0 only then.
    - Until the gate passes, build roadmap issues with the manual lane: `specify`, then `implement`.
    - After it passes, the pipeline lane is the default.

## The criteria

| # | Criterion | Threshold |
|---|---|---|
| G1 | CI on main | The last 10 completed Verify runs on `main` succeeded without a rerun (`run_attempt == 1`), and every job's median duration over those runs is at most 60% of the job's tightest `timeout-minutes` in `.github/workflows/verify.yml`. |
| G2 | Suite speed | The slowest Ubuntu `core` job's median is at most 150 s over the same runs, and the local full suite takes at most 4 minutes on a 4-core machine with `--jobs auto`. |
| G3 | Pipeline runs | The last 5 pipeline runs (approved plan to pull request) had no interventions. At least 2 of them changed 10 or more files, at least 1 had red proof, and Claude and Codex routes were both used across them. Any intervention restarts the count. |
| G4 | Stop quality | Every stop in those 5 runs has a reason and a next command. |
| G5 | Scenario harness | Every [target scenario](generated/scenario.md) step whose owners are all among #18, #46, #47, #48 and #49 passes in CI. |

## Where the numbers come from

- **G1 and G2 (CI).** plovi reads workflow runs and job durations through
  `gh api repos/OWNER/REPO/actions/workflows/verify.yml/runs?branch=main&per_page=20`
  and `/actions/runs/ID/jobs`. Runs that are still in progress are ignored.
- **G2 (local).** Record the local suite with:

    ```sh
    python3 scripts/run_tests.py --jobs auto --record
    ```

    It writes the CPU count, jobs, seconds and date to `.plovi/local/stats/local-suite.json`,
    and only after a full run that passed. The gate shows the CPU count next to the time.
- **G3 and G4.** plovi reads the [ledger](ledger.md). A run starts at `run.started` and ends
  at its first pull request, a complete `run.finished`, or a cancel. Resumes, retries and
  answers stay inside the same run.
    - **Red proof** means the plan ran `implement-tests` without an approved no-red reason,
      recorded as `red_proof` on `run.started`. plovi has no separate bugfix task type, so
      G3's bugfix requirement counts a run with red proof.
    - **Files changed** comes from `files_changed` on `pr.opened`.
    - **Routes** come from `provider` on `attempt.finished`.
    - **Next command** comes from `next` on stop events. Runs recorded before stops carried
      `next` fail G4 until newer runs replace them.
- **G5.** Each Ubuntu Python 3.14 `core` batch uploads `scenario-results.json` as a
  `scenario-results-N` artifact. plovi downloads them all from the newest completed Verify run
  on `main` and takes each step's result from the batch that ran it.

Missing data is a FAIL with the reason, never an error: no `gh`, no runs, no local record.

## Interventions

An intervention is a person stepping into a run. Approving a plan is never one, so a project
that requires plan approval can still pass G3. These count:

- `question.answered` by a person;
- `run.resumed` by a person after the run `failed`, `escalated` or was `interrupted`, unless
  the same person had asked it to pause;
- `approval.granted` by a person for anything except a plan;
- `plan.rebound`, `checkpoint.migrated` and `handoff.started` by a person;
- `run.cancelled` followed by a new run of the same task;
- `commits.adopted` whose author isn't plovi.

`plovi stats` lists each run's interventions. `plan.rebound`, `commits.adopted` and
`handoff.started` count as soon as plovi records them.

## Using the gate

- **Before the gate:** build each issue with the manual lane: `plovi task start TASK`, then
  `specify` and `implement` in the same session.
- **During gate trials:** use the pipeline lane on real roadmap issues. When a run needs a
  person, finish it manually: the count restarts. File the cause as a stabilization bug.
- **After the gate:** the pipeline lane is the default. Once the factory schedule lands,
  issues up to M size (40 files or fewer) go through it on this repository.
- **Falling back:** if two consecutive pipeline runs need interventions after the gate,
  build the next issue with the manual lane and file the cause.

## Read the report

```sh
plovi stats                      # runs, then totals
plovi stats --since 14d --json   # the same data as JSON
plovi stats --gate               # G1 to G5; exit 0 only when all pass
```

The table lists each run's task, start, result, duration, attempts, interventions, stops and
tokens. Tokens and cost are sums of what providers reported; `-` means none reported.
