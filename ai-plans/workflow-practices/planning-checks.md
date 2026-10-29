# Planning and project-configuration checks

Revision: explicit Codex-only manual implement choice, 29 October 2026.

- The user authorized the project harness edit now. Changed only agents from
  Codex/Cursor to Codex in .plovi/project.json and added the matching harness line
  in PROJECT_WORKFLOW.md. Project pipeline defaults remain unchanged. No global
  settings, native preferences, installed harnesses or other projects were changed.
- Preserved the previous complete full-contract proposal, all four plan documents,
  evaluator facts/snapshot, checks and pipeline.json under v3/. v1/ and v2/ remain
  unchanged. Removed pipeline.json from the active plan directory to prevent this
  manual task being mistaken for an approved runner contract.
- Updated all current plan documents to manual implement only. Implement owns tests,
  implementation, verification and self-review in the active Codex session. There
  is no independent test-author/reviewer or detached run. Feature implementation
  has not started. The planned full-contract default still honors explicit manual
  requests; this task is one such request.
- Ran the existing offline models evaluate command implementation once in isolated
  temporary planning storage using the earlier read-only discovery evidence and
  this project's now Codex-only provider restriction. The informational recommendation
  is Codex gpt-6.1-sol medium with Codex gpt-6-astra medium as fallback. It does not
  switch the active session or start either model. No real key was read, no model
  inference or benchmark request ran, and no machine catalogue/settings were updated.
- Validated the project profile using the package validator and resolution code.
  Asserted that only Codex is enabled, project default stages remain unchanged,
  current facts/snapshot select only implement, every recommended route is Codex,
  the active manifest is absent, and the archived manifest remains available.
- validate-plan/preflight do not apply to this manual task. Historical successful
  full-contract checks are retained in v3/planning-checks.md; they are not claimed
  as current manual readiness checks.
- The system Python lacks MkDocs. The existing project virtual environment provides
  it; .venv/bin/python -m mkdocs build --strict passed without changing dependencies.

Full feature acceptance checks remain required when implementation is authorized.
Current verification:

- Full suite: 154 tests ran; 151 passed in restricted execution. Three disposable
  local-server fixtures could not report readiness there. Reran exactly those three
  outside restricted execution; all passed. No test code or assertions changed.
- Strict documentation build passed through the existing project virtual environment.
- 3,943 internal links/assets checked, zero failures.
- Public-content scan: 698 items, zero findings; no external private denylist.
- Whitespace/diff check passed.

Additional planning proposal: specify prepares/reuses the configured task branch
or worktree before plan writes, keeps plans and implementation together, and uses
worktrees for concurrent file isolation. worktree-start must accept planning-time
selection before a manifest exists. Honor current-checkout and multi-repository
plan ownership; preserve dirty/staged work. The current task was not moved and
its checkout strategy was not changed.
