# Project layout

A project is one Git repository or a parent folder containing registered repositories.

~~~text
project/
  PROJECT_WORKFLOW.md
  .agent-workflow/
    project.json
    package-lock.json
    skills/              # your overrides and new skills
    rules/               # scoped project conventions
    references/          # project guidance
    connectors/          # capabilities, never credentials
    stages.json          # optional custom stages
    local/               # ignored state, evidence, baselines
    runtime/             # ignored project-installed package
  ai-plans/
    task-name/
  app/                   # multi-repository example
  checks/
~~~

## Four distinct locations

| Location | Owns |
|---|---|
| Installed package | Versioned defaults and runtime. |
| Project | Configuration, extensions, and shared plans. |
| Repository | Its base branch, remote, commands, and role. |
| Task checkout | Selected writable code for one task. |

The package never discovers unrelated sibling repositories by a hard-coded name.
Child references, registered Git common directories, and explicit membership determine the project.
Nested folders, spaces, symlinks, and Git worktrees resolve to the same profile.

## Select participation per task

A profile's **task_policy** is always, when-changed, or never.
A plan selects each participating repository as read or write.
Only writable participants receive task branches/worktrees or delivery actions.

Never means never writable through the runner; it may still be explicitly selected as a read-only check provider.
Only declared writable path patterns may change.

For a single repository, plans default to tracked `ai-plans/<task>/`.
For several repositories, they live at the configured shared project root.
Runtime evidence stays ignored.
