---
title: Lanes and bugfixes
description: Choose the manual or full lane, and handle a defect with a proven regression check.
question: Which lane fits this change?
---

# Lanes and bugfixes

!!! summary "In one minute"
    - Both lanes start with `specify` and a plan you confirm. They differ in how the plan runs.
    - **Manual:** `implement` in the same session. Small, contained changes with an established pattern.
    - **Full pipeline:** `implement-pipeline`. Fresh stages, saved evidence, optional review and delivery.
    - The manual lane is first-class, not a reduced-quality run: same rules, same named checks.
    - A bugfix is a normal task that must prove its regression check fails before the fix.

## Two lanes

| Lane | Commands | Use when |
|---|---|---|
| Manual | `specify`, then `implement` | A small, contained change, especially a follow-up to work that already has an established local pattern. |
| Full pipeline | `specify`, then `implement-pipeline` | Test-first work, several repositories, migrations, public contracts or access boundaries, or when you want independent review and runner-owned delivery. |

The manual lane keeps a concise, decision-complete plan instead of a detached manifest.
`implement` owns tests plus implementation in the same session, follows the same path and authorization rules, runs the named checks, and reports what it observed.
It does not start a runner, run an independent review, commit, or push.

The full lane writes the four plan files and `pipeline.json`, then lets the runner execute each selected stage in a fresh session, verify it independently, and keep the evidence.
See [task lifecycle](tasks.md).

## Bugfixes

There is no separate bugfix pipeline. A defect is an ordinary task whose plan records four compact facts:

1. **Expected behavior.**
2. **The observable failure,** with a reliable reproduction.
3. **The suspected cause and affected scope,** based on evidence.
4. **A regression check** that fails before the fix and passes after it.

!!! note "Recommended practice"
    `specify` does not enforce this template yet. Treat it as the team convention, or [copy the skill](customize.md#change-a-skill) and make it part of your project's `specify`.

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
| Isolated defect, deterministic reproduction, established local pattern | Manual |
| Narrow feature follow-up with an established local pattern | Manual |
| The regression needs several test layers, or the cause is uncertain | Full pipeline |
| Authorization, money, schema or migrations, public contracts, data correction | Full pipeline with review |
| Several repositories, or runner-owned delivery wanted | Full pipeline |

Lane choice is guidance, not a gate. You confirm it when you approve the plan.

<!-- checkpoints: IN-1, PLN-1, VER-5 -->

## See also

[Task lifecycle](tasks.md) · [Your first task](first-task.md) · [Evidence and checks](verification.md)
