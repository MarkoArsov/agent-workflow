# Harden unattended runs and prepare each task in its own worktree

Addresses #16.

## Shipped behavior

Stop explicit blocked/spec-conflict/impossible outcomes without consuming retries;
add diff-bound size/protected-path approvals, reviewed plovi.toml, restricted
unattended execution, per-task claims/locks, delivery crash recovery and verified
PR evidence.

New project setup defaults to a branch
and worktree per issue/task; specify prepares/reuses that checkout before writing,
commits the complete contract when planning commits are enabled, and reports its
requirements/manifest links, branches, checkout paths and planning commit. Setup retains explicit checkout overrides for new specifications.
Detection findings and generated profiles agree.

Delivery retries preserve the original frozen inputs when changes to bundled
workflow guidance are verified, committed task output; unrelated changes still
require review. The pipeline handoff checks the selected GitHub CLI path so an
existing account-routing wrapper can be used for delivery.

## Verification

- Regression red at `3bc42c754456e7bd07860ced728faea93374dd99`: all five expected assertion failures, then green for `test_blocked_stops_after_one_attempt`, `test_spec_conflict_stops_after_one_attempt`, `test_impossible_stops_after_one_attempt`, `test_41_files_need_approval`, and `test_new_project_defaults_to_worktree`.
- All 16 named green checks passed through `plovi verify`. The final full-suite rerun passed 249 tests, no skips, on local macOS/Python 3.14.
- New suites: runner outcomes (10), limits (14), policy (10), permissions (9), concurrency (6), recovery (12), evidence (5), task planning (5). Existing assertions remain intact.
- Abrupt-exit cases after commit, push and PR creation prove one delivery effect with local bare remotes and a recorded gh double. Negative cases reject changed content/message/paths/parents, foreign index content and remote divergence.
- Two detached worktree tasks overlapped and completed. Isolated planning walkthroughs verified complete contracts committed in separate task worktrees with the parked checkout unchanged; these are manual procedures, not agent-execution claims.
- Generated references are current; strict MkDocs passed; 4,135 internal links/assets passed; public source/history scan had zero findings. Private denylist was not supplied.
- Tests use isolated child configuration, provider/GitHub doubles and local remotes. Hosted cross-platform CI and real-account provider inference were not run.

- Merge and checkout override verification: 260 tests passed locally; the additional
  unrelated-branch safety case passed separately. Strict documentation build and
  4,141 links/assets passed. Explicit setup selections are honored for new tasks;
  unmarked legacy profiles retain isolated worktrees.
- Follow-up recovery check: 250 tests passed locally, including verified task-owned
  workflow changes and rejection of altered configuration, evidence, commit and
  dirty files. Strict documentation build and 4,137 links/assets passed. The
  Evidence section reflects the original runner checkpoint before this follow-up.

Detailed acceptance mappings and observed commands: `ai-plans/runner-hardening/implementation-evidence.md`. The runner adds verified Evidence independently.

## What changes for your workflow

Each task gets a new branch and worktree by default. Specify writes and commits the
full contract there, then asks for implementation approval. Setup lets you explicitly choose another checkout strategy or disable planning commits. Explicit agent stops retain
their reasons, oversized/protected diffs request approval, unattended execution
starts restricted, disjoint worktree tasks run together, interrupted delivery
resumes safely, and PRs show observed evidence.
