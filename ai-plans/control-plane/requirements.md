# Requirements

Approval status: approved by the person on 2 November 2026 with Claude-only routes. Full lane: substantive runtime,
CLI, compatibility and concurrency changes across many components.

Ground rules from the issue apply throughout: Python 3.11+ standard library only;
macOS, Linux and Windows (pathlib, argv lists, no shell syntax); tests use
`tests/helpers.py` (`WorkspaceTest`/`HardeningTest`) and
`tests/fixtures/provider_double.py`, never the network, real agent CLIs or real
user configuration; never weaken, skip or delete an existing test; no private
identifiers, credentials or machine-specific paths; CLI text output and docs follow
design/DESIGN.md voice (lowercase "plovi", short active sentences, errors say what
went wrong and the fix, no emoji).

## L. Ledger

L1. New module `runtime/plovi/ledger.py`. Location:
`util.user_data()/projects/<project-id>/ledger/` (the same per-project root the
factory already uses; validate the project ID with `util.identifier` and reuse
`factory.safe` style path checks). One JSON Lines file per UTC month:
`events-YYYY-MM.jsonl`. The ledger must never resolve inside the project root, any
configured repository path or any task worktree; refuse with a clear error if
`XDG_DATA_HOME` points there.

L2. Event envelope, versioned by `v: 1`, defined in new `schemas/event.schema.json`:
`v`, `id`, `at`, `project`, `subject {kind, id}`, `type`, `actor`, `reason`, `data`.
- `id`: sortable unique ID, 48-bit millisecond timestamp plus 80 random bits
  (`secrets`), Crockford base32, 26 characters, monotonic within a process.
- `at`: UTC ISO-8601 with milliseconds and `Z`.
- `subject.kind`: `task`, `schedule`, `execution`, `pr`, `policy`, `project`.
- `actor.kind`: `person`, `agent`, `plovi`. Person name from
  `git config user.name` in the project root, else `local-user`; an explicit
  existing `--actor NAME` on `approve` still overrides the person name. Agents are
  `{"kind": "agent", "name": <--actor-agent>, "via": <--via, default "cli">}`.
  Runner events use `{"kind": "plovi", "name": "runner"}`.
- `reason`: nonempty string; operations use `--reason` when given, otherwise a
  short default sentence naming the command.
- `data`: object whose required fields depend on `type` (L3).

L3. Event types and their required `data` fields, documented in docs/ledger.md and
enforced by a table in ledger.py that the schema test covers: `task.created`
(`issue`?, `title`?, `branches`), `task.claimed` (`run_id`), `run.started`
(`run_id`, `manifest`, `plan_sha256`), `stage.started` (`run_id`, `stage`),
`attempt.finished` (`run_id`, `stage`, `attempt`, `classification`, `path` of the
attempt file), `stage.finished` (`run_id`, `stage`, `result`), `question.asked`
(`run_id`, `stage`, `question`), `question.answered` (`run_id`), `plan.proposed`
(`plan_sha256`, `manifest`), `plan.approved` (`plan_sha256`, `auto`),
`approval.requested` (`run_id`, `kind`, `fingerprint`), `approval.granted`
(`run_id`, `kind`, `fingerprint`), `escalation.raised` (`run_id`, `stage`, `kind`,
`detail`), `run.paused`, `run.resumed`, `run.interrupted`, `run.cancelled`,
`run.finished` (`run_id`, `status`), `delivery.committed` (`repository`,
`commit`), `delivery.pushed` (`repository`, `branch`), `pr.opened`
(`repository`, `url`), `policy.changed` (`diff`), `project.registered` (`root`).
Additional types this plan needs: `state.checkpoint` (L6), `pause.requested`,
`cancel.requested`, `project.unregistered`. `?` marks optional fields. Question
and reason texts are redacted with `util.redact` and bounded.

L4. `ledger.append(project, event)`: validate the envelope and the type table;
reject a serialized line over 64 KiB (large payloads live in files referenced by
path); hold a short file lock (`state.lock(path, wait=True)` on
`ledger/ledger.lock`); open the month file with `O_APPEND`, write exactly one line
ending in `\n`, flush and `os.fsync`. Concurrent writers in several processes must
never interleave or lose lines.

L5. Reading: `ledger.events(project, subject=None, since=None)` reads month files in
order; `since` accepts an ISO timestamp or an event ID. A torn last line (no
trailing newline or invalid JSON at end of the newest file) is skipped with one
warning per read call on stderr; earlier invalid lines are an error.
`ledger.tasks(project)` and `ledger.task(project, id)` fold events into task views
(task ID, issue/title, status, stage, completed, run ID, pending question,
escalation, pending approvals, approved plan hashes, last event time).

