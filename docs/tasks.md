# Task lifecycle

## Choose a lane

Use **specify** for the request and select a lane proportionate to the change.

**Manual:** a concise plan, implementation in the current agent session, and observed checks.
Useful for small, contained changes.

**Full runner:** a complete plan, independent stages, saved evidence, recovery, and optional delivery.
Useful when test-first work, independent review, or several repositories justify it.

## Write the plan

The full lane creates:

| File | Purpose |
|---|---|
| prompt.md | Original request and decisions. |
| requirements.md | Required outcomes and acceptance criteria. |
| implementation.md | Approach, existing patterns, and scope. |
| deferred.md | Deliberately excluded work and reasons. |
| pipeline.json | Repositories, checks, stages, routes, and delivery contract. |

Every outcome maps to named executable checks. Plans remain complete when revised.

## Start the runner

~~~sh
agent-workflow validate-plan ai-plans/task-name/pipeline.json
agent-workflow preflight ai-plans/task-name/pipeline.json
agent-workflow run ai-plans/task-name/pipeline.json --detach
agent-workflow status task-name
agent-workflow watch task-name --seconds 60
~~~

For a project-local install, use `.agent-workflow/bin/agent-workflow`.

The default sequence is **implement-tests → implement → review → commit-and-push → draft-pr**.
Each plan explicitly selects its optional stages. No provider is mandatory for every stage.

## What completion means

The runner observes the expected test failures, successful checks, current diff, path boundaries, and blocking rules.
Implementation and review cannot rewrite assertion-proven tests.
Review receives the requirements and actual diff without the implementation reasoning file.

The final result records stages, checks, changes, and per-repository delivery.
A missing check or failed stage is visible; it is never converted into a success summary.

[Recover a run](recovery.md) · [Customize stages](customize.md#add-a-stage)
