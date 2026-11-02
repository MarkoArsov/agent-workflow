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
| `starting`, `running` | A worker owns the task; inspect its last activity. | Keep watching, or `watch` if you left. Don't start a duplicate; the task lock would refuse it anyway. |
| `needs_input` | A stage needs a decision only you can make. | Answer the saved question with `answer --file`. |
| `failed` | A safety, verification, or delivery check failed, or attempts ran out. | Read `error` and the latest evidence. Fix the cause, then `resume`. |
| `cancelled` | You asked the orchestrator to stop. | `resume` when ready. |
| `complete` | Every selected stage finished and the final guard passed. | Review the diff, evidence, and delivery state. |

## If something failed

Start with `plovi status TASK`. The `error` field names the failure; the evidence directory holds each attempt's output and each stage's check results.
Read the failing command or provider result before retrying.

| What happened | Best next step |
|---|---|
| A connection or service was briefly unavailable | The orchestrator already retried within its limits. If it keeps failing, investigate the environment, then `resume`. |
| Authentication, quota, or model unavailable | The orchestrator moved through your approved fallbacks. Repair access, or add a route you approve, then `resume`. |
| Timeout, inactivity, or a stalled tool | Inspect the attempt's output and the dependency's health. Don't raise limits indefinitely to hide a repeated failure. |
| A named check failed | Fix the underlying code, test, or local setup within scope. Never weaken the check to make it pass. |
| Scope violation | The changes are kept for inspection. Undo only the unauthorized edits, or revise the plan. |
| A frozen test changed | Restore it. If the test or requirement was wrong, revise the plan completely and `resume --rebind`; red proof runs again. |
| A stage touched your pre-existing changes | Keep your changes separate from the task, then `resume`. |
| A check command modified source files | Fix the command's output or cleanup configuration so checks leave the checkout unchanged. |
| Partial delivery | Inspect the per-repository delivery state. `resume` continues without recreating successful commits or pushes. |
| Plan, profile, or skills changed | Review the complete revision, then `resume --rebind`. |
| The task discovered a missing product decision | Revise the plan with `specify` before continuing. |

The orchestrator retries temporary problems and resumes saved progress. It does not silently change the approved route, or ignore a failed check.

## Answer, resume, rebind, cancel

~~~sh
plovi answer csv-export --file answer.txt
plovi resume csv-export
plovi resume csv-export --rebind
plovi cancel csv-export
~~~

- **Answer** resumes the exact provider session that asked. Retries and fallbacks always start fresh sessions.
- **Resume** continues from the first incomplete stage. A stage whose verified evidence still matches the current files is not repeated.
- **Rebind** accepts a reviewed revision of the plan, profile, or skills. It archives the previous inputs and invalidates the stages they affect. Changing which repositories participate needs a new task ID.
- **Cancel** asks the owning orchestrator to stop its own process group. A stale PID in the journal never authorizes killing a process, and one orchestrator owns each task at a time.

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

## When GitHub Actions fails

The **Verify** workflow checks pull requests, pushes to `main`, and manual dispatches.
A feature branch without a PR can be checked with **Run workflow** in GitHub Actions.
New updates cancel superseded verification runs for that PR or branch; documentation
publishing uses a separate concurrency group.

The six `core` jobs run isolated tests on Linux, macOS, and Windows with Python 3.11
and 3.14. The `audit` job checks generated documentation and public content once,
including all fetched reachable history. The `docs` job checks the built site.
`windows-install` installs the checked-out source in Windows PowerShell 5.1 and
reinstalls it in PowerShell 7 using temporary child environments. This proves local
installation, discovery stability, and the installed command; it does not prove
remote archive availability. Keep the documented remote bootstrap release smoke
check separate.

Read the failing step first. A failed test or audit stays blocking; there is no
blanket retry or success override. Failed jobs retain their diagnostic logs as
artifacts for seven days and add a short job summary. These logs come from isolated
checks, not from a dump of the runner's credentials or environment.

For an audit finding, the diagnostic identifies a file or a representative commit
and a finding type without printing matched credentials or private denylist terms.
Repeated unchanged path/blob pairs are inspected once; every reachable commit
message is still checked. One reviewed public automation address is accepted only
inside a final `Co-Authored-By` trailer block. That exception does not apply to ordinary
file content or to other addresses, and a supplied private denylist still takes
precedence. Investigate an unexpected finding before changing the policy.

To reproduce the shared audit locally:

```sh
python3 scripts/generate_docs.py --check
python3 scripts/check_public_content.py --history
```

The history audit checks every locally reachable ref. Fetch the relevant remote
history before comparing local and CI results. Scan a release tree or built site
separately when verifying those deliverables.

## Escalations and interruptions

`blocked`, `spec_conflict` and `impossible` stop after one attempt with status
`escalated`. Status retains the reason, stage, route and session, and shows the
retry command. Ordinary resume cannot clear an escalation.

```sh
plovi retry TASK --note decision.txt
```

Retry retains history and starts a fresh session with your redacted note under
NOTE FROM THE PERSON. `needs_input` still uses `answer` and the exact asking session.

