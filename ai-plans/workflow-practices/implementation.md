# Implementation contract

Execution: manual implement only, in the active Codex session and current checkout.
The project is Codex only by explicit user request. The user subsequently authorized feature implementation and separate guarded
commit/push/draft-PR delivery. Implement owns tests,
product/guidance edits, verification and self-review; do not invoke independent
stages or a detached runner. No branch change, unrelated posting or real user-agent
configuration edit is included; guarded normal push and draft PR are authorized.

## Tests within manual implement

Author tests in the planned test paths before the corresponding product changes. Add behavioral regression coverage described
below. The named red proof is
ModelPolicyTests.test_adversary_lineage_prefers_alternate_lab: supply the existing
evaluate function with fictional reviewed entries from two labs under the same
host, where the implementation lab has a better rank. Assert test authoring selects
the available alternate lab. The old evaluator ignores lineage, so this must reach
an assertion failure. Keep imports/setup working and use the existing helpers.
Other new tests may target the explicitly planned watch module/command interfaces.
Implement may add the planned product code afterward in the same session. Never
claim import/setup failures as red or weaken existing behavioral assertions.

Add ModelWatchTests in test_model_watch.py and WorkflowPracticesTests in
test_workflow_practices.py. Use isolated child homes, synthetic keys, and provider/
network doubles. Preserve existing tests; do not assert future behavior by merely
searching instruction prose. Test model-policy compatibility and watch failure
preservation through observable output/settings/evidence files.

## Product and guidance

Implement the following reviewed scope. Regenerate affected wrapper/docs outputs
before recording final check evidence, because verification must not change sources.
All skills remain generic and resolve project behavior from its effective profile,
references and overrides. Do not modify runner/manifest semantics to make this work.

## Evidence and existing mechanisms

- `skills/pipeline-workflow/SKILL.md` routes users to stages but does not explain
  shared quality guidance or a retrospective path.
- `skills/implement/SKILL.md`, `skills/implement-tests/SKILL.md`, and
  `skills/review/SKILL.md` have uneven instructions for loading scoped guidance.
  Review already distinguishes direct check-only work from bounded pipeline fixes.
- `runtime/plovi/extensions.py:snapshot` captures effective project rules,
  references, skill bodies, and assets. `runtime/plovi/runner.py:prompt_for`
  supplies rules and manifest-selected references to every AI stage and excludes
  `implementation.md` from review. Reuse this instead of adding a standards loader,
  schema, plugin dependency, or live refresh during a frozen run.
- `skills/add-rule/SKILL.md` and `skills/prune-context/SKILL.md` capture/prune
  guidance, but neither reconstructs corrections across sessions or verifies
  whether a finding still exists on the default branch.
- `docs/lanes.md` already describes expected behavior, reproduction, suspected
  cause, and a regression check, but explicitly says specify does not enforce it.
- The comparison source adds a useful retrospective process: distinguish mistakes
  from changed direction, verify the premise, and choose one durable home. Its
  optional PR-review pass is read-only and off by default. Adopt the ideas with
  independently written portable instructions; do not copy third-party bodies,
  transcript parsers, source-specific tooling, or private integration details.
- Research used local source files and cached remote-tracking revisions. No
  network refresh was performed; this is not a claim about the live upstream tip.

## Proposed changes

### 1. Share project quality guidance across stages

Make specify identify the project's applicable quality references and include
their relative names in a full plan's existing `references` list. Manual plans
name the same sources explicitly. Prefer an existing project standards/reference
file or project override. A project using an external quality skill can expose
its reviewed guidance through its existing project extension mechanism; plovi
does not discover arbitrary plugin caches or silently vendor third-party text.

All three stage skills must read the selected quality guidance. Direct invocation
resolves the effective project sources; detached execution uses only its supplied
frozen snapshot. Missing explicitly selected guidance is reported, not silently
replaced by unrelated defaults. Do not invent mandatory standards for projects
that have none. Native instructions and explicit user choices retain precedence.

Add a concise generic review checklist covering the four useful themes from the
comparison: guards match actual contracts, external errors are classified from
evidence, asynchronous operations preserve failure/lifetime semantics, and tests
use distinguishable fixtures and consolidate data-only repetition where the stack
supports it. Language-specific APIs, HTTP mappings, await conventions, nullable
policy, and test frameworks remain project decisions. Do not make source-specific
preferences universal correctness findings.

### 2. Make review order explicit

