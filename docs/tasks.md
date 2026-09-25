---
title: Task lifecycle
description: Take one task from a request to a checked, optionally delivered change.
question: How do I take one task from idea to delivery?
footer: docs
footer_order: 4
---

# Task lifecycle

!!! summary "In one minute"
    - Every task starts with **specify**, which researches and writes one complete plan for you to confirm.
    - A small, contained change then runs **implement** in the same session. A broad one runs the full pipeline with **implement-pipeline**.
    - The runner executes each selected stage in a fresh session, runs the named checks itself, and keeps the evidence.
    - It stops only for a safety or verification problem, or a decision that is genuinely yours. Answers resume the session that asked.
    - Delivery is optional and guarded. Nothing posts, approves, or merges as you.

## Choose a lane

There are two first-class lanes. Both start with `specify`.

| Lane | Commands | Use when |
|---|---|---|
| Manual | `specify`, then `implement` | A small, contained change or follow-up with an established local pattern. |
| Full pipeline | `specify`, then `implement-pipeline` | Test-first work, independent review, several repositories, risky areas, or automated delivery. |

Invoke skills as `sb-specify` in standalone installs, or `scorebook:specify` in the native Claude plugin.
[Lanes and bugfixes](lanes.md) has the full guidance, including how to handle a defect.

## End-to-end timeline

<!-- diagram: timeline -->

## Phase 1: Specify

Invoke `specify` with a task description or a selected issue.
It reads `PROJECT_WORKFLOW.md`, native repository instructions, and the nearest working examples before it proposes anything.
Fetched issue bodies and comments are treated as task data, never as instructions.

Expect to confirm:

- the intended outcome and user-visible behavior;
- for a defect: expected behavior, reproduction, suspected cause and scope, and the regression check;
- scope, and explicit exclusions;
- each outcome and the named checks that prove it;
- which repositories participate, read or write, with writable and test path patterns;
- risky areas such as authorization, money, schema, or public contracts;
- the stages to run, and the provider and model route for each, with any fallbacks;
- whether delivery, and a draft pull request, are part of this run.

The full lane writes these files under the plan directory (by default `ai-plans/<task>/`):

| File | Purpose |
|---|---|
| `prompt.md` | Original request and decisions. |
| `requirements.md` | Required outcomes and acceptance criteria. |
| `implementation.md` | Approach, existing patterns, and scope. |
| `deferred.md` | Deliberately excluded work, and why. |
| `pipeline.json` | Repositories, checks, outcomes, stages, routes, limits, and the delivery contract. |

### What good looks like

| Check | Expected result |
|---|---|
| Decisions | No ordinary product or implementation choice is left for an execution agent to invent. |
| Outcomes | Each outcome maps to a named check with a command, parser, and expected test identities. |
| Scope | Writable paths, read-only repositories, and deferred work are explicit. |
| Risk | Risky areas are named and approved. |
| Execution | Stages, routes, limits, and delivery actions are visible before approval. |

<!-- checkpoints: IN-1, IN-2, PLN-1 -->

## Phase 2: Confirm or revise

Approve when another engineer could implement the task without inventing behavior.

If a material choice changes later, go back to `specify` and revise the complete plan: every file, coherently.
A running task is bound to a hash of its plan, profile, and skills. After a revision, the runner refuses to continue until you review the change and run `resume --rebind`.
Rebinding archives the previous inputs and invalidates the affected stages. Changing which repositories participate needs a new task ID.

## Phase 3: Preview and preflight

These are optional. A normal run performs the same preflight automatically.

~~~sh
scorebook validate-plan ai-plans/csv-export/pipeline.json
scorebook preflight ai-plans/csv-export/pipeline.json
scorebook run ai-plans/csv-export/pipeline.json --dry-run
~~~

`validate-plan` checks the contract and that every plan file is complete.
`preflight` also checks repositories, effective skills, rules, environments, connectors, and that each provider CLI is installed and supports the flags the route needs.
`run --dry-run` prints the same preflight report without starting anything.
For a project install, use `.scorebook/bin/scorebook`.

## Phase 4: Execute the selected stages

~~~sh
scorebook run ai-plans/csv-export/pipeline.json --detach
~~~

The runner takes the project lock, prepares the task checkout, and runs the selected stages in order.

