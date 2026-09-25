---
title: When a task stops
description: Read a paused or failed run, answer it, resume safely, or cancel it.
question: What do I do when the happy path stops?
---

# When a task stops

!!! summary "In one minute"
    - Most pauses are not a recovery project. Read `status`, then do the one thing it asks.
    - `needs_input`: answer the saved question. Your answer resumes the session that asked.
    - `failed`: read the recorded error and evidence, fix the cause, then `resume`. Revise the plan and `resume --rebind` if the plan was wrong.
    - Advisory findings never stop a run, and a failed safety check is never reported as complete.
    - A good recovery ends with evidence, not with a clean-looking checkout.

## The usual case

If you started the run through `implement-pipeline`, stay in that conversation.
When the run needs a decision, the agent shows you the exact saved question. Answer in chat; it writes your answer to a file and runs `answer --file`, which resumes the same provider session.

Go back to `specify` only when your answer would change behavior, scope, a public contract, a security decision, a migration, or a required check.

## These do not stop the task

- Review findings. They are advisory unless a deterministic guard backs them.
- Advisory rule findings. They are recorded with the stage evidence.
- Using one provider and model for every stage.
- Usage or cost the provider didn't report. It stays unknown.

These still do: edits outside the declared paths, secret material or a blocking rule, a changed frozen test, a failed named check once attempts run out, and delivery guards.
See [stop or flag](principles.md#stop-or-flag).

## Choose the next step

<!-- diagram: task-stops -->

| Status | What it means | What to do |
|---|---|---|
| `starting`, `running` | The run is making progress. | Keep watching, or `watch` if you left. Don't start a duplicate; the project lock would refuse it anyway. |
| `needs_input` | A stage needs a decision only you can make. | Answer the saved question with `answer --file`. |
| `failed` | A safety, verification, or delivery check failed, or attempts ran out. | Read `error` and the latest evidence. Fix the cause, then `resume`. |
| `cancelled` | You asked the runner to stop. | `resume` when ready. |
| `complete` | Every selected stage finished and the final guard passed. | Review the diff, evidence, and delivery state. |

## If something failed

Start with `scorebook status TASK`. The `error` field names the failure; the evidence directory holds each attempt's output and each stage's check results.
Read the failing command or provider result before retrying.

| What happened | Best next step |
|---|---|
| A connection or service was briefly unavailable | The runner already retried within its limits. If it keeps failing, investigate the environment, then `resume`. |
| Authentication, quota, or model unavailable | The runner moved through your approved fallbacks. Repair access, or add a route you approve, then `resume`. |
| Timeout, inactivity, or a stalled tool | Inspect the attempt's output and the dependency's health. Don't raise limits indefinitely to hide a repeated failure. |
| A named check failed | Fix the underlying code, test, or local setup within scope. Never weaken the check to make it pass. |
| Scope violation | The changes are kept for inspection. Undo only the unauthorized edits, or revise the plan. |
| A frozen test changed | Restore it. If the test or requirement was wrong, revise the plan completely and `resume --rebind`; red proof runs again. |
| A stage touched your pre-existing changes | Keep your changes separate from the task, then `resume`. |
| A check command modified source files | Fix the command's output or cleanup configuration so checks leave the checkout unchanged. |
| Partial delivery | Inspect the per-repository delivery state. `resume` continues without recreating successful commits or pushes. |
| Plan, profile, or skills changed | Review the complete revision, then `resume --rebind`. |
| The task discovered a missing product decision | Revise the plan with `specify` before continuing. |

The runner retries temporary problems and resumes saved progress. It does not silently change the approved route, or ignore a failed check.

## Answer, resume, rebind, cancel

~~~sh
scorebook answer csv-export --file answer.txt
scorebook resume csv-export
scorebook resume csv-export --rebind
scorebook cancel csv-export
~~~

- **Answer** resumes the exact provider session that asked. Retries and fallbacks always start fresh sessions.
- **Resume** continues from the first incomplete stage. A stage whose verified evidence still matches the current files is not repeated.
- **Rebind** accepts a reviewed revision of the plan, profile, or skills. It archives the previous inputs and invalidates the stages they affect. Changing which repositories participate needs a new task ID.
- **Cancel** asks the owning runner to stop its own process group. A stale PID in the journal never authorizes killing a process, and only one runner owns a project at a time.

Retries, run time, inactivity, and stalled tools are bounded by the plan's limits.

## Keep partial work, but inspect it

After a failed stage, in-scope changes stay in place, so useful work isn't lost.
Before continuing, check that the changed files still belong to the task and still match the plan.

Don't reset, commit, or discard changes just to get back to a clean-looking state. If something is unexpected, stop and understand it first.

## A good recovery ends with evidence

Before calling a task recovered, you should be able to answer:

1. What stopped, and why?
2. What changed to address it?
3. Which check now shows the task is healthy?

The run state, the evidence directory, and the final status should hold those answers.

<!-- checkpoints: REV-4, PLN-3, VER-2 -->

## See also

[Task lifecycle](tasks.md) · [Code map](code-map.md#where-to-look-for-an-answer) · [Evidence and checks](verification.md)
