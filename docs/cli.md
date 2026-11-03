---
title: CLI
description: Commands for setup, checked runs, evidence, recovery, and local installation.
footer: reference
footer_order: 1
---

# CLI

Use plovi from your terminal or your agent. Commands share the same project profile,
permissions, checks, and saved evidence. Run `plovi --help` for the complete list.

<div class="cli-commands">
<div class="cli-command"><code>plovi setup [path]</code><p>Preview project setup. Apply the reviewed proposal with its approval digest.</p></div>
<div class="cli-command"><code>plovi policy show [--json]</code><p>Read effective policy and each value's source.</p></div>
<div class="cli-command"><code>plovi policy set SECTION.KEY VALUE [--yes | --approve DIGEST]</code><p>Review and save a validated TOML edit. Agents preview, then apply by digest.</p></div>
<div class="cli-command"><code>plovi inbox [--format text|json]</code><p>List what needs you across registered projects, oldest first, with the command that resolves each item.</p></div>
<div class="cli-command"><code>plovi events [--task ID] [--since TIME|ID]</code><p>Read the ledger: every transition and command, with actor and reason.</p></div>
<div class="cli-command"><code>plovi stats [--since DATE|DURATION] [--task ID] [--json] [--gate]</code><p>Count runs, interventions, stops, time, attempts and tokens from the ledger. <code>--gate</code> checks the stability gate and exits 0 only when it passes.</p></div>
<div class="cli-command"><code>plovi retry TASK [--note FILE]</code><p>Resolve an escalation in a fresh session, retaining history.</p></div>
<div class="cli-command"><code>plovi approve TASK --plan|--size|--paths [--approve DIGEST] [--actor NAME] [--reason TEXT]</code><p>Approve a plan by its hash, or the current diff gate and verify retained output.</p></div>
<div class="cli-command"><code>plovi pause TASK</code><p>Stop a running task before its next stage. <code>resume</code> continues it.</p></div>
<div class="cli-command"><code>plovi cancel TASK</code><p>Ask the owning runner to stop the task.</p></div>
<div class="cli-command"><code>plovi projects add|list|remove</code><p>Register projects for the inbox. Removing one never deletes files.</p></div>
<div class="cli-command"><code>plovi rebuild-state TASK</code><p>Restore a task's state cache from the ledger.</p></div>
<div class="cli-command"><code>plovi commands [--json]</code><p>List every operation, its arguments, whether it changes anything and its risk.</p></div>
<div class="cli-command"><code>plovi inspect</code><p>Show the project profile and effective skill sources.</p></div>
<div class="cli-command"><code>plovi skill list</code><p>List the skills available in this project.</p></div>
<div class="cli-command"><code>plovi validate-plan PLAN</code><p>Check a full pipeline's requirements, paths, stages and routes.</p></div>
<div class="cli-command"><code>plovi preflight PLAN</code><p>Check readiness before starting a full pipeline.</p></div>
<div class="cli-command"><code>plovi migrate TASK [--apply]</code><p>Preview or apply a reviewed legacy test checkpoint, renew its proof, and leave implementation stopped.</p></div>
<div class="cli-command"><code>plovi pipeline PLAN|TASK</code><p>Start or safely resume an approved task with a pinned runtime. Reuse an active worker and attach tracking in the current terminal. Add <code>--no-watch</code> for a tracking descriptor.</p></div>
<div class="cli-command"><code>plovi run PLAN</code><p>Run the approved pipeline. Add <code>--detach</code> to run it in the background, <code>--no-wait</code> to refuse claim conflicts, or <code>--trusted</code> for explicit trusted execution.</p></div>
<div class="cli-command"><code>plovi status [TASK]</code><p>Read the saved status for a task, or list every task from the ledger.</p></div>
<div class="cli-command"><code>plovi answer TASK --file FILE|--text TEXT</code><p>Answer the question saved by a stopped task.</p></div>
<div class="cli-command"><code>plovi resume TASK</code><p>Resume a stopped task. Use <code>--rebind</code> only for an approved plan revision.</p></div>
<div class="cli-command"><code>plovi verify PLAN</code><p>Run the plan's checks again against its current changes.</p></div>
<div class="cli-command"><code>plovi models inspect</code><p>Inspect workflow-local model settings.</p></div>
</div>

## Start a run

Validate the approved full plan and check readiness before running it.

```sh
plovi validate-plan ai-plans/example/pipeline.json
plovi preflight ai-plans/example/pipeline.json
plovi pipeline ai-plans/example/pipeline.json
```

For a smaller change, use `plovi-specify`, then `plovi-implement` in your agent.
A full manifest is optional in that lane. See [lanes and bugfixes](lanes.md).

## Read status and recover

```sh
plovi status example
plovi watch example
plovi pipeline example
```

Read the saved question before using `answer`, and the failed check before using
`resume`. [Recovery](recovery.md) explains the choices and their effects.

## Choose a project

`--project PATH` selects an explicitly registered project. It does not make an
unrelated repository a member of that project.

