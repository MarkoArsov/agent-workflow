# Issue #48: plans that can pass

Lane: **manual**. The issue's ground rules require it until the #49 stable-enough gate passes
(`plovi stats --gate` fails today on G1–G5; P3 and D0 are the steps this issue owns).
`specify` + `implement` in one session, in this task worktree. No detached pipeline manifest.
Implement owns tests and verification.

- Branch: `codex/plans-that-can-pass`, created by `plovi task start` from `main` at `50293d5`
  (local `main` fast-forwarded to `origin/main` first; it includes #47 / PR #56 and #49 / PR #55).
  The task records issue `MarkoArsov/agent-workflow#48`.
- Checkout: `.plovi/local/worktrees/plans-that-can-pass/agent-workflow`.
- Delivery: local commits only. Push and PR need a separate explicit request.

## Outcome

A plan can't be approved with checks that can never pass, and a PR can't present an unrun command
as verification. `plovi validate-plan <manifest> --run-checks` runs each named check once in the
task checkout and classifies it (`ran`, `missing-tool`, `bad-cwd`, `unparseable`, `timeout`,
`modifies-files`) with one fix line per failure. Its results land in `planning-checks.json`, bound
into `plan_sha256`. Exit codes decide green; success patterns become optional extra assertions.
Skips are advisory unless a planned identity is skipped. Checks declare `when` they run: the
implement loop runs focused checks cheapest first; final verification runs the full set once per
diff fingerprint, reusing passing results. Red runs only the planned identities. The runner's
evidence block is the PR's only verification section, and it lists commands the agent's body
mentions that plovi never ran.

## Gaps found in the issue, and the decisions this plan takes

Each row is part of what you approve.

| # | Issue assumes | Evidence | Decision |
|---|---|---|---|
| A | `templates/pr-body.md` exists and has a verification section to remove | No such file. The body is whatever the plan's `delivery.body_file` holds (for example `ai-plans/control-plane/pr-body.md`, whose "All named checks through `plovi verify`…" section is the problem) | Add `templates/pr-body.md` as the delivery body skeleton: What changed, Why, Tests added, Scenario steps, What changes for your workflow. No verification or testing section. `references/pipeline-contract.md` and `skills/specify/SKILL.md` point at it. `test_template_has_no_verification_section` guards it. |
| B | Red runs append unittest test IDs to the argv when it is `python -m unittest …` | Planned identities are often short names (`test_append_read_round_trip`), and the most common argv is `unittest discover -s tests`, which takes no test names. Appending IDs to `tests.test_x` would also still run the whole module | Filter with `-k`, which works with explicit modules **and** `discover`: unittest gets one `-k <identity>` per identity; pytest gets one `-k "a or b"` built from each identity's last segment (only when every segment is a plain identifier). Applied only when the argv is `<python> -m unittest …` or `pytest`/`<python> -m pytest …`. If any identity is absent from the filtered output, run the whole command once and use that result. Other parsers always run the whole command. |
| C | `validate-plan --run-checks` finds the task checkout | The task-start receipt (`.plovi/local/tasks/<task>.json` under the configuration root) holds each repository's path, for every strategy | Checkouts come from the receipt, then a saved run's `checkouts`. With neither, refuse (exit 2): "No task checkout for TASK. Run plovi task start TASK, then validate again." Never fall back to the person's main checkout. Run it from the configuration root or pass `--project`, like the other plan commands. |
| D | "The parser recognised the output" | The pitfall: at plan time the new tests don't exist yet, so the run fails before any assertion | Recognised output per parser: unittest `Ran N tests` (a missing test module still prints it); pytest a result summary, `no tests ran`, or `file or directory not found`; dotnet `Passed!`/`Failed!`/`Total tests` or a compile error (`error CS…`, planned tests may not compile yet); jest `Tests:` or `No tests found`; tap a plan line or `ok`/`not ok`. A failing run with recognised output is `ran`. Exit non-zero with nothing recognised is `unparseable`, like exit 0 with nothing recognised. `missing-tool` wins over both when `argv[0]` doesn't resolve or a `<python> -m X` run prints `No module named X`. |
| E | Results reused "for the same check ID, argv, phase and fingerprint" | A reused failure would make a flaky check fail forever at one fingerprint | Reuse **passing** results only. Key: check ID, the argv actually run (after identity filtering), phase and diff fingerprint, stored in the run state. Failures always rerun. |
| F | "The implement loop runs loop checks; final verification runs final checks once" | `verify_stage` runs every green check after each implement/review attempt and each #47 fix round. `publish_guard` reruns them when the fingerprint changed | `verify_stage` runs loop checks cheapest first and **stops at the first failure** (the rest show "not run: an earlier loop check failed"). Only when every loop check passes does it run the final checks, reusing passing loop results at the same fingerprint. `publish_guard` runs final checks. The default `when` is both, so plans without `when` keep today's set, in the new order. `autonomy.loop_checks` changes to `"loop" in when`, as #47 left for this issue. |
| G | Register the operation as `validate_plan` | Registry names use hyphens and dots (`rebuild-state`, `policy.set`) and the CLI command is `validate-plan` | Register `validate-plan` with `run_checks: bool`. The CLI dispatches through it, so #21 calls the same operation. |
| H | Append `delivery.unverified_claims` to the ledger | It is not an event type | Add the type `delivery.unverified_claims` (`repository`, `count`, `commands`) to `ledger.TYPES` and the schema. Record it only when `count > 0`. |
| I | Patterns compile (static validation) | `validate` never compiles `success_pattern` or `failure_pattern` | A pattern that doesn't compile is invalid input: `validate` raises, exit 2, for every plan command, not only `--run-checks`. |
| J | A skipped declared identity can be detected | Per-test skip lines appear only in verbose output (`unittest -v`, `pytest -v` or `-rs`) | An identity counts as skipped when a line names it with `skipped`/`SKIPPED`. Without per-test lines, skips stay advisory. `docs/verification.md` says to use verbose output for checks with identities. New field `skips`: `"advisory"` (default) or `"fail"`. |
| K | "The command isn't in this task's evidence" | Bodies write `mkdocs build --strict`; evidence holds `.venv/bin/python -m mkdocs build --strict` | Normalise both sides: drop a leading interpreter (`python`, `python3`, `python3.N`, `.venv/bin/python`, any path ending in `python`) with `-m`, and split into words. A mentioned command counts as run when its words are a prefix of any command this run executed (red, green, setup, loop or final). Commands come from inline code spans and fenced code block lines. |
| L | `validate-plan` writes `planning-checks.json` and adds it to `plan_files` | The manifest is the person's file | `--run-checks` edits the manifest only to append `planning-checks.json` to `plan_files` when missing (key order kept, 2-space indent). Results are written even when a check fails. `plan.proposed` is recorded only when every check `ran`, so a failing plan never reaches the inbox as proposed. |
| M | Before/after timings for replaying the #18 manifest | The #18 checks call real suites; the measurement needs doubles and the code before and after this change | `ai-plans/plans-that-can-pass/replay.py` (plan evidence, not shipped) builds a temporary project with the #18 check layout (same IDs, phases, identities and argv shapes; commands replaced by doubles that sleep in proportion to their size) and runs implement-tests, implement with one fix round, and review through the provider double. It runs once against `main` and once against this branch; the PR shows both timings and check-run counts. |
| N | This PR lists "commands run with their results" (roadmap ground rule) | The new rule makes the runner's block the only verification section, but this manual-lane PR has no runner evidence | The new rule covers runner-delivered PRs. This PR, written in the session, still lists the commands run and their results, as the ground rule asks. |

## Scope

The issue's sections 1–7 are the specification. The plan follows them, with the decisions above.

### Contract fields (`runtime/plovi/manifest.py`)

- `success_pattern` becomes optional for `generic` checks. `failure_pattern` stays required for generic red.
- New optional fields, validated: `when` (non-empty subset of `loop`, `final`; default both),
  `expected_seconds` (positive integer), `skips` (`advisory` or `fail`).
- Every pattern compiles (decision I).

### Parsing (`runtime/plovi/verification.py`)

- Green passes when exit 0, no parser failures or errors, every identity present, and the
  `success_pattern` matches if set (section 3). Red is unchanged.
- Skips: counted (`counts.skipped`, also for non-unittest parsers where the summary has it) and
  shown in evidence; fail only on a skipped identity or `skips = "fail"`. `approved_skip_reason`
  stays accepted and shows in evidence.
- Identity filtering for red (decision B), loop/final selection and ordering (decision F),
  passing-result reuse (decision E). Ordering without `expected_seconds`: last recorded duration
  in the run state, then manifest order.

### `validate-plan --run-checks` (new `runtime/plovi/plan_checks.py`)

Static validation, one run per check (timeout default 300 s, its environment, stdin closed,
managed environments leased like `plovi verify`, container mode through the same context as
`plovi verify`), `git status --porcelain` before and after, classification (decision D), text
table with fix lines, `--json`, `planning-checks.json` (decision L), exit 0/1/2. Fix lines follow
the issue's examples and `design/README.md` voice. The `plovi verify` context setup in `cli.py`
moves into one helper both commands use.

### Claim only what ran (`runtime/plovi/evidence.py`, `git_ops.py`, `ledger.py`)

The evidence block's heading becomes "Verification (from plovi's evidence)". It lists each
check with its command, result, duration and `skipped: N`, then the existing stage, attempt,
size and fingerprint lines. At delivery, the agent body is scanned (decision K); unrun commands
appear under "Mentioned but not run by plovi" at the end of the block, and the ledger gets
`delivery.unverified_claims` (decision H). `synchronize` keeps replacing only the managed block.

