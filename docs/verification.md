---
description: Understand red and green evidence, current artifacts, and task checks.
---

# Evidence and checks

A successful agent response is a proposal to complete the stage.
The runner independently executes the named checks and examines the files.

## Red evidence

Test-first stages need expected test identities and observed assertion failures.
Missing imports, syntax errors, failed compilation, startup failures, and absent tools do not prove a behavior is unimplemented.

After meaningful red evidence, the runner records test-file hashes.
Implementation and review cannot rewrite those tests to make them pass.
A wrong requirement/test needs a reviewed plan revision and renewed proof.

## Green evidence

Every required outcome maps to a named check.
Evidence records command, repository, exit status, output, test identities, changed paths, and a diff fingerprint.
Unexpected skipped tests fail unless the plan records an explicit justification.

Built-in parsers cover unittest, pytest, .NET test summaries, Jest, and TAP.
Other tools use explicit generic success/failure patterns.
Use a precise marker tied to the check's outcome; a broad word such as "passed" is poor evidence.

## Current artifacts

Provider edits outside the declared scope block completion and remain available for inspection.
Verification commands must not change source files.
Ignored build output is fine; configure cleanup and ignore files appropriately.

Review/custom-stage changes invalidate stale fingerprints.
Publication rechecks the final diff when needed and reruns blocking rules.

Run local E2E checks against disposable environments using named scenarios and explicit readiness.
For deployed behavior, use the separate **test-on-staging** skill and its configured data/cleanup boundaries.
