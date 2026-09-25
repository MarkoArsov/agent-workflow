---
name: draft-pr
description: Create an approved draft pull request for verified, pushed task branches.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/scorebook for commands.
<!-- resolver:end -->

# draft pr

1. Read current plan, actual commits, base branch, repository conventions, and observed check results. The runner handles creation when draft-pr is selected.

2. Write a concise title and body describing the problem and final behavior, with relevant validation and limitations. Use the project's PR template when present.

3. Compare the entire feature branch to its base so the description includes the complete change. Do not list abandoned approaches or claim unperformed testing.

4. Require current green evidence and a successful normal push. Reuse the existing matching PR; do not create duplicates on resume.

5. Use draft status. Include only approved public task content and links. Do not add reviewers, mark ready, post comments, or update a tracker implicitly.

6. Refresh an existing body only when requested, showing the concrete text if approval is needed. Report the verified PR URL and per-repository delivery state.

