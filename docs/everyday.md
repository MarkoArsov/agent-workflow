---
title: Review and everyday use
description: Review as the bottleneck, a short queue, and what to do while a task waits.
question: How should I review, run work in parallel, and use wait time?
---

# Review and everyday use

!!! summary "In one minute"
    - Review is now the bottleneck, not writing code. Give it real time and priority.
    - Use AI to review faster and see more: **understand, then review**. Neither replaces the named approver.
    - Keep a short queue. Finish one task; two or three only when they are small and already waiting on someone else.
    - Fill waits with review, not with new tasks.

## Why review comes first now

Before agents, producing the change was the slow part and review fit in a short daily slot. That split no longer holds.
Agents produce diffs faster than anyone can responsibly merge them, and a green run is not a merge signal: in METR's study, roughly half of test-passing AI pull requests would not have been merged by their maintainers. See [the verification gap](why.md).

The scarce work is now:

- understanding what changed and why;
- judging whether it is the *right* change, not only a green one;
- reviewing other people's pull requests at the same increased volume.

Stageway can open a draft pull request. It never approves or merges one.

<!-- checkpoints: REV-3, REV-1 -->

## Review with AI assistance

| Skill | Use it to |
|---|---|
| `review` | Review your own branch against the requirements and the actual diff. Findings are advisory; in a direct invocation it makes no edits unless you ask. |
| `understand` | Learn a change deeply enough to judge it. It teaches one concept at a time and checks your understanding before moving on. |
| `review-guide` | Get a reading order through a finished change: the key decision, the risky boundaries, the strongest tests, and reproducible checks. |
| `peer-pr-review` | Review someone else's pull request read-only, and prepare feedback that is not sent. |
| `peer-rfc-review` | Do the same for a design proposal. |
| `request-review` | Draft a short review request. It sends nothing without your explicit authorization. |
| `address-pr-comments` | As the author, retrieve every comment and thread, apply the fixes you select, and draft replies. Nothing posts without approval. |
| `pr-preflight` | Check a branch before it goes out: scope, evidence, credentials, and a PR body that does not claim testing that never happened. |

The useful pattern is **understand, then review**. `understand` raises the quality of the human judgment. `review` and `peer-pr-review` widen what that judgment can see.
Neither replaces the named approver.

## Prefer a short queue

Worktrees isolate parallel checkouts. That is an isolation feature, not a throughput target.
Stageway also admits only one runner per project, held by an operating-system lock, so concurrent runs can't fight over the same files.

Running many tasks at once produces:

- a pile of pending draft pull requests;
- merge conflicts against the base branch and against each other;
- review debt that grows faster than any one task.

!!! summary "Rule of thumb"
    Finish **one** task at a time. Two or three are reasonable when they are small, independent, and already waiting on CI or a reviewer.

This is a limit on attention, not on tools. The runner can still work unattended; you just don't start the next task only because you can.

<!-- checkpoints: EXE-5 -->

## Where a task waits

~~~text
specify
    → short wait while the agent researches
    → you answer questions and confirm the plan
implement-pipeline
    → long wait: tests, implementation, optional review, optional delivery
    → you review the result
    → wait for CI and peer review
    → address comments or fix CI
    → wait again as needed
~~~

The manual lane shortens the middle wait because implementation stays in your session.
It does not remove the CI and peer-review waits, or the need to review the diff yourself.

## What to do in the wait

| Wait | Better use of the time | Worse use of the time |
|---|---|---|
| After specify, before you confirm | Read the plan. Check scope, checks, and exclusions. | Start a second specify on an unrelated task. |
| While the pipeline runs | Review an open pull request, yours or a colleague's. Run `understand` on a change you must approve soon. | Start another full pipeline. |
| After a draft pull request | Review this diff with `review-guide` and `understand`. Watch CI. | Open the next issue in a new worktree. |
| Blocked on comments or CI | Address the comments. Diagnose CI. Stay on the same change. | Start another task "so you are not idle". |

Starting a new task during a wait is justified only when all three are true:

1. the current task is genuinely idle, waiting on someone else, with nothing you can act on;
2. you are still within the one-to-three task limit;
3. the new task is small enough not to create another long-lived draft pull request.

Otherwise, review.

## Everyday patterns

**One medium task, full pipeline.** Specify, confirm, and start `implement-pipeline`. Spend the long wait reviewing another pull request. When the run completes, review *this* diff before asking a colleague. Start the next medium task only once this one is in CI or with a reviewer.

**Two or three small follow-ups.** Use the manual lane. Keep each change independently mergeable. Switch only when one is waiting on CI or a reviewer.

**What not to do.** Several worktrees, several draft pull requests, and a day spent resolving merge conflicts. The isolation works. The queue doesn't.

## See also

[Task lifecycle](tasks.md) · [Review and delivery](review.md) · [Skills](generated/skills.md)
