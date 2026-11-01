# Reliable factory requirements

Status: approved; manual implementation and draft PR explicitly requested. Success means measurable completion and recovery
of approved work, with bounded resource use and understandable status. No claim
of a perfect or never-stopping agent. Genuine account, authorization, product or
publication decisions remain explicit stops.

## R1: One entry point and a stable runtime

Use implement-pipeline for new and existing tasks: allocate/reuse the saved owned
worktree, resolve canonical project/task/runtime once, and select run or resume.
Save a version/content fingerprint of the runtime and adapters outside the mutable
task source. All commands emitted for start/status/watch/cancel/retry target that
same runtime and project. A linked package source changing during a run never
silently changes worker semantics. Missing/incompatible pinned runtimes produce a
specific repair action. Task IDs/paths are not shell fragments. Handle relocation,
spaces, Windows .cmd launchers and concurrent tasks without nested worktrees.
Runtime installation/migration uses existing receipts and exact reviewed updates;
do not rewrite native accounts, global preferences or unrelated project profiles.

## R2: Failure classification and bounded correction

Use structured failures: verification, fixture_setup, transient_transport,
provider_authentication, provider_quota, unsupported_model, invalid_report,
product_decision, scope_violation, approval_required and cancellation_failure.
An agent narrative is evidence, not authorization. A keyword such as fixture does
not override a real account or requirements decision. Mechanical setup defects
settled by approved behavior enter a correction loop, rather than automatically
becoming a person-facing spec conflict. Permanent provider failures stop/re-route
according to approved routes without repeated identical attempts. Verified account
mismatch always stops before inference, including child processes and resume.

Save action/route/session/attempt identities, reason and evidence before each
transition. Bound autonomous corrections to two rounds per stage by default, with
one attempt per selected repair route and existing overall/tool/inactivity limits.
Optional known usage budgets stop before a new request when exhausted. Missing
cost/usage is unknown, not zero. Exhaustion reports attempted repairs and one next
action. Authentication/approval failures never become retry loops.

## R3: Repair tests while preserving their independent contract

Keep production implementation separate from test authoring. During test authoring,
run named fixture-health/setup checks as well as assertion-red checks; fail startup,
imports and missing dependencies as setup failures. Stage authors repair setup
before freeze. These checks must actually exercise helpers even when product APIs
are still absent. Support an explicit setup check phase with green semantics.

If implementation/review later proves a fixture defect, request test_fixture_repair
with test paths, reproduction and unchanged expected behavior. Route a bounded
repair to the approved test-authoring route in a fresh context. It can change only
declared test paths, cannot commit/switch branch, and cannot weaken assertions,
skip tests, remove cases or change expected product behavior. A separate checker
(the review route) compares requirements, old/new tests and reproduction before the
runner accepts the repair. Deterministic checks enforce paths, test identity and
skip/deletion guards; no AST/text comparison alone proves unchanged semantics.

Persist the original tests, repair diff and review result. Rerun fixture checks and
red proof where product behavior has not yet changed, or affected green/negative
checks when implementation exists; never fake pre-implementation red against
already changed production code. Invalidate old test hashes and dependent green
proof only after accepted review, freeze the repaired revision, and continue from
the interrupted implementation checkpoint. Reject requirement changes or weakening
with one concrete decision request. No blanket unfreeze in the implement stage.

## R4: Recovery and idempotent effects

Resume first checks exclusive task ownership, account, worktree/branch, pinned
runtime, approved contract and current diff. Revalidate retained stage output before
another model request. A report or commit timestamp cannot prove success. Reuse
current evidence only when command/contract/diff fingerprints match; otherwise run
only affected deterministic checks. Never repeat completed inference, commits,
pushes or PR creation because the worker lost its in-memory result.

Known repairs use exact reviewed commit IDs and a journaled previous baseline.
Unrecognized commits, staged/foreign edits, changed branch/membership or modified
requirements stop with a compact repair proposal. Never auto-approve a new baseline
based solely on a path whitelist. Keep recovery plans distinct from applying them;
ordinary resume automatically applies proven-safe cases and explains the rest.
An explicit cancellation remains stopped until a person requests continuation.
Retry means a new bounded attempt; answer resumes the exact pending input session.
No arbitrary saved-state editing by an assistant is part of normal operation.

## R5: Truthful events, status and watch