### Skill and contract guidance

`skills/specify/SKILL.md` and `references/pipeline-contract.md`: run
`plovi validate-plan <manifest> --run-checks` after writing `pipeline.json`, repair until it
passes, show the table with the plan; name existing repository commands; focused `loop` checks
and full `final` checks; the documented docs interpreter; `expected_seconds` for checks over
30 s; no `success_pattern` unless the exit code can't be trusted; `templates/pr-body.md` for
`delivery.body_file`. Regenerate `templates/plugin-skills/*` if the generator covers it.

## Delivery order (one commit each)

1. Contract fields and parsing: optional `success_pattern`, `when`, `expected_seconds`, `skips`,
   pattern compilation, exit-code-authoritative green, advisory skips (sections 3, 4).
2. Check selection in the runner: loop/final, cheapest first, fail fast, identity-only red,
   passing-result reuse, `publish_guard` on final checks, `autonomy.loop_checks` (section 5).
3. `validate-plan --run-checks`, `planning-checks.json`, the `validate-plan` operation (sections 1, 2).
4. Claim only what ran: evidence block, body scan, ledger type, `templates/pr-body.md` (section 6).
5. Skill and contract guidance, docs, scenario steps P3 and D0, `owners.json` `48: done`,
   regenerated docs, CHANGELOG (section 7 and the issue's Docs list).

## Tests

All test files and case names from the issue's "Tests (required)" section:
`tests/test_plan_checks.py` (13), `tests/test_verification_v2.py` (9), `tests/test_pr_claims.py` (3). Plus:

- `tests/test_plan_checks.py`: `test_dotnet_compile_error_is_ran` and `test_pytest_missing_file_is_ran`
  (decision D); `test_bad_pattern_is_invalid_input` (I); `test_no_receipt_refuses` (C);
  `test_failed_validation_records_no_proposal` (L; this is the operation test for "specify can't
  present a plan whose checks fail").
- `tests/test_verification_v2.py`: `test_red_identity_filter_falls_back_to_whole_command` (B),
  `test_red_filter_works_with_discover` (B), `test_failed_result_not_reused` (E),
  `test_loop_stops_at_first_failure_and_final_waits` (F).
- `tests/test_pr_claims.py`: `test_interpreter_prefix_counts_as_run` (K),
  `test_unverified_claims_ledger_event` (H).
- `tests/test_ledger.py`: a sample for `delivery.unverified_claims`.
- The #18 fixtures from the acceptance criteria: the bad success pattern (`links`), mkdocs missing
  for the system `python3` (`docs-build` through a fixture interpreter without the module), and an
  environment skip (advisory) are three of the cases above, named after the #18 checks.

Every new test must fail before its change (red evidence saved in `ai-plans/plans-that-can-pass/red.txt`).

**Existing tests updated, not deleted** (each listed in the PR with its reason): `tests/test_evidence.py`
and `tests/test_gates_v2.py` cases that read the evidence block's format or `## Evidence` heading;
`tests/scenario/test_target_scenario.py` `test_D0_push_and_pr` (new heading, plus the issue's
"every claim matches a check plovi ran"); any `test_verification.py` case that treated a skip
as a failure without an identity. None of these weakens an assertion.

Scenario steps this PR marks done: **P3** (`test_P3_plan_checks_validated`) and **D0**
(`test_D0_push_and_pr`, shared with #49); `tests/scenario/owners.json` sets `48` to `done`.

## Docs

`docs/verification.md` (exit codes, skips, `when`, `expected_seconds`, reuse, identity filters),
`docs/tasks.md` and `docs/cli.md` (`validate-plan --run-checks`), `docs/review.md` (the PR
verification section), `docs/ledger.md` (new event type), `references/pipeline-contract.md`,
`CHANGELOG.md`. Regenerate `docs/commands.md` and `docs/generated/*`. CLI text follows
`design/README.md`: lowercase plovi, short active sentences, errors say what went wrong and the fix.

## Checks (all must pass)

| Check | Command |
|---|---|
| Tests | `python3 scripts/run_tests.py --jobs auto` |
| Generated docs | `python3 scripts/generate_docs.py --check` |
| Docs build | `.venv/bin/python -m mkdocs build --strict` (main checkout's venv) |
| Links | `.venv/bin/python scripts/check_links.py site` (main checkout's venv) |
| Public content | `python3 scripts/check_public_content.py --history` |
| Scenario | `python3 -m unittest tests.scenario.test_target_scenario tests.scenario.test_traceability` (P3, D0 pass) |
| Replay timing | `python3 ai-plans/plans-that-can-pass/replay.py` against `main` and this branch (decision M) |

CI green is checked after a push you request separately.

## Risks

- **Verification semantics change.** Optional patterns and advisory skips loosen two fail-closed
  rules. Exit codes and identities still gate green, and existing patterns keep their meaning.
  The decision rows and docs say exactly what passes.
- **Fail fast hides later failures for a round.** A fix round sees only the first failing loop
  check. Cheapest-first ordering makes the next round quick; final checks still run in full.
- **`-k` matches substrings.** `-k test_a` also runs `test_a_more`. That only adds tests, and the
  fallback covers identities the filter misses.

## Model routing (informational, manual lane)

`plovi models evaluate` with `model-facts.json` (large, high risk, complex) chose `claude/opus` for
specify and implement (`explicit-route`, required band deep), with advisory
`uninstalled-provider-skipped` and the notice "No model catalogue". Snapshot: `model-selection.json`.
This session (Claude Opus) implements; no route change.
