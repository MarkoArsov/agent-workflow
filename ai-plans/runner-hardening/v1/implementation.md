# Implementation proposal

Approval pending. Scope is issue #16; do not execute this file during specification.

## Research and starting point

The source tree at 55cae30 equals local main at 0fe14a9. Current checkout is clean
before planning and remains codex/rename-plovi under current-checkout policy.
No other repository participates. Existing registered worktrees are unrelated.
Use this checkout and its configuration root for all implementation handoff.

Observed in an isolated existing RunnerTests fixture, without product/test edits:
blocked with attempts_per_route=2 produced two provider calls, failed status and
no escalation. Events.report() returned None for spec_conflict and impossible.
runner.py holds local/runner.lock; retry loops do not distinguish a blocked report.
git_ops.py has only path guards and persists delivery progress after side effects.
integrations/github.py reuses a PR without checking/updating its body. state.py
does not detect interrupted owners. The issue's cited defects match this checkout.

Existing facilities to reuse: OS-held POSIX/Windows state locks; atomic JSON writes;
files/content-mode fingerprints; scoped writes and frozen red tests; exact-session
answer; saved verified-stage recovery; argv-based subprocess handling including
Windows .cmd; isolated WorkspaceTest and provider doubles; setup's byte-bound
proposal/three-way preservation. The existing CI matrix already covers all three
OSes and Python 3.11/3.14, with automatic Windows test sharding.

## Sequence

1. implement-tests writes the seven requested test modules plus minimal shared
   fixture support. Red checks exercise existing APIs only: one blocked call,
   the two ignored statuses, and 41 task-owned files requiring approval. Assert
   user-visible behavior, not implementation structure. The new feature checks
   can exercise missing commands through subprocess results; no new-module import
   failures count as red. Save outputs before product edits. No live provider or
   account access is needed.
2. implement adds policy.py and schema; policy resolution/provenance, guarded TOML
   editing, doctor integration and setup generation. Keep policy merging in one
   helper rather than duplicating precedence in CLI/preflight/run. Extend manifest
   validation/schema for new limits; retain old limits and bindings.
3. Add effective execution context shared by preflight, run, detach and resume.
   Preserve explicit profile tool allowlists and derive safe restricted Claude
   defaults from selected check argv only. Record mode/source in binding/state.
4. Extend report parsing, escalation/retry, approvals and retained-stage checkpoints.
   Put diff measurement and gate decisions in reusable helpers used by code-writing
   stages and publish_guard. Fingerprints derive from task-only baseline deltas,
   including new files/modes, rather than unrelated project files. An approval
   pause retains the provider result and verification checkpoint.
5. Refactor locks/claims around a consistent order: task lock first, brief repo-ops
   lock second; never acquire another task lock while holding repo-ops. Stale-owner
   probes must be nonblocking. Claim registration and Git preparation are coordinated
   without nested repo-ops reacquisition. Cleanup is finally-based; crashes reconcile
   claims from OS-held ownership. Include migration.py's legacy-lock guard and
   existing environment locks in the compatibility review.
6. Persist commit intent before mutation; validate/adopt exact commit/tree after
   a crash, reconcile pushed branches and PRs, and expose interruption safely.
   Add fault hooks guarded by PLOVI_TESTING. Use evidence.py (or a comparably small
   module) for the pure formatter and helpers for verified count/assumption inputs.
   Enhance verification parsing only where counts are demonstrably available.
7. Update docs/contracts and affected skill resources, regenerate reference pages,
   run all named green checks, then independent review. Review gets requirements,
   tests and current artifacts, not this implementation narrative. It checks
   outcomes first, then regressions, failure paths, concurrency/recovery and shared
   quality guidance. Correct only in-scope defects and reverify affected checks.
8. Commit logical verified changes locally, respecting runner-owned delivery
   boundaries. No publication is part of this plan.

## Concrete decisions refining the issue

- A full TOML editor is unnecessary. Preserve unaffected source spans/comments,
  replace the selected assignment or append a validated table/key, parse again and
  compare the intended semantic delta. Refuse unsupported edits without data loss.
- A broad Claude Bash wildcard would undermine restricted mode. Build narrow,
  syntax-safe command rules or require an explicit user tool list.
- A saved PR URL cannot skip Evidence updates. Reconcile the body even on resume,
  and use managed-section boundaries to avoid replacing unrelated prose.
- Exact paths/message do not prove ownership of a crash-window commit. Persist
  its expected content/tree before commit and compare on adoption.
- Keep legacy locks readable during transition, and teach migration about task
  locks. Otherwise removing runner.lock could allow migration during live work.
- Pauses release compute claims. Approval/retry/resume reacquire them and revalidate
  the diff, preventing indefinite ownership while a person decides.
- Policy slot/autonomy/grants fields are schema groundwork only. No new scheduling
  engine, ledger or broad command framework is included.

## Model and readiness facts

All executable AI stages use Codex gpt-6.1-sol, medium, no fallbacks, explicitly
selected by the user. The evaluator's initial unresolved output is retained as
model-selection-unresolved.json; the subsequent explicit route revision is the
active model-selection.json and is copied exactly into pipeline.json.
Capability-below-recommendation and single-lineage advisories do not replace the
user's pins. Fresh-session review provides procedural independence, not model
diversity. Provider help/flags can be checked without generation; model entitlement
is verified only on an actual authorized run.

This project currently selects trusted execution. That is the current runner's
readiness mode, not evidence that the proposed unattended-default change exists.
Do not change the real project profile or global agent settings while implementing
fixture behavior. planning-checks.md records actual checks separately from planned
acceptance. Missing MkDocs in the default interpreter is addressed by a disposable
documentation environment; no runtime dependency or user-agent installation changes.
