# Approved completion of the compatibility corrections

The user requested fixing all remaining issues and resuming after seeing the
51-file/3024-line size gate and the missing legacy-test scope. Expand only the named
legacy test modules to permit the required compatibility corrections. Task-specific
limits are 80 changed files and 5000 changed lines for this expanded work; protected
paths, secrets, ownership, independent review and final evidence guards still apply.
This is not unrestricted approval for unrelated work or delivery.

The product implementation now exists. Continue with implement and independent
review rather than running pre-implementation test authoring/red proof against the
implemented product again. Preserve all existing test cases and valid assertions.
The original red results stay archived. This explicitly reviewed contract revision
permits correcting the affected legacy fixtures during implementation, with renewed
focused and full green evidence and independent final requirements/diff review.

Keep approved F1 semantics: new unattended execution, including non-TTY detection,
uses factory ownership. Tests intentionally exercising the classic Python API
strategy must pass unattended=False explicitly. CLI permission/factory tests need
usable temporary remotes and valid allocations; assert results in the actual saved
checkout, retaining user-clone preservation checks. Do not change production defaults
or add test-only permission/factory bypasses to accommodate old fixtures. Audit all
legacy runner/lifecycle/recovery/limits/permissions/concurrency tests together.

Correct fake Docker inspect to preserve an already immutable sha256 image ID.
Add a regression that resolves a tag and reinspects its ID, asserting equality.
Keep existing image/preflight/credential/cleanup requirements and negative tests.

Run the complete suite from the runner's verification environment. Do not classify
provider sandbox-denied loopback listeners as product failures: the runner-owned
host checks must obtain real results. Provider reviewers should use the exact named
check commands permitted by their reviewed allowlist; execution denial is missing
evidence, not a failed product assertion. Keep genuine account/security decisions
explicit; use bounded independent correction for settled in-scope discrepancies.

Continue until all named checks and independent review pass, correcting failures
inside this expanded scope. No remote publishing, native login switch, container
pull or deployment is newly authorized by this revision.
