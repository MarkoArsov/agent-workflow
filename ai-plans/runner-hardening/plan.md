# Issue #16: revised full contract

Approval pending. The previous complete contract is preserved in v1/.
The user added worktree-per-task defaults, full-contract planning commits and
complete handoff reporting to this issue and its planned PR.

## Checkout and delivery

- Canonical project profile: worktree, explicitly changed by request in 53070e1.
- New task branch: codex/runner-hardening.
- New task checkout: .plovi/local/worktrees/runner-hardening/agent-workflow,
  relative to the canonical project root. The old checkout stays parked and clean.
- All task plans and implementation belong in this worktree. Pass the canonical
  project root explicitly to prevent a nested checkout during runner handoff.
- Stages: implement-tests -> implement -> independent review -> commit-and-push ->
  draft-pr. The first three use Codex gpt-6.1-sol, medium, no fallbacks, as requested.
- The PR includes the runner and planning/default fixes. No remote action happens
  before implementation approval and verification. Tracker comments, installation
  and deployment are excluded.

## What will change

1. Stop on blocked/spec_conflict/impossible after one attempt, retain the reason
   and add retry with a note and a fresh session.
2. Enforce diff-bound size/protected-path approvals; resume retained verification.
3. Add validated plovi.toml, policy show/set, provenance, doctor and reviewed setup.
4. Default unattended runs to restricted permissions across providers.
5. Support disjoint worktree tasks with task locks, short repository locks and claims.
6. Recover delivery effects after crashes and prepend observed, redacted PR evidence.
7. Default new project setup to a distinct branch/worktree per issue/task. Fix the
   detector's disagreement between findings and generated checkout strategy.
   Preserve explicit setup opt-outs; never rewrite other projects automatically.
8. Default planning.commit_plans to true, allow a reviewed setup opt-out, prepare
   the task checkout before plan writes, commit the entire contract and report
   requirements/manifest links plus actual branches, paths and commit hashes.
9. Write regression tests first, update docs/contracts and run independent review.

The full scope is in requirements.md; executable mappings and delivery settings
are in pipeline.json. implementation.md gives the proposed sequence; deferred.md
bounds the scope; project-quality.md freezes native/design guidance. plan.md is
only this summary. pr-body.md records the requested PR scope and workflow changes.

## Verification

The manifest maps all nine outcome groups to executable checks. Assertion-level
red first covers the three stop outcomes, 41-file gate and the wrong new-project
checkout default through existing APIs. Green checks cover the requested runner
modules plus real isolated setup/worktree/commit fixtures. Static skill wording
checks do not count as live-agent proof.

The existing suite passed 178 tests before this revision's runtime implementation;
strict MkDocs, generated-doc freshness and 3,964 links also passed. The new runner
features and defaults have not been implemented. planning-checks.md records the
revised validation/preflight and their actual limits.

## What changes for your workflow

Each issue/task gets its own branch and worktree by default. Specify puts the full
contract there and commits it before asking you to approve implementation. Setup
lets you explicitly choose another checkout strategy or disable planning commits.
Blocked runs stop, large/protected diffs ask for approval, unattended runs use
restricted permissions, concurrent worktrees can progress, interrupted delivery
resumes, and PRs show evidence.

Approve this revised plan and start implementation?
