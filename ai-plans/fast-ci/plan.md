# Fast, reliable CI and a fast test suite (issue 46)

Lane: **manual**, at the user's explicit request (the issue's ground rules also
require the manual lane until the #49 gate). `specify` and `implement` run in the
same session, in this task worktree. No detached `pipeline.json`.

- Task: `fast-ci`; branch `codex/fast-ci` (created by `plovi task start`).
- Checkout: `.plovi/local/worktrees/fast-ci/agent-workflow`.
- Base: `origin/main` at `15ef365`. `plovi task start` cut the branch from the
  stale local `main` (`401da80`), which lacks PR #45, a stated dependency. The
  branch had no commits, so it was fast-forwarded to `origin/main`.
- Source of requirements: GitHub issue 46. This plan resolves its open points; the
  issue text stays authoritative for anything not changed below.

## Evidence that changes the issue's scope

1. **More Windows failures than the issue lists.** The latest `main` run
   (Verify `41655839802`, `15ef365`) shows 50 failing or erroring tests across the
   six Windows jobs before the 12-minute timeout cut each log. All six timed out,
   so the true set is larger. See `windows-failures-2026-11-03.txt`. Beyond the
   issue's table it includes `test_background_runs` (5), `test_companion_fixture_health`,
   `test_concurrency`, more `test_container` and `test_factory_checkouts` cases,
   `test_isolation_fixture_health` (6), `test_operations` (2), two more
   `test_permissions` cases, and `test_projects.test_text_format`.
   **Decision:** the acceptance bar is "every test passes on every Windows shard",
   not just the table. Causes for the extra ones are diagnosed from tracebacks once
   the per-test timeout (Scope 2) stops hiding them. Most share the listed causes
   (`seed_remote` rmtree, bare `gh`, `isatty`, local time zone).
2. **No tracebacks exist in the logs.** Every Windows log ends at the step timeout
   before unittest's summary. So Scope 2 (per-test timeout) lands before the
   Windows fixes are judged complete.
3. **`git_ops.py` ~123 already compares branch names with `!=`.** The issue's
   suspected cause (unnormalised paths) is not proven. The worktree-ownership check
   just above it (`target.resolve() not in worktrees`) compares paths and is the
   likelier candidate. **Decision:** use `same_path` there and wherever paths are
   compared, keep the branch-name comparison exact, and confirm the real cause from
   the Windows traceback.
4. **`tests/test_ci_test_runner.py` already tests sharding.** It stays and must keep
   passing. The new `tests/test_run_tests.py` covers the new behaviour.
5. **`TZ=UTC` is not valid for the Windows C runtime**, which requires an offset
   (`tzn[+|-]hh…`). **Decision:** set `TZ=UTC0`, which means UTC on POSIX and on
   Windows. `test_projects.test_text_format` gets the same deterministic rendering
   as `test_inbox.test_text_format_snapshot`.
6. **Windows cannot be run locally** (this machine is macOS). Windows behaviour is
   proven only by Verify on a pushed branch. Pushing and opening a PR need a
   separate explicit request (AGENTS.md).

## Scope

Everything in the issue's Scope 1–8, with these decisions:

### 1. Windows correctness

- `process.resolve(argv, env=None)` as specified; `executable` stays as an alias.
  Used by `util.run`, `process.spawn` and `process.execute`. Resolution always uses
  the PATH the child will get (`env["PATH"]` when `env` is given).
- `util.is_interactive(stream=sys.stdin)` replaces every `sys.stdin.isatty()` in
  `runtime/plovi` (`runner.py` 57/440/444/447, `policy.py` 244, `cli.py` 296/313).
  `cli.py` 214 checks `sys.stdout` and uses `is_interactive(sys.stdout)`.
- `util.is_absolute_anywhere(value)` replaces `Path(x).is_absolute()` where a
  repository-relative path or glob is validated: `policy.py` 58, `manifest.py`
  88/148/210, `profile.py` 19/43/72/77, `runner.py` 112. Not changed: places that
  require an absolute host path (`identity.py`, `runtime_pin.py`,
  `providers/__init__.py`) and `migration.py` (operates on real host paths).
- `util.same_path(a, b)`: audit `git_ops.py`, `tasks.py`, `factory.py`,
  `project.py`, `claims.py`; apply it to path equality and membership checks
  (including the worktree set in `git_ops.py`).
- `tests/helpers.py` `remove_tree(path)`; replace all 5 `shutil.rmtree` calls in
  `tests/` (`helpers.py`, `test_projects.py`, `test_runner.py`,
  `test_factory_checkouts.py`, `test_install.py`).
- `WorkspaceTest.env`: `TZ=UTC0`; `LC_ALL=C.UTF-8` on POSIX; `PYTHONUTF8=1` on
  Windows.

### 2. Per-test timeout

As in the issue. When the watchdog fires, the worker records the test as an error
(`TimeoutError("test exceeded <timeout> s")`), writes its result file with a
`notRun` list of tests it did not reach, flushes and exits 3. The parent reports the
timed-out test and lists the not-run tests by ID as errors. It does not restart
them, so the run fails and the counts stay honest. Serial mode (`--jobs 1`, the
default) uses the same faulthandler dump and watchdog in-process.

### 3. Parallel runs

As in the issue. Timings default to `<repo>/.plovi/local/test-timings.json`
(already git-ignored via `.plovi/local/`); `--timings PATH` overrides it, and the
new tests always pass a temporary path.