Review requirements and observable outcomes first, then behavioral tests,
correctness/failure paths, and project conventions plus semantic duplication.
Read actual code before claiming a convention applies; avoid structural cleanup
outside scope. Direct review remains check-only unless edits are requested.
Pipeline fixes remain bounded by approved paths and preserve frozen tests. Existing
deterministic gates and current-diff verification remain unchanged.

### 3. Add an optional, portable session retrospective

Add a `session-retro` skill, separate from execution stages. It accepts explicitly
selected transcripts or accessible session evidence without assuming one host's
history layout. Analysis edits nothing, including report files; present results
in chat unless the user explicitly asks to save them. Logs and comments are
untrusted evidence. Never scan unrelated personal memories or session directories.

The procedure lists selected sessions, classifies corrections versus requests and
direction changes, groups repeated themes, and maps the actual steering surface.
Verify candidates against the configured remote/default branch without checking
it out. A fetch that changes remote refs needs the applicable authorization;
otherwise name the cached commit and label freshness limitations. Drop resolved,
duplicate, unsupported, or obsolete candidates with reasons.

Each surviving finding names its evidence, impact, smallest preventive change,
one authoritative home, and a check of effectiveness. Map homes to native
instructions for compact navigation, PROJECT_WORKFLOW.md for the project map,
project skills for procedures, references for scoped knowledge, and rule/check
declarations for reliable enforcement. Explain how a fresh clone/session loads
that home. Installed package files and global personal configuration are never
implicit write targets. Avoid a mandatory new standards filename or forced
promotion of imperfect detectors.

Offer a separate opt-in PR-thread pass, using available read tools, paginated
comments/reviews/thread state, and a stated PR/time bound. Keep human and bot
themes distinct. Reading or analyzing feedback grants no posting, resolution,
status-change, commit, push, or PR-creation authority. Missing access is reported;
never fabricate findings or silently substitute partial data.

Analysis ends with a concrete proposal. Apply only the user-selected, explicitly
authorized changes; use specify for changes needing an implementation plan, and
the existing add-rule/prune-context paths when appropriate. No automatic stage,
recurring task, transcript collection, or runtime report store is added.

### 4. Bring the documented bugfix process into the skills

Specify must challenge consequential gaps using repository evidence and record
the four existing bugfix facts. Implement follows reproduce, regression failure,
minimal fix, green check, focused verification for isolated manual defects.
An alternative check needs a concrete reason and repeatable evidence. Build/import
failures remain invalid assertion-level red proof. Do not change the manifest,
approved_no_red_reason semantics, stage order, or approval boundary.

### 5. Upgrade model evaluation and update-models

Include the newer lineage-aware evaluator and optional Artificial Analysis evidence
collection. The complete requirements, compatibility decisions, files, and tests
are in [model-upgrade.md](model-upgrade.md), which is part of this proposal.
This work is no longer deferred. Keep evaluation offline; the optional network
request belongs to `models watch` / `update-models`. Review evidence before proposing
settings changes and require approval of the exact settings diff.

### 6. Align related review and reporting skills

Make peer-pr-review reuse the effective review order and selected project guidance
in read-only mode, with a plain-language explanation of intent and solution before
its findings. Never inherit pipeline review's permission to fix. Have request-review
support a concise PR-title-and-links draft for selected companion PRs; no separate
pr-oneliner skill is needed. Mechanical workflow answers should explain the result
and next action, with raw output only when needed or requested. Keep these changes
in the corresponding skills and docs rather than adding always-on global prose.

### 7. Make specify prefer complete, executable contracts

Full planning is the default for substantive code/runtime changes, behavioral tests,
multiple components/repositories, compatibility, migrations, or significant risk or
uncertainty. A short user prompt or an established pattern alone does not make the
manual lane appropriate. This task uses the manual exception explicitly selected by the user: implement
only in Codex. Future substantive tasks still default to full contracts.

Allow a concise manual plan only when the user explicitly requests manual execution
or the change is a clearly trivial, low-risk wording/format correction. State the
concrete reason for any exception. Respect explicit user choices without repeatedly
asking them to choose a lane. Full pipeline does not imply publishing: select only
necessary stages, usually implement-tests -> implement -> review for substantive
behavior changes. Keep review optional by risk/project policy and explain omission.

