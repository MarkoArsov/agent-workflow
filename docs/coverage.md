---
description: See automated coverage, real-host checks, and known limitations.
footer: reference
footer_order: 3
---

# Coverage and host checks

The automated suite uses temporary repositories, bare local remotes, isolated homes/configuration, and labeled provider/connector doubles.
It never installs into a contributor's real agent settings or publishes to a real account.

| Area | Automated evidence |
|---|---|
| Setup | Preview/apply, stale approval rejection, re-run preservation, project membership. |
| Customization | Per-project overrides, new skills, custom stages, provider prompts. |
| Runtime | Red/green evidence, frozen tests, scope/index guards, fresh retries/fallbacks, exact-session input, stalls, interrupted recovery. |
| Installation | Global/project modes, rollback, updates, owned removal, compatible fallback, plugin relocation. |
| Git | Selected worktrees, parked/read-only repositories, base guards, partial delivery resume. |
| Integrations | Paginated feedback, connector availability/patches, bot draft restoration, rule recurrence. |
| Fixtures | Actual Python checks and an HTTP request to a disposable local application. |
| Environments | Readiness, exported connection details, shared leases, release requests, and cleanup on failed startup. |

## Real-host smoke procedure

Vendor command-help and manifest validation are separate from model execution.
Local native Claude lifecycle and inventory checks have also been run in an isolated configuration.
A double passing does not prove account access, native discovery, or a provider's changing event format.

For each enabled host:

1. Use an isolated sample project and temporary host configuration.
2. Install the package or load the native plugin.
3. Confirm the setup skill is discoverable and resolves its effective file.
4. Create a project override; confirm direct invocation uses it.
5. Select a model available to that account and run a tiny implementation-only task.
6. Ask for a deliberate input pause; answer and verify the same session resumes.
7. Inspect actual evidence, usage fields, permission settings, and cleanup.

Account-authenticated generation, hosted GitHub publication, GitHub Pages deployment, and native Windows are not claimed by isolated tests.
See the local handoff for the specific checks performed for this release.
