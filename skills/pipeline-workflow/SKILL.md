---
name: pipeline-workflow
description: Explain the installed workflow and route a request to its project-aware stage.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/plovi for commands.
<!-- resolver:end -->

# pipeline workflow

1. Resolve the active project and run inspect. Read PROJECT_WORKFLOW.md, effective skill origins, stage routes, and configured repository policies.

2. Explain the user's immediate path: setup for an unconfigured project, specify for a new task, implement for the manual lane, or implement-pipeline for an approved full plan.

3. Use the effective project skill instead of assuming package defaults. Different projects may change stages, rules, connectors, and delivery.

4. Answer workflow questions with the actual configuration and documented runtime capabilities. Do not launch a pipeline merely because the user asked how it works.

5. For customization, use skill copy/new and refresh; for package changes use update. Keep project-owned instructions separate from installed defaults.


Substantive changes default to specify's full contract, then implement-pipeline after
approval. Manual implement is an explicit user choice or a trivial edit, with its
reason stated. Prepare/reuse the configured task checkout before plan writes; use
separate worktrees for concurrent tasks and honor current-checkout policy. Missing
routes leave a full draft pending rather than silently selecting manual execution.

Load project quality guidance consistently for implementation, test authoring and
review (references/quality-guidance.md). models evaluate remains offline;
update-models can use optional models watch evidence from Artificial Analysis with
AA_API_KEY or an explicitly selected key file, then proposes settings for approval.
Use session-retro for read-only learning from selected sessions, with optional PR
threads and explicit apply; add-rule/prune-context own the resulting maintenance.
Translate mechanical output into a concise result and next action. Keep raw output
available when requested and use brief excerpts when they explain a failure.