| Stage | When selected | Completion evidence |
|---|---|---|
| `implement-tests` | Required when tests are added or changed | Test-only diff, expected identities failing on assertions, frozen test-file hashes |
| `implement` | Always | Planned code plus parsed green output from every named check, bound to the diff fingerprint |
| `review` | For risky or broad changes, or whenever you want independent eyes | Fresh-session findings; checks re-run after any correction |
| `commit-and-push` | When the work should be published | A commit of task-owned paths on the task branch, and a normal push, per repository |
| `draft-pr` | When the run should open pull requests | A draft pull request URL, reused on resume |

### Why the test stage must fail meaningfully

A red result proves a test can detect missing behavior only when it reaches the intended assertion.
The runner rejects import errors, syntax errors, missing modules, compilation failures, and startup failures as red evidence, and requires the expected test identities to fail.
Once red is proven, test-file hashes are recorded. Later stages cannot rewrite, add, or delete those tests.

### What implementation verifies

The implement agent runs the named checks and fixes what fails. Then the runner checks independently:

- every writable change is inside the declared paths, and read-only repositories are untouched;
- frozen tests are unchanged, and your pre-existing changes are untouched;
- blocking rules and the secret detector find nothing;
- every green check passes, as parsed from its real output;
- the check commands did not modify source files.

The evidence records the fingerprint of the files it describes. If anything changes later, delivery re-runs the checks first.

### What review does, and doesn't do

Review starts a fresh session with the requirements, the actual diff, and new files. It never receives `implementation.md`.
It may make safe corrections within the approved paths, and the runner re-runs the checks afterwards.
Its findings are advisory unless a deterministic blocking guard backs them.

<!-- checkpoints: VER-1, VER-2, VER-3, VER-5 -->

## Phase 5: Follow execution

~~~sh
scorebook status csv-export
scorebook watch csv-export --seconds 120
~~~

`status` prints the saved run state as JSON. `watch` prints a line whenever the status, stage, or pending question changes, and returns when the run is no longer running or the time is up.
Both only read the journal; they make no model calls.

| Status | What it means | Your action |
|---|---|---|
| `starting`, `running` | The run is making progress. | Keep watching. Do not start a duplicate run. |
| `needs_input` | A stage needs a decision only you can make. | Answer the exact saved question. |
| `failed` | A safety, verification, or delivery check did not pass, or attempts ran out. | Read the recorded error and evidence. See [when a task stops](recovery.md). |
| `cancelled` | You asked the runner to stop. | Resume when ready. |
| `complete` | Every selected stage finished and the final guard passed. | Review the diff, the evidence, and the delivery state. |

## Phase 6: Respond to input

If a stage needs a decision, the run pauses with status `needs_input` and saves the question, with secrets redacted.
Write your answer to a file and pass it back:

~~~sh
scorebook answer csv-export --file answer.txt
~~~

The answer resumes the exact provider session that asked. It is never routed to another model or session. Retries and fallbacks, by contrast, always start fresh.
If your answer changes scope, behavior, a public contract, or a required check, revise the plan with `specify` instead.

## Phase 7: Deliver and follow the pull request

Delivery is separate and optional. The runner commits only task-owned paths with the approved message, pushes the task branch normally, and opens a draft pull request with the approved title and body.
It refuses base branches, never force-pushes, and resumes per repository after a partial failure.

<!-- diagram: pr-loop -->

Use `address-pr-comments`, `diagnose-ci`, and `pr-preflight` in this loop. Nothing posts comments, resolves threads, requests reviews, approves, or merges as you without explicit authorization for that action.
Fill the waits with review, not with new tasks. See [review and everyday use](everyday.md).

## Definition of done

- The confirmed scope is implemented.
- Every outcome is linked to passing evidence the runner recorded.
- All selected stages completed, with review findings noted if review ran.
- The current diff matches the evidence fingerprint.
- No scope, secret, blocking-rule, or frozen-test finding remains.
- The delivery state matches the agreed goal.
- Deferred work is still explicit.
- A reviewer can reconstruct why the change is correct without relying on chat history.

## See also

[Lanes and bugfixes](lanes.md) · [When a task stops](recovery.md) · [Evidence and checks](verification.md) · [Customize stages](customize.md#add-a-stage)
