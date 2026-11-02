Closes #18.

## What changed

- An append-only ledger in your user data folder records every run, stage,
  attempt, question, approval, escalation, delivery, pause, cancel and policy
  change, with who did it and why. `state.json` is now a cache that
  `plovi rebuild-state <task>` restores from the ledger.
- One operations layer is the only way to change state. `plovi commands --json`
  lists every operation with its arguments, whether it changes anything, and its
  risk. High-risk operations preview first and apply by digest.
- `plovi inbox` lists everything waiting on a person, oldest first, each with the
  command that resolves it.
- `plovi projects add|list|remove` registers the projects plovi manages; setup
  registers new projects automatically.
- New `pause`, `events`, `answer --text` and `approve --plan` commands; `status`
  without a task lists every task from the ledger.
- Every changing command accepts `--reason`, `--actor-agent` and `--via`. A person's
  `approve --size|--paths` and `policy set --yes` keep working; agents must preview and
  apply by digest.
- New `plovi-factory` skill: how an agent operates plovi through these commands.
- Background (factory) runs now start from the task branch, so planning commits
  reach the pull request; preflight and dry runs no longer allocate checkouts.
- Plans can name extra commands (`allowed_commands`) that restricted runs may use.
- Usage limits pause the run with the reset time instead of failing it, and
  resume keeps the interrupted attempt's work.
- Completion reports may end with a bare JSON line after prose.

## Tests added

- `tests/test_ledger.py`: `LedgerTests` (`test_append_read_round_trip`,
  `test_every_event_type_validates_against_schema`, `test_concurrent_processes_never_interleave`,
  `test_torn_last_line_skipped_with_one_warning`, `test_month_rollover_reads_across_files`,
  `test_state_import_is_idempotent`, `test_ledger_lives_outside_repository_and_worktrees`,
  `test_oversized_event_rejected`) and `LedgerCliTests.test_runner_transitions_are_listed_by_events`.
- `tests/test_operations.py`: `OperationCliTests` (`test_commands_json_lists_every_operation`,
  `test_mutating_operations_record_actor_and_reason`, `test_answer_with_text_and_file`,
  `test_retry_with_note`, `test_pause_stops_before_next_stage_and_resume_continues`,
  `test_cancel_records_event`, `test_high_risk_without_digest_previews_and_changes_nothing`,
  `test_agent_actor_requires_digest_for_existing_approvals`, `test_existing_json_output_shapes_preserved`)
  and `PlanApprovalTests` (`test_unattended_worker_refuses_without_plan_approval`,
  `test_approval_of_different_hash_rejected`, `test_explicit_run_records_approval_automatically`,
  `test_pipeline_launch_records_approval_before_worker`, `test_policy_can_disable_worker_gate`).
- `tests/test_inbox.py`: `InboxTests` (`test_question_item_appears_and_clears_after_answer`,
  `test_plan_item_clears_after_approval`, `test_approval_item_clears_after_approve`,
  `test_escalation_item_clears_after_retry`, `test_failed_item_clears_after_resume`,
  `test_interrupted_item_clears_after_resume`, `test_items_oldest_first_with_issue_titles`,
  `test_text_format_snapshot`).
- `tests/test_projects.py`: `ProjectRegistryTests` (`test_add_list_remove_keeps_files`,
  `test_setup_registers_project`, `test_add_is_idempotent_and_rejects_conflicting_root`, `test_text_format`).
- `tests/test_rebuild_state.py`: `RebuildStateTests` (`test_rebuilt_state_gives_identical_status`,
  `test_rebuild_rejects_tampered_blob`, `test_rebuild_without_history_fails_clearly`).
- Shared helpers in `tests/fixtures/control_plane.py`. No existing test changed.

## Commands run

The implementation stage replaces this section with the commands actually run and
their results, taken from the runner's verification evidence: unittest discover,
`.venv/bin/python -m mkdocs build --strict`, `.venv/bin/python scripts/check_links.py site`,
generate_docs --check, generate_plugin_skills --check, check_public_content --history.

## What changes for your workflow

- New daily loop: `plovi inbox` shows what needs you; resolve items with
  `plovi answer`, `plovi approve`, `plovi retry` or `plovi resume`.
- You can ask any agent session to "check the plovi inbox" or "retry 146 with
  this note": it uses the `plovi-factory` skill.
- Runs you start yourself (`plovi run`, `plovi pipeline`, resume, answer, retry)
  record the plan approval automatically. Background workers refuse a plan whose
  hash has no recorded approval; approve one with
  `plovi approve <task> --plan --approve <sha>`.
- Run history now lives in your user data folder and survives deleting the
  project's local folder. Keep `XDG_DATA_HOME` outside your projects; plovi refuses
  to write the ledger inside a project, repository or worktree.
- Tasks pinned to a runtime from before this change keep working but record no
  runner transitions until `--upgrade-runtime --rebind`.
- A background run of a planned task delivers the plan commits with the code.
- When your provider usage limit is reached, the task shows as paused in
  `plovi inbox`; run `plovi resume <task>` after the reset time.
