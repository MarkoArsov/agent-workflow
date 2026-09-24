---
title: Design principles
description: The design decisions behind Stageway, each answering a failure mode.
question: What is Stageway, and why is it designed this way?
---

# Design principles

!!! summary "In one minute"
    - You confirm the outcome, scope, checks, and delivery stages. Agents research, implement, and verify inside those limits.
    - Optional stages may be skipped. Their order never changes.
    - Every important claim has an owned, observable proof. An agent's response is a proposal; the runner's observation is the evidence.
    - The run stops only for safety. Advisory findings are recorded and the work continues.
    - All of it is open-source code that runs on your machine.

## At a glance

Stageway takes one task from a written plan to a draft pull request.
Think of fresh horses at every stage: each stage starts a new agent session with the plan, the project's rules, and the repository, so no chat history or bias carries over.

<!-- diagram: workflow -->

The built-in order is fixed:

~~~text
specify → implement-tests? → implement → review? → commit-and-push? → draft-pr?
~~~

`implement` is always required. Writing tests first is required when the task adds or changes tests. Review and delivery are chosen per task.
[Custom stages](customize.md#add-a-stage) slot in before or after a named stage and cannot follow publication.

## Core design decisions

| Decision | Problem it solves | Result |
|---|---|---|
| Research before planning | Agents otherwise guess, or ask questions the repository can answer. | `specify` reads instructions and nearby working examples first, then asks only for decisions that are still missing. |
| Confirm one complete plan | Goals drift while code is being written. | Scope, outcomes, checks, stages, routes, and delivery are agreed before any stage runs. |
| Keep plans complete and auditable | A silent edit hides when a decision changed. | A run binds to a hash of the plan, profile, and skills. A change stops the run until a reviewed `resume --rebind` archives the old inputs and invalidates the affected stages. |
| Map every outcome to a named check | A requirement can be declared done without being exercised. | Validation rejects a plan with an outcome that has no green check. |
| Write tests first when tests change | A test written after the code may prove the implementation instead of the requirement. | The red stage must show the expected tests failing on assertions. Import, syntax, compile, and startup errors do not count. |
| Freeze assertion-proven tests | An agent under pressure can weaken a test until it passes. | Test-file hashes are recorded after red proof. Any later change to them stops the run. |
| A fresh session per stage and per retry | Shared history biases later judgment. | Tests, implementation, review, and every retry start from the plan and the repository, not from each other's chat. |
| Review never sees the implementation's reasoning | A reviewer that reads the author's story tends to agree with it. | The review stage receives the requirements and the actual diff, never `implementation.md`. |
| Allow any confirmed route | A hard model split can block a valid plan. | One provider and model may run every stage, or each stage may differ. Fallbacks are explicit, ordered, and never silent. |
| Verify mechanically | A confident report may still be wrong. | The runner runs the named checks itself and parses their output. |
| Bind green evidence to the diff | Evidence goes stale when the code changes. | Green results carry a fingerprint of the files. Delivery re-runs the checks if anything changed since. |
| Stop only on safety | Treating every finding as a stop turns automation into babysitting. | Scope, secret, frozen-test, verification, and delivery-guard failures stop the work. Review notes and advisory rules do not. |
| Separate implementation from publishing | Correct code and permission to publish are different decisions. | A run can finish without committing, pushing, or opening a pull request. |
| Every external action needs its own authorization | A broad "go ahead" can turn into messages and tracker changes nobody asked for. | Selecting `commit-and-push` and `draft-pr` authorizes exactly those actions. Comments, reviews, messages, and tracker updates each need their own approval. |
| One runner per project | Concurrent runners fight over the same files and hide each other's evidence. | An operating-system lock admits one runner per project. |
| Apply setup only with an approval digest | A proposal can change between review and apply. | Setup applies only the exact proposal you reviewed, identified by its digest. A stale proposal is rejected. |
| Open source and local-first | A closed verification layer is one more claim to trust. | MIT-licensed, readable standard-library code that runs on your machine with your own agent CLIs. See [open source](open-source.md). |

## Responsibilities

| Participant | Owns | Does not own |
|---|---|---|
| You | Product intent, consequential trade-offs, final scope, external actions | Repeating mechanical checks by hand |
| Specify agent | Research, questions, plan completeness, traceability | Product implementation in the full lane |
| Test agent | Plan-specified tests and a meaningful failing state | Product code |
| Implement agent | The planned code and the complete verify-and-fix loop | Unapproved scope, delivery, or publishing |
| Review agent | Independent correctness, regression, and test-adequacy checks; safe fixes within scope | Rewriting the agreed plan. Its findings are advisory unless a deterministic guard backs them |
| Runner | Ordering, path limits, command parsing, state, evidence, safety gates, delivery mechanics | Product decisions, ever |

## When people are involved

The workflow is autonomous inside confirmed, reversible boundaries. It pauses when only a person can supply the missing authority:

- an unresolved product behavior;
- a change beyond the agreed scope;
- a high-risk decision about authorization, money, migrations, or a public contract;
- permission for an external action, such as posting a comment or updating a tracker;
- unrelated local changes that cannot be isolated safely.

And nothing else. Routine retries, local setup, and review findings never become approval steps.

## Stop or flag

| Recorded, run continues | Blocks completion |
|---|---|
| Review findings (advisory) | Secret material or a blocking rule finding |
| Advisory rule findings | Edits outside the declared paths, or to a read-only repository |
| One route for every stage (allowed) | A named check fails, or red or green evidence is missing |
| Usage the provider didn't report (kept as unknown) | A frozen test changed, or a stage touched your pre-existing changes |
| | A check command modified source files |
| | Stale green evidence fails its re-run before delivery |
| | A delivery guard trips: base branch, unrelated staged changes, or a moved HEAD |
| | Configured attempts or time limits run out |

Some blocks are immediate: scope violations, frozen tests, your pre-existing changes, and delivery guards fail the run at once.
Failed checks and blocking rule findings go back to the agent as feedback first, and fail the run only when its attempts run out.

The rule behind the table: a check may stop the run only when every match is genuinely unsafe or incorrect.

## What it optimizes for

| Priority | Meaning |
|---|---|
| Traceability | A reviewer can follow a requirement through implementation and tests to recorded evidence. |
| Bounded autonomy | Agents act independently inside explicit limits, without stopping for advisory notes. |
| Independent judgment | Review does not inherit the implementation narrative. |
| Safe delivery | Publishing happens only after current evidence and the publication guard pass. |
| Maintainability | Recurring mistakes become scoped rules or mechanical checks. |
| Inspectability | Anyone can read, run, and change the code that judges the work. |

## Where it came from

Stageway started from spec-driven development, in the spirit of [GitHub Spec Kit](https://developer.microsoft.com/blog/spec-driven-development-spec-kit/): specify first, then implement.
It grew out of daily use on production codebases, one failure mode at a time.

`specify` interviewed the engineer and wrote the plan. `implement` built it. `review` looked at the result independently.
Test writing was then split out, so new tests fail before product code exists. Commit, push, and draft pull request became optional last stages.
Worktrees made parallel checkouts safe, and skills grew around the rest of the delivery loop: pull request comments, CI, and review.
The [checkpoint rubric](why.md#the-36-checkpoints) shaped how each stage is proven.

<!-- checkpoints: IN-1, IN-2, PLN-1, PLN-3, VER-2, VER-3, VER-5, EXE-4 -->

## See also

[The verification gap](why.md) · [Task lifecycle](tasks.md) · [Evidence and checks](verification.md) · [Checkpoint scorecard](scorecard.md)