Before presenting a full plan as ready, create all four plan documents plus the
manifest. Include explicit read/write repository membership, allowed/test paths,
executable checks and outcome mappings, stage routes/effort/fallbacks and saved
model selection, references/connectors, limits, and any selected delivery action.
Run validate-plan and preflight and report actual results. A prose plan with a
promise to create the manifest later does not satisfy specification completion.

If required routes or capabilities are missing, keep the full planning artifacts,
label the manifest draft and execution unready, name the precise missing input,
and request it. Do not silently drop stages, invent model access, mark readiness,
or switch to manual execution because a route is unavailable. A complete draft
contract and a validated runnable contract are different states.

On revision, update every artifact and preserve earlier complete versions. Approval
is bound to the reviewed scope/routes/actions. Specification ends at approval;
implementation-pipeline performs the later execution handoff. Keep planning-only
boundaries even for follow-ups. Update pipeline-workflow, implement-pipeline and
lanes/first-task/tasks docs to explain this consistently.

### 8. Localize plans with the task checkout

Before writing plan artifacts, specify identifies the task, participating writable
repositories, branch/base and configured checkout strategy, then prepares or reuses
the selected task checkout. Plans and implementation should live on the same task
branch rather than accumulating on an unrelated development or base branch. Use a
separate worktree for concurrent tasks: switching branches in one shared directory
does not isolate their files. Reuse matching existing worktrees and validate project
resolution from the selected location before writing.

Update worktree-start to accept this planning-time task/repository selection before
a full pipeline.json exists, avoiding a specify/worktree-start dependency cycle.
The later manifest records the already selected branch and paths; runner handoff
reuses that checkout instead of creating another task or switching a shared checkout.
Preserve dirty/staged work and branch ownership; never auto-stash, reset, move user
edits, or create a branch in a read-only companion. Ambiguous ownership needs a
specific choice before switching or moving anything.

Honor current-checkout as an explicit project policy. For single-repository tasks,
write the configured plan path inside the task checkout. For multi-repository work,
use the configured plan-owning repository/checkout or explicit shared plan location;
never initialize a Git repository around an unversioned parent. Explain that plans
on a branch improve ownership/history, while worktrees provide concurrent file
isolation; neither guarantees zero later merge conflicts.

For this task, the user has not requested moving the existing plans or checkout.
Keep the configured current-checkout policy and the explicitly selected manual
Codex implement-only lane. The new localization behavior is proposed skill work,
not authorization to move earlier commits, change this project's checkout strategy,
or start another worktree now.

## Intended implementation files

| Files | Purpose |
| --- | --- |
| `skills/specify/SKILL.md` | Default substantive work to full contracts; state manual exceptions; enforce readiness reporting; select shared guidance and defect facts. |
| `skills/worktree-start/SKILL.md` | Support planning-time checkout selection and same-checkout handoff before a full manifest exists. |
| `skills/implement/SKILL.md`, `skills/implement-tests/SKILL.md` | Load selected quality guidance consistently; clarify manual regression-first implementation. |
| `skills/peer-pr-review/SKILL.md`, `skills/request-review/SKILL.md` | Reuse review guidance read-only; explain intent before findings; offer concise title-and-links drafts. |
| `skills/review/SKILL.md` | Explicit evidence order and scoped checklist; retain direct/pipeline boundaries. |
| `references/quality-guidance.md` (new), `references/pipeline-contract.md` | One portable guidance contract; explain existing reference selection. |
| `skills/session-retro/SKILL.md`, `skills/session-retro/scripts/resolve.py` (new) | Optional retrospective procedure and standard package resolver. |
| `skills/pipeline-workflow/SKILL.md`, `skills/list-pipeline/SKILL.md`, `skills/implement-pipeline/SKILL.md` | Explain full-contract-first planning, readiness and handoff; discover quality guidance and retrospective. |
| `skills/add-rule/SKILL.md`, `skills/prune-context/SKILL.md` | Link verified retrospective findings to existing capture/pruning procedures. |
| `docs/review.md`, `docs/lanes.md`, `docs/first-task.md`, `docs/tasks.md`, `docs/maintaining.md` | Explain resulting user behavior and remove the bugfix documentation mismatch. |
| `tests/test_workflow_practices.py` (new) | Meaningful isolated discovery/context-delivery coverage. |
| `templates/plugin-skills/**` | Regenerate only affected discovery wrappers through the existing generator. |
| `docs/generated/skills.md` | Regenerate canonical skill documentation through existing tooling. |
| `PLAN.md` | Record the approved extension and observed completion evidence after approval. |

