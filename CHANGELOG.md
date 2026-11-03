# Changelog

## Unreleased

- Add the append-only ledger: one event per task transition and changing command,
  with actor and reason, stored per project under user data. `state.json` becomes a
  cache that `plovi rebuild-state TASK` restores from state checkpoints.
- Add one command layer: `plovi commands --json` lists every operation with its
  arguments and risk. Changing commands accept `--reason`, `--actor-agent` and `--via`.
  High-risk operations preview first and apply with `--approve DIGEST`.
- Add `plovi inbox`, `plovi events`, `plovi pause`, `plovi projects add|list|remove`,
  `plovi status` without a task, `answer --text` and `approve --plan`.
- Background workers require a recorded plan approval for the current plan hash;
  explicit launches record it. Disable with `execution.require_plan_approval = false`.
- `setup --apply` registers the project; `task start` accepts `--issue` and `--title`.
- Add the plovi-factory skill for agents acting on the control plane.
- Background runs start from the task's own branch, so planning commits are
  delivered; `preflight` and `run --dry-run` no longer create factory checkouts.
- Plans can name `allowed_commands` that restricted runs may execute.
- A provider usage limit pauses the run with its reset time instead of failing it,
  skips fallbacks from the same provider, and resume keeps the interrupted edits.
  Failure kinds come from structured provider errors, not transcript text.
- Completion reports may end with a bare JSON line after prose.
- Add `plovi stats [--since] [--task] [--json] [--gate]`: runs, interventions, stops,
  time, attempts and tokens from the ledger. `--gate` checks the stability gate
  (G1 to G5) and exits 0 only when every criterion passes.
- The ledger records the provider, token usage and cost on `attempt.finished`,
  `red_proof` on `run.started`, `files_changed` on `pr.opened`, and an optional `next`
  command on stop events. `plovi migrate --apply` records `checkpoint.migrated`.
- Add the target-scenario harness in `tests/scenario`, a stateful GitHub CLI fake for
  tests, and the generated `docs/generated/scenario.md` page.
- `scripts/run_tests.py` gains `--record` (the local suite time for the gate) and
  `--scenario-results PATH`; `--changed` now selects nested test modules.
- CI batches and test workers are balanced by per-test time from `tests/timings.json`
  (refresh it with `scripts/update_test_weights.py`), so each CI job runs about five
  minutes of tests. Windows runs eight batches, macOS three and Ubuntu two per version.
- `plovi clean` removes finished task worktrees on Windows, where Git prints paths
  with forward slashes.
- Windows tests install command doubles as `.exe` launchers, so arguments with `&` or
  newlines reach them intact.

## 0.1.1

- Rename Agent Flow to lowercase plovi across the runtime, installers, CLI,
  discovery, plugin metadata, and documentation.
- Keep `agentflow` and `af-*` as compatibility aliases until 1.0.
- Move project `.agentflow/` configuration to `.plovi/` on first use of the new
  runtime, with recoverable metadata rebasing and no automatic folder merging.
- Preserve existing installation ownership, model settings, and older runtime pins.
- Keep the GitHub repository name, site domain, and visual styling unchanged.
