---
name: e2e-test-engineering
description: Design and implement focused end-to-end tests against configured disposable environments.
---

<!-- resolver:start -->
Run this skill folder's scripts/resolve.py from the active project once. If it returns a different effective skill, follow that file instead. Otherwise continue below. Use the selected package's bin/stageway for commands.
<!-- resolver:end -->

# e2e test engineering

1. Read the project's E2E reference, existing tests, environment lifecycle, data boundaries, and accepted behavior.

2. Choose the smallest representative flow and assertions that test externally visible behavior. Use established fixtures/selectors and explicit readiness checks.

3. Use a disposable local environment by default. Confirm any staging/production side effects and cleanup before performing them.

4. Run a named file or scenario, not an entire expensive suite by habit. Obtain meaningful red then green evidence when adding behavior tests.

5. Avoid fixed sleeps, destructive shared-data mutation, skipped assertions, and permanent environment workarounds. Record cleanup and reproducible commands.

