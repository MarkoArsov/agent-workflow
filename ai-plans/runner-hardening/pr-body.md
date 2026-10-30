# Harden unattended runs and prepare each task in its own worktree

Addresses #16.

## Scope

Stop explicit blocked/spec-conflict/impossible outcomes without consuming retries;
add diff-bound size/protected-path approvals, reviewed plovi.toml, restricted
unattended execution, per-task claims/locks, delivery crash recovery and verified
PR evidence.

Include the planning fixes in this same PR: new project setup defaults to a branch
and worktree per issue/task; specify prepares/reuses that checkout before writing,
commits the complete contract when planning commits are enabled, and reports its
requirements/manifest links, branches, checkout paths and planning commit. Setup
retains explicit overrides. Detection findings and generated profiles must agree.

## Verification

Specification is complete; implementation verification is pending. Before runner
publication, update this section with the shipped test file/case names, observed
assertion-red revisions, full-suite/docs/link/generated/public audit results and
actual platform coverage. Do not present the pre-implementation baseline as proof
of new behavior. The runner prepends current verified Evidence independently.

Planned modules: test_runner_outcomes, test_limits, test_policy, test_permissions,
test_concurrency, test_recovery, test_evidence and test_task_planning, plus existing
setup/fixture compatibility coverage. Tests use isolated configuration, local Git
remotes and provider/GitHub doubles; no real accounts are used for fixture delivery.

## What changes for your workflow

Each task gets a new branch and worktree by default. Specify writes and commits the
full contract there, then asks for implementation approval. Setup lets you choose
another checkout strategy or disable planning commits. Explicit agent stops retain
their reasons, oversized/protected diffs request approval, unattended execution
starts restricted, disjoint worktree tasks run together, interrupted delivery
resumes safely, and PRs show observed evidence.
