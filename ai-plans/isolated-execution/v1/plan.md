# Proposed plan for issue #17

Implement factory-owned Git checkouts for new unattended runs, preserving interactive
profile choices, with safe refresh, companions, delivery, ownership and cleanup.
Add experimental opt-in Docker/Podman execution for stages and checks with explicit
mount/environment limits, local image preflight, consent before pulls, restricted
fallback diagnostics and owned-container cleanup. Update the isolation/security/
policy/projects/CLI docs and provide a minimal Dockerfile.

Author regression tests first, implement, then review independently. Requirements
and executable outcome mappings are in requirements.md and pipeline.json. Green
checks include both new suites, the full unittest suite, generated docs, strict
MkDocs, links and public-content/history scans. Only a separately opted-in real
container smoke may be skipped by default; fake runtime coverage is mandatory.
No product code or product tests have been written during planning.

Branch codex/isolated-execution was created from main then fast-forwarded to
origin/main bd6b824, incorporating completed dependency #16. Per the explicit user
checkout instruction, plans stay in the current checkout. The configured worktree
strategy is unchanged. Automatic runner handoff would allocate another checkout;
execute the full contract stages directly here after approval, or first obtain a
user choice permitting allocation. Do not claim pipeline launch is prepared for
the current path merely because validation/preflight succeeds.

Model routes: implement-tests, implement and review each use codex:gpt-6.1-sol,
high effort, no fallbacks. These plan-specific routes respect this base profile's
Codex-only provider set and do not alter global or project model settings. Offline
evaluation completed once. Advisories: selected routes below the evaluator's
recommended deep band; test/review share model lineage; no model catalogue present.
Review is a separate context, with requirements and tests first, not authorship
reasoning. Model account entitlement remains verified only on first actual request.

Permission mode observed during noninteractive preflight: restricted, from the
unattended default. The issue's opt-in container mode does not exist yet. No delivery
stage is selected. Only local logical commits are authorized; no push, PR, tracker
message, deployment or image publication is included.

Approve this plan and start implementation?
