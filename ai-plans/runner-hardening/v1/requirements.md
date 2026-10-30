# Requirements

Status: proposed; implementation approval pending. Outcome IDs below match
pipeline.json. All behavior is additive for saved schema-version-1 runs.

## R1. Stop outcomes and retry

Accept complete, needs_input, blocked, spec_conflict and impossible in provider
reports, prompts and public contracts. Require a nonempty question for needs_input
and a nonempty reason for each escalation. Retain an optional string assumptions
list. Malformed reports are not successful evidence.

blocked, spec_conflict and impossible record the attempt and stop immediately with
status escalated and escalation {stage, kind, reason, route, session, at}. They never
consume another attempt or fallback. Cancellation and hard scope guards retain
their protections; preserve and expose an escalation even if a scope violation must
also be reported. Transient errors and verification failures retain bounded retry;
authentication/quota/model failures retain the existing approved fallback behavior.
Do not weaken the existing out-of-scope-write guard to make it retryable.

retry <task> [--note FILE] is allowed for an escalated task; it clears the active
escalation, retains its history and attempts, resumes the same stage in a fresh
session and adds the redacted note under NOTE FROM THE PERSON. Ordinary resume
cannot silently clear an escalation. needs_input continues to use answer and its
exact provider session. status includes reason and the retry command.

Checks: stop-regressions; outcomes. Distinct fixtures cover all three escalation
kinds, no second route, needs_input, malformed reports, transient recovery and notes.

## R2. Size and protected-path gates

Count cumulative task-owned changes against the saved baseline, including tracked,
untracked, removed, renamed and binary files. Added plus removed text lines use
Git numstat semantics; each changed binary counts as one line. Exempt paths count
toward neither size total; exemption does not bypass scope or protected-path rules.
Defaults: 40 files and 1,500 lines. Normalize glob behavior for root and nested
lockfiles, including package-lock.json, poetry.lock and *.lock. Count all writable
participants together, retaining repository identities for protected paths.

Check after every code-writing attempt/stage and again before delivery. Retain
needs_approval, with approval.kind size and files/lines/limit, or protected_paths
and the exact matching paths. If both apply, retain both pending requirements and
require both approvals. No provider fallback or delivery runs through a pending gate.

approve <task> --size|--paths records actor, reason, time and a content/mode/path
fingerprint of the current task diff. Support optional --reason and --actor;
default actor comes from configured identity, never a fabricated person. Missing
identity gets an actionable error; the default reason describes the explicit
--size/--paths approval so the issue's short command forms remain sufficient.
Approval resumes verification of the retained
stage output, not the completed provider call. A subsequent diff change invalidates
the relevant approvals. Ordinary resume cannot bypass pending approvals. Runner
and plan inputs are not automatically approved for modifying policy itself.

Checks: size-regression; limits. Include exact boundaries, binary/untracked/deleted
and renamed paths, exemptions, two gates, stale approvals and pre-delivery recheck.

## R3. Evidence in PRs

Provide a pure evidence_markdown(state, manifest) -> str. Prepend one Evidence
section to the plan body: outcome checks and results/counts where actually parsed;
completed stages with provider/model; attempts used; changed-file/line totals;
final-report assumptions; fingerprint. Use existing verified state, not agent claims.
Counts not supplied by a parser remain unknown. Redact every displayed string,
escape Markdown structure, and redact the whole final body too.

Reuse the one matching open PR for the branch/base. Read its body and update with
gh pr edit --body-file only when generated Evidence changes. Preserve the plan
body and any unrelated existing body content. Store the PR URL and evidence digest;
reconcile remote state after interruption instead of trusting a missing local flag.

Checks: evidence; recovery. Assert stable rendering and unchanged evidence causes
no edit, changed evidence causes exactly one edit, and secrets never appear.

## R4. Policy file and setup

Add policy.py with defaults(), validate(dict) and load(project), plus
schemas/policy.schema.json. Load configuration_root/plovi.toml with tomllib. Validate
unknown keys with their dotted path and a close-key suggestion, exact types
(including rejecting bool as int), positive bounded limits, lists of strings,
repository-relative globs and enumerations. Malformed TOML is actionable.

