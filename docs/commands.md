---
title: Command reference
description: Every plovi operation, its arguments, whether it changes anything and its risk.
footer: reference
footer_order: 3
---

# Command reference

Generated from the operations registry by `scripts/generate_docs.py`. Agents read the same data with `plovi commands --json`.

Every operation that changes something accepts `--reason`, `--actor-agent NAME` and `--via TOOL`, and records an event with that actor and reason in the [ledger](ledger.md). High-risk operations return a preview with a digest and change nothing until you pass `--approve DIGEST`.

| Operation | Changes | Risk | What it does |
|---|---|---|---|
| [`answer`](#answer) | yes | low | Answer the question a stopped task asked, then continue it |
| [`approve`](#approve) | yes | high | Approve a plan, or a diff that crossed the size or protected-path limits |
| [`cancel`](#cancel) | yes | low | Ask the runner to stop a task and its child processes |
| [`commands`](#commands) | no | none | List every operation with its arguments, whether it changes anything and its risk |
| [`events`](#events) | no | none | List ledger events, optionally for one task or after a time or event ID |
| [`inbox`](#inbox) | no | none | List what needs you across registered projects, oldest first |
| [`pause`](#pause) | yes | low | Stop a running task before its next stage starts |
| [`policy.set`](#policyset) | yes | high | Change one project policy value in plovi.toml |
| [`policy.show`](#policyshow) | no | none | Show the effective project policy and where each value comes from |
| [`projects.add`](#projectsadd) | yes | low | Register a configured project so the inbox covers it |
| [`projects.list`](#projectslist) | no | none | List registered projects and whether each root still exists |
| [`projects.remove`](#projectsremove) | yes | low | Unregister a project; its files stay on disk |
| [`rebuild-state`](#rebuild-state) | yes | low | Rebuild a task's state.json and status.json from the ledger |
| [`resume`](#resume) | yes | low | Continue a paused, failed or interrupted task without repeating finished stages |
| [`retry`](#retry) | yes | low | Retry an escalated task, optionally with a note for the agent |
| [`stats`](#stats) | no | none | Report runs, interventions, stops, time, attempts and tokens from the ledger; --gate checks the stable-enough gate |
| [`status`](#status) | no | none | Show one task's progress, or every task the ledger knows |

## answer

Answer the question a stopped task asked, then continue it.

```sh
plovi answer TASK (--text TEXT | --file FILE) [--reason TEXT]
```

Risk: **low**. Changes a task or the registry.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `task` | yes | string | Task ID |
| `text` | no | string |  |
| `file` | no | string | Path to the answer |
| `rebind` | no | boolean | Accept a reviewed plan revision |
| `upgrade_runtime` | no | boolean | Move the task to the current runtime; needs rebind |
| `reason` | no | string | Why this change is made; recorded in the ledger |
| `actor_agent` | no | string | Agent name; agents must always pass it |
| `via` | no | string | Tool the agent acts through |

## approve

Approve a plan, or a diff that crossed the size or protected-path limits.

```sh
plovi approve TASK (--plan | --size | --paths) [--approve DIGEST] [--manifest PATH] [--actor NAME] [--reason TEXT]
```

Risk: **high**. Preview, then apply by digest.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `task` | yes | string | Task ID |
| `plan` | no | boolean |  |
| `size` | no | boolean |  |
| `paths` | no | boolean |  |
| `approve` | no | string | Digest from the preview; required for --plan and for agents |
| `manifest` | no | string |  |
| `actor` | no | string | Person name override |
| `rebind` | no | boolean | Accept a reviewed plan revision |
| `upgrade_runtime` | no | boolean | Move the task to the current runtime; needs rebind |
| `reason` | no | string | Why this change is made; recorded in the ledger |
| `actor_agent` | no | string | Agent name; agents must always pass it |
| `via` | no | string | Tool the agent acts through |

## cancel

Ask the runner to stop a task and its child processes.

```sh
plovi cancel TASK [--reason TEXT]
```

Risk: **low**. Changes a task or the registry.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `task` | yes | string | Task ID |
| `reason` | no | string | Why this change is made; recorded in the ledger |
| `actor_agent` | no | string | Agent name; agents must always pass it |
| `via` | no | string | Tool the agent acts through |

## commands

List every operation with its arguments, whether it changes anything and its risk.

```sh
plovi commands [--json]
```

Risk: **none**. Reads only.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `json` | no | boolean |  |
| `format` | no | text, json |  |

## events

List ledger events, optionally for one task or after a time or event ID.

```sh
plovi events [--task ID] [--since TIME|EVENT_ID] [--format text|json]
```

Risk: **none**. Reads only.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `task` | no | string |  |
| `since` | no | string | ISO timestamp or event ID |
| `format` | no | text, json | Output format |

## inbox

List what needs you across registered projects, oldest first.

```sh
plovi inbox [--format text|json]
```

Risk: **none**. Reads only.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `format` | no | text, json |  |

## pause

Stop a running task before its next stage starts.

```sh
plovi pause TASK [--reason TEXT]
```

Risk: **low**. Changes a task or the registry.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `task` | yes | string | Task ID |
| `reason` | no | string | Why this change is made; recorded in the ledger |
| `actor_agent` | no | string | Agent name; agents must always pass it |
| `via` | no | string | Tool the agent acts through |

## policy.set

Change one project policy value in plovi.toml.

```sh
plovi policy set KEY VALUE [--approve DIGEST | --yes] [--reason TEXT]
```

Risk: **high**. Preview, then apply by digest.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `key` | yes | string | section.key |
| `value` | yes | string | TOML value |
| `approve` | no | string | Digest from the preview |
| `yes` | no | boolean | Person shortcut; refused for agents |
| `reason` | no | string | Why this change is made; recorded in the ledger |
| `actor_agent` | no | string | Agent name; agents must always pass it |
| `via` | no | string | Tool the agent acts through |

## policy.show

Show the effective project policy and where each value comes from.

```sh
plovi policy show [--json]
```

Risk: **none**. Reads only.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `json` | no | boolean |  |

## projects.add

Register a configured project so the inbox covers it.

```sh
plovi projects add PATH [--reason TEXT]
```

Risk: **low**. Changes a task or the registry.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `path` | yes | string | Project root |
| `reason` | no | string | Why this change is made; recorded in the ledger |
| `actor_agent` | no | string | Agent name; agents must always pass it |
| `via` | no | string | Tool the agent acts through |

## projects.list

List registered projects and whether each root still exists.

```sh
plovi projects list [--format text|json]
```

Risk: **none**. Reads only.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `format` | no | text, json |  |

## projects.remove

Unregister a project; its files stay on disk.

```sh
plovi projects remove ID [--reason TEXT]
```

Risk: **low**. Changes a task or the registry.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `id` | yes | string | Registered project ID |
| `reason` | no | string | Why this change is made; recorded in the ledger |
| `actor_agent` | no | string | Agent name; agents must always pass it |
| `via` | no | string | Tool the agent acts through |

## rebuild-state

Rebuild a task's state.json and status.json from the ledger.

```sh
plovi rebuild-state TASK [--reason TEXT]
```

Risk: **low**. Changes a task or the registry.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `task` | yes | string | Task ID |
| `reason` | no | string | Why this change is made; recorded in the ledger |
| `actor_agent` | no | string | Agent name; agents must always pass it |
| `via` | no | string | Tool the agent acts through |

## resume

Continue a paused, failed or interrupted task without repeating finished stages.

```sh
plovi resume TASK [--rebind] [--budget-minutes N] [--budget-attempts N] [--budget-cost USD] [--reason TEXT]
```

Risk: **low**. Changes a task or the registry.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `task` | yes | string | Task ID |
| `rebind` | no | boolean | Accept a reviewed plan revision |
| `upgrade_runtime` | no | boolean | Move the task to the current runtime; needs rebind |
| `budget_minutes` | no | integer | Raise this task's time budget in minutes |
| `budget_attempts` | no | integer | Raise this task's attempt budget |
| `budget_cost` | no | number | Raise this task's known cost budget in US dollars |
| `reason` | no | string | Why this change is made; recorded in the ledger |
| `actor_agent` | no | string | Agent name; agents must always pass it |
| `via` | no | string | Tool the agent acts through |

## retry

Retry an escalated task, optionally with a note for the agent.

```sh
plovi retry TASK [--note FILE] [--reason TEXT]
```

Risk: **low**. Changes a task or the registry.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `task` | yes | string | Task ID |
| `note` | no | string | Path to a note the next attempt reads |
| `rebind` | no | boolean | Accept a reviewed plan revision |
| `upgrade_runtime` | no | boolean | Move the task to the current runtime; needs rebind |
| `reason` | no | string | Why this change is made; recorded in the ledger |
| `actor_agent` | no | string | Agent name; agents must always pass it |
| `via` | no | string | Tool the agent acts through |

## stats

Report runs, interventions, stops, time, attempts and tokens from the ledger; --gate checks the stable-enough gate.

```sh
plovi stats [--since DATE|DURATION] [--task ID] [--json] [--gate]
```

Risk: **none**. Reads only.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `since` | no | string | ISO date or time, or a duration such as 7d |
| `task` | no | string | Task ID |
| `json` | no | boolean | Print JSON |
| `gate` | no | boolean | Evaluate G1-G5; exit 0 only when all pass |

## status

Show one task's progress, or every task the ledger knows.

```sh
plovi status [TASK] [--json] [--format text|json]
```

Risk: **none**. Reads only.

| Argument | Required | Format | Meaning |
|---|---|---|---|
| `task` | no | string | Task ID; omit to list every task |
| `json` | no | boolean |  |
| `verbose` | no | boolean |  |
| `format` | no | text, json | Output format |

!!! note "What changes for your workflow"
    Agents read `plovi commands --json` first and use these operations instead of editing plovi files.
    People can use the same commands; `plovi inbox` names the one to run next.
