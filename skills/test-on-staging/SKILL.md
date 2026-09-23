---
name: test-on-staging
description: Perform an approved post-merge smoke check with observed readiness and bounded side effects.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/agent-workflow for commands.
<!-- resolver:end -->

# test on staging

1. Resolve the merged revision, deployment target, and configured smoke plan. Confirm the deployed version before interpreting test results.

2. Read permitted identities, data boundaries, and cleanup steps. Use non-destructive reads by default; execute mutations only within explicit authorization.

3. Run the smallest browser/API/check sequence that covers the changed behavior. Record actual request/UI outcomes and relevant evidence without credentials.

4. Separate deployment readiness from feature correctness. A missing deployment is a blocker, not a passing smoke test.

5. Clean up created test data, then report passed checks, observed failures, and only the irreducible manual steps.

