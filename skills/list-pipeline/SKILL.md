---
name: list-pipeline
description: List effective stages, skills, repository policies, and current task state.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/stageway for commands.
<!-- resolver:end -->

# list pipeline

1. Run inspect and skill list from the active project. Report the selected package version, profile location, effective origins, stage defaults, routes, and relevant repository participation.

2. If a task is named, read status for that task and distinguish completed, running, awaiting input, failed, and cancelled stages.

3. Identify missing routes or integrations concretely. Do not imply an enabled default stage is automatically selected for every task.

4. Keep the inventory concise and link to the configuration or effective skill file for details.

