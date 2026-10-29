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
<div class="cli-command"><code>plovi inspect</code><p>Show the project profile and effective skill sources.</p></div>
<div class="cli-command"><code>plovi skill list</code><p>List the skills available in this project.</p></div>
<div class="cli-command"><code>plovi validate-plan PLAN</code><p>Check a full pipeline's requirements, paths, stages and routes.</p></div>
<div class="cli-command"><code>plovi preflight PLAN</code><p>Check readiness before starting a full pipeline.</p></div>
<div class="cli-command"><code>plovi run PLAN</code><p>Run the approved pipeline. Add <code>--detach</code> to run it in the background.</p></div>
<div class="cli-command"><code>plovi status TASK</code><p>Read the saved status and evidence for a task.</p></div>
<div class="cli-command"><code>plovi answer TASK --file FILE</code><p>Answer the question saved by a paused task.</p></div>
<div class="cli-command"><code>plovi resume TASK</code><p>Resume a stopped task. Use <code>--rebind</code> only for an approved plan revision.</p></div>
<div class="cli-command"><code>plovi verify PLAN</code><p>Run the plan's checks again against its current changes.</p></div>
<div class="cli-command"><code>plovi models inspect</code><p>Inspect workflow-local model settings.</p></div>
</div>

## Start a run

Validate the approved full plan and check readiness before running it.

```sh
plovi validate-plan ai-plans/example/pipeline.json
plovi preflight ai-plans/example/pipeline.json
plovi run ai-plans/example/pipeline.json
```

For a smaller change, use `plovi-specify`, then `plovi-implement` in your agent.
A full manifest is optional in that lane. See [lanes and bugfixes](lanes.md).

## Read status and recover

```sh
plovi status example
plovi watch example
plovi resume example
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

Every new task receives a distinct owned branch/worktree. The output gives checkout,
branch, plan paths and canonical project root. Use those paths for all subsequent
work; the command does not switch or copy edits from the shared source checkout.
Explicit resume validates the same task's ownership. An existing unowned branch or
path is refused, and partial multi-repository progress can be resumed safely.
Manual tasks use this command too; no full manifest or model call is required.
