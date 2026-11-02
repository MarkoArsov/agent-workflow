# Revised planning evidence

Prior proposal and evidence are preserved under v1/. User requested evaluator
improvements and Codex/Claude setup on the #17 branch, superseding the earlier
suggestion to deliver evaluator changes separately.

Research confirmed that the starting branch's dual-provider configuration was
absent from main and this task branch, and the planner inserted facts.routes
forcing Sol/high. Those task pins are now removed. Restored only agents and route
arrays from the earlier project configuration; harness prose now names both hosts.
The project-only configuration change does not alter native or global settings.

Both CLIs are installed. Read-only discovery during the diagnostic turn reported
Claude aliases opus/sonnet/haiku with needs-confirmation, no local restrictions flag;
Codex model listing failed. No successful account inference or model entitlement is
claimed. No discovery catalogue or confirmation was invented or persisted.

One offline 1.1 evaluation for this revision saved the exact model-selection.json
and embedded it in pipeline.json. It inherits Sonnet tests / Sol implementation /
Opus review with their prior fallbacks and no added effort. No facts.routes.
Advisories: tests and implementation below recommended band, review same lineage
as tests, no model catalogue. There are no unresolved routes. These are inherited
project pins, not output from the proposed evaluator improvements.

Product tests named in the manifest are acceptance contracts to be authored after
approval; their names do not claim those cases already exist or have run.
Validation/build/check results for this revision are recorded below as observed.

## Observed revision checks

- validate-plan passed after the complete contract and routing scenarios were saved.
- preflight passed for Sonnet, Sol and Opus CLI help/capability checks, restricted
  unattended defaults, no connectors and no selected delivery stages. Model account
  access still requires the first actual request.
- Strict MkDocs build passed using the existing .venv interpreter. The default
  python3 lacked MkDocs; no dependencies or user installations were changed.
- Generated-documentation check passed; 4,141 internal links/assets, zero failures.
- Full existing suite: 261 tests ran; one failure and four errors were local socket
  or disposable service startup failures in the restricted test environment.
  The environment/fixture suites were rerun with local-service permission: all
  five tests passed. Concurrency rerun evidence follows. This is not a single
  successful full-suite invocation and is not evidence for the future product tests.
- Task artifact scan: 21 files, zero findings; reachable history: 2,102 items, zero
  findings before this revision's commit. No private denylist supplied. The known
  pre-existing ignored runner-hardening evidence findings remain outside delivery.
- git diff --check passed. Project profile contains both providers, facts.routes is
  absent, manifest routes exactly match the saved snapshot and no route adds a
  reasoning argument. No evaluator/isolation product source or tests were edited.

Concurrency rerun with temporary-socket permission: all six tests passed in
7.143 seconds. All five failures/errors in the initial full-suite invocation are
covered by the passing environment/fixture and concurrency reruns (11 tests).
No source change or test weakening was used to obtain these results.
