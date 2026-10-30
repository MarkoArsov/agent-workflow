# Runner hardening: issue #16

Request: run plovi-specify for the public agent-workflow issue #16.
Source: https://github.com/MarkoArsov/agent-workflow/issues/16
Issue updated: 2026-10-29T10:00:08Z; researched 30 October 2026; open, no comments.
Title: Harden the runner for unattended work: stop outcomes, size limits, evidence,
policy file, safe defaults, per-task locks and crash recovery.

Preserve all eight areas of the issue: explicit stop outcomes and retry; diff-bound
size/protected-path approvals; PR evidence; reviewed plovi.toml; restricted unattended
runs; task locks and concurrent worktrees; idempotent crash recovery; tests before
behavior changes. Include the issue's documented commands and workflow changes.

The user selected Codex gpt-6.1-sol with medium effort for implement-tests,
implement and review. No fallback was selected. This is a route choice, not approval
to implement. The full lane is appropriate because this changes runtime behavior,
persistence, security defaults and concurrent delivery across multiple components.

Use the source checkout, Python 3.11+ standard library runtime and isolated fixtures.
Do not modify actual user agent configuration. Planning stays local. The revised contract selects eventual push/draft-PR delivery
after approval and verification; no tracker comment, installation or deployment
is selected. Tests may simulate delivery using
temporary bare remotes and a recorded gh double.

Planning initially used current-checkout on codex/rename-plovi and committed the
complete contract as 3abe720. The user corrected the desired project policy:

> The project setup should not be current checkout, but new branch and worktree
> per issue/task. Specify should create the branches and include the full contract
> there. This should be the default for plovi and all projects using it unless
> changed during project setup, include these fixes in the #16 plan and PR.

The explicitly authorized project policy change is committed as 53070e1. The active
task branch is now codex/runner-hardening, in the configured worktree at
.plovi/local/worktrees/runner-hardening/agent-workflow relative to the canonical
project root. The base remains main. The old branch is parked and clean; no branch
history is rewritten. All future task plan writes and implementation belong in
this worktree. Pass the canonical project root explicitly at runner handoff.
The previous complete contract is retained in v1/ for provenance.

Add default worktree-per-task setup, explicit setup opt-outs, full-contract planning
commits and complete handoff reporting to issue #16. Include those changes in the
planned draft PR, with a prepared pr-body.md. Local planning commits and checkout
preparation are authorized now; provider implementation and remote delivery still
follow approval of this revised full contract.
Specification ends at the user's approval. No product code or product tests are
authored during specification.
