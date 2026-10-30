# Issue #16: proposed plan

Approval pending. Full lane: implement-tests -> implement -> independent review.
All three stages use Codex gpt-6.1-sol, medium effort, with no fallback, as requested.
One writable repository, current checkout codex/rename-plovi; no branch switch.
No publishing stages, tracker updates, real installations or agent settings edits.

## What will change

1. Stop on blocked/spec_conflict/impossible after one attempt, expose the reason,
   and add retry with an optional note and a fresh session.
2. Stop for changes above 40 files/1,500 lines or to protected paths; approvals
   bind to the exact diff and resume verification without repeating finished work.
3. Add validated plovi.toml, policy show/set, per-value sources, doctor notices and
   reviewed setup generation. Preserve existing profiles, policy comments and runs.
4. Default detached/non-interactive runs to restricted mode across providers,
   derive narrow Claude tools and record explicit --trusted overrides.
5. Replace the project runner lock with task locks and short repository locks;
   allow disjoint worktree tasks, wait for overlapping claims and clean stale claims.
6. Reconcile commits, pushes and PRs after crashes; detect interrupted owners via
   locks, and prepend verified, redacted Evidence to PR bodies.
7. Add the seven requested regression modules first, update docs/contracts and
   verify all existing behavior and cross-platform fixture boundaries.

requirements.md gives the complete contract and decision refinements. In particular,
commit adoption checks exact content/tree; multiple approval gates cannot bypass
each other; migration still refuses active tasks after the lock layout changes.
project-quality.md freezes the applicable native/design guidance, and the manifest
selects the package's shared quality checklist.

## Verification

The manifest maps all eight outcome groups to executable checks. implement-tests
first proves the three stop outcomes and 41-file limit with assertion-level red
using existing runner APIs. New feature coverage then joins the green checks.
No setup/import failures qualify as red. Seven focused suites, the full suite,
strict MkDocs build, links, generated-doc freshness and public source/history audit
must pass. Current macOS evidence does not substitute for the existing hosted
Linux/Windows/macOS matrix; remote execution is separately authorized.

planning-checks.md distinguishes actual research/readiness results from acceptance
work that has not started. A successful preflight confirms CLI/flag readiness, not
account entitlement or implementation approval. The evaluator retained the user's
pins with capability-band and same-lineage advisories; it made no provider call.

## What changes for your workflow

Blocked tasks stop with a reason and can be retried. Large/protected changes ask
for a diff-specific approval. Projects can review limits in plovi.toml. Background
runs default to restricted mode. Independent worktree tasks can run together, and
interrupted runs resume without duplicating delivery. PRs show observed evidence.

Approve this plan and start implementation?
