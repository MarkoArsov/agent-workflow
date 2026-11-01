# Revised combined plan for issue #17

Proposed, awaiting renewed approval. Keep factory checkouts, optional container
execution, evaluator improvements and project Codex/Claude setup on the same branch:
codex/isolated-execution. The previous complete proposal is preserved under v1/.

## Scope

- Factory-owned checkouts for new unattended runs, safe mirror refresh, independent
  companions, host delivery, ownership and terminal cleanup.
- Experimental Docker/Podman stages/checks with explicit mounts/environment,
  image-pull consent, restricted fallback diagnostics and owned-container cleanup.
- Stage-specific model facts; routine test size becomes an advisory; capability
  and effort are separate. Planner suggestions cannot become pins. Every decision
  explains source, requirements, eligibility, effort, restrictions and fallbacks.
- Restore Codex/Claude project setup. Keep genuine user/project pins compatible;
  migrate this project's restored preferences to adaptive defaults after evaluator
  implementation. No global or native settings writes.
- Required isolated tests and docs for all four parts; logical commits on this one
  branch. No push, PR, tracker change, deployment or image publication selected.

## Current routes for implementing this plan

These inherit the restored existing project configuration; they are not planner
pins or recommendations from the future evaluator. No high-effort argument is set.

| Stage | Primary | Fallback |
| --- | --- | --- |
| Tests | Claude Sonnet | Codex Sol |
| Implementation | Codex Sol | Claude Opus |
| Review | Claude Opus | Codex Sol |

The 1.1 evaluator was run once with no facts.routes. No unresolved routes. It warns
that tests/implementation pins are below its current recommended deep band, review
shares lineage with test authoring, and no catalogue is saved. This is a capability
check of inherited configuration, not proof of subscription entitlement or cost.
A later task will use the improved evaluator/adaptive project defaults; do not
re-evaluate the frozen routes mid-implementation.

Full lane: implement-tests, implement, independent review. The three new regression
suites cover factory checkouts, container execution and evaluator changes. Existing
model-policy/watch/workflow tests, portable policy selftest, full unittest suite,
generated docs, strict MkDocs, links and public-content checks remain required.
All outcomes map to named executable checks in pipeline.json. Only the explicit
opt-in real-container smoke may be skipped in default automated coverage.

The explicit user instruction keeps work in this checkout. The profile still uses
worktrees; automatic runner launch would allocate another checkout. Execute the
contract stages directly here after approval, or obtain a user choice allowing
allocation. This restriction is not concealed by a passing preflight.

requirements.md and pipeline.json contain the complete revised contract. Existing
project setup edits are included now as requested; no evaluator/isolation product
code or product tests have been implemented during this planning revision.

Approve this plan and start implementation?
