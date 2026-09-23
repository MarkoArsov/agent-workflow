# Recover a run

Start with `status TASK` and the saved evidence under the configured local evidence directory.
Read the failing command or provider result before retrying.

| State | Next step |
|---|---|
| needs_input | Read the exact question; use answer with the user's response. |
| failed check | Fix the concrete cause within scope, then resume. |
| authentication/quota/model failure | Repair access or use an already approved fallback. |
| timeout/inactivity/tool stall | Inspect the owned process log and dependency health. |
| scope violation | Inspect retained edits; revise or undo only the unauthorized task changes. |
| partial delivery | Inspect per-repository state; resume without recreating successful commits. |
| changed plan/profile/skills | Review a complete revision, then resume --rebind. |

## Answer a paused stage

~~~sh
agent-workflow answer task-name --file /tmp/task-answer.txt
~~~

This resumes the exact provider and session that asked.
Retries and fallbacks start fresh sessions.

## Resume or cancel

~~~sh
agent-workflow resume task-name
agent-workflow resume task-name --rebind
agent-workflow cancel task-name
~~~

Rebinding archives prior inputs and invalidates affected stages.
Changing repository membership/checkouts requires a new task ID.

Cancellation asks the owning runner to stop its own process group.
A stale PID never authorizes killing an unrelated process.
Only one runner owns a project at a time.

Retries, inactivity, stage duration, and stalled tools are bounded by the plan's limits.
Do not increase limits indefinitely to hide a repeated failure.