Add a versioned append-only event stream with run ID, monotonic sequence number,
UTC timestamp and stage/attempt IDs. Record start, route, tool start/end, check
start/end, repair/recovery, waits, decision, cancellation and terminal result.
Redact secrets; never stream prompts, credentials or arbitrary full tool output
by default. Save a small atomic live summary independently from large baseline
snapshots. Handle partial trailing records, restart, rotation, duplicate delivery,
slow consumers and concurrent viewers with bounded reads and retention.

Human-readable status/watch is concise; explicit --json provides a documented
summary/event schema and --verbose/diagnostics exposes detail deliberately. Publish
heartbeats every 15 seconds by default, showing elapsed and last provider/tool
activity separately. An idle provider, a long running tool and a live waiting worker
must look different. A heartbeat is never evidence of product progress. Emit an
inactivity warning before the bounded timeout. Show actual selected provider/model,
repair count, completed checks and exact next action. Clear stale errors after a
successful transition while retaining history. Stop and return a meaningful exit
code on completion, cancellation or required input. Default watch follows until a
terminal state; --seconds bounds observation without cancelling the worker.

A missing/stopped worker is determined through held ownership/process handles,
not PID-only signalling. Cancellation targets only owned process groups, confirms
termination, and records cleanup failures honestly. Repeated cancel is idempotent.
An error while stopping cannot leave status looking like healthy ongoing work.

## R6: Automatic tracking in the launching app

At setup, select tracking=auto|current-terminal|app-terminal|command-only|off (auto).
At start/resume return a structured tracking descriptor: task/run identity, argv,
cwd, canonical runtime/project references and an optional existing terminal handle.
Keep these as data, never interpolate untrusted issue/task text into a shell.

Implement host capability negotiation: open_and_run, open_only, current_terminal,
command_only, unavailable. Resolve the host from verified launch context/settings,
not the provider model. A headless Claude process is not proof of a Claude app panel.
Use supported host tools/extensions/action APIs. Do not drive keyboard shortcuts,
scrape private app databases or invent command-injection APIs.

With open_and_run, create/reuse one dedicated tracker terminal per task/run, start
only the watch command and verify the returned session or first event before saying
tracking is attached. With open_only, open the panel and provide a reviewed action
or exact safe command; say the command is not running yet. In a CLI, attach the
read-only watcher in the existing terminal after safely detaching the worker.
Unsupported/headless/cloud hosts still return useful tracking output. A viewer
failure must not restart/cancel the worker or consume model attempts. Closing the
viewer leaves the worker running. Reattach never creates duplicate workers or
unbounded tracker tabs. UI opening is done by the foreground host adapter, never
by detached model stages. No run-time permission bypass to open a panel.

Codex, Claude/VS Code and Cursor need separate capability adapters and native
smoke evidence. Supported documentation establishes terminals exist, not that an
arbitrary Python CLI can open-and-run a new host terminal. Report measured support
by host/version; auto mode gracefully falls back if a capability is absent.

## R7: Identity and preflight before paid work

Extend the existing private Claude guard into generic host-local identity/provider
configuration. Expected account selectors and config paths remain outside public
profiles and run exports; preserve existing business logins. Bind an opaque selector
fingerprint, verify identity before requests and block backend/credential overrides
that invalidate it. Where a host cannot expose account identity, report unavailable
verification and require the reviewed provider policy; never claim proof from --help.

Preflight validates toolchain, provider interfaces, identity, repository ownership,
contract completeness, repair routes, tracker capabilities and runtime fingerprint.
Use non-generative discovery by default; a paid health probe requires explicit
consent/budget and is cached by account/model/config fingerprint. A tracker fallback
is a warning, not a failed implementation preflight. Do not broaden permissions
or switch accounts to make a check pass.

## R8: Acceptance and quality

Keep Python 3.11+ standard-library installation/runtime, existing project profiles,
legacy snapshots and all three provider subsets. Migrate saved states explicitly
and idempotently, retaining originals. Existing paused #17 is a pilot after isolated
acceptance; never rewrite it just to make tests pass. No private reference bodies
or organization-specific automation enters the package. Follow frozen native/design
quality guidance and token-only UI styling. No new agent attribution trailers.

A disposable end-to-end factory scenario must author faulty fixtures, detect and
repair them through the independent path, validate tests, implement, verify, review,
crash/recover and finish exactly once with a continuously useful watcher. Cases
must prove wrong-account refusal, requirement-change pause, bounded exhaustion,
malformed/missing reports, terminal unavailability and cancellation cleanup.
Use fixture providers, temporary homes/remotes and deterministic clocks/events;
no network, real provider credentials or inference in default tests.
