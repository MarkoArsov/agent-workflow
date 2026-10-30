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
Do not modify actual user agent configuration. Work locally; no push, PR, tracker
comment, installation or deployment is selected. Tests may simulate delivery using
temporary bare remotes and a recorded gh double.

Planning uses the clean current checkout on codex/rename-plovi, as required by
PROJECT_WORKFLOW.md and the current-checkout profile. Its starting revision is
55cae30; the local main ref is 0fe14a9. Their file trees are identical. Do not switch
branches or prepare another worktree for this task. Plans and later implementation
stay here; execution must explicitly use this project's configuration root.

Specification ends at the user's approval. No product code or product tests are
authored during specification.
