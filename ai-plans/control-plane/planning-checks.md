# Specification evidence, 2 November 2026

## Scope and resolution

- PROJECT_WORKFLOW.md and .plovi/project.json resolve this single-repository
  package: worktree checkout strategy, ai-plans task storage, Codex and Claude
  harnesses, trusted interactive execution, GitHub tracking. The resolver
  selects .plovi and preserves .agentflow with its existing warning.
- Issue MarkoArsov/agent-workflow#18 was read with the GitHub CLI; it has no
  comments. Dependencies #15, #16 and #17 are closed and merged (PRs 39, 42, 44).
- Local `main` was 68f83aa (behind). It was fast-forwarded only (`git fetch
  origin main:main`) to 401da80, which contains the #16 and #17 work this issue
  depends on. `main` was not checked out anywhere.
- `plovi task start control-plane` created branch `codex/control-plane` and the
  owned worktree `.plovi/local/worktrees/control-plane/agent-workflow` from
  `main` at 401da80. No product files were changed.

## Repository facts the contract relies on

- `state.save` writes state.json/status.json; `progress.Reporter` keeps a
  per-task events.jsonl inside the evidence directory (in the repository).
- `cli.py` already has `approve --size|--paths --actor --reason`, `retry --note`,
  `cancel`, `policy show|set --yes`; `status` defaults to human text.
- `plovi pipeline` always spawns `run --unattended`; about 35 existing tests start
  runs non-interactively, and 21 call `runner.run(unattended=True)` directly.
- `project.resolve` already reads `<user_data>/projects.json` (`root` entries),
  but nothing writes it. The factory root is `<user_data>/projects/<id>/`.
- No JSON-schema validator exists in the runtime; schemas are documentation.

## Person decisions during specification

1. Plan gate: explicit launches self-approve; only background workers enforce.
2. Delivery: commit-and-push and draft-pr selected.
3. Routes: keep the configured routes as an explicit task choice.

## Model routes (evaluator 1.2.0, offline, no catalogue)

- First evaluation with facts.json and no explicit routes: unresolved
  `configured-default-below-required-band` for implement and implement-tests.
- After the person chose the configured routes (recorded as user-task-route):
  no unresolved stages. Advisories: explicit-route-below-recommended-band
  (implement, implement-tests), large-test-scope (implement-tests),
  single-lineage (review). Snapshot hash in model-selection.json.

## Validation and preflight

- `plovi validate-plan ai-plans/control-plane/pipeline.json`: valid.
- `plovi preflight ai-plans/control-plane/pipeline.json`: failed with
  "Install/authenticate codex or choose another configured route". The codex
  CLI is not installed on this machine (not on PATH, Homebrew, npm global or
  Applications). The manifest is therefore a labelled draft
  (`plan_status: draft-preflight-blocked-codex-unavailable`) until codex is
  installed and authenticated or the person selects Claude-only routes.

## Red evidence

Planned, not executed: the `control-plane-red` check names six CLI-level tests
that fail on assertions before product changes (unknown commands or an
unenforced gate). New test modules import new product modules lazily so red is
never an import error.

## Revision: Claude-only routes (approved)

- The person approved the plan with Claude-only routes. facts.json now records
  explicit user-task routes: opus then sonnet for implement-tests, implement
  and review. Evaluator 1.2.0: no unresolved stages; advisories large-test-scope
  (implement-tests) and single-lineage (implement-tests, review). Opus meets the
  deep band, so the earlier below-band advisories are gone.
- `plovi validate-plan`: valid. `plovi preflight`: passed; permission mode
  restricted (unattended default), claude binary found, model availability is
  verified on the first request. plan_status: approved.
