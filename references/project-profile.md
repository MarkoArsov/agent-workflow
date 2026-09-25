# Project configuration

The versioned JSON profile lives in .scorebook/project.json. PROJECT_WORKFLOW.md explains it for people and agents. A project may contain one repository or several sibling repositories. Registration is explicit; neighboring folders are not automatically part of a task.

Keep per-repository roles, commands, base branches, task participation, and checkout strategy independent. Use task_policy when-changed for a repository that only needs a feature branch when its files change. Reading or running checks does not require creating a branch.

Project skills override bundled skills by name. Keep new and modified skill bodies, scoped rules, references, connectors, and stage definitions in project-owned directories. Refresh native host adapters after adding skills. Updates preserve these extensions.

Use setup to preview changes and apply an approved proposal. Native instructions and the current user's request take precedence over defaults. Process permission settings do not authorize messages or tracker writes.

