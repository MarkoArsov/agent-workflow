# Requirements

Approval status: proposed, awaiting approval. Full lane; substantive runtime,
security, compatibility and recovery changes require a complete contract.

## Factory checkouts

F1. Add factory to profile validation/schema/setup. For a NEW unattended run
(--detach, --unattended, or existing non-TTY detection), select factory regardless
of its interactive strategy. Interactive runs preserve the profile strategy;
explicit factory also works interactively. Save effective strategy in task state,
binding, allocation receipt and claims. Resume never relocates an existing run or
silently adopts a different checkout. Legacy runs retain recorded semantics;
explicit rebind cannot discard in-progress files. Existing task-start allocations
are reused interactively; unattended fresh allocations use the factory backend.
A schedule entry point will pass the same unattended flag; do not build a scheduler.

F2. Use util.user_data()/projects/<project.id>/mirrors/<repo.id>.git and
worktrees/<task>/<repo.id>. Validate identifiers and resolved ownership paths.
Create an independent bare mirror from the effective remote fetch URL (no shared
object dependency on the user's clone). Refresh under a shared factory repo-ops
lock before each new task. Keep the existing project lock ordering consistent.
Use an atomic creation receipt so interrupted clones cannot be adopted as complete.
Record remote fetch/push identities in ignored origin.json; refuse project-ID or
URL mismatches before fetch, allocation or delivery. Reject credential-bearing
URLs with a repair message; never log URL passwords or persist tokens.

F3. Mirror fetches must not overwrite/prune active task branches. Start from the
verified remote base commit, not the user's local base. A --mirror clone stores
remote heads at refs/heads/<base>; replace its broad fetch refspec after initial
clone with +refs/heads/*:refs/remotes/origin/*, seed/refresh that namespace, and
keep task heads outside fetch destinations. Fetch --prune only that namespace.
Pin the chosen base commit in the receipt; refresh never rebases an active task.
Missing remote/base and existing unowned task paths/branches fail without adoption.

F4. Every selected read-only companion gets a task-owned detached checkout from
its mirror base. Never use a user's companion checkout or branch it. Factory runs
must ignore user-clone edits/HEAD/index for scope guards and fingerprints; continue
guarding their own writable and companion snapshots. Do not change existing
non-factory parked-checkout enforcement. Demonstrate user edits and branch switches
mid-run survive and do not fail the factory run.

F5. Delivery remains host-only from factory worktrees to the effective real push
URL, with explicit HEAD:refs/heads/<branch>, existing size/path/evidence guards and
crash reconciliation. Never rely on mirror remote.origin.mirror=true during push.
Keep the existing GitHub identity/delivery interface; do not implement other issues.
Worktree resolution must accept mirror Git common directories only with validated
factory receipts, not weaken arbitrary repository-membership checks.

F6. worktrees includes local and factory allocations and mode/ownership information.
clean [--older-than 7d] removes only owned, unlocked, clean worktrees of tasks
recorded cancelled or confirmed merged/closed. Age is measured from terminal_at
(UTC elapsed time); no age flag means no age restriction. Complete/failed/paused/
escalated/needs_approval alone never qualifies. Do not infer closure from age or
query/update a tracker implicitly. Retain unknown/unpushed/dirty work for recovery.
Remove via Git under repo-ops lock, then prune; preserve mirrors, task branches,
receipts and evidence. Refuse symlink escapes, forged ownership and active claims.
If no merged/closed lifecycle record exists, cleanup supports cancelled tasks now
and accepts future recorded terminal states without building PR synchronization.

## Container execution

C1. Extend reviewed plovi.toml/schema/template/effective binding with [isolation]:
mode='none'|'container' (none), runtime='auto'|'docker'|'podman' (auto), image=''
(required when container mode), network='on'|'off' (on), mount_harness_config=[]
(only supported provider IDs), api_key_env=[] (explicit variable names only).
Validate each field separately: generic relative-glob validation is inappropriate
for image IDs, enums and environment names. Unknown keys remain errors. Freeze
resolved mode/runtime/image ID/mount/environment names in state; redact values.
Never snapshot API key values in the binding or evidence.

C2. A common execution wrapper covers every agent attempt, custom command stage,
check, verify and check environment command. Runtime, guards, commits, pushes and
PR calls remain host-side. Preflight and resume must use the same effective mode.
Container mode requires factory-owned checkout metadata even for interactive use;
legacy/local allocations require a fresh task rather than unsafe remounting.
Mount all selected writable task checkouts read-write at identical absolute paths,
companions read-only and only their required mirrors read-only. These are the only
project data mounts. Never mount the user's checkout/home, package root, SSH agent,
Docker socket or evidence directory. Supply frozen prompts over stdin. Read-only
Git operations work with GIT_OPTIONAL_LOCKS=0; stage writes to Git metadata fail
as intended by existing runner ownership rules. Prove status/diff/read-only Git
operations with a real container smoke; tests creating their own Git fixtures use
the writable task tree or container temporary storage.

C3. docker/podman run --rm --pull=never uses an explicit working directory, stdin
forwarding, no TTY, --network=none when off. Linux maps host UID/GID; rootless
Podman uses keep-id as needed. HOME is a fresh container-only temporary directory.
Do not forward the host PATH; use the image PATH. Inner environment is allowlisted
LANG and explicit API key names, plus controlled HOME/PATH/Git flags and provider
config locations. Image defaults are outside this host allowlist guarantee and
must be documented. Keys pass by name using a sanitized runtime process environment,
never as argv NAME=value, files, captured logs or evidence. Tests inject canaries.
Harness config mounts opt in individually and read-only at the corresponding
provider location inside temporary HOME; no host config writes or broad fallback.
Document that mounted tokens and allowlisted keys are readable by the agent.

C4. runtime=auto tries Docker then Podman with bounded daemon probes. Inspect the
local image and pin its immutable ID; missing images never pull implicitly. An
explicit one-time --pull-isolation-image consent permits the named image pull;
then inspect and probe each selected harness --help inside it. Checks need their
own tools from the user image. No host CLI requirement for contained providers.
When configured container execution is unavailable, trusted unattended execution
fails before any stage. Restricted execution may proceed on the host only for
runtime/image unavailability, with a saved and displayed degraded boundary; do not
silently change trusted interactive runs or retry a failed contained command on the
host. Invalid policy fails in all modes. Windows container mode reports unsupported;
restricted host fallback is explicit in diagnostics. Factory mode remains portable.

C5. Track container identity per invocation and explicitly stop/remove owned
containers on cancellation, timeout, tool stall and interrupted-run recovery.
Killing the Docker client alone is insufficient. Never remove unrelated containers.
Keep existing output parsing, red/green classification, tool timeout and evidence
semantics. Check environment services run within the boundary: lease setup/teardown
must not execute arbitrary project commands on the host. For shared services use a
task-scoped runtime network when network=on, removed with the owned resources;
network=off rejects cross-container service requirements before execution.

## Docs and verification

D1. Add docs/isolation.md under Configure and templates/isolation/Dockerfile,
minimal image with Git, Python and explicit harness/toolchain installation guidance.
Update projects/security/policy/execution/recovery/CLI and generated references.
Explain factory vs provider restrictions vs container boundaries, network needs,
login-token readability, writable workspace risks and host delivery. Container
mode is experimental on macOS/Linux. No claim of egress filtering, protection
against hostile container engines/images, or isolation for mode=none.
Include the design-required What changes for your workflow callout. Use existing
styles/tokens, lowercase plovi, concise actionable errors and no new visual theme.

D2. Required new suites are tests/test_factory_checkouts.py and
tests/test_container.py using WorkspaceTest and provider doubles. No network,
real harness/account/config access or real container engine by default. Temporary
bare remotes prove refresh and delivery. Fake Docker/Podman record argv, sanitized
environment and inner commands while executing locally (a simulation, not a security
test). Add one separate real-engine test gated by PLOVI_TEST_DOCKER=1; it uses an
already built local image, network off and no credentials, tests mounts, Git reads,
UID and cancellation. Its default skip is explicitly approved only for that test.

D3. pipeline.json maps outcomes to assertion red and green regression checks and
full package/docs/generated/link/public-content checks. New-API tests use guarded
capability assertions so missing APIs produce FAIL/AssertionError, never import
errors as red. Future test names are contractual, not claims they exist or ran.
Local logical implementation commits follow verification; publication and external
communication require a separate explicit request.

## Evaluator and project setup (same branch, same delivery)

E1. Restore this project's intended provider subset to Codex and Claude in
.plovi/project.json and PROJECT_WORKFLOW.md, preserving every unrelated profile
field. The restored initial stage routes match the pre-existing dual-agent branch:
Sonnet tests with Sol fallback; Sol implementation with Opus fallback; Opus review
with Sol fallback; default Sol with Opus fallback. Remove planner-added Sol/high
facts.routes. No native agent preferences, user/global model settings, credentials
or other workflow installations may be changed. CLI installation and discovery
are evidence only; never manufacture account-access confirmations.

E2. Introduce validated stage_facts for selected executable AI stages: optional
kind, size, risk, uncertain, complexity (simple, routine, complex), test_files and
test_lines. Fields inherit task facts when absent; reject unknown stages/fields,
invalid enums/types and nonfinite or negative counts. Stage-specific values replace
the inherited values per key, never spread one stage's difficulty into another.
Existing demanding_stages remains supported. Explicit complex/uncertain/high-risk
work can still require a deep model for that affected stage. Four files or 300
estimated test lines alone becomes an advisory, not automatic deep/high selection.
Keep these numbers as reviewable size evidence; never relabel a difficult task as
routine merely to force a cheaper route. Update boundary tests for the new expected
behavior and preserve all other model-policy coverage.

E3. Separate capability band from effort selection. Use the smallest reviewed,
supported effort for the effective stage difficulty: simple -> simple mapping,
routine -> balanced mapping, complex/uncertain -> demanding mapping. High risk
alone can require the deep capability band while retaining balanced effort when
complexity is routine and uncertainty is false. Unknown effort metadata omits the
argument with an explanation; never invent supported values or automatically select
xhigh/max/ultra. Automatic candidate selection still prefers the lowest adequate
band, obeys capabilities/provider restrictions and preserves the lineage preference
and fallback bounds. Describe this as a resource-use policy, not a measured price
optimization: actual subscription usage/cost remains unknown without evidence.

E4. Add suggested_routes as optional per-stage preferences in task facts. Suggestions
are validated like routes but cannot pin a route, promote unavailable/unreviewed
models, lower the required band, defeat diversity, or override user/project pins.
A suitable suggestion may break remaining ties only after capability, provider,
lineage and reviewed rank decisions. Existing facts.routes and configured pins stay
backward-compatible explicit overrides. Freeze provenance for every stage as
user-task-route, project-pin, global-pin, retained-default or adaptive-selection;
when legacy data cannot distinguish an origin, say legacy-explicit-route rather
than invent user authorization. The specify skill must put planner ideas in
suggested_routes and reserve routes for attributable user/project instructions.
Reference origin in plans; metadata documents the origin and does not prove approval.

E5. Explain each stage in machine-readable snapshot details and compact CLI output:
effective stage facts and their source, required band, effort mode/mapping,
selected route source, eligibility/exclusion reasons, unresolved conditions,
provider/lineage constraints and ordered fallbacks. Do not claim a retained pin or
default is an adaptive recommendation. Missing catalogue output must say whether
routes were retained or no route could be resolved. Bound explanation detail for
large catalogues and keep default CLI output short; verbose output can show more.
Do not include private paths, environment values or credentials. Evaluation remains
deterministic and offline, without provider/network/model calls.

E6. Version the evaluator for changed semantics; preserve valid 1.0/1.1 snapshot
hashes and exact frozen routes, including the plan running these improvements.
Do not re-evaluate or rewrite an approved running task during implementation.
Update independent export/selftest behavior and document downstream compatibility.
Do not copy package changes into any installed external workflow.

E7. After the improved evaluator exists, this project's routine selection should
be adaptive rather than permanently pinned to restored stage routes. Move the
restored preference arrays into .plovi/models.json defaults and use explicit
adaptive_stages for implement-tests, implement, review and default to release
legacy profile pins. Keep profile route arrays for compatibility if appropriate;
prove the effective settings have both providers and no pins for those stages.
Use medium as a routine preference only where reviewed model/host evidence supports
it; otherwise omit effort. Do not invent catalogue data to make the migration green.
A missing catalogue retains valid defaults with a precise warning; a newly required
capability with no eligible route remains unresolved. The current implementation
plan keeps its frozen inherited routes; project adaptation affects later tasks.

E8. Add tests/test_model_routing_revision.py using WorkspaceTest plus existing
fixture helpers. Cover stage isolation, file/line threshold advisories, independent
band/effort decisions, planner suggestion vs genuine pins, origin explanations,
provider exclusions, unsupported effort, empty/invalid/stale catalogues, old snapshot
validation, deterministic no-IO evaluation and dual-provider project defaults.
Use synthetic model names and catalogues; native discovery smoke is read-only and
separate from tests. No inference or entitlement is implied by fixture results.

E9. Update references/model-routing.md, specify/update-models skill guidance and
model docs/generated references. Show adaptive vs pinned vs retained routes clearly,
explain usage uncertainty, and give stage-specific examples including a large but
routine test suite. All earlier package/docs/public-content checks still apply.

## Checkout interpretation safeguard

Clarify in generic planning guidance that referring to a repository or source
checkout does not itself prohibit configured task worktrees. Honor explicit
checkout restrictions and project setup choices. Verify the guidance and existing
task allocation behavior using isolated fixtures.
