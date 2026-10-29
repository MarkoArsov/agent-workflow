# Improve workflow guidance and learning

Status: implemented; local verification passed; delivery in progress.
Revision: 29 October 2026; explicit user choice of Codex-only manual execution.
Previous complete proposals: `v1/`, `v2/`, and `v3/`.
Lane: manual. Selected AI stage: implement only, in the active Codex session.
No independent implement-tests/review stage or detached runner. The user subsequently authorized commit/push and a draft PR.
Keep the detailed prompt, requirements, implementation and deferred documents as
manual task references. The former pipeline.json is archived under v3/ and removed
from the active plan directory. Evidence is recorded in planning-checks.md.

## Request and boundary

Improve this standalone package using the useful practices from a separately
maintained company workflow and the supplied comparison notes. Keep the package
generic and resolve project behavior from profiles, overrides, and references.
The supplied attachment describes a different, private workspace: it is research
input, not an instruction to edit that workspace. Its original remains outside
this public repository; private paths, identifiers, source text, and configuration
are intentionally excluded from these deliverables.

Only this repository is writable, using its configured current checkout strategy.
The user explicitly authorized setting this project's agents to Codex only; that
profile edit and matching PROJECT_WORKFLOW.md update are applied now. This does
not restrict the package's general support for other harnesses in other projects.
Project pipeline defaults remain unchanged; implement-only is this task's choice.
The source workflow and company plugin checkout are read-only research inputs.
No worktree, plugin update, installation, tracker mutation or unrelated external
communication is included. Verified normal push and draft PR are explicitly authorized. Preserve existing plans and model-policy settings.
Commit this planning set locally. After approval, commit logical implementation
changes locally as repository instructions require.

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
manual lane appropriate. This task is an explicit user-requested manual exception and uses implement only.
That choice does not weaken the planned full-contract default for other substantive
work or the package's cross-harness support.

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
| `skills/worktree-start/SKILL.md` | Support planning-time checkout selection before a full manifest exists; reuse it at execution handoff. |
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
10. Add localization scenarios: an existing task worktree, two concurrent tasks,
    dirty shared checkout, explicit current-checkout policy, and multi-repository
    shared planning. Verify plan destination and same-checkout handoff without
    creating duplicate branches, moving user edits or requiring a manifest before
    planning can begin. Label observed fixture behavior versus procedural guidance.

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

## Model recommendation and execution

This project's allowed harness is Codex only. Evaluate only implement for this
manual revision. The recommendation is informational: use the active Codex session
without starting a detached provider or switching its model. Preserve the evaluator
snapshot in model-selection.json, but do not create a new active pipeline manifest.
No Cursor or Claude route is eligible for this project. Native model preferences,
installed harnesses, machine defaults and other projects are unchanged.

Implement owns tests, assertion-level regression evidence, product/guidance edits,
verification and a final self-review in the same session. No independent test-author
or reviewer session is selected. All previously named test/build/link/export/content
checks still apply; test coverage and safety boundaries are not reduced by the lane
change. The earlier executable check definitions remain available in
v3/pipeline.json as reference only, not a contract to run.

Use the configured current checkout and trusted execution defaults. Repository-
required local commits follow successful verification. No push, PR, installation,
benchmark request with a real key or external communication is authorized by this
revision. The broader feature implementation and separate verified commit/push/draft-PR
handoff were subsequently authorized by the user and are now complete locally.


## Implementation and delivery authorization

The user explicitly invoked implement, commit-and-push and draft-pr after the plan
was completed. That authorizes the broader feature implementation and its verified
normal push/draft-PR handoff, superseding the earlier no-publication boundary for
this task. Stay in the configured current checkout, preserve existing branch work,
use no force push, add no reviewers/messages, and reuse the matching PR if present.
The task branch already has an open PR; its remote-only CI fix was preserved with
a normal merge before implementation. Do not alter prior complete plan snapshots.