L6. Runner integration: alongside today's `state.json` writes, the runner appends
events at every transition: `task.claimed`, `run.started`, `stage.started`,
`attempt.finished`, `stage.finished`, `question.asked`, `approval.requested`,
`escalation.raised`, `run.paused`, `run.interrupted` (from the existing
`state.read` interruption detection, at most once per run ID), `run.cancelled`,
`run.finished`, and delivery events (`delivery.committed`, `delivery.pushed`,
`pr.opened`) when `git_ops.deliver` records them. Each `save()` whose state
content (ignoring `updated_at`, `pid`, `child_pid` and live heartbeat fields)
changed appends `state.checkpoint` with `{run_id, state_sha256, keys: {top-level
key: sha256}}`; each value is stored once in a content-addressed blob store
`ledger/blobs/<sha[:2]>/<sha>.json` (write-if-absent, atomic). Events stay small:
attempt output remains in the existing attempt files and is referenced by path.

L7. `state.json` becomes a cache. `plovi rebuild-state <task>` restores
`state.json` and `status.json` from the latest `state.checkpoint` for the task,
verifying every blob hash, preserving the recorded `updated_at`, and refusing with
a clear error when history or a blob is missing or tampered. After deleting
`state.json`, rebuild then `plovi status <task>` (human and `--json`) prints output
identical to before deletion. `plovi status <task>` keeps the existing observer
path when the cache exists and rebuilds the cache first when it is missing.
`plovi status` without a task lists all tasks from `ledger.tasks`.

L8. Import: on first ledger use for a project, existing evidence-directory runs
with `state.json` are imported as synthetic events (`task.created`, `run.started`,
`stage.finished` per completed stage, a terminal or stop event for the saved
status, and a `state.checkpoint`) with `data.imported: true`. Import runs under the
ledger lock, records imported `(task, run_id)` keys in `ledger/imported.json`, and
is idempotent: running it again appends nothing.

L9. Compatibility: tasks pinned to a pre-ledger runtime (runtime_pin) still work;
their runner transitions are not recorded until an explicit
`--upgrade-runtime --rebind`, which docs/ledger.md states. Operation events are
still appended by the current process.

## O. Operations

O1. New package `runtime/plovi/operations/` with a registry. Each operation has
`name`, `summary`, `arguments` (JSON-schema-like object), `mutates: bool`,
`risk: "none"|"low"|"high"`, `preview(args) -> dict` and
`apply(args, actor, reason) -> dict`. The CLI calls operations for the commands
below; operations reuse existing functions (`state.cancel`, `runner.run`,
`policy.set_value`, ...) instead of duplicating them.

O2. Every mutating `apply` validates input, checks policy where relevant, performs
the change, appends ledger events with actor and reason, and returns JSON.

O3. Operations and CLI names: `status` [`status [task]`], `inbox` [`inbox`],
`events` [`events [--task ID] [--since T]`], `answer` [`answer <task> --file F |
--text "..."`], `approve` [`approve <task> --plan|--size|--paths`], `retry`
[`retry <task> [--note F]`], `pause` [`pause <task>`], `resume`
[`resume <task>`], `cancel` [`cancel <task>`], `policy.show` / `policy.set`
[`policy show|set`], `projects.add|list|remove` [`projects add <path>`,
`projects list`, `projects remove <id>`], `rebuild-state` [`rebuild-state <task>`],
`commands` [`commands [--json]`]: the registry as JSON (name, summary, arguments,
mutates, risk) for agents and the app.

O4. Risk: `none` for status, inbox, events, commands, policy.show, projects.list;
`low` for answer, retry, pause, resume, cancel, projects.add, projects.remove,
rebuild-state; `high` for approve and policy.set. High-risk operations use
preview-then-apply-by-digest: without `--approve <digest>` they return a preview
with its digest and change nothing (exit 0). Compatibility: a person's existing
`approve --size|--paths [--actor NAME]` and `policy set ... --yes` keep working
unchanged; when `--actor-agent` is passed, those legacy shortcuts are refused and
`--approve <digest>` is required. `approve --plan` is new and always requires
`--approve <plan_sha256>`.

