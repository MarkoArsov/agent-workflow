---
name: commit-and-push
description: Deliver verified task changes through guarded commits and normal pushes.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/stageway for commands.
<!-- resolver:end -->

# commit and push

1. Read the approved task manifest and current project conventions. This stage is mechanical and normally executed by the runner after current green evidence.

2. Confirm every writable repository is on the selected feature branch, with no base-branch delivery, force push, or unrelated staged changes.

3. Use runner delivery to stage only observed task-owned paths, commit with the approved subject, and push the explicit branch to its configured remote. Never add AI attribution trailers.

4. Preserve per-repository progress after each commit and push. If one repository fails, report partial delivery and resume without recreating successful commits.

5. In direct invocation, inspect all diffs and obtain any missing scope/message choice before equivalent mechanical actions. Existing user edits are not automatically part of the task.

6. A new change after verification requires rechecking; an agent saying tests passed is not evidence. Do not create or publish PRs unless separately selected.