Status and watch probe the OS-held task lock. A running journal with no owner
becomes `interrupted`; no process is killed by a saved PID. Resume verifies retained
stage output and preserves completed work. Delivery persists intent before commit,
then adopts only the exact expected tree, message, paths and single parent. It
reconciles the remote branch and matching open PR after a crash. Foreign changes
or failed remote queries stop recovery. Never force push to repair recovery.

`needs_approval` retains size and protected-path requirements. See [policy](policy.md).

!!! note "What changes for your workflow"
    Use retry for an escalation, answer for a question, and resume for an
    interruption. Inspect the recorded reason and diff before continuing.

## Delivery after workflow changes

A task may update plovi's own skills or shared references. If delivery stops after
the task's verified commit was pushed, resume can retain the original frozen
inputs when those changes are part of that exact verified commit. Changes to the
plan or project settings, a different commit, or uncommitted edits still require
review. Configure the intended `gh` executable in the launching environment's
`PATH`; plovi does not select a GitHub account from a repository owner.

## Resume retained work after a repair

`resume` checks the current task worktree and revalidates successful saved provider
output before invoking another agent. A valid completion report alone does not
complete a stage: current scope guards and named checks must pass.

When a person has approved local repair commits, a reviewed plan revision can list
full commit IDs under `recovery.approved_commits`, keyed by repository ID. Resume
with `--rebind` adopts only those linear descendant commits and task-plan-only
follow-up commits. Unknown commits, branch changes, staged content and uncommitted
changes to repair paths stop recovery. Prior baselines are saved in local recovery
journals. The runner preserves uncommitted stage output and verifies it; it never
resets or stashes that work. Existing escalations and diff approvals still require
their explicit retry or approval commands. Recovered stages consume no new model
request. An explicit retry starts a fresh attempt.

## Start or continue through one entry point

Use `implement-pipeline` again, or `plovi pipeline TASK`. It reuses an active worker
and safely resumes interrupted/failed work with the saved runtime. Retained output
is checked before new inference. Pending questions, explicit cancellation,
escalations and diff approvals stay visible; use their named answer, resume, retry
or approval action after review. Runtime upgrades require explicit
`--upgrade-runtime --rebind`, preserving the old receipt.

Mechanical fixture failures can enter the independent correction path described in
[verification](verification.md#fixture-health-and-independent-correction).
Requirements decisions and identity mismatch remain stops. The worker records
structured provider failures, approved fallback attempts and bounded exhaustion.
No normal recovery requires hand-editing `state.json`.

Status separates worker heartbeat from provider/tool activity. A heartbeat confirms
the worker is alive; it does not prove product progress. Waiting on a repository
claim remains observable. An unowned running/waiting journal becomes interrupted.
An inability to terminate owned children is recorded as `cancellation_failure`,
with cleanup unconfirmed, and stops further requests. Inspect it before retrying;
never signal a process based only on a saved PID.

New retained-output receipts include the artifact changes observed at completion.
If those files change before recovery, plovi refuses to adopt the report. Inspect
foreign edits or approve exact repair commits first. Legacy receipts without these
hashes still require complete deterministic verification; they do not gain stronger
provenance retroactively. A runtime receipt cannot be replaced while a worker or
launch owns the task.

## Migrate a legacy authored-test checkpoint

For an existing run stopped before implementation, `plovi migrate TASK` previews a
reviewed checkpoint handoff. `--apply` performs it without starting product work.
The manifest must name exact original binding and fixture-escalation hashes in
`recovery.test_checkpoint`. Requirements, existing checks/outcomes, stages and
routes must stay unchanged; authored frozen tests must still match. Baseline test updates require exact source approval and an unchanged assertion/test contract. Only additive
fixture-health checks are accepted. New health commands can refresh a derived
restricted Claude check allowlist; explicit tool settings and permission mode stay
in force.

Approved source updates still require exact `recovery.approved_commits`. Merge
commits additionally require `recovery.approved_merges` and reviewed rebind; ordinary
resume never adopts an unreviewed merge. The handoff checks for foreign edits and
archives the original state/binding before adoption. An optional `fixture_request`
uses the bounded independent test-author/reviewer path, preserving test identities
and assertions. Setup and red proof must pass before the existing test stage is
retained and its exact escalation is archived.

A completed handoff leaves the run interrupted at implementation. Use `pipeline
TASK` to continue when requested. Repeating migrate with unchanged proof reuses its
receipt without another provider request. Changed requirements, tests, identity,
permissions, ownership, pending decisions or unconfirmed cleanup require review.
No normal operation involves editing the saved state by hand.

## Recover factory and container work

Resume validates the saved factory receipt, branch and real remote identities. It
never relocates existing local work or refreshes/rebases an active task. User-clone
edits do not affect factory scope guards; task-owned writable and companion
snapshots remain guarded. Changed ownership needs inspection, not automatic adoption.

Container resume uses the frozen image ID and effective boundary. The task lock
protects cleanup of retained owned containers and networks before provider replay.
Restore an unavailable engine to complete pending cleanup; no unrelated resource
is removed. A failed contained command never retries on the host. See
[isolated execution](isolation.md) for fallback and safe terminal cleanup.

!!! note "What changes for your workflow"
    Inspect the saved task checkout when recovery reports ownership changes. Keep
    its receipts, mirrors and evidence until the task is cancelled or confirmed
    closed/merged and all work is safely retained.
