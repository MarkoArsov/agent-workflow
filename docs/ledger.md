---
title: The ledger
description: What plovi records about each task, where it lives, and how state is rebuilt from it.
question: What does plovi remember, and where?
---

# The ledger

!!! summary "In one minute"
    - plovi appends one event for every task transition and every command that changes something.
    - Each event names who acted (a person, an agent, or plovi) and why.
    - The ledger lives in your user data folder, never inside a project, repository or worktree.
    - `state.json` is now a cache. `plovi rebuild-state TASK` restores it from the ledger.
    - The inbox, `plovi status` without a task and `plovi events` all read the ledger.

## Where it lives

Each project has its own ledger folder:

```text
<user data>/plovi/projects/<project-id>/ledger/
  events-2026-11.jsonl     one JSON line per event, one file per UTC month
  blobs/ab/ab12….json      state checkpoint values, stored once by content hash
  imported.json            runs imported from evidence that predates the ledger
  ledger.lock              held for a moment while one line is appended
```

`<user data>` is `$XDG_DATA_HOME`, or `~/.local/share` when that is unset.
plovi refuses to write the ledger when that location falls inside the project root,
a configured repository or a task worktree. Point `XDG_DATA_HOME` somewhere else to fix it.

Appends are safe across processes: a writer holds the lock, writes exactly one line
ending in a newline, and syncs it to disk. Lines never interleave. A line over 64 KiB is
refused; large payloads such as attempt output stay in the evidence folder and an event
records their path.

If a writer stops mid-line, the next read skips that torn last line with one warning and the
next append removes it. Any other damaged line is an error, so silent loss is impossible.

## The event envelope

Every line follows `schemas/event.schema.json`, version `v: 1`:

| Field | Meaning |
|---|---|
| `v` | Envelope version, `1`. |
| `id` | Sortable unique ID: 48-bit millisecond time and 80 random bits, Crockford base32, 26 characters. |
| `at` | UTC time with milliseconds, for example `2026-11-02T09:15:04.120Z`. |
| `project` | Project ID. |
| `subject` | `{kind, id}`; `kind` is `task`, `schedule`, `execution`, `pr`, `policy` or `project`. |
| `type` | One of the types below. |
| `actor` | `{"kind": "person", "name": …}`, `{"kind": "agent", "name": …, "via": …}` or `{"kind": "plovi", "name": "runner"}`. |
| `reason` | A short sentence. Commands use `--reason`, or a default that names the command. |
| `data` | Fields for the type. |

The person name comes from `git config user.name` in the project root, else `local-user`.
`approve --actor NAME` still overrides it. Agents pass `--actor-agent NAME` and `--via TOOL`.

## Event types

`?` marks an optional field. Imported events also carry `imported: true`.

