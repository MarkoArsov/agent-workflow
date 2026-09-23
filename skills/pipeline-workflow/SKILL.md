---
name: pipeline-workflow
description: Explain the installed workflow and route a request to its project-aware stage.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agent-workflow for commands.
<!-- resolver:end -->

# pipeline workflow

1. Resolve the active project and run inspect. Read PROJECT_WORKFLOW.md, effective skill origins, stage routes, and configured repository policies.

2. Explain the user's immediate path: setup for an unconfigured project, specify for a new task, implement for the manual lane, or implement-pipeline for an approved full plan.

3. Use the effective project skill instead of assuming package defaults. Different projects may change stages, rules, connectors, and delivery.

4. Answer workflow questions with the actual configuration and documented runtime capabilities. Do not launch a pipeline merely because the user asked how it works.

5. For customization, use skill copy/new and refresh; for package changes use update. Keep project-owned instructions separate from installed defaults.