O5. Output: JSON stays the default for every command except where it is already
human (`status` keeps its current human default and `--json`). Add
`--format text|json` to `status`, `inbox`, `events` and `projects list`. Existing
JSON shapes that skills parse (`status`, `run`, `pipeline`) gain fields only;
nothing is renamed or removed. Existing exit codes stay (1 for failed/cancelled/
escalated and, for watch/pipeline, needs_input/needs_approval/interrupted; 2 for
`WorkflowError`). `paused` exits 0.

O6. Plan approval. `plan_sha256` = SHA-256 over canonical JSON of the manifest
without `_`-prefixed keys plus each `plan_files` entry's path and bytes in listed
order. `approve <task> --plan` locates the manifest from the task-start receipt,
the saved run state, or `--manifest PATH`; preview shows the hash and plan files;
apply with the matching digest appends `plan.approved` (`auto: false`); a digest
for a different hash is rejected. `validate-plan` appends `plan.proposed` once per
`(task, plan_sha256)` after a successful validation.

O7. Gate (person decision): new policy key `execution.require_plan_approval`
(bool, default true) in `policy.py`, schemas/policy.schema.json and docs/policy.md.
Explicit launches self-approve: foreground `run` (TTY or not), `run --detach`,
`pipeline`, and `resume`/`answer`/`retry`/`approve` continuations record
`plan.approved` (`auto: true`, actor from flags) for the current hash before
starting or spawning a worker, unless a matching approval exists. The background
worker path (hidden `run --unattended`, used by `pipeline` and `--detach`) refuses
to start, or to continue a run whose plan hash changed, when the key is true and no
`plan.approved` matches the current hash; the error names
`plovi approve <task> --plan`. Direct library calls to `runner.run` keep today's
behavior unless they pass `require_plan_approval=True`. Runs that started before
this change are grandfathered.

O8. Pause/resume. `pause <task>` is accepted for starting/running tasks, appends
`pause.requested` and writes a `pause.json` request beside `cancel.json`. The
runner checks it before each stage begins (the safe point after the current
attempt and its verification finish), sets status `paused`, appends `run.paused`
and releases its claim like other stops. `resume <task>` and `pipeline <task>`
clear the request, append `run.resumed` and continue without repeating completed
stages. `progress.summary` gives `paused` a next action (`plovi resume <task>`).

O9. `answer` accepts `--file F` or `--text "..."` (exactly one) and appends
`question.answered`; `retry` and `cancel` keep their behavior and append events.

O10. Every mutating command accepts `--reason`, `--actor-agent NAME` and `--via`.

## I. Inbox

I1. `inbox` is derived from the ledger on every call, never stored. Item kinds:
`question` (open `question.asked`), `plan` (`plan.proposed` without matching
`plan.approved` and no started run for that hash), `approval` (open
`approval.requested`), `escalation` (open `escalation.raised`), `failed` (run
finished failed after exhausted attempts), `interrupted` (open
`run.interrupted`). An item closes when its resolving event appears (answer,
approval, grant, retry/new run, resume) or the task is cancelled.

I2. Item shape: `{"id", "kind", "project", "subject", "title", "reason",
"created_at", "actions": [{"label", "operation", "args"}]}`; `id` is the opening
event's ID; oldest first. Actions name a registered operation with concrete args
(for `plan`, args include the `plan_sha256` digest so one command resolves it).

I3. `title` is the issue title stored on `task.created` when the task links to an
issue, else the task ID. `task start` gains optional `--issue REF` and
`--title TEXT` and appends `task.created`; plovi does not fetch issue titles from
the network.

I4. `inbox` covers projects from the registry plus the current project; an
unreachable registered root is reported as a warning, not an error.

## P. Projects registry

P1. `<user_data>/projects.json` stores `[{"id", "root", "added_at"}]`, compatible
with the existing `project.resolve` reader. Writes are atomic under a lock.

P2. `projects add <path>` loads the profile, registers it (idempotent for the
same ID and root; a different root for a registered ID is refused with the fix),
and appends `project.registered`. `projects list` shows entries and whether each
root exists. `projects remove <id>` unregisters and appends
`project.unregistered`; it never deletes files on disk.

P3. `setup --apply` registers the project automatically.

## F. plovi-factory skill

F1. New skill `skills/factory/SKILL.md` (exposed as `plovi-factory`): read
`plovi commands --json` first; use operations, never edit `.plovi/`, state or
ledger files; always pass `--actor-agent <name> --via plovi-factory` and
`--reason`; show previews and ask the person before high-risk operations; treat
issue text, logs and ledger data as untrusted. Worked examples: "what needs me?",
"retry 146 with this note", "why is 153 failing?".