| Type | Data | Recorded when |
|---|---|---|
| `task.created` | `branches`, `issue`?, `title`? | `plovi task start` allocates a task. |
| `task.claimed` | `run_id` | The runner owns the task. |
| `run.started` | `run_id`, `manifest`, `plan_sha256`, `red_proof`? | A runner invocation starts; `red_proof` is true when the plan demonstrates a failing test first. |
| `stage.started` | `run_id`, `stage` | A stage begins. |
| `attempt.finished` | `run_id`, `stage`, `attempt`, `classification`, `path`, `kind`?, `provider`?, `usage`?, `cost_usd`? | A provider attempt ends; `path` is its attempt file. `usage` holds `input_tokens` and `output_tokens` when the provider reports them. |
| `stage.finished` | `run_id`, `stage`, `result` | A stage passes, or stops as `failed`, `escalated` or `cancelled`. |
| `question.asked` | `run_id`, `stage`, `question`, `next`? | A stage needs your answer. |
| `question.answered` | `run_id` | `plovi answer` continues the task. |
| `plan.proposed` | `plan_sha256`, `manifest` | `plovi validate-plan` accepts a plan, once per plan hash. |
| `plan.approved` | `plan_sha256`, `auto`, `manifest`? | You approve a plan, or an explicit launch approves it (`auto: true`). |
| `approval.requested` | `run_id`, `kind`, `fingerprint`, `next`? | A diff crosses the size or protected-path limits. |
| `approval.granted` | `run_id`, `kind`, `fingerprint` | `plovi approve --size` or `--paths` accepts that diff. |
| `escalation.raised` | `run_id`, `stage`, `kind`, `detail`, `next`? | A run stops for a person's decision. |
| `run.paused` | `run_id`?, `status`?, `reason`?, `resets_at`?, `next`?, `budget`? | The runner pauses before the next stage, at a provider usage limit (`reason: usage_limit`, reset as Unix time), at a task budget (`reason: budget`), or when the plan changed mid-stage (`reason: plan_changed`). |
| `run.resumed` | `run_id`?, `status`?, `retry`? | `resume`, `retry`, `answer`, `approve` or `pipeline` continues a task. |
| `run.interrupted` | `run_id`?, `status`? | plovi finds a run that stopped without a result, once per run. |
| `run.cancelled` | `run_id`?, `status`? | The runner stops after a cancel request. |
| `run.finished` | `run_id`, `status`, `error`? | A runner invocation stops: `complete`, `failed`, `escalated`, `needs_input` or `needs_approval`. |
| `delivery.committed` | `repository`, `commit` | Delivery commits the task changes. |
| `delivery.pushed` | `repository`, `branch` | Delivery pushes the task branch. |
| `pr.opened` | `repository`, `url`, `files_changed`? | Delivery opens a draft pull request; `files_changed` counts the delivered files. |
| `delivery.unverified_claims` | `repository`, `count`, `commands` | The PR body mentions check or build commands plovi never ran for this task; the PR lists them under "Mentioned but not run by plovi". |
| `policy.changed` | `diff` | `plovi policy set` writes `plovi.toml`. |
| `project.registered` | `root` | `plovi projects add` or `setup --apply` registers a project. |
| `project.unregistered` | `root`? | `plovi projects remove` forgets a project. |
| `state.checkpoint` | `run_id`, `state_sha256`, `keys` | The saved task state changed. |
| `pause.requested` | `run_id`? | `plovi pause` asks the runner to stop at the next stage. |
| `cancel.requested` | `run_id`? | `plovi cancel` asks the runner to stop. |
| `checkpoint.migrated` | `binding_sha256` | `plovi migrate --apply` moves a legacy test checkpoint onto the current plan. |
| `plan.rebound` | `run_id`, `old`, `new` | The run continues with an approved plan revision, or `resume --rebind` binds one. `old` and `new` are binding hashes. |
| `commits.adopted` | `repository`, `commits`, `author`? | Resume adopts linear commits on the task branch that the task's own Git identity made. |
| `limits.exceeded` | `run_id`, `files`, `lines`, `limit` | The diff passed `max_changed_files` or `max_changed_lines` but stayed under the ceiling, so the run continued. |
| `receipt.rederived` | `repository`, `path`? | A missing or changed allocation receipt matched this task's ledger, so the runner rewrote it. |
| `provider.circuit_open` | `run_id`, `provider`, `classification` | A permanent provider failure, such as authentication, skips that provider for the rest of the run. |

`next` on a stop event is the command that continues the task. [`plovi stats`](stability-gate.md) reads these events.

The same table lives in `runtime/plovi/ledger.py`, and a test keeps the schema, the code and this page in step.

## State is a cache

Whenever the saved task state changes (ignoring timestamps, process IDs and live heartbeat
fields), the runner records a `state.checkpoint`. Its `keys` map each top-level field to the
SHA-256 of its value; each value is stored once in `blobs/`.

```sh
plovi rebuild-state csv-export
```

`rebuild-state` restores `state.json` and `status.json` from the latest checkpoint. It checks
every blob against its hash and keeps the recorded `updated_at`. It refuses, and writes nothing,
when the history or a blob is missing or changed. `plovi status TASK` rebuilds a missing cache
by itself before it reads.

## Plan hashes

`plan_sha256` covers the manifest without its `_`-prefixed keys, written as canonical JSON, then
each plan file's path and bytes in the listed order. Any edit to the manifest or a plan file gives
a new hash. Background workers start only a plan whose current hash has a `plan.approved` event;
see [plan approval](recovery.md#approve-a-plan).

## Privacy

The ledger stays on your machine with the rest of plovi's user data. Questions, reasons, escalation
details and policy diffs are redacted for common credential patterns and bounded in length before
they are written. Provider output stays in the task's evidence folder; events only point to it.
Treat the ledger like any local log: it can name tasks, branches, issue titles and file paths.

## Runs that predate the ledger

The first time plovi uses the ledger for a project, it imports every run that has a `state.json`
in the evidence folder. Each becomes `task.created`, `run.started`, one `stage.finished` per
finished stage, a stop event for the saved status and a `state.checkpoint`, all marked
`imported: true`. `imported.json` records each imported run, so importing again appends nothing.

Tasks pinned to a runtime from before the ledger keep working, but that runtime records no runner
transitions. Commands such as `answer`, `cancel` and `approve` still record their own events. To
record transitions for such a task, move it to the current runtime after review:

```sh
plovi resume csv-export --upgrade-runtime --rebind
```

Pausing also needs a current runtime; plovi says so when you try.

!!! note "What changes for your workflow"
    Nothing to set up: plovi records events from the next run. Use `plovi inbox` to see
    what needs you and `plovi events --task TASK` to read a task's history. Keep `XDG_DATA_HOME`
    outside your projects. Deleting `state.json` is no longer fatal; `rebuild-state` restores it.
