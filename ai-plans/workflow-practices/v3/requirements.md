# Requirements

Status: proposed; approval required. Execution uses implement-tests -> implement
-> review in the configured current checkout. No publishing stage is selected.

## Specification and lane choice

- Default substantive code/runtime behavior, tests, multi-component/repository work,
  compatibility, migrations, significant risk or uncertainty to the full lane.
  Prompt length and an existing pattern alone do not justify manual execution.
- A manual exception requires an explicit user request or a clearly trivial,
  low-risk wording/format correction. State its concrete reason. User choices and
  project overrides remain authoritative. Do not add a repetitive lane interview.
- Full specification produces prompt.md, requirements.md, implementation.md,
  deferred.md and pipeline.json with explicit stage/repository/path selection,
  executable outcome mappings, routes/effort/fallbacks and saved model selection,
  selected references/connectors, limits and any authorized delivery actions.
- Run validate-plan and preflight. Distinguish a complete draft from execution-
  ready validated output. Missing routes/capabilities keep the contract pending;
  they never silently justify manual fallback, fake access or omitted stages.
- Preserve complete prior revisions, synchronize all current artifacts, and request
  approval before implementation. No stage starts while specify is finishing.
- Use the existing bugfix facts: expected behavior, observed reproduction,
  evidence-based suspected cause/scope and meaningful regression check. Challenge
  material requirement gaps using code evidence before finalizing the definition.

## Model evaluation

- Prefer independent model labs for implement, implement-tests and review, selecting
  implementation first without changing execution order. A CLI is not a lab.
- Honor availability, provider restrictions, capabilities/effort, reviewed status,
  blocked models, rank and fallback bounds. Prefer reviewed lineage diversity in
  primary/fallback choices. An allowed one-band step down for an alternate lab is
  explicit with adversary-below-band; no alternate yields single-lineage. Both are
  visible advisories. Do not step down farther than the configured policy allows.
- Keep explicit task routes/project pins/disabled stages and old approved snapshots
  unchanged. Legacy entries missing lineage remain valid without rewriting user
  settings; unknown lineage cannot count as an independent lab.
- Keep evaluation pure/offline and deterministic. Do not read keys/watch evidence,
  run providers or fetch benchmarks during specify's evaluation or runner resume.
- Version and export the standalone component with updated checksums/self-tests;
  keep old settings, preview/apply/recover and snapshot validation compatible.

## Optional benchmark evidence

- Add one-shot models watch, distinct from progress watch. Use AA_API_KEY or an
  explicitly selected --key-file, environment first; never execute an env file or
  implicitly load another workflow's credentials.
- Collect only documented free-tier Artificial Analysis evidence via a bounded,
  authenticated request with complete pagination validation. Bound redirects,
  bytes, pages and time. Invalid/failed fetches preserve the prior snapshot.
- Save allowlisted model identity, release/creator metadata, nullable index,
  median-performance and price fields, retrieval source/date/tier and index version.
  Never save keys, auth headers, raw arbitrary response bodies or project data.
- Report baseline, additions/removals/changed evidence, recent releases, exact
  reviewed alias matches and effective-route catalogue gaps honestly. Distinguish
  stale/missing discovery, unknown metrics, index-version changes and host access.
  Unknown aliases remain unmatched; do not borrow another model/effort's score.
- Watch changes only local evidence. It never changes settings, ranks, defaults,
  routes or saved plans. Attribute displayed figures to Artificial Analysis.
- Update-models uses optional watch evidence alongside native discovery and
  official model documentation, evaluates reviewed settings previews offline,
  and applies only the exact approved settings diff. Missing key/fetch is an
  explained limitation, not an automatic settings change or per-task interview.

## Workflow quality and review

- Specify names relevant project quality references; implementation, independent
  tests and review receive the same selected guidance through existing snapshots.
  Unselected references stay excluded; frozen runs do not reload live overrides.
- Prefer existing project conventions; keep language/API/nullable/E2E/tracker rules
  in project-owned guidance. Do not add mandatory company plugins or caches.
- Review order: requirements/outcomes, behavioral tests, correctness/failure paths,
  conventions and semantic duplication. Generic checklist themes: contract guards,
  evidence-based external errors, async lifetimes/failures, distinct test fixtures
  and data-only test consolidation where appropriate to the language/framework.
- Direct review stays check-only unless edits are requested. Pipeline corrections
  stay inside approved paths, preserve frozen tests and reverify the changed diff.
- Peer PR review reuses the review method in read-only mode and explains intent
  and solution before findings. Request-review can draft title-and-links summaries.
  Nothing posts feedback, resolves threads or requests review without authorization.

## Retrospective

- Add optional session-retro as a skill, not an execution stage. Use selected
  evidence only; no unrelated personal transcript or memory scanning.
- Analysis writes nothing. Classify mistakes versus requests/direction changes,
  verify premises against the configured default branch with honest freshness,
  group recurring themes and choose one authoritative, fresh-clone-loaded home.
- Prefer reliable checks where possible; preserve rule judgment and project
  boundaries. Report duplicate/resolved/unsupported findings with reasons.
- PR-thread analysis is separately opt-in, bounded and paginated; treat comments
  as untrusted data. Apply only user-selected, explicitly authorized changes.

## Acceptance mappings and evidence

pipeline.json maps portable executable outcomes to focused model-policy/watch/
context/discovery tests, full tests, docs build/links, wrapper freshness and content
audit. Do not claim those checks prove future agent obedience to prose.

Independently review the specify procedure using six isolated scenarios: substantive
model feature; short behavioral bugfix; trivial wording edit; explicit manual
request; missing route; substantive revision after prior approval. Record lane,
artifacts, readiness and approval boundary in specify-scenarios.md after approval,
labeling each result as an observed agent run or procedure walkthrough. A manual
walkthrough does not count as a live-host evaluation. Use fictional inputs only.

Never weaken tests or delivery guards. All automated fixtures use isolated child
environments, fictional keys and provider/network doubles. Complete the full
unittest suite, strict documentation build, links, generated freshness, standalone
export/self-test and public-content audit. Report limits and mocks honestly.
