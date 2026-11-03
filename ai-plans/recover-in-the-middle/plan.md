# Issue #47: recover in the middle

Lane: **manual**. The issue's ground rules require it until the #49 stable-enough gate passes
(`plovi stats --gate` fails today). `specify` + `implement` in one session, in this task worktree.
No detached pipeline manifest. Implement owns tests and verification.

- Branch: `codex/recover-in-the-middle`, created by `plovi task start` from `main` at `4ea03fd`
  (local `main` fast-forwarded to `origin/main` first; it includes #49 / PR #55).
- Checkout: `.plovi/local/worktrees/recover-in-the-middle/agent-workflow`.
- Delivery: local commits only. Push and PR need a separate explicit request.

## Outcome

One rule for the runner: **fail closed at the edges, recover in the middle.** Between an approved
plan and a verified diff, plovi fixes failing checks and premature stops in the same provider
session, treats reports as optional, narrows frozen tests, turns the size gate advisory below a
ceiling, rebinds approved plan revisions, adopts task-owned work on resume, and defaults new
tasks to the person's task worktree, unpinned, from the remote base, in the project's permission
mode. Every stop names its next command; `plovi status` shows time, attempts, tokens and cost per
stage; per-task budgets pause runaway tasks. Edges stay closed: publishing, secrets, writes
outside the task's repositories, undeclared protected paths, the diff ceiling, removed tests,
stop-list questions.

## Gaps found in the issue, and the decisions this plan takes

Each row is part of what you approve.

| # | Issue assumes | Evidence | Decision |
|---|---|---|---|
| A | Complete plan revisions rebind automatically at the next stage boundary | Background workers require a recorded `plan.approved` for the current plan hash (#18, `require_plan_approval`). An automatic rebind would run an unapproved plan | Rebind automatically only when the new `plan_sha256` has a recorded approval, or the run doesn't require plan approval. Otherwise stop with "The plan changed. Approve it with `plovi approve TASK --plan`, then resume" (next command set). Only plan files may differ: a profile, skill, rule or policy change still stops with today's `resume --rebind` message. Repository membership changes still need a new task. |
| B | `budgets.task_attempts` default 6, counting every kind except nudges | A normal full run (implement-tests, implement, review) with 2 fix rounds and 1 challenge already uses 6, so the 7th attempt would pause the task. That contradicts "stop less" | **Default 10**, counted per logical run (since its `run.started` window, as in #49 stats), all kinds except nudges. `task_minutes` 120 and `task_cost_usd` 0 (no cap) as the issue says. |
| C | The account guard refuses credential overrides "in every context" | `claude_environment` checks overrides only when the project opted into the local guard (`.plovi/local/claude-account.json`); without it nothing is checked | Keep the guard opt-in. Within it: unattended runs stop as today; interactive runs (`util.is_interactive()`) print the same message as a warning and continue. No new guard for projects without the file. |
| D | New keys fit `policy.validate` | Every integer must be 1..10,000,000; `task_cost_usd = 0` and `corrections.* = 0` would be rejected; there is no float type | Add `corrections` and `budgets` sections. `corrections.same_session_rounds` and `corrections.challenges` accept 0..10 (0 disables). `budgets.task_cost_usd` accepts int or float >= 0. `limits.ceiling_factor` 1..100. `execution.runtime_pin` bool. `execution.unattended_permission_mode` gains `"profile"`. `isolation.checkout` is `"task-worktree"` or `"factory"`. |
| E | Loop checks are those with `when` containing `"loop"` (#48) | #48 is open; no check has `when` | All named checks with a green phase are loop checks. One helper (`loop_checks(manifest)`) so #48 changes one line. |
| F | "Compare the parser's identities per module" to catch removed or skipped tests | `verification.parse` records no identities per module. It counts tests only for `unittest` (`counts.tests`, `skipped`). A skipped test already fails a check unless the plan gives `approved_skip_reason` | Fail closed when a check's test count drops between the last evidence before the stage and the green evidence after it. Add the same `counts` for `pytest` (`N passed`, `N skipped`). Skips stay covered by the existing skip rule. Checks with other parsers have no count; their red files stay frozen. `docs/verification.md` says so. |
| G | Freeze "the files that contain the plan's red identities" | Identities are test names in parser output, not file paths | After implement-tests, freeze the files under `test_paths` that changed during implement-tests **and** contain a red identity's final name segment (for example `test_behavior`). When no file matches, freeze every file implement-tests changed, as a safe fallback. |
| H | Ledger events `plan.rebound`, `commits.adopted`, `limits.exceeded`, `receipt.rederived`, `provider.circuit_open` | None of these types exist. #49 stats already counts person-actor `plan.rebound` and `commits.adopted` without a plovi author as interventions | Add all five types to `ledger.TYPES` and the schema. An automatic rebind is actor `plovi` (not an intervention). Commits adopted on resume were made while no worker ran, so they record `author: {"kind": "person"}`, and G3 counts them as an intervention, which is accurate. Stop events (`escalation.raised`, `run.paused`, `approval.requested`, `question.asked`) now write `next`, so G4 can pass. |
| I | Diff ceiling = `ceiling_factor ×` both limits | — | Advisory when files <= 4 × 40 **and** lines <= 4 × 1,500; `needs_approval` when either exceeds its ceiling. The stop-list key `oversize` is the agent-side counterpart; the runner's ceiling check doesn't depend on it. |
| J | `turns` counts assistant turns | Events differ per provider | Count Codex `item.completed` with an `agent_message`, Claude `assistant` events with text, and Cursor `assistant` events; `null` when the stream has none. |

## Scope

The issue's sections 1–9 are the specification. The plan follows them, with the decisions above.
The points below fix the design where the issue leaves a choice.

### Runner shape

`_run_locked`'s attempt loop gains one inner loop per provider attempt, `_continue_session`, that
handles fix rounds (section 1), challenges (section 2) and the nudge (section 3) through
`providers.command(route, execution, session=..., prompt=...)`. Each continuation is an attempt
record with its `kind`, saved and recorded like today's attempts. The order after a provider ends:

1. Classify the provider result as today (usage limit, cancellation and permanent failures first).
2. Report missing or invalid: one nudge (section 3).
3. Report `blocked` / `spec_conflict` / `impossible` / `needs_input`: stop list first, then
   recoverable categories; challenge or stop (section 2). `spec_conflict` keeps the existing
   `reconcile` path when the reason matches no recoverable category.
4. Report `complete`, or no report after the nudge: run `verify_stage`. Failing checks: same-session
   fix round, up to `corrections.same_session_rounds`; then today's fresh attempt.

New module `runtime/plovi/autonomy.py`: the stop list, the recoverable categories with their
patterns, `classify_stop(reason, stage, manifest)`, `challenge_prompt`, `fix_prompt`, `NUDGE`,
`loop_checks`, and the backoff (`PLOVI_CHALLENGE_BACKOFF_SECONDS` override).

### Gates, defaults and visibility

Sections 4–8 land in `limits.py`, `runner.py`, `checkpoints.py`/`recover_resume`, `factory.py`,
`runtime_pin` dispatch (`cli.py`, `operations/tasks.py`), `tasks.py`, `providers/__init__.py`,
`model_policy/storage.py`, `progress.py`, `operations/tasks.py`, `operations/inbox.py`,
`ledger.py` and `policy.py`. `state_version` 2 is written by new runs; resume migrates 1 → 2.

## Delivery order (one commit each)

1. Policy keys, ledger types and `state_version` (sections 9, H, 5.7 state part).
2. `autonomy.py` tables, prompts and category tests (section 2 data, `test_autonomy` table test).
3. Reports optional: marker parsing, nudge, checks decide (section 3).
4. Same-session fix loop (section 1).
5. Challenges (section 2 runner part).
6. Narrow frozen tests and test-count guard (section 4).
7. Gates: ceiling, declared protected paths, plan rebind, commit and edit adoption, receipts (5.1–5.6).
8. Defaults: runtime pin off, profile permission mode, task worktree, remote base, account guard (5.7–5.11).
9. Provider availability and circuits (section 6).
10. Visibility and budgets: attempt fields, status, watch, budgets, inbox (sections 7, 8).
11. Scenario steps B3 and V7, owners.json `47: done`, regenerated docs; docs pages (issue's Docs list).

## Tests

All test files and case names from the issue's "Tests (required)" section, plus:

- `tests/test_autonomy.py`: `test_resume_argv_per_provider` (Claude `--resume ID`, Codex `exec resume ID`, Cursor `--resume ID`).
- `tests/test_gates_v2.py`: `test_plan_revision_without_approval_stops_with_next_command` (decision A).
- `tests/test_policy.py`: new keys validate, including 0 for `corrections.*` and a float `task_cost_usd` (decision D).
- `tests/test_ledger.py`: samples for the five new event types.

Provider double gains: `text` (a raw agent message, for the marker forms), `no_report`, and an
authentication failure step. Every new test must fail before its change (red evidence saved in
`ai-plans/recover-in-the-middle/red.txt`).

**Existing tests updated, not deleted** (each listed in the PR with its reason): the blocked /
spec_conflict / impossible stop-after-one-attempt tests in `test_runner_outcomes`, the invalid-report
test, `test_non_tty_defaults_to_restricted_codex` (becomes the opt-in restricted variant), the
factory-default tests in `test_factory_checkouts`, the size-gate tests in `test_limits`, and any test
that relied on non-interactive runs getting factory checkouts or a restricted mode. Those opt in
with `isolation.checkout = "factory"` or `unattended_permission_mode = "restricted"`, so the old
behaviour stays reachable and tested.

Scenario steps this PR marks done: **B3** (`test_B3_recovers_in_the_middle`) and **V7**
(`test_V7_status_explains_stop_and_cost`); `tests/scenario/owners.json` sets `47` to `done`.

## Docs

`docs/recovery.md`, `docs/execution.md`, `docs/isolation.md`, `docs/policy.md`,
`docs/verification.md`, `docs/principles.md`, `docs/tasks.md` as the issue lists, plus
`docs/ledger.md` (new event types) and `CHANGELOG.md`. Regenerate `docs/commands.md` and
`docs/generated/*`. CLI text follows `design/README.md`: lowercase plovi, short active sentences.

## Checks (all must pass)

| Check | Command |
|---|---|
| Tests | `python3 scripts/run_tests.py --jobs auto` |
| Generated docs | `python3 scripts/generate_docs.py --check` |
| Docs build | `.venv/bin/python -m mkdocs build --strict` (main checkout's venv) |
| Links | `python3 scripts/check_links.py site` |
| Public content | `python3 scripts/check_public_content.py --history` |
| Scenario | `python3 -m unittest tests.scenario.test_target_scenario tests.scenario.test_traceability` (B3, V7 pass) |

## Risks

- **Size.** This is the largest roadmap issue so far: about 50 new tests in 9 new test files and
  updates across 6 or more existing ones. The commit order keeps each step testable on its own.
- **Default changes ripple through tests.** Non-interactive test runs currently get factory
  checkouts and restricted mode. Commit 8 updates them, and its message lists each one.
- **Trusted by default.** Unattended runs use the profile's mode (trusted by default). This is the
  roadmap decision of 3 November 2026; the docs say plainly that trusted is not a sandbox.

## Model routing (informational, manual lane)

`plovi models evaluate` with `model-facts.json` (large, high risk, complex) kept the configured routes
`codex/gpt-6.1-sol`, then `claude/opus`, for specify and implement, with advisory
`explicit-route-below-recommended-band` and the notice "No model catalogue". Snapshot:
`model-selection.json`. This session (Claude Opus) implements; no route change.
