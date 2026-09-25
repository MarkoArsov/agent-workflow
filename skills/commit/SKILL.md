---
name: commit
description: Commit explicitly selected local changes using project conventions.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/scorebook for commands.
<!-- resolver:end -->

# commit

1. Inspect status and the complete selected diff, including untracked and staged files. Identify unrelated or pre-existing changes.

2. Run relevant checks and rule/secret guards for the selected scope. Draft a concise imperative subject using the project's recorded convention.

3. Stage explicit task-owned paths, commit, and verify the resulting commit. Do not use git add . when unrelated changes exist.

4. Never add AI attribution or generated-by trailers. A commit request does not imply pushing or opening a PR.

