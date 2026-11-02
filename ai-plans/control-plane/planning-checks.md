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

## Run 1 outcome and revision 2

- Run 946d1d44: implement-tests complete (opus, 12 min, $3.85 list price).
  Implement attempt 1 (opus) hit the Claude 5-hour usage limit after 11 min
  ($4.52) and was recorded as `authentication` because classification
  regex-scans the whole 1.3 MB transcript; attempt 2 (sonnet) failed in 2 s on
  the same limit (`quota`). Resume then refused the attempt's leftover edits as
  foreign; they were archived to `.plovi/local/set-aside/control-plane-attempt-0001/`
  in the configuration root and the tree restored to the saved snapshot before
  resuming. Attempt 3 (opus, 34 min, $10.43) completed.
- Verification of attempt 3: every behavioural check passed (control-plane-red
  6, ledger 9, operations 14, inbox 8, projects 4, rebuild-state 3,
  compatibility 130, full suite 415 with 1 approved skip, generated-docs, links,
  public-content). Failed: plugin-skills (wrong success pattern in this contract)
  and docs-build (system python3 has no mkdocs). Attempt 4 correctly reported
  `blocked` but as prose plus a bare JSON line, which the parser rejects, so the
  run escalated with `invalid_report`.
- The implementer's pr-body claimed a docs build that could not have run; C2
  corrects that.
- Revision 2 evidence before approval, run by hand against the current tree:
  `generate_plugin_skills.py --check` prints the expected line; `.venv/bin/python
  -m mkdocs build --strict` built; `check_links.py site` 5006 links, 0 failures.
  The worktree `.venv` (git-ignored) was created from requirements-docs.txt.
- Evaluator 1.2.0 with test_files 7 / test_lines 1800: no unresolved stages;
  advisories large-test-scope and single-lineage. validate-plan: valid.
  preflight (from the person's terminal; this agent shell carries Claude
  credential variables that the account guard rejects): passed, trusted/profile.

## Revision 2 manual implementation (approved for in-session work)

Red, before product changes (`revision-red` identities, all assertion failures):
- test_factory_branch_includes_task_branch_plan_commits: factory HEAD was the
  remote base, not the task branch head.
- test_preflight_and_dry_run_never_allocate: "True is not false : no receipt is
  written" for both `preflight` and `run --dry-run`.
- test_usage_limit_classified_from_structured_result_not_transcript:
  'authentication' != 'usage_limit' (the exact production misclassification).
- test_prose_then_bare_json_report_is_accepted: report was None.

Green after the change: tests.test_background_runs 7/7 and
tests.test_provider_outcomes 6/6; tests.test_providers unchanged and passing.
Full named-check results are recorded below once `plovi verify --phase green` ends.

`plovi verify --phase green` (run from the person's terminal): 15/16 passed on the
first run, including full-suite 428 tests (1 approved skip). compatibility-regressions
failed only because this revision added tests.test_container (opt-in Docker smoke
skip) without an approved skip reason; the plan now carries the same reason as
full-suite, and the rerun passed: 169 tests, 0 failures, 1 approved skip.

## CI on PR #45, run 41473755145 (head 54fbe42)

core (ubuntu-latest, 3.11) failed: test_pipeline_resume returned `interrupted`
(exit 1), then temp cleanup failed because the detached worker was still writing.
Cause: launcher/worker race on the first save (see requirements C3). Regression
test red without the fix ('interrupted' == 'interrupted'), green with it;
tests.test_pipeline_resume passes locally.