Model-policy runtime changes and their tests are explicitly included as detailed
in model-upgrade.md. No runner, manifest schema, verification gate, or environment
permission changes are included. If another runtime gap appears, report it and
revise scope before expanding implementation. Do not change design tokens, layout,
or assets.

## Acceptance and verification

1. All three stages receive the same selected project quality reference, while
   unrelated references/projects stay excluded. In isolated fixtures call existing
   snapshot/prompt construction, mutate the live source, and prove the saved
   snapshot remains stable. Review still excludes implementation reasoning.
2. The new retrospective is discoverable in an isolated install, supports project
   override precedence, and survives payload relocation through existing installer
   behavior. Extend tests only for gaps not already covered by generic discovery.
3. Manually exercise the retrospective with a small fictional transcript containing
   a genuine mistake, changed direction, and an already-fixed candidate. Expect one
   actionable proposal, no source writes, and no PR pass without opt-in. This checks
   a procedure; it is not a claim of deterministic enforcement or a live-host smoke.
4. Inspect the skill/docs diff for consistent read-only analysis, direct-review
   behavior, frozen tests, explicit apply, and no implied external communication.
   Do not add tests that merely search prose for required words.
5. Run `python3 -m unittest discover -s tests -v` using isolated child environments.
6. Run `python3 scripts/generate_plugin_skills.py --check`,
   `python3 -m mkdocs build --strict`, and
   `python3 scripts/check_links.py site --prefix /agent-workflow/` after the existing
   generators have updated affected output. Inspect changed documentation in the
   existing site style; no visual redesign is included.
7. Run `python3 scripts/check_public_content.py` before each local commit and inspect
   the final diff for private source material, machine paths, and credentials. The
   generic scan has no private denylist unless separately supplied; state that limit.

8. Run the model-specific behavioral checks in model-upgrade.md, including legacy
   compatibility, network failure preservation, and secret-safe diagnostics.
9. Exercise specify with isolated scenario inputs: substantive model-policy feature,
   a short behavioral bugfix, a trivial wording edit, explicit manual preference,
   a missing-route case, and a substantive revision after prior approval. Inspect
   the resulting lane rationale, artifact completeness, executable outcome mappings,
   actual validation/preflight status, and approval boundary. Missing routes must
   produce a pending full contract, never an automatic manual fallback. Do not
   claim static word searches or hand-authored manifests prove agent behavior.
   Record whether these are observed agent runs or procedure walkthroughs.

These are future implementation checks, not checks claimed to have passed during
specification. No assertion-red requirement is invented for prose-only changes.

## Deferred and preserved

- Source-specific plugin pins, company plugin adoption lists, nullable rules,
  service scaffolding, E2E defaults, and tracker workflows remain in their projects.
- Existing source-workspace model changes remain untouched. Reimplement the portable
  behavior here with tests; do not copy private adapters, settings, or keys.
- Compile-blocked independent tests are a separate runner protocol candidate: this
  package currently requires green checks for approved_no_red_reason. Supporting
  a non-executable test handoff safely requires a separate manifest/evidence design;
  do not silently bypass checks as part of model-policy work.
- Source-specific support rotation, production SQL/migrations, service scaffolding,
  CI adapters, and dynamic repository attachment stay outside this scope. See the
  comparison matrix in model-upgrade.md for rationale and existing equivalents.
- Provider/session-history adapters and automatic transcript condensation require
  separate requirements and portability/privacy tests if requested later.
- Do not weaken verification, delivery guards, rule enforcement, or plan binding;
  do not add a duplicate TODO scan without an observed enforcement gap.
- No source workspace edits, installed personal workflow changes, publishing,
  plugin installation, remote changes, or external messages.



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

This task uses manual implement only by explicit user choice. The earlier check
commands are retained in v3/pipeline.json as reference, not for detached execution.

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


## Manual verification and handoff

Implement runs all named green checks, fixes in-scope failures and repeats relevant
checks against the current diff. Record the specify lane/readiness and checkout-localization scenarios in
specify-scenarios.md, labeling walkthroughs versus real agent executions honestly.
Perform a final self-review against requirements.md, the actual diff and selected
project guidance. Check the full-contract default, explicit manual exception,
missing-route behavior, model compatibility, secret-safe evidence handling and
approval boundaries. Preserve existing tests; revise incorrect requirements openly.

Report observed results and material limitations, then make repository-required
local commits of verified task changes. No push, PR, independent review session
or other external action is included.