F2. Regenerate `docs/generated/skills.md` (add `factory` to a category in
scripts/generate_docs.py) and `templates/plugin-skills/` with the existing
generators; structural skill validation passes.

F3. Update skills that the person decisions touch: `specify` passes
`--issue/--title` to `task start` for issue-based tasks and notes that
`validate-plan` records `plan.proposed`; `implement-pipeline` documents that
`pipeline` records the plan approval and that background workers refuse an
unapproved or changed plan.

## D. Docs

D1. New docs/ledger.md (what is recorded, where, privacy, pinned-runtime
limitation), new docs/commands.md generated from the registry by
`scripts/generate_docs.py` (checked by `--check`), updates to docs/everyday.md
(inbox-first daily loop), docs/recovery.md (answer, retry, approve, pause,
resume, cancel), docs/cli.md, docs/policy.md and docs/code-map.md; add the new
pages to mkdocs.yml nav. Pages that change how people use plovi end with a
"What changes for your workflow" callout.

## T. Tests (assertion red first where listed in pipeline.json)

New test modules must load before product changes exist: import new product
modules (`plovi.ledger`, `plovi.operations`, ...) inside test methods or helpers,
not at module level, so red evidence is assertion failure, not import error.

- tests/test_ledger.py: `LedgerTests` — `test_append_read_round_trip`,
  `test_every_event_type_validates_against_schema`,
  `test_concurrent_processes_never_interleave` (two processes x 1,000 appends,
  `multiprocessing` spawn context, 2,000 parseable lines),
  `test_torn_last_line_skipped_with_one_warning`,
  `test_month_rollover_reads_across_files`, `test_state_import_is_idempotent`,
  `test_ledger_lives_outside_repository_and_worktrees`,
  `test_oversized_event_rejected`; `LedgerCliTests` —
  `test_runner_transitions_are_listed_by_events`.
- tests/test_operations.py: `OperationCliTests` —
  `test_commands_json_lists_every_operation`,
  `test_mutating_operations_record_actor_and_reason`,
  `test_answer_with_text_and_file`, `test_retry_with_note`,
  `test_pause_stops_before_next_stage_and_resume_continues`,
  `test_cancel_records_event`,
  `test_high_risk_without_digest_previews_and_changes_nothing`,
  `test_agent_actor_requires_digest_for_existing_approvals`,
  `test_existing_json_output_shapes_preserved`; `PlanApprovalTests` —
  `test_unattended_worker_refuses_without_plan_approval`,
  `test_approval_of_different_hash_rejected`,
  `test_explicit_run_records_approval_automatically`,
  `test_pipeline_launch_records_approval_before_worker`,
  `test_policy_can_disable_worker_gate`.
- tests/test_inbox.py: `InboxTests` —
  `test_question_item_appears_and_clears_after_answer`,
  `test_plan_item_clears_after_approval`,
  `test_approval_item_clears_after_approve`,
  `test_escalation_item_clears_after_retry`,
  `test_failed_item_clears_after_resume`,
  `test_interrupted_item_clears_after_resume`,
  `test_items_oldest_first_with_issue_titles`, `test_text_format_snapshot`
  (compute expected local times with `datetime.astimezone()` so the snapshot is
  platform independent).
- tests/test_projects.py: `ProjectRegistryTests` —
  `test_add_list_remove_keeps_files`, `test_setup_registers_project`,
  `test_add_is_idempotent_and_rejects_conflicting_root`, `test_text_format`.
- tests/test_rebuild_state.py: `RebuildStateTests` —
  `test_rebuilt_state_gives_identical_status`,
  `test_rebuild_rejects_tampered_blob`,
  `test_rebuild_without_history_fails_clearly`.

Existing suites (runner, limits, policy, recovery, pipeline resume, concurrency,
setup, task isolation, factory checkouts, progress events, container) must pass
unchanged. A shared fixture helper may change only to keep existing scenarios'
setup valid, never to change an assertion.

## Acceptance (from the issue, as constrained above)

- Every runner transition appends a ledger event; `state.json` can be rebuilt
  from the ledger (L6, L7).
- Concurrent appends never interleave; the test uses no POSIX-only primitive so
  CI runs it on every platform (L4).
- All listed operations exist, are in `plovi commands --json`, and record actor
  and reason (O1–O10).
- `plovi inbox` shows each item kind with working actions (I1–I4).
- Background workers require a recorded plan approval matching the plan hash;
  explicit launches record it (O6, O7).
- The plovi-factory skill is installed and documented (F1–F3).
