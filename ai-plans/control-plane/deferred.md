# Deferred and decided

## Decided during specification

- Gate strength (person): explicit launches self-approve; only background workers
  and later schedules enforce a prior approval. A stricter gate that makes
  `pipeline` require a separate `approve --plan` was offered and declined.
- Delivery (person): commit-and-push and draft-pr are selected.
- `status` keeps its existing human default and `--json`; the issue's "JSON by
  default" is applied to new commands only, so skills and people see no change.
- Existing `approve --size|--paths` and `policy set --yes` remain person
  shortcuts; agents must use preview and `--approve <digest>`.
- `state.json` rebuild uses content-addressed state checkpoints stored in the
  ledger directory, outside the repository, rather than reconstructing every
  field from typed events.
- `plan.proposed` is recorded by `validate-plan`, which specify already runs.
- Issue titles come from `task start --issue/--title`; no network fetch.

## Out of scope (from the issue)

- The app, schedules, the PR shepherd, MCP.
- Inbox kinds `review`, `breakdown`, `schedule_failed`.

## Deferred

- Ledger compaction, retention and export.
- Recording runner transitions for tasks pinned to a pre-ledger runtime without
  an explicit runtime upgrade.
- Pausing inside a stage between attempts; pause stops at stage boundaries.