### 4. Faster fixtures

As in the issue. The template repository lives in a per-process temporary
directory removed with `atexit`. `cli_inproc` also catches `SystemExit` and turns
it into `returncode`. Converted tests keep their assertions byte-for-byte; only the
call changes from `self.cli(...)` to `self.cli_inproc(...)`. The PR lists, per CLI
command, the subprocess contract test that remains.

### 5. Tiers

`tests/tiers.json`, chosen from measured timings. A `--start-directory` without a
`tiers.json` has empty tiers.

### 6. `--changed`

As in the issue. The repository root is `git -C <start-directory> rev-parse
--show-toplevel`; source modules come from `<root>/runtime/plovi`. This is how
`test_changed_selects_importing_tests` runs against its temporary repository.

### 7. CI workflows

As in the issue: `smoke` gates `core`, `audit`, `docs`, `windows-install`. New
`nightly.yml`. Step timeout 20 min, job 25 min.

### 8. Docs

`docs/development.md` "Run the checks" (it has no "Running tests" heading; the
new content goes there), `CONTRIBUTING.md`, and `docs/recovery.md` "When GitHub
Actions fails". Follow `design/README.md` / `design/DESIGN.md` voice. AGENTS.md
keeps `python3 -m unittest discover -s tests -v`, which must keep working
unchanged.

## Out of scope

As in the issue: no assertion changes, deletions, skips or loosening; no new
dependencies; no behaviour changes beyond the Windows defects. Fixes for newly
exposed Windows failures are in scope only when they are portability defects of the
same kind. Anything else is reported, not fixed here.

## Order of work (one local commit each, suite green after each)

1. `run_tests.py`: per-test timeout, worker mode, `--jobs`, tiers, `--changed`;
   `tests/test_run_tests.py`; `tests/tiers.json`.
2. Windows correctness: Scope 1 and `tests/test_platform_paths.py`.
3. Faster fixtures: template repo, cached seeding, `cli_inproc` conversions,
   `wait_for`.
4. CI: `verify.yml`, `nightly.yml`.
5. Docs.

## Quality guidance

- `AGENTS.md`, `PROJECT_WORKFLOW.md`, `CONTRIBUTING.md`.
- The issue's ground rules and pitfalls (argv lists, no `shell=True`, plain
  template repos, isolated `HOME`/`XDG_*`/`TMP` per worker, `sys.__stderr__` for
  faulthandler, restore state in `finally`, timings file not committed).
- `references/quality-guidance.md` review questions applied to changed paths.
- `design/README.md`, `design/DESIGN.md` for CLI output and docs.

## Checks

Run from the task worktree. Local machine: macOS, 15 cores.

| # | Check | Expected evidence |
|---|---|---|
| 1 | `python3 -m unittest tests.test_run_tests tests.test_platform_paths tests.test_ci_test_runner -v` | all pass; `test_hanging_test_dumps_stacks_and_fails` finishes in < 15 s |
| 2 | `python3 scripts/run_tests.py --jobs auto` | exit 0; tests run ≥ baseline count (below) |
| 3 | `python3 scripts/run_tests.py --jobs 4` | exit 0 in ≤ 4 min (4-worker stand-in for a 4-core machine; machine and time go in the PR) |
| 4 | `python3 -m unittest discover -s tests -v` | exit 0; plain discovery still works |
| 5 | `python3 scripts/run_tests.py --tier smoke --jobs auto` | exit 0; time recorded |
| 6 | `python3 scripts/run_tests.py --changed` (after editing one runtime module) | prints the importing tests plus smoke |
| 7 | `python3 -m compileall -q runtime scripts tests` | exit 0 |
| 8 | `python3 scripts/generate_docs.py --check` | exit 0 |
| 9 | `.venv/bin/python -m mkdocs build --strict` and `.venv/bin/python scripts/check_links.py site` | exit 0 (the docs venv is in the main checkout; use its interpreter) |
| 10 | `python3 scripts/check_public_content.py --history` | exit 0 |
| 11 | `git diff origin/main -- tests` reviewed for removed or changed `assert*` lines | none removed or weakened; counts before/after in the PR |

Baseline: `python3 scripts/run_tests.py --list` count and serial wall time, captured
before the first change.

**Needs a push (separately authorized):** Verify green on every job including all
3 Windows shards; job durations (smoke ≤ 90 s, Ubuntu ≤ 150 s, macOS ≤ 300 s,
Windows shard ≤ 360 s); the nightly workflow's manual dispatch, which GitHub allows
only once `nightly.yml` is on the default branch, so that criterion is met after
merge. If Windows jobs fail after the push, the tracebacks drive the next fix in
this same task.

## Delivery

Local commits only. Commit subjects in imperative style. Pushing, the draft PR (its
body follows the issue's "PR body lists" rule) and the post-merge nightly dispatch
each need an explicit request.

## Routes (informational, manual lane)

Evaluator facts: stages specify+implement, code, large, standard risk, uncertain
(Windows unverifiable locally), 1 repository, ~12 test files, ~450 test lines.
Result: `deep` band required for both stages; project pins `codex/gpt-6.1-sol` then
`claude/opus`, with advisory `explicit-route-below-recommended-band`. Manual
`implement` runs in this session (Claude Opus); the pins are not changed.
