# Specification evidence, 30 October 2026

## Scope and resolution

- PROJECT_WORKFLOW.md and .plovi/project.json resolve this source package, Codex
  only, current-checkout, ai-plans task storage, and trusted execution.
- Both legacy/canonical configuration folders exist. The resolver selects .plovi
  and preserves .agentflow, issuing its existing warning. No configuration changed.
- Starting revision 55cae30, branch codex/rename-plovi, local base main 0fe14a9.
  `git diff --stat HEAD main` is empty. The checkout was clean before planning.
- GitHub CLI refused missing account credentials. A read-only unauthenticated
  public API request fetched issue #16 successfully; it has no comments. No
  authenticated operation, tracker mutation or message was performed.

## Reproduction observed before implementation

Using the existing RunnerTests fixture and deterministic provider double in a
temporary isolated workspace, blocked + two permitted attempts returned:

```text
observed_status=failed; provider_calls=2; escalation=None
spec_conflict parsed_report=None
impossible parsed_report=None
```

This reproduces the defect without changing product source or authoring product
tests. Required new assertion-red tests remain planned, not executed.

## Model routing and readiness

- Offline evaluator initially reported no catalogue/routes. Its exact unresolved
  snapshot is retained. After the user selected Sol/medium for all three stages,
  a revised facts file was evaluated; the active snapshot has no unresolved route.
- All stages: codex / gpt-6.1-sol / medium; no fallbacks. Advisories are
  explicit-route-below-recommended-band for all three, single-lineage for tests and
  review, and missing catalogue. No benchmark fetch or model-generation call.
- `bin/plovi validate-plan ai-plans/runner-hardening/pipeline.json`: passed.
- `bin/plovi preflight ai-plans/runner-hardening/pipeline.json`: passed; Codex CLI
  exists and accepts required flags. Current effective permission mode is trusted.
  Entitlement is checked on the first authorized request, not established here.
- Selected stages: implement-tests, implement, review. No delivery stages or
  connectors. Native local-commit instructions remain in force.

## Existing verification

- Initial `python3 -m unittest discover -s tests -v`: 178 tests in 102.264s;
  one failure, three errors. Service fixtures could not become ready and process
  inspection raised permission errors under restricted execution. This is not a
  clean baseline. Repeated the full command with local service/process access:
  **178 tests passed in 91.435s**. No product/test files changed between runs.
- Default `python3 -m mkdocs build --strict` could not import MkDocs. Installed
  requirements-docs.txt into a disposable external environment and repeated the
  exact module/build arguments with that interpreter: passed (0.18s). Nothing was
  installed into actual user agent configuration or the package runtime.
- `python3 scripts/generate_docs.py --check`: passed, no generated changes.
- `python3 scripts/check_links.py site`: 3,964 links/assets, zero failures.
- `python3 scripts/check_public_content.py --history`: 2,681 source/history items,
  zero findings at that checkpoint; the completed plan scan covered 2,683 items,
  zero findings. Private denylist not supplied. Recheck after
  the final artifacts and local planning commit.

The final validation and preflight were repeated after completing the plan files;
both passed. Before executing the pipeline, expose a Python development environment
with requirements-docs.txt installed as `python3` on PATH for the named checks.
The disposable environment used here satisfies that prerequisite locally; its
machine-specific path is deliberately not embedded in the manifest. No global
installation is needed. The runner's preflight does not itself execute acceptance
checks; new test identities are intentionally absent until implement-tests.

## Not yet performed

New regression tests, feature implementation, new-policy activation, live-provider
inference, hosted CI and cross-platform crash/concurrency results. All remain
acceptance work after plan approval. No push, PR or deployment is selected.
