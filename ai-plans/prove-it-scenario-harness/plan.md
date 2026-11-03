# Issue #49: target-scenario harness, run statistics and the stable-enough gate

Lane: **manual** (explicit user request). `specify` + `implement` in one session, in this
task worktree. No detached pipeline manifest. Implement owns tests and verification.

- Branch: `codex/prove-it-scenario-harness` (created by `plovi task start`, base `main` at `2a94b31`
  after fast-forwarding local `main` to `origin/main`).
- Checkout: `.plovi/local/worktrees/prove-it-scenario-harness/agent-workflow`.
- Delivery: local commits only. Push and PR need a separate explicit request.

## Outcome

1. A stateful fake GitHub CLI that fails loudly on anything unmapped.
2. `tests/scenario/`: the 33-step target scenario, owners, traceability and a generated status page.
   Steps owned only by done issues (#18, #46, #49) pass; the rest skip with "owned by #N (pending)".
3. `plovi stats [--since] [--task] [--json] [--gate]` reading the ledger (and GitHub Actions for `--gate`).
4. `docs/stability-gate.md`, the live smoke checklist in `docs/coverage.md`, and `docs/generated/scenario.md`.

## Gaps found in the issue, and the decisions this plan takes

Repository evidence contradicts a few assumptions in the issue. Each decision below is part of
what you approve.

| # | Issue assumes | Evidence | Decision |
|---|---|---|---|
| A | Fixture projects set `[pipeline] stages`, `[delivery]`, `[merge]`, `[intake]` in `plovi.toml` | `policy.validate` rejects unknown sections and keys; none of these exist yet (#21, #23 add them) | Stage lists come from the plan manifest `stages`, which is how plovi selects stages today. `docs-check` is a real custom command stage in the project's stage extension file. The fixture builder writes only keys that exist; it keeps the intended future keys in one dict per fixture (`FUTURE_POLICY`) with a comment naming the owning issue, so #21/#23 move them into `plovi.toml` when their keys land. |
| B | U1 asserts "disabled built-in schedules" | Schedules don't exist (#20 is open) | U1 asserts profile + `plovi.toml` now. Its docstring and `steps.py` note say #20 extends U1 with the schedules assertion (the same pattern the issue uses for D0 and U2). U1's owners stay `[49]`, as in the table. |
| C | Stats reports tokens and cost "from the ledger" | `attempt.finished` carries no usage or cost; they live only in `state.json` attempts | Add optional `usage` (`input_tokens`, `output_tokens`) and `cost_usd` to `attempt.finished`, written by `Recorder.attempt` from the attempt entry. Older events give `null`. |
| D | G3 needs "≥ 10 files changed", "a bugfix with red proof", "Claude and Codex routes used" | Not in the ledger | Add optional `provider` to `attempt.finished`, optional `files_changed` to `pr.opened` (from the delivered diff), and optional `red_proof` (bool) to `run.started` (true when the manifest selects `implement-tests` without `approved_no_red_reason`). plovi has no "bugfix" task type, so G3's bugfix clause counts **a run with red proof**; `docs/stability-gate.md` says so. |
| E | G4 checks that stop events carry `next` | No stop event has `next`; #47 adds the writers | Add optional `next` to the schema of `escalation.raised`, `run.paused`, `approval.requested`, `question.asked` (no writers yet). G4 fails on real data until #47; that is the honest result. |
| F | A "run" is `run.started` … `run.finished` | Every worker start (including resume, retry and answer) gets a new `run_id` and its own `run.started`; `run.finished` is also written for `needs_input`/`needs_approval`/`failed`/`escalated`, which are not the end | A **logical run** is a per-task window. It opens at a `run.started` with no open window for that task. It closes at the first of: `run.finished` with status `complete`, the first `pr.opened`, or a `run.cancelled` with no later `run.started` for that task. Later `run.started` events inside an open window belong to the same logical run (attempts and stops accumulate). A window still open at the end is reported with result `running`. A `run.cancelled` followed by a new `run.started` closes the window as `cancelled` and counts one intervention on it. |
| G | G5 reads the CI artifact `scenario-results.json` | Needs an Actions download path | `--gate` uses `gh run download RUN_ID --name scenario-results --dir TMP`; the fake implements it. |
| H | "add it to `mkdocs.yml` under Verify" | There is no Verify section | Add `generated/scenario.md` and `stability-gate.md` under **Trust**, next to "How it's tested". |
| I | `docs/cli.md is regenerated` | `docs/cli.md` is hand-written; the generator writes `docs/commands.md` | Regenerate `docs/commands.md`; add a `plovi stats` entry to `docs/cli.md` by hand. |

## Scope

### 1. Stateful fake GitHub: `tests/fixtures/github_fake.py`

- Standard library only; reads and writes the JSON state at `PLOVI_TEST_GITHUB_STATE`.
- Handlers registered by argv prefix in one table; each handler is a small function. Unmapped argv:
  print `unmapped gh call: [...]` to stderr, exit 99.
- Every call is appended to `<state>.calls.json` (`argv`, `body` from `--body-file`).
- State: `repo`, `issues` (number, title, body, state, labels, author, comments, `events` with
  `actor.login` and `actor.type` `User`/`Bot`), `pulls` (number, head, base, draft, state, merged,
  `auto_merge`, body, `head_sha`), `check_runs` and `statuses` per SHA as scripted sequences
  (each read advances one step and the last value sticks), `reviews`, `review_threads`,
  `collaborators` (login → permission), `actions` (`workflow_runs` per workflow file, `jobs` per run id,
  `artifacts` per run id → file contents).
- Handlers: `repo view --json nameWithOwner [--jq]`; `pr list/view/create/edit/ready [--undo]`;
  `pr merge --auto` / `--disable-auto`; `issue view/create/comment/edit --add-label`;
  `run list`, `run view --log-failed`, `run download --name --dir`; `api` with `--paginate --slurp`
  and plain, for: issue and PR comments, PR comments, reviews, `issues?labels=…&state=open`,
  `issues/{n}/events`, `collaborators/{login}/permission`, `commits/{sha}/check-runs`,
  `commits/{sha}/status`, POST `statuses/{sha}`, `actions/workflows/{file}/runs?...`,
  `actions/runs/{id}/jobs`; `api graphql` for the review-thread query `integrations/github.py` sends.
- `WorkspaceTest.install_github_fake(state=None) -> Path` in `tests/helpers.py`: writes initial state
  (default: `repo = "example/fixture"`, empty collections), installs `gh` (POSIX copy + chmod;
  Windows `gh.cmd` running `python <fake>`), prepends the bin dir to `PATH` in `self.env` and
  `os.environ`, sets `PLOVI_TEST_GITHUB_STATE` in both. `gh_double.py` and `install_gh_double` stay.

### 2. Scenario harness: `tests/scenario/`

- `__init__.py`; `steps.py` with `SCENARIO_STEPS` (exactly the 33 rows: `id`, `text`, `owners`, `test`)
  and `owned_by(*owners)`, reading `owners.json` once. `owners.json`: `18`, `46`, `49` → `done`;
  `19 20 21 22 23 25 47 48 50` → `pending`.
- `validate(steps, owners, test_class)` in `steps.py` returns problems; `test_traceability.py`
  calls it on the real data (expects none) and on fixtures for each failure in Scope 2.5 of the issue
  (no owner, missing method, owner missing from `owners.json`, value not `done`/`pending`, a deliberately
  unowned step).
- `test_target_scenario.py`, `class ScenarioTests(WorkspaceTest)`, one method per step:
  - `setUpClass` builds the **hobby** and **product** templates once into the per-process cache
    (project via `setup_project`, a bare remote, provider-double binaries, plan manifests with
    stages `["implement", "review"]` and `["implement-tests", "implement", "review", "docs-check"]`,
    `docs-check` a command stage running `python -c` that prints a success pattern). `setUp` copies them.
  - Real bodies: **U1** (CLI `plovi setup` preview then apply: profile and `plovi.toml` exist and
    `plovi policy show --json` loads them), **U2** stage-list part written and skipped until #23,
    **B1** (ledger `stage.started` sequence is exactly implement, review), **B2** (exactly
    implement-tests, implement, review, docs-check; docs-check evidence recorded), **B4** (usage limit
    pauses with `resets_at`; resume keeps the partial edit; one more provider call),
    **V1** (`plovi status` and `plovi inbox --format json` show the running and the waiting task),
    **V2** (pause, resume, cancel through the CLI, each with a person-actor ledger event),
    **X1** (`plovi stats --gate --json` against a scripted fake repository reports G1–G5 with
    numbers and the right exit code), **D0** written (push to the bare remote and open a PR on the fake;
    the verification section comes from evidence) but skipped until #48 adds claims assertions.
  - Every other step: `self.fail("not implemented")`. V3/V4: once their owner is done, assert
    `app/e2e/scenario.spec.ts` contains a test titled `"V3 …"` / `"V4 …"`.
  - Meta-test (in `test_traceability.py`): flips one pending owner in a temporary `owners.json`
    and runs that step's test method; it fails with "not implemented".
- Speed: no per-test `git init` beyond copying templates; keep the class under ~20 s locally.
- `tests/tiers.json`: scenario modules are not smoke; `test_target_scenario` goes in `slow` if it
  exceeds the slow threshold.

### 3. `plovi stats`: `runtime/plovi/stats.py`

- Operation `stats` (risk `none`, `mutates=False`) in `runtime/plovi/operations/` (new module,
  added to `_load`), CLI `plovi stats [--since DATE|DURATION] [--task ID] [--json] [--gate]`.
  `--since` accepts an ISO date/time, an event ID, or a duration like `7d`/`12h`.
- Logical runs as in decision F. Per run: task, started, finished, result, duration seconds,
  attempts by `kind` (missing → `attempt`), challenges (`kind == "challenge"`), fix rounds
  (`kind == "fix"`), tokens and cost (sums; `null` when none reported), stops (each
  `escalation.raised`, `run.paused`, `approval.requested`, `question.asked`, with reason and `next`),
  interventions (list with type, actor, reason).
- **Interventions** (person-actor events in the window, never `plan.approved`):
  `question.answered`; `run.resumed` when the previous stop was `failed`, `escalated` or
  `interrupted` and not preceded by a `pause.requested` from the same person; `approval.granted`
  with `kind != "plan"`; `plan.rebound` by a person; `checkpoint.migrated`; `handoff.started`;
  `run.cancelled` followed by a new run of the task; `commits.adopted` whose `author` isn't plovi.
  Types that don't exist yet (`plan.rebound`, `commits.adopted`, `handoff.started`) are matched by
  name, so they count when #47/#25 add them.
- Text output: a table (design voice, no colour codes beyond what existing CLI text uses), then totals:
  runs, interventionless runs, median duration, attempts per run, tokens per run when known.
- `--gate`: G1–G5 as in the issue, each line `G1 PASS|FAIL <numbers>`; exit 0 only when all pass.
  - G1/G2-CI: `gh api repos/{slug}/actions/workflows/verify.yml/runs?branch=main&per_page=20` and
    `/actions/runs/{id}/jobs`. Job timeouts come from `.github/workflows/verify.yml`
    (`timeout-minutes` per top-level job, read with a narrow line reader: no YAML dependency);
    API job names map to workflow job ids by the name prefix before ` (`.
  - G2-local: `.plovi/local/stats/local-suite.json`.
  - G3/G4: logical runs from the ledger (decisions D, E).
  - G5: last main Verify run's `scenario-results.json`; every step whose owners ⊆ {18, 46, 47, 48, 49}
    must be `passed`.
  - Missing data (no `gh`, no runs, no local record) is a FAIL with the reason, never a crash.
- Ledger changes (`ledger.py` `TYPES`, `schemas/event.schema.json`, `docs/ledger.md`): new
  `checkpoint.migrated` (data: `task`, `binding_sha256`); optional fields from decisions C, D, E.
  `checkpoints.migrate(..., apply=True)` appends `checkpoint.migrated` with the person actor
  (`operations.actor`). `Recorder` writes the new optional fields.

### 4. Test runner and CI

- `scripts/run_tests.py --record`: after a successful full run, write
  `.plovi/local/stats/local-suite.json` (`cpu_count`, `jobs`, `seconds`, `date`, `tier`).
- `--scenario-results PATH`: write `{step_id: "passed"|"skipped"|"failed"|"error"}` for
  `tests.scenario.test_target_scenario` methods, mapping method names to step IDs.
- `verify.yml` core job: pass `--scenario-results "$RUNNER_TEMP/scenario-results.json"` and upload
  an artifact named `scenario-results` only for `ubuntu-latest` + `3.14`.

### 5. Docs

- `docs/stability-gate.md` (new): G1–G5 table, decisions D/E wording, before/during/after/falling back.
- `docs/coverage.md`: "Live smoke checklist" section (L1–L8 table and recording rules).
- `docs/generated/scenario.md` from `scripts/generate_docs.py` (ID, step, owners, test, status);
  covered by `--check`.
- `docs/commands.md` regenerated; `docs/cli.md` gains `plovi stats`; `docs/ledger.md` table updated.
- `docs/development.md`: "Scenario tests: how to own a step".
- `mkdocs.yml` Trust section: `Stability gate: stability-gate.md`, `Target scenario: generated/scenario.md`.
- `CHANGELOG.md` entry.

## Out of scope

App statistics view, weekly summaries, schedules, intake, delivery/merge policy keys, Playwright
specs, migrating existing tests off `gh_double.py`, writers for `next`/`plan.rebound`/
`commits.adopted`/`handoff.started`.

## Tests (named)

- `tests/test_github_fake.py`: one case per handler group; unmapped call exits 99 with argv;
  label events keep actor login and `Bot` type; check runs advance pending → success/failure in
  scripted order; `pr merge --auto` and `--disable-auto` toggle the flag; calls logged;
  `--paginate --slurp` shape matches `integrations.github.api`.
- `tests/scenario/test_traceability.py`: real data valid; five fixture failures; the
  flipped-owner meta-test.
- `tests/scenario/test_target_scenario.py`: U1, B1, B2, B4, V1, V2, X1 pass; all others skip with
  "owned by #N (pending)".
- `tests/test_stats.py`: the six-run fixture → interventions `1, 1, 0, 0, 1, 0`; logical-run
  grouping across resume; tokens `null` vs summed; `--gate` all-pass, then one failing case per
  G1–G5 printing FAIL with numbers; missing `gh` data is FAIL, not a crash.
- `tests/test_ledger.py`: new optional fields validate; `checkpoint.migrated` round-trips.
- `tests/test_run_tests.py`: `--record` writes the local-suite file; `--scenario-results` writes
  the results file.
- `tests/test_ci_workflow.py`: the core Ubuntu 3.14 job passes `--scenario-results` and uploads
  `scenario-results`.
- Existing tests that assert the ledger type table or `plovi commands` output are updated, and the
  PR says why.

## Quality guidance

`AGENTS.md`, `CONTRIBUTING.md`, `design/README.md`, `design/DESIGN.md` (CLI text voice),
`references/quality-guidance.md`, and the issue's ground rules: stdlib only; argv lists; resolve
`gh` before running (Windows `.cmd`); isolated `HOME`/`XDG_*`/`APPDATA`; no network; no private
identifiers. Fixtures use distinct values so swapped fields fail.

## Checks (run in the task worktree; all must pass)

| Check | Command | Expected |
|---|---|---|
| Full suite | `python3 scripts/run_tests.py --jobs auto` | exit 0; scenario steps for #18/#46/#49 pass, others skipped with owner |
| Unittest discovery | `python3 -m unittest discover -s tests -v` | exit 0 |
| New tests alone | `python3 -m unittest tests.test_github_fake tests.test_stats tests.scenario.test_traceability tests.scenario.test_target_scenario -v` | exit 0 |
| Generated docs | `python3 scripts/generate_docs.py --check` | exit 0 |
| Docs build | `.venv/bin/python -m mkdocs build --strict` then `.venv/bin/python scripts/check_links.py site` | exit 0 (use the main checkout's `.venv` if the worktree has none) |
| Public content | `python3 scripts/check_public_content.py --history` | exit 0 |
| Gate on this repo | `./bin/plovi stats --gate` | prints G1–G5 with numbers (FAIL lines are expected today); output saved to `ai-plans/prove-it-scenario-harness/gate-output.txt` for the PR |

Red proof: before the stats implementation lands, `tests.test_stats` fails on assertions
(interventions, gate lines), not on import; capture that run in `red.txt` in this plan folder.

## Model routing (informational, manual lane)

Evaluator run once (`model-selection.json`): implement → codex `gpt-6.1-sol`, fallback claude `opus`,
deep band, demanding effort; no catalogue, configured defaults retained, flagged
`configured-default-below-required-band`. This session (Claude Opus) implements; no route change.

## Delivery

Commit logical changes locally on `codex/prove-it-scenario-harness`. No push, no PR, no issue
comment without a separate request. A later PR body follows the issue's ground rules.
