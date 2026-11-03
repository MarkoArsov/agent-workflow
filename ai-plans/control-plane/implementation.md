# Implementation guide

Suggested order and anchors. Requirements.md is the contract; this file only
points at existing code to reuse.

## 1. Ledger core (`runtime/plovi/ledger.py`, `schemas/event.schema.json`)

- Root: reuse `factory.root(project)` / `factory.safe` for
  `<user_data>/projects/<id>/ledger`. Check containment against `project.root`,
  every `project.repo_path(...)` and the configured worktree directory.
- Lock: `state.lock(root / "ledger.lock", wait=True)`; it already handles
  `fcntl`/`msvcrt`. Append with `os.open(path, O_WRONLY|O_APPEND|O_CREAT, 0o600)`
  (add `O_BINARY` on Windows), one `os.write` of the encoded line, `os.fsync`.
- Schema validation: write a small validator for the subset the schema uses
  (type, required, properties, additionalProperties, enum, pattern, maxLength,
  const) plus the per-type data table. Do not add a dependency.
- IDs: keep `_last` per process to make IDs monotonic within the same millisecond.
- Torn line: compare the newest file's last byte with `\n`; emit the warning via
  `warnings`/stderr once per `events()` call.
- Blob store and `state.checkpoint` live here (`checkpoint(project, task, state)`,
  `restore(project, task)`); `progress.MAX_BYTES`-style bounds are not needed
  because blobs are content-addressed and deduplicated.
- Import (`import_existing(project)`): iterate
  `state.directory(project, "*")` siblings under the evidence directory.

## 2. Runner hooks

- `runner._run_locked`: the local `save()` closure is the single choke point.
  Extend it to call `ledger.checkpoint` and to emit typed transition events by
  diffing the previous and current status/stage/completed/pending fields
  (mirroring how `reporter.emit("state_changed")` is already gated). Emit
  `attempt.finished` next to the existing `reporter.emit("attempt_finished")`.
- `claims.acquire` success → `task.claimed`.
- `state.read` interruption branch → `run.interrupted` once per run ID.
- `git_ops.deliver` → delivery events from the recorded `state["delivery"]`.
- Pause: add a `paused()` check beside the existing `cancelled()` check at the top
  of the stage loop; keep `cancel.json` semantics unchanged.
- Gate: add `require_plan_approval=False` to `runner.run`; the CLI worker path
  (`run --unattended`) passes the effective policy value. Compute `plan_sha256`
  in one helper (operations/plans.py or manifest.py) used by `validate-plan`,
  `approve --plan`, launches and the gate.

## 3. Operations (`runtime/plovi/operations/`)

- `__init__.py`: `Operation` dataclass, `REGISTRY`, `register`, `actor(args,
  project)`, `digest(preview)`, `catalog()` for `commands --json` and docs.
- Modules by area: `tasks.py` (status, events, answer, approve, retry, pause,
  resume, cancel, rebuild-state), `inbox.py`, `policy.py` (wrap
  `policy.effective`/`policy.set_value`; split preview and apply so the diff is
  computed without printing or prompting when a digest is used), `projects.py`,
  `catalog.py` (commands).
- `cli.py`: keep the parser explicit; add the new subcommands and flags; route
  the listed commands through `operations.call(name, args)`. Respect
  `runtime_pin.dispatch`: new commands (`inbox`, `events`, `pause`, `projects`,
  `commands`, `rebuild-state`) are not forwarded to pinned runtimes;
  `answer --text` is normalized to a temporary `--file` before forwarding.
- `entrypoint.launch`: record the auto approval before spawning the worker.

## 4. Inbox, projects, setup

- Inbox folds `ledger.events` per project; collect projects from
  `projects.json` plus the current project.
- Projects: `util.user_data() / "projects.json"`, atomic `write_json` under
  `state.lock(user_data()/"projects.lock", wait=True)`.
- `setup.apply` → `projects.add` after a successful apply.
- `tasks.start` → optional `issue`/`title`, `task.created` event.

## 5. Skill, docs, generators

- `skills/factory/SKILL.md` follows the frontmatter and resolver block used by
  other skills; run `python3 scripts/generate_plugin_skills.py` and
  `python3 scripts/generate_docs.py` to regenerate outputs.
- `scripts/generate_docs.py`: add `factory` to "Core workflow", a FAST_LOOKUP
  row for "See what needs you", and generation of docs/commands.md from
  `operations.catalog()`.

## Verification

Run the named checks in pipeline.json. The full suite and docs checks are the
issue's pre-PR command list: unittest discover, mkdocs build --strict,
check_links site, generate_docs --check, check_public_content --history.

## Revision 2 anchors

- G1: `factory.allocate` (base selection before `git worktree add`), with the
  local receipt from `tasks.receipt_path`/`tasks.owned_checkout`. Fetch from the
  source clone into `refs/plovi/tasks/<task>/<repo>` in the mirror; check
  ancestry with `git merge-base --is-ancestor`. Keep task heads outside the
  mirror's fetch destinations (requirements F3 of the isolated-execution plan).
- G2: `cli.py` preflight / `--dry-run` branch currently calls `git_ops.prepare`
  for factory strategies; replace with a read-only feasibility report.
  `factory.receipt` raises the ownership error.
- G3: `manifest.validate`, `schemas/pipeline.schema.json`,
  `policy.execution` (where restricted `allowed_tools` are built from checks).
- G4: `providers.Events.line` / `classify` / `failure_kind`; runner route loop
  (`if classification in {"authentication", "quota", "model"}: break`); pause
  status from O8; `recover_resume.validate_artifacts`; inbox kinds.
- G5: `providers.Events.report`.
