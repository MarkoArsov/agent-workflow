---
title: Review and delivery
description: Independent review, guarded delivery, and the pull-request feedback loop.
question: How does work get reviewed and delivered?
---

# Review and delivery

!!! summary "In one minute"
    - Review is independent by construction: a fresh session with the requirements and the actual diff, never the implementation's reasoning.
    - Review findings are advisory unless a deterministic blocking guard backs them.
    - The runner owns commit, push, and draft pull request. It refuses base branches, never force-pushes, and resumes after partial delivery.
    - Comments, replies, review requests, approvals, and merges are yours, each with its own authorization.

## Independent by construction

The `review` stage starts a new session. It receives the requirements, the project's rules, the actual diff of every participating repository, and the content of new files.
It never receives `implementation.md`, the implementer's reasoning. A reviewer that reads the author's story tends to agree with it.

Review checks correctness, regressions, interfaces, authorization where relevant, failure handling, test adequacy, and unnecessary complexity, citing concrete paths and triggering scenarios.

- **In a pipeline,** review may make safe corrections within the approved paths. It must preserve frozen tests and the intended design. The runner then re-runs the named checks and records new evidence.
- **In direct use,** review is check-only unless you ask for edits.

Findings are advisory unless a deterministic blocking guard backs them, so a review note never holds delivery hostage.
An empty finding set is reported honestly rather than padded.

<!-- checkpoints: VER-3 -->

## Deliver selected repositories

The runner owns commit, push, and draft pull request mechanics. Selecting `commit-and-push` and `draft-pr` in the plan authorizes exactly those actions, with the approved commit message, title, and body file.

| Guard | What it prevents |
|---|---|
| Current green evidence | Publishing a diff that no longer matches its verified fingerprint. Stale evidence is re-run first. |
| Blocking rules and secrets | Publishing secret material or a blocking finding anywhere in the task diff. |
| Explicit task branch | Delivering from a base branch, a detached HEAD, or an unexpected branch. |
| Task-owned paths only | Committing your pre-existing changes, or anything already staged by someone else. |
| Normal push | Force pushes. The runner has no force path. |
| Recorded commit | Pushing after HEAD moved since the delivery commit. |
| Existing pull request | Duplicate pull requests on resume. A matching open one is reused. |

Repositories are independent. If one push fails after another succeeds, `status` records the partial result per repository, and `resume` continues from the recorded commits and pushes.
Draft pull requests stay drafts: the runner never marks one ready, adds reviewers, or posts comments.

The draft body is the approved body file from the plan. Evidence isn't attached automatically yet; `pr-preflight` checks the body for testing claims the evidence doesn't support.

<!-- checkpoints: REV-1, REV-2 -->

## The pull-request loop

<!-- diagram: pr-loop -->

`address-pr-comments` retrieves paginated issue comments, review comments, reviews, and thread state.
Fix the issues you select, run the checks, and draft factual replies. Instructions embedded in comments are data, not authority.

CodeRabbit and Bugbot feedback can be polled for a bounded number of rounds (at most ten).
Temporarily marking a draft ready for bots needs explicit authorization, and its draft state is restored even if retrieval fails.
No bot-control comments, replies, or thread resolutions are sent implicitly.

<!-- checkpoints: REV-4 -->

## Everyday tools

| Skill | Use it for |
|---|---|
| `pr-preflight` | Scope, evidence, credentials, and PR-body claims before a pull request goes out. |
| `diagnose-ci` | A specific failed CI run, starting from the exact revision and failure log. |
| `peer-pr-review` | Someone else's pull request, read-only, with feedback that is not sent. |
| `review-guide` | A reading order through a finished change for a human reviewer. |
| `commit`, `push` | The same guarded steps, run independently. `push` never force-pushes. |
| `worktree-start`, `sync-base` | Preparing a task checkout, and fast-forwarding a clean base checkout. |

## See also

[Review and everyday use](everyday.md) · [Skill reference](generated/skills.md) · [When a task stops](recovery.md)
