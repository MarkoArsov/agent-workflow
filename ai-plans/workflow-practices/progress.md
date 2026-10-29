# Implementation evidence

The user approved manual Codex implement-only execution, then explicitly requested
commit-and-push and draft-pr. Source workspaces and real user agent configuration
remain untouched. No benchmark key was read and no authenticated AA request ran.

## Regression and focused evidence

- The first test-helper attempt had a duplicate rank argument; that setup error
  was corrected and is not counted as red evidence.
- Before product changes, ModelPolicyTests.test_adversary_lineage_prefers_alternate_lab
  failed on an assertion: old selection returned favored where alternate was
  required for test authoring. It now passes with three explicit fictional labs
  on the same host and reversed input stage order.
- Model-policy compatibility, band tradeoffs, unknown legacy lineages, pinned
  routes, fallback diversity and old snapshot hashes have executable coverage.
  Further review added cases preventing unreported lower-band fallbacks and
  confirming exact reviewed lineage inheritance without settings writes.
- Eight watch tests exercise mocked transport/pagination, metrics/nulls, error and
  write-failure preservation, key-file precedence/non-execution, secret-safe
  errors, redirect refusal, bounds, date/version reporting and effective pins.
  Fixtures use synthetic keys and isolated homes; they are not a live API smoke.
- Three workflow fixtures exercise frozen shared guidance, project-local skill
  resolution and planning-time worktree creation/reuse. A copied-profile nuance
  is handled by explicitly carrying the canonical configuration root at handoff,
  without changing runner or project resolution behavior.
- Skill scenarios and the fictional retrospective are documented separately in
  specify-scenarios.md and labeled as walkthroughs, not live model evaluations.

## Verification

- Full suite initially passed 170 tests, including actual disposable local-server
  checks and isolated release/export/installation behavior. Subsequent model
  changes were checked with the focused suite; the final suite result is recorded
  at completion below.
- Strict MkDocs build passed in the existing documentation virtual environment.
- 3,964 internal links/assets passed. Generated docs and native wrappers are current.
- Skill-creator structural validation passed for session-retro.
- Source rename audit passed with two exact generated deprecated-alias exceptions;
  no broad scanner exemption was added.
- Public-content scan passed without an external private denylist. This is a
  generic scan and human diff review, not proof that no private data can exist.
- Local browser inspection confirmed the updated models content and the planning
  page's rendering in the existing docs style; no tokens/layout/assets changed.

## Delivery

The current task branch already had PR #39. Its remote-only CI fix was preserved
by a normal merge before implementation, without resetting/rebasing or force push.
The final PR description must cover the existing rebrand/compatibility changes as
well as these workflow/model improvements. Reuse that PR and set it to draft;
do not create a duplicate, request reviewers, post comments or change issue state.


## Final local verification

The completed source passed `python3 -m unittest discover -s tests -v`: **172 tests**
in 80.285 seconds. This includes mocked benchmark transport and real disposable
local fixture servers; tests use isolated child homes. No hosted OS result or real
model-generation/API smoke is inferred from it. Both specification and retrospective
skill structural validation passed. Strict docs build, 3,964 link/asset checks,
wrapper/generated-doc/design freshness, standalone export checksums and seven
portable provider-subset contracts passed. Source/site rename audits and generic
source/site/history public-content scans had zero findings, without a private denylist.
The existing exact generated-search compatibility hash was refreshed after reviewing
that its old names occur only in existing migration documentation.
