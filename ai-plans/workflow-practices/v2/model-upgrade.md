# Model-policy upgrade and broader comparison

Part of the revised workflow-practices proposal; not implementation approval.
The original proposal is preserved under v1/. All source-workspace files remain
read-only, including their uncommitted model-policy edits.

## Findings

The package currently ships model-policy 1.0.0. The comparison source declares
1.1.0 and adds lineage-aware stage selection, lineage-diverse fallbacks, watch.py,
an alias map, and an update-models watch step. These changes are present locally,
including uncommitted files; their presence is evidence of intended behavior,
not proof that they passed tests or are ready for direct redistribution.

Three concrete adaptation gaps matter:

- The source makes lineage mandatory. Existing plovi custom registry entries do
  not have it; copying that validator would break valid settings on update.
- The source documentation describes a broad evidence snapshot, but normalization
  currently keeps only identity, release date, creator, and the intelligence index.
  Specify and test the fields actually saved rather than making unsupported claims.
- Source-specific credential paths, user agent, creator filters, and exact alias
  assumptions do not belong in this package. Unmapped or unverified aliases must
  stay unknown rather than borrowing another model/effort variant's score.

Official API verification on 29 October 2026: the free language-model endpoint is
`GET /api/v2/language/models/free`, authenticated with `x-api-key`. Its documented
response includes pagination, model identity and release metadata, headline and
capability indices, median performance, and input/output pricing. Values can be
null. Record the intelligence-index version so comparisons can expose changes in
measurement. Source: [Artificial Analysis API reference](https://artificialanalysis.ai/data-api/docs/reference).
No authenticated request was made and no real credential was read during planning.

## A. Lineage-aware offline evaluator

1. Add reviewed lineage metadata (the model's lab, independent of its hosting CLI)
   to bundled registry entries. Hosting the same lab's model in two CLIs does not
   count as independent model lineage. Never infer lineage solely from provider.
2. Select implementation first, then test authoring, then review, irrespective of
   input stage order. Test authoring avoids implementation's lab; review avoids
   both. Other stages keep their existing suitability and effort rules. Do not
   reorder the pipeline's execution stages.
3. Prefer an available reviewed alternate lineage at the required capability band
   over a better-ranked model from an already selected lab. Prefer lineage diversity
   in ordered fallbacks too; preserve provider restrictions, blocked models, effort
   compatibility, maximum fallback limits, and deterministic tie-breaking.
4. Match the source's explicit policy: if no different lineage exists in band,
   test authoring/review may use one band lower, with `adversary-below-band`.
   If no qualifying alternate exists, keep the suitable in-band choice and report
   `single-lineage`. Both are visible advisories, not execution blockers. Never
   silently step down more than the declared policy permits. This tradeoff must
   appear in the proposed routes before approval.
5. Preserve explicit task routes, project pins, explicitly disabled stages, and
   saved approved snapshots. Report limitations without silently rewriting pins.
   A different CLI/family from the same lab is not sufficient diversity evidence.
6. Keep legacy custom registry entries valid without rewriting settings. Resolve
   lineage from an exact reviewed registry match where available; otherwise retain
   an explicit unknown lineage and disclose that diversity cannot be established.
   Unknown is never counted as an independent lab. New lineage values validate as
   stable slugs. Do not guess that every arbitrary family string names a lab.
7. Bump the portable component version, preserve validation of 1.0 snapshots from
   their recorded routes/hash, and update standalone self-tests and export hashes.
   Evaluation remains pure: no network, subprocess, credential lookup, watch-file
   access, or extra model call on specify/run/resume.

## B. Optional Artificial Analysis evidence

Add `plovi models watch` as an explicit one-shot evidence refresh. It is distinct
from the existing task-progress watch command and does not install an automation.

- Read `AA_API_KEY` from the environment. Optionally accept `--key-file <path>`
  for an explicitly selected local env-style file, with environment taking
  precedence. Parse only the named assignment; never source/execute the file.
  No implicit lookup in another workflow's credential files and no copying keys
  into this repository, settings proposals, exports, or snapshots. The portable
  component accepts caller-supplied paths rather than hard-coding a company name.
- Use urllib with bounded request/overall time, response-size, and page limits.
  Request only the documented free endpoint; no paid fallback, model inference,
  unrelated service, or provider account probe. Prevent credential forwarding
  through redirects to another origin. HTTP errors and response bodies are
  untrusted; diagnostics must not echo headers, key values, or raw response bodies.
- Validate complete pagination and response shape before replacing evidence.
  Failure, timeout, bad JSON, malformed types, page-limit exhaustion, or missing
  key leaves the previous snapshot byte-for-byte intact and reports a concise
  actionable reason. Do not make corrupt/partial output look like mass removals.
  A successful legitimate empty response is distinct from a malformed response.
- Normalize explicitly allowlisted identity, release, creator, evaluation index,
  median performance, and price fields, retaining nulls as unknown. Save source,
  retrieval time, index version, and response tier. No API key, arbitrary raw
  response, provider auth, transcript, or project source goes into evidence.
- Use existing machine-local model storage and atomic replacement under its
  existing lock; no tracked project writes. Retain one current snapshot and compare
  with the previous value before replacement; no unbounded historical archive.
- Report baseline versus subsequent refresh correctly: a baseline is not a list
  of newly launched models. Report new/removed slugs and changed evidence for labs
  used by effective routes, plus recent releases with a tested UTC-date window.
  Unknown release dates are unknown. Expose an index-version change rather than
  presenting across-version score differences as measured improvements.
- Add a reviewed, versioned provider/model-to-benchmark alias table. Exact mappings
  must distinguish model versions and effort variants; unresolved aliases remain
  unmatched. Do not populate the table by copying the source's unverified IDs.
  Preserve entries for existing supported registry models only when verified;
  otherwise ship the explicit unmatched state. Arbitrary project route IDs work
  without a benchmark alias and can be assessed through settings registry sources.
- Compare effective primary routes and pins, not merely package defaults, with
  the host catalogue. Distinguish absent IDs from missing/stale discovery and
  advertised from proven account access. Benchmark presence never proves access.
- Attribute all displayed benchmark figures to Artificial Analysis and include
  the source/date; API price or speed does not measure host subscription cost or
  the user's stage performance. Use only the actual stored fields in reports.

## C. Update-models procedure and docs

The skill keeps its current inspect -> confirm scope/providers -> native refresh
-> reviewed assessment -> preview -> exact-diff approval -> apply/read-back flow.
Insert optional watch evidence after native discovery when the user has configured
the key. Without a key or a successful fetch, explain the limitation and continue
using host discovery plus official model documentation; preserve existing settings.
If a snapshot exists, label it cached with its date. No extra credential interview
or API call is introduced on every specify.

AA evidence helps the user/agent review registry assessments; it does not directly
rewrite rank, suitability, effort, model defaults, fallbacks, or saved plans.
Benchmark scores alone do not establish task suitability. Evaluate proposed
settings offline with --settings, show old/new routes and diversity advisories,
and require the existing exact-diff approval before applying changes. Refresh/watch
is not settings approval. No periodic watch job is included.

Update model-routing reference, model docs and CLI reference, specify's explanation
of recommendations, pipeline-workflow and list-pipeline discovery, and generated
skill wrappers. Correct the stale statement that plovi ships no registry: it ships
reviewed seed assessments, while host availability remains locally discovered.
Update PLAN.md only after implementation is approved.

## Additional intended paths

- `runtime/plovi/model_policy/{core.py,commands.py,storage.py,__init__.py}`:
  selection, compatibility, watch command arguments and evidence orchestration.
- `runtime/plovi/model_policy/{registry.json,policy.json,selftest.py}`:
  lineage metadata, adversary policy, portable behavioral contract.
- `runtime/plovi/model_policy/{watch.py,aliases.json}` (new): bounded evidence
  collection/reporting and explicit reviewed alias metadata.
- `skills/update-models/SKILL.md`, `references/model-routing.md`,
  `docs/models.md`, `docs/cli.md`: user procedure and documented behavior.
- `tests/test_model_policy.py`, `tests/test_model_watch.py` (new): offline
  behavioral regression coverage. Reuse current isolated test helpers.
- `scripts/export_model_policy.py`, `tests/test_release.py`, and
  `runtime/plovi/cli.py` only if required for portable export, payload validation,
  or host-specific argument plumbing; no unrelated refactor or schema changes.

## Behavioral checks and execution order

First author focused tests and observe assertion failures for missing behavior,
then implement in two logical chunks: evaluator compatibility and watch evidence.
Tests use fictional model IDs and synthetic keys in isolated child environments;
no test reads real user config, contacts AA, probes real providers, or installs to
the actual machine. Test missing features without treating import errors as red.

1. Evaluator: two/three labs across the same/different CLIs; input order invariant;
   same-lab aliases; band versus rank; permitted one-band step; no alternate;
   fallback diversity; pins; unknown/missing legacy lineage; blocked/unavailable/
   provisional entries; every host subset; unchanged effort/maximum rules.
2. Compatibility: legacy settings read and preview/apply/recover still work;
   old snapshots remain valid; tampering still fails; no settings bytes change
   from evaluate/watch; a saved run retains its prior routes after an update.
3. Watch transport: mocked single/multiple pages; bounds; HTTP auth/rate/server
   errors; redirects; timeouts; invalid JSON/schema; null fields; interrupted write;
   previous snapshot preservation. Compare files before/after, not just flags.
4. Watch reporting: first baseline; additions/removals; same-version changes;
   index-version change; date window; reviewed/unmapped aliases; effective pins;
   stale/missing host catalogue. Distinguish unknown from zero/unavailable.
5. Secret handling: environment precedence, explicit key-file parsing without
   execution, missing key, and error bodies containing a synthetic key. Assert the
   key is absent from stdout/stderr, saved evidence, exports, and proposals.
6. Patch network, subprocess and credential lookup to fail during evaluation;
   patch provider execution during watch. Prove each path's boundary independently.
7. Export to a temporary directory, verify checksums with --check, and run
   `python3 -m model_policy.selftest` from the export parent with isolated env.
   Existing package release tests verify inclusion and relocation.
8. Run the complete unittest suite, strict docs build, link checks, generated
   wrapper checks, and public-content scan specified in plan.md. Report mocks as
   mocks. A real authenticated API smoke is optional and separate, using a user-
   configured key after implementation; never claim one occurred from fixtures.

## Broader comparison and disposition

| Source practice | This proposal |
| --- | --- |
| Lineage evaluator, diverse test/review routes and fallbacks | Include with backward compatibility and advisories. |
| AA watch, alias map, update-models evidence | Include as optional evidence, using portable credential paths and complete tested normalization. |
| Shared quality guidance, review order, retrospective | Include in plan.md; preserve project-specific decisions. |
| Peer review orientation and reuse of review method | Include, read-only. |
| Concise mechanical answers and title/link review sharing | Include in existing workflow/request-review skills; no new one-liner command. |
| Manual regression-first bugfix posture | Include; docs already describe it. |
| Fresh processes, exact-session input resume, current-diff evidence | Already implemented; retain existing lifecycle tests, do not rewrite. |
| Interrupted verified-stage reuse | Already implemented and covered by runner lifecycle tests. |
| Non-executable compile-blocked independent test handoff | Defer: differs from this package's green-check no-red contract; needs a separately reviewed manifest/evidence change. |
| Post-merge readiness verdict, batch smoke and production change range | Existing generic test-on-staging is narrower; defer expansion of its public contract and environment permissions. No company CI/SQL adapter is imported. |
| Support rotation, production migration generation, IDE commands | Project extensions; no generic package addition without a portable use case. |
| Dynamic company repository attachment | Keep explicit configured repository membership; no organization-specific discovery or mirrors. |
| Publish command, guarding pushes, tracker confirmation | Existing package mechanisms remain authoritative; no permission relaxation. |

This matrix records reviewed themes, not a claim that every source file or every
private integration has been audited. It makes exclusions explicit so future
requests can select the next workstream without guessing what was overlooked.