```sh
plovi --project . inspect
```

!!! change "What changes for your workflow"
    The command is now `plovi`; `agentflow` remains an alias until 1.0.
    Skills use `plovi-*`, with deprecated `af-*` aliases. Existing project and
    user-data folders migrate once, with a notice. Finish running tasks before
    upgrading. If both project folders exist, plovi uses `.plovi/`, warns, and
    leaves the legacy data intact.


## Model evidence

`plovi models watch` refreshes optional Artificial Analysis evidence once, separate
from `plovi watch <task>`, which follows task progress. Supply AA_API_KEY through the
environment, or select a local assignment file:

~~~sh
plovi models watch --key-file /path/to/local/models.env
~~~

The file is parsed, never executed. The command updates only machine-local evidence;
missing keys or failed fetches preserve the previous snapshot. Unmatched aliases
stay unknown and displayed figures include attribution/date. Review the evidence
through update-models, then approve the exact settings proposal before applying it.
See [models and cost](models.md).


## Start an isolated task before planning

~~~sh
plovi task start fix-validation
plovi task start backend-change --repository app --repository checks
plovi task start followup --base feature/dependency
plovi task start fix-validation --resume
~~~

New tasks default to an owned branch/worktree; explicit setup checkout choices are honored. The output gives checkout,
branch, plan paths and canonical project root. Use those paths for all subsequent
work; the command does not switch or copy edits from the shared source checkout.
Explicit resume validates the same task's ownership. An existing unowned branch or
path is refused, and partial multi-repository progress can be resumed safely.
Manual tasks use this command too; no full manifest or model call is required.

## Runtime and tracking

`pipeline` starts the worker separately and follows it in an interactive terminal.
`--no-watch` returns its task, log, process and tracking descriptor instead. Calling
it again for the same active task reuses that worker. In an agent app, the foreground
skill uses available host tools to attach a tracker; unavailable tools fall back to
the exact command. See [tracking capabilities](tracking.md).

Each managed task saves a content-addressed runtime outside its mutable source.
Commands continue through that runtime even if an installed link or task code
changes. Use an absolute launcher with `--project` from any working directory, or
use the tracking descriptor's `argv` and `cwd`. Do not copy shell fragments from
issue titles into commands. To adopt a reviewed runtime and plan revision:

```sh
plovi pipeline example --upgrade-runtime --rebind
```

Ordinary status/watch never upgrades a runtime. A missing or changed runtime stops
with a restoration/upgrade action. Keep task evidence and runtime receipts together
when relocating a project; update the reviewed project allocation before resuming.

`status` and `watch` default to concise human output. `status --json` returns a
versioned summary; `status --verbose --json` deliberately returns detailed state.
`watch --json` emits summary and event objects as JSON Lines. Default watch follows
to completion or a stop; `--seconds 60` bounds observation without cancelling work.
Watch/pipeline exit status is 0 for completion or a still-active bounded observation,
1 for a stopped run requiring action, 2 for a command error, and 130 for interruption
of the viewer. Existing run/answer/approval inspection contracts remain compatible;
a question or pending gate is a successful command with a paused task. Closing a viewer leaves the detached worker running.

## Factory allocations and container checks

```sh
plovi worktrees
plovi clean --older-than 7d
plovi verify ai-plans/example/pipeline.json --check behavior --phase green
plovi run ai-plans/example/pipeline.json --pull-isolation-image
```

Clean uses recorded terminal lifecycle status, never age as proof of closure.
Verify uses the saved execution boundary, including check services.
The pull flag is one-time consent for the configured image; ordinary runs never
pull. Container preflight pins the local image ID. See [isolated execution](isolation.md).

## Operations, actors and the ledger

Every command that changes something is an operation in one registry.
`plovi commands --json` lists each one with its arguments, whether it changes
anything, and its risk; [the command reference](commands.md) is generated from it.

```sh
plovi commands
plovi answer csv-export --text "Keep the column order." --reason "Product decision"
plovi events --task csv-export --format text
```

Every changing command accepts `--reason TEXT`, `--actor-agent NAME` and `--via TOOL`
and records an event with that actor and reason in the [ledger](ledger.md). Without
`--actor-agent`, the actor is the person from `git config user.name`.

High-risk operations, `approve` and `policy set`, preview first: without
`--approve DIGEST` they print what would change and its digest, change nothing and
exit 0. Your existing `approve --size|--paths` and `policy set ... --yes` keep working.
When `--actor-agent` is passed, those shortcuts are refused and the digest is required.
`approve --plan` always needs the plan hash.

JSON stays the default output, except `status`, which keeps its human default.
`status`, `inbox`, `events` and `projects list` accept `--format text|json`.
`paused` is a successful stop and exits 0.

!!! note "What changes for your workflow"
    Read `plovi inbox` to see what needs you, and pass `--reason` when the why
    matters later. Agents always pass `--actor-agent` and preview high-risk changes
    before you approve them.
