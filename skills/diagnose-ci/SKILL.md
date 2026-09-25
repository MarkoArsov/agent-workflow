---
name: diagnose-ci
description: Diagnose a failing CI run using the current revision and complete failure evidence.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/scorebook for commands.
<!-- resolver:end -->

# diagnose ci

1. Resolve repository, branch, and exact run ID. Use GitHub checks and failure-log or the project's configured CI adapter.

2. Confirm the run's head revision matches the change being discussed. Read the failed job/step and relevant logs before guessing.

3. Distinguish code defects, test failures, infrastructure problems, dependency/authentication issues, and flaky evidence. Never disable checks to obtain green.

4. Reproduce the narrow failure locally where practical, implement an in-scope fix, and run the relevant checks.

5. Report observed cause, changed files, verification, and any external action still needed. Reruns, deployment changes, and comments follow the user's actual authorization.

