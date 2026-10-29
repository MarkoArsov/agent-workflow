# Improve workflow guidance and learning

Status: revised proposal; awaiting implementation approval.
Revision: 29 October 2026; expands the comparison beyond the supplied attachment.
Previous complete proposal: `v1/`.
Lane: manual, in-session implementation in logical chunks, with test-first runtime changes.
No detached stages or automatic delivery are selected.

## Request and boundary

Improve this standalone package using the useful practices from a separately
maintained company workflow and the supplied comparison notes. Keep the package
generic and resolve project behavior from profiles, overrides, and references.
The supplied attachment describes a different, private workspace: it is research
input, not an instruction to edit that workspace. Its original remains outside
this public repository; private paths, identifiers, source text, and configuration
are intentionally excluded from these deliverables.

Only this repository is writable, using its configured current checkout strategy.
The source workflow and company plugin checkout are read-only research inputs.
No worktree, plugin update, installation, push, PR, tracker edit, or external
communication is included. Preserve existing plans and model-policy settings.
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

## Intended implementation files

| Files | Purpose |
| --- | --- |
| `skills/specify/SKILL.md` | Select shared guidance; require the documented defect facts and evidence-based request refinement. |
| `skills/implement/SKILL.md`, `skills/implement-tests/SKILL.md` | Load selected quality guidance consistently; clarify manual regression-first implementation. |
| `skills/peer-pr-review/SKILL.md`, `skills/request-review/SKILL.md` | Reuse review guidance read-only; explain intent before findings; offer concise title-and-links drafts. |
| `skills/review/SKILL.md` | Explicit evidence order and scoped checklist; retain direct/pipeline boundaries. |
| `references/quality-guidance.md` (new), `references/pipeline-contract.md` | One portable guidance contract; explain existing reference selection. |
| `skills/session-retro/SKILL.md`, `skills/session-retro/scripts/resolve.py` (new) | Optional retrospective procedure and standard package resolver. |
| `skills/pipeline-workflow/SKILL.md`, `skills/list-pipeline/SKILL.md` | Discover quality guidance and the optional retrospective without adding a stage. |
| `skills/add-rule/SKILL.md`, `skills/prune-context/SKILL.md` | Link verified retrospective findings to existing capture/pruning procedures. |
| `docs/review.md`, `docs/lanes.md`, `docs/maintaining.md` | Explain resulting user behavior and remove the bugfix documentation mismatch. |
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

Run the required offline evaluator once for this revision; `facts.json` now reflects
runtime work rather than documentation alone. `model-selection.json` is the revised
result, while v1 retains the prior complete snapshot. The project allows Codex and
Cursor, but currently has no catalogue or configured routes, so a valid automatic
recommendation may remain unavailable. Do not inspect credentials or refresh real
provider state just to prepare the plan.

The manual lane uses the active session after approval and does not switch models.
Runtime work proceeds test-first in logical chunks, followed by the package suite
and a final review against this plan. If the user chooses detached execution instead,
first select valid routes and prepare a full validated manifest; no detached run can
start with unresolved routes. This manual plan needs no pipeline.json, so
validate-plan/preflight do not apply.

Approve this plan and start implementation?
