---
description: Configure repositories, agents, checks, and delivery choices for a project.
footer: docs
footer_order: 2
---

# Set up your project

Open the intended repository or multi-repository parent and invoke **aw-project-setup**
(**agent-workflow:project-setup** in the native Claude plugin).

The setup skill reads existing instructions, manifests, commands, Git conventions, and CI configuration.
It reports findings with their sources, asks about unresolved choices, and presents a complete proposal.

## Decisions you own

Confirm:

- Repositories and their roles, including which participate always, only when changed, or never.
- Whether writable tasks use the current checkout, a feature branch, or a worktree.
- Build/test/lint commands and where they run.
- Plan storage, tracker, PR flow, selected agents, model routes, and fallbacks.
- Trusted or restricted execution and any connector configuration.

A repository's role does not dictate its branch policy. An E2E repository can remain on its existing branch and provide checks without being writable.

Trusted execution is the offered default. It uses provider permission-bypass flags.
[Restricted execution](execution.md) is configurable during setup. This choice does not authorize messages or tracker changes.

## Preview, then apply

For a CLI preview:

~~~sh
agent-workflow setup . --output /tmp/workflow-proposal.json
~~~

The skill gathers answers, regenerates the proposal, and shows its file changes.
Applying requires that proposal's exact approval digest:

~~~sh
agent-workflow setup --apply /tmp/workflow-proposal.json --approve APPROVED_DIGEST
~~~

An unresolved or stale proposal is rejected. Do not reuse an approval after changing its contents.

The result is [project configuration](projects.md), a concise PROJECT_WORKFLOW.md, and host discovery adapters.
Keep these in version control where appropriate. In a non-Git parent, shared configuration and plans are durable local files unless you choose a configuration repository.

## Reconfigure later

Run the same setup skill again. It compares previous generated defaults, current edits, and new detection.
Manual settings, deletions, unknown extension fields, and prose are preserved.
Conflicting changes are shown for a decision. An identical run leaves file bytes unchanged.
