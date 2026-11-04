---
title: Target scenario
description: Every step of the target scenario, the issues that own it, its test and whether it works yet.
question: How much of the target scenario works today?
---

# Target scenario

Generated from `tests/scenario/steps.py` and `tests/scenario/owners.json` by `scripts/generate_docs.py`.

!!! summary "In one minute"
    - The target: tag issues, set a project up once, and let plovi plan, build and deliver them while you watch and steer.
    - 11 of 33 steps are done: every owning issue has landed and the step's test runs in CI.
    - A pending step's test is skipped with the issues it waits for. Each owning issue writes the test and marks itself done.
    - [The stability gate](../stability-gate.md) counts these steps in G5.

| ID | Step | Owners | Test | Status |
|---|---|---|---|---|
| U1 | Set up a project once: `plovi setup` writes the profile, `plovi.toml` and disabled built-in schedules | #49 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_U1_setup_once` | done |
| U2 | Project settings change behaviour: the stage list (including a custom stage) and the delivery and merge keys | #49, #23 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_U2_project_settings_apply` | pending |
| I1 | Only issues labelled by allowed people are candidates; bot and non-writer labels never start work | #21 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_I1_only_allowed_labels_count` | pending |
| I2 | The factory schedule picks up the next labelled issue on its own | #21 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_I2_tick_picks_next_issue` | pending |
| I3 | Concurrency is configurable; `max_active = 1` never runs two factory tasks | #21 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_I3_max_active_one` | pending |
| I4 | Dependencies and path overlaps hold an issue back with a visible reason | #21 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_I4_blocked_because` | pending |
| P1 | Headless specify answers its own questions with recommended answers and records assumptions | #21 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_P1_headless_assumptions_recorded` | pending |
| P2 | A stop-list question stops with grouped questions; one answer resumes the same session | #21 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_P2_stop_list_asks_once` | pending |
| P3 | Plan checks are validated with `validate-plan --run-checks` before approval | #48 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_P3_plan_checks_validated` | done |
| P4 | An auto-approved plan goes straight into the pipeline | #21 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_P4_auto_approved_plan_builds` | pending |
| B1 | The hobby stage list runs exactly implement and review | #49 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_B1_hobby_stages` | done |
| B2 | The product stage list runs implement-tests, implement, review and a custom stage | #49 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_B2_product_stages_with_custom` | done |
| B3 | A recoverable blocked report, one failing-check round, a missing report and a 2× diff-budget overshoot complete without a person | #47 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_B3_recovers_in_the_middle` | done |
| B4 | A usage limit pauses with the reset time, and resume keeps partial edits | #18 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_B4_usage_limit_pause_resume` | done |
| D0 | Push and open a PR whose verification section comes only from plovi's evidence | #49, #48 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_D0_push_and_pr` | done |
| D1 | The PR's CI readiness is tracked | #23 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_D1_readiness_tracked` | pending |
| D2 | A CI failure is fixed on the same PR | #23 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_D2_ci_failure_fixed_same_pr` | pending |
| D3 | Accepted review comments are fixed | #23 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_D3_review_comment_fixed` | pending |
| D4 | Auto-merge is enabled when green within the risk class after the shadow period; the kill switch disables it | #23 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_D4_auto_merge_policy` | pending |
| D5 | Manual-merge configuration: the PR is opened and nothing is merged | #23 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_D5_manual_merge_untouched` | pending |
| J1 | A daily job runs at its time and follows its catch-up rule | #20 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_J1_daily_job_runs` | pending |
| J2 | The QA job tests yesterday's merged changes against a named target | #50 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_J2_tests_merged_changes_on_target` | pending |
| J3 | A found problem becomes one well-formed issue | #50 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_J3_files_well_formed_issue` | pending |
| J4 | Duplicates get a comment instead of a new issue; caps apply; no intake label by default; the loop guard holds | #50 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_J4_dedupe_caps_no_loop` | pending |
| J5 | Job budgets and daily caps stop spending | #20 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_J5_budgets_stop_jobs` | pending |
| V1 | `plovi status` and `plovi inbox` show what runs and what waits on the person | #18 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_V1_status_and_inbox` | done |
| V2 | Pause, resume and cancel any task from the CLI | #18 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_V2_pause_resume_cancel` | done |
| V3 | The same in the app: Board, Inbox and side-panel actions | #19 | Playwright `app/e2e/scenario.spec.ts › "V3 …"`, checked by `tests/scenario/test_target_scenario.py` `ScenarioTests.test_V3_app_board_inbox_actions` | pending |
| V4 | Project settings changed in the app | #22 | Playwright `app/e2e/scenario.spec.ts › "V4 …"`, checked by `tests/scenario/test_target_scenario.py` `ScenarioTests.test_V4_app_settings` | pending |
| V5 | Take over a task and hand it back | #25 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_V5_take_over_hand_back` | pending |
| V6 | Stop all automation at once: `plovi pause --schedules` and `plovi pause --merges` | #20, #23 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_V6_pause_all_automation` | pending |
| V7 | Status explains why a task stopped, what it cost and the next command | #47 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_V7_status_explains_stop_and_cost` | done |
| X1 | `plovi stats --gate` measures stability | #49 | `tests/scenario/test_target_scenario.py` `ScenarioTests.test_X1_stats_gate` | done |

To own a step, see [Scenario tests: how to own a step](../development.md#scenario-tests-how-to-own-a-step).