Defaults:

| Section | Values |
| --- | --- |
| limits | running_tasks=2; waiting_for_review=3; attempts_per_stage=2; max_changed_files=40; max_changed_lines=1500; size_exempt=["**/package-lock.json", "**/*.lock"] |
| paths | protected=[".github/workflows/**", "**/migrations/**"] |
| execution | unattended_permission_mode="restricted" |
| autonomy | level="assisted"; accept assisted, ready, auto without enabling later autonomy features |
| grants | empty reserved table; reject unsupported entries until defined |

Precedence per key: explicit plan limits > policy > corresponding existing profile
values > built-ins. Map attempts_per_stage to existing attempts_per_route; this
retains per-route behavior, not a new aggregate attempt budget. Review/running slot
keys are accepted/reserved for later scheduling and do not implement a scheduler.
Only explicit TOML keys override the profile. doctor reports missing policy and
duplicate policy/profile values without breaking install-only/global doctor.

policy show [--json] gives effective values and each source, excluding secrets.
policy set <dotted.key> <value> shows a unified diff, validates before writing and
requires --yes or a literal interactive y; non-TTY without --yes refuses. A small
canonical writer supports tables, quoted strings, finite floats, ints, booleans and
string arrays, retaining unrelated comments and untouched text. No-op edits preserve
bytes. Detect stale edits, use atomic replacement, and reject unsupported TOML edits
without rewriting the document. Test CRLF, quoted/comment characters and round trips.

New-project setup includes a commented policy in the displayed proposal and approval
digest; repeated setup preserves existing policy, comments and user edits. Existing
projects keep missing-file defaults until a reviewed write. Freeze effective policy
and permission decisions in run binding/state; changes use explicit rebind rather
than silently altering a running task. Existing saved bindings without policy remain
resumable with a documented legacy policy interpretation.

Checks: policy; full-suite; docs-build; generated-docs.

## R5. Unattended permission defaults

Unattended means --detach or non-TTY stdin, with a future schedule able to pass
the same explicit context. Default to restricted unless explicit policy allows
trusted or --trusted is supplied. A normal interactive run keeps profile behavior.
Persist mode and source (unattended default, policy, --trusted, or profile), propagate
them to the detached child and resume, and show them in preflight. Do not infer
TTY state from the child's DEVNULL and lose the original choice. Existing provider
command construction remains the source of platform-specific arguments.

For restricted Claude, preserve explicit allowed_tools. Otherwise derive Read,
Edit, Write, Glob, Grep, Bash(git status*) and Bash(git diff*) plus each selected
configured check's argv. Escape/validate CLI tool syntax and shell metacharacters;
never grant a broad Bash wildcard to accommodate an unsafe expression. Unsupported
command encodings fail preflight with a precise instruction to supply allowed_tools.
Document extension and the fact that restricted agent tools do not restrict runner-
owned checks/delivery beyond their existing contracts. No new Claude/Cursor calls
or real-account smoke tests are required by automated tests.

Checks: permissions; full-suite. Cover each provider, detached and non-TTY runs,
--trusted propagation and recording, interactive profile mode, resume and preflight.

## R6. Concurrent tasks and locks

Use the task evidence directory's runner.lock for the run lifetime. Use a short
repo-ops.lock around claim changes and repository mutations (worktree add/remove,
fetch, branch creation, push). Never hold that lock across providers or checks.
Keep existing POSIX/Windows OS-held locking; open each handle once and retain it.

claims.json records task identity, canonical repository/common-dir identity,
checkout strategy and writable patterns. Acquire claims atomically before Git
preparation, remove them on complete/failure/cancel and pauses, then reacquire on
resume. Remove stale claims only after confirming the owning task lock is free,
never by PID alone. Claims for an active legacy project runner block new work.

Only worktree tasks can share one repository. current-checkout and feature-branch
cannot run concurrently there even with disjoint patterns. Use normalized relative
paths, literal prefixes plus existing-file intersection for glob overlap; conservatively
report a conflict for patterns whose non-overlap cannot be established. Handle **,
root-level patterns, case rules and unborn/untracked future file names explicitly.

