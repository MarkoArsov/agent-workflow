---
title: Project policy
description: Review limits, protected paths, and unattended permissions in plovi.toml.
question: How do I review runner policy?
---

# Project policy

`plovi.toml` lives at the configuration root. Setup includes a commented proposal;
existing projects use defaults until you review a write. Repeated setup preserves
policy comments and edits. Inspect effective values and their sources:

```sh
plovi policy show --json
plovi policy set limits.max_changed_files 60
plovi policy set execution.unattended_permission_mode '"restricted"' --yes
```

`set` shows a diff and validates before saving. Enter a literal `y` interactively,
or pass `--yes` after review. Noninteractive edits require `--yes`, or the digest of a
reviewed preview. Agents always preview first and apply by digest; `--yes` is refused
when `--actor-agent` is passed:

```sh
plovi policy set limits.max_changed_files 60 --actor-agent helper --via plovi-factory --reason "Keep diffs small"
plovi policy set limits.max_changed_files 60 --actor-agent helper --via plovi-factory --reason "Keep diffs small" --approve DIGEST
```

The preview prints the diff and its digest and changes nothing. Every saved change
records a `policy.changed` event with the actor and reason in the [ledger](ledger.md). Unsupported
TOML edits and stale previews leave the original file intact. No-op edits preserve
bytes. `doctor` reports missing policy and values duplicated in the profile.

| Key | Default |
|---|---|
| `limits.running_tasks` | 2, reserved |
| `limits.waiting_for_review` | 3, reserved |
| `limits.attempts_per_stage` | 2 attempts per route |
| `limits.max_changed_files` | 40 |
| `limits.max_changed_lines` | 1500 added plus removed lines |
| `limits.size_exempt` | `["**/package-lock.json", "**/*.lock"]` |
| `paths.protected` | `[".github/workflows/**", "**/migrations/**"]` |
| `execution.unattended_permission_mode` | `"restricted"` |
| `execution.tracking_mode` | `"auto"` |
| `execution.require_plan_approval` | `true`; background workers need an approved plan hash |
| `autonomy.level` | `"assisted"` |
| `grants` | Empty reserved table |
| `isolation.mode` | `"none"` |
| `isolation.runtime` | `"auto"` |
| `isolation.image` | Empty; required for container mode |
| `isolation.network` | `"on"` |
| `isolation.mount_harness_config` | `[]`, opt-in provider IDs |
| `isolation.api_key_env` | `[]`, explicit environment names |

`ready` and `auto` are accepted autonomy values; they do not enable additional
actions. Slot limits are reserved configuration, not a scheduler. Unknown keys,
unsupported grants, invalid types and repository-escaping globs are errors.

Precedence is per key: explicit plan limits, explicit TOML keys, corresponding
profile values, built-ins. `attempts_per_stage` maps to `attempts_per_route`; it
keeps the existing per-route budget. Policy and permission decisions are frozen
with a run. Review changes and use `resume --rebind` to adopt them. Legacy runs
without a policy binding retain legacy inputs and built-in policy interpretation;
adding explicit policy requires rebind.

## Size and path approvals

The runner measures the cumulative task diff across writable repositories after
code attempts and before delivery. Tracked, untracked, deleted, renamed and binary
files count. Binary files count as one line. Size exemptions cover root and nested
lockfiles; they do not exempt scope or protected paths.

```sh
plovi approve TASK --size
plovi approve TASK --paths --reason "Reviewed migration" --actor "Reviewer"
```

Approvals record identity, reason, time and a path/content/mode fingerprint. The
actor defaults to configured Git identity; supply `--actor` if none exists. Both
gates need approval when both apply. Any diff change invalidates prior approvals.
Resume does not bypass a pending approval, and approval verifies retained stage
output without replaying a successful provider call. Policy inputs themselves
receive no automatic path approval.

!!! note "What changes for your workflow"
    Review policy during setup. When a run pauses for size or protected paths,
    inspect its diff and approve each pending gate. Changes to that diff need a
    fresh approval.

## Plan approval for background workers

With `execution.require_plan_approval = true`, the background worker that `pipeline`
and `run --detach` start refuses a plan whose current hash has no `plan.approved`
event, and refuses to continue a run whose plan changed since it started. Explicit
launches approve the plan they start: `run`, `run --detach`, `pipeline`, and the
`resume`, `answer`, `retry` and `approve` continuations record the approval first.
Approve a plan without starting it:

```sh
plovi approve TASK --plan
plovi approve TASK --plan --approve PLAN_SHA256
```

Set the key to `false` to let workers start any validated plan. Runs that started
before plan approvals existed keep running.

## Tracking preference

Setup profiles include `execution.tracking_mode`. Review it in `plovi.toml` or the
profile: `auto`, `current-terminal`, `app-terminal`, `command-only`, or `off`.
Auto uses the launching host's demonstrated capabilities. App-terminal falls back
to a command when no supported app terminal tool exists. This preference does not
change worker permissions or authorize additional model requests.

Review [isolated execution](isolation.md) before enabling container mode. Image IDs,
enums, provider IDs and environment names have separate validation; they are not
repository globs. Names and immutable image identity are frozen, never API key values.
