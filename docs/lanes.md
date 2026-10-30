---
title: Lanes and bugfixes
description: Choose the manual or full lane, and handle a defect with a proven regression check.
question: Which lane fits this change?
---

# Lanes and bugfixes

!!! summary "In one minute"
    - Both lanes start with `specify` and a plan you confirm. They differ in how the plan runs.
    - **Manual:** `implement` in the same session when explicitly requested, or for a trivial low-risk edit.
    - **Full pipeline:** `implement-pipeline`. Fresh stages, saved evidence, optional review and delivery.
    - The manual lane is first-class, not a reduced-quality run: same rules, same named checks.
    - A bugfix is a normal task whose regression check should fail before the fix and pass after it.

## Two lanes

| Lane | Commands | Use when |
|---|---|---|
| Manual | `specify`, then `implement` | An explicit manual request, or a clearly trivial low-risk wording/format correction. |
| Full pipeline | `specify`, then `implement-pipeline` | The default for substantive code, behavioral tests, multiple components/repositories, compatibility, migration, risk or uncertainty. |

The manual lane keeps a concise, decision-complete plan instead of a detached manifest.
`implement` owns tests plus implementation in the same session, follows the same path and authorization rules, runs the named checks, and reports what it observed.
It does not start an orchestrator, run an independent review, commit, or push.

The full lane writes the four plan files and `pipeline.json`, then lets the orchestrator execute each selected stage in a fresh session, verify it independently, and keep the evidence.
See [task lifecycle](tasks.md).

## Bugfixes

There is no separate bugfix pipeline. A defect is an ordinary task whose plan records four compact facts:

1. **Expected behavior.**
2. **The observable failure,** with a reliable reproduction.
3. **The suspected cause and affected scope,** based on evidence.
4. **A regression check** that fails before the fix and passes after it.

`specify` requires these four facts before finalizing a defect plan. An import, startup or build failure is not assertion-level regression evidence.

For an isolated defect in the manual lane, `implement` should:

1. reproduce the failure;
2. add the regression check;
3. prove it fails for the original defect;
4. fix the cause;
5. rerun the check green;
6. run the other named checks that cover the change.

Record the before and after evidence in the task's notes.

The regression check must show the original bad behavior, not merely execute the changed code.
If a true automated check is impractical, for example a flaky third-party dependency or one-off corrupted production data, write down why and use the strongest repeatable alternative: a focused script, a fixture, or a local reproduction.
That is an exception, not a loophole.

The full lane already has the ideal shape for a defect: `implement-tests` proves the red state on an assertion, `implement` makes it green, and optional `review` looks at the result independently.

## Choose by situation

| Situation | Recommended lane |
|---|---|
| Isolated defect, deterministic reproduction, established local pattern | Full by default; manual when explicitly requested |
| Narrow feature follow-up with an established local pattern | Full by default; manual when explicitly requested |
| The regression needs several test layers, or the cause is uncertain | Full pipeline |
| Authorization, money, schema or migrations, public contracts, data correction | Full pipeline with review |
| Several repositories, or orchestrator-owned delivery wanted | Full pipeline |

A short prompt or familiar pattern alone does not justify manual execution.
An explicit user choice takes precedence; specify records why the manual exception
applies. Missing routes leave the full contract pending rather than changing lanes.
A full plan needs all four documents and pipeline.json, with actual validate-plan
and preflight results before it is called ready. Neither lane starts implementation
until the plan is approved.

<!-- checkpoints: IN-1, PLN-1, VER-5 -->

## See also

[Task lifecycle](tasks.md) · [Your first task](first-task.md) · [Evidence and checks](verification.md)


!!! note "What changes for your workflow"
    Expect a full contract for substantive work. Ask for manual execution when you
    want implement to own tests, code and verification in one session. Full planning
    selects only needed stages; it does not automatically authorize publishing.


## New tasks use the configured checkout

Lane choice changes how implementation runs, not where files live. Before a new
specification writes its plan, run `plovi task start <task>`. It allocates a distinct
branch and worktree by default, including for manual tasks and older unmarked
current-checkout profiles. Explicit setup checkout overrides are honored.
Continue editing at the returned paths and use --project with the returned canonical
root for the runner. A task name collision is refused; --resume is only for an
explicit continuation of that same owned task. Existing shared source edits stay
where they are. Branches alone do not isolate two agents in one working directory.