Overlap produces waiting with waiting_for task IDs; cancellable bounded polling
retries claims after the owner releases them. --no-wait fails immediately with a
clear conflict. Same-task starts are serialized. Existing shared-environment locks
remain in force. Migration checks both legacy project locks and active task locks;
changing the runner lock must not permit migration during a live run.

Checks: concurrency; full-suite. Two detached worktree tasks must overlap in time
and complete; separate scenario files avoid races in the provider double's call log.
Also test wait/no-wait, cleanup on error/cancel/crash/pause, same-task rejection,
current-checkout refusal, read-only companions and live-lock migration refusal.

## R7. Crash recovery and compatible state

Before commit, persist delivery intent: baseline head, expected paths, message,
approved content/modes and expected result tree. After a crash adopt HEAD only if
its single parent is baseline HEAD, its exact message matches, changed paths are
exactly task-owned, and contents/tree match the saved intent. A message/path-only
comparison is insufficient. Unexpected HEAD, altered contents or a foreign index
still fails safely. Keep pre-existing user changes out of delivery.

When pushed is missing, compare ls-remote's exact branch to the saved commit;
equality adopts without a push. Query failure is not proof of absence. Otherwise
use normal guarded push, never force. Reuse the one matching open PR and its URL.
Recompute/verify content evidence without treating the delivery commit's HEAD-only
change as a new diff. Do not skip a saved PR's Evidence synchronization.

On status/watch, resume, retry and existing task enumeration, probe the task lock
non-blocking. Under that acquired lock re-read and persist interrupted if starting
or running was left without an owner; this prevents races with resume. Never kill
by stored PID. Live legacy project locks retain their meaning for old states.
Interrupted resume keeps finished stages and work, verifies the active stage's
retained output and adopts delivery effects. It must not repeat successful provider
work just because the process died before verification was saved.

Use additive state fields, optional on read, with explicit checkpoints and old-run
fixtures. Fault injection PLOVI_TEST_CRASH_AFTER=commit|push|pr is inert unless
PLOVI_TESTING=1. Include pre/post-save windows and an actual abrupt child exit.

Checks: recovery; concurrency; evidence; full-suite. Prove exactly one commit, push
and PR with local bare remotes, reflogs/call counts and gh fixtures, plus negative
adoption cases for extra parents, changed message/content/path and diverged remote.

## R8. Verification, docs and delivery boundary

Author the seven requested modules: test_runner_outcomes.py, test_limits.py,
test_policy.py, test_permissions.py, test_concurrency.py, test_recovery.py and
test_evidence.py. Use WorkspaceTest, temporary repositories/remotes, isolated child
homes and configuration, and deterministic provider/gh doubles; no network. Do not
weaken, delete or skip existing tests. Assertion red precedes product changes for
the existing blocked/parser/size defects; new APIs are imported only inside relevant
green tests so their absence does not masquerade as assertion red. Keep frozen
tests unchanged in implementation/review; revise the plan if requirements need it.

Run the regression red checks on the unchanged starting code, whose file tree equals
local main, and retain the exact revision/output. Windows/Linux/macOS verification
uses the existing CI matrix; no hosted run or cross-platform result is claimed here.

Update recovery.md, profile.md, security.md, execution.md, add policy.md under
Configure in mkdocs.yml, update pipeline-contract.md and affected CLI/schema/setup
documentation and skill guidance. Generate committed reference pages. Copy is short,
active and lowercase plovi, and includes What changes for your workflow. Retain the
existing docs components/tokens; no restyle is included.

Required checks: full-suite, docs-build, links, generated-docs and public-content.
Run generated-docs before a build so auto-generation cannot conceal stale files.
Run link checks after the strict build; scan public source/history before each
logical local commit and again afterwards. Private-denylist absence is reported.

Implementation remains local. Do not select commit-and-push or draft-pr stages.
The native instruction to commit logical changes locally remains applicable;
commits happen outside runner-owned AI stages. A later separately authorized PR
must list shipped behavior, exact test cases/results and workflow changes.
