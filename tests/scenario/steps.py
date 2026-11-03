"""The target scenario: every step, the issues that own it, and the test that proves it.

An owning issue replaces its step's stub with a real test and sets itself to "done" in
owners.json in the same pull request. Until every owner is done, the step is skipped
with "owned by #N (pending)". scripts/generate_docs.py renders docs/generated/scenario.md
from this file, and scripts/run_tests.py --scenario-results reads it for the stability gate.
This module uses only the standard library: run_tests.py loads it with runpy.
"""
import functools
import json
import unittest
from pathlib import Path

OWNERS_PATH = Path(__file__).with_name("owners.json")
STATUSES = ("done", "pending")
TEST_FILE = "tests/scenario/test_target_scenario.py"
APP_SPEC = "app/e2e/scenario.spec.ts"


def step(id, text, owners, method, app_test=None):
    row = {"id": id, "text": text, "owners": owners, "test": f"ScenarioTests.{method}"}
    if app_test:
        row["app_test"] = app_test
    return row


SCENARIO_STEPS = [
    step("U1", "Set up a project once: `plovi setup` writes the profile, `plovi.toml` and disabled built-in schedules",
         [49], "test_U1_setup_once"),
    step("U2", "Project settings change behaviour: the stage list (including a custom stage) and the delivery and merge keys",
         [49, 23], "test_U2_project_settings_apply"),
    step("I1", "Only issues labelled by allowed people are candidates; bot and non-writer labels never start work",
         [21], "test_I1_only_allowed_labels_count"),
    step("I2", "The factory schedule picks up the next labelled issue on its own", [21], "test_I2_tick_picks_next_issue"),
    step("I3", "Concurrency is configurable; `max_active = 1` never runs two factory tasks", [21], "test_I3_max_active_one"),
    step("I4", "Dependencies and path overlaps hold an issue back with a visible reason", [21], "test_I4_blocked_because"),
    step("P1", "Headless specify answers its own questions with recommended answers and records assumptions",
         [21], "test_P1_headless_assumptions_recorded"),
    step("P2", "A stop-list question stops with grouped questions; one answer resumes the same session",
         [21], "test_P2_stop_list_asks_once"),
    step("P3", "Plan checks are validated with `validate-plan --run-checks` before approval", [48], "test_P3_plan_checks_validated"),
    step("P4", "An auto-approved plan goes straight into the pipeline", [21], "test_P4_auto_approved_plan_builds"),
    step("B1", "The hobby stage list runs exactly implement and review", [49], "test_B1_hobby_stages"),
    step("B2", "The product stage list runs implement-tests, implement, review and a custom stage",
         [49], "test_B2_product_stages_with_custom"),
    step("B3", "A recoverable blocked report, one failing-check round, a missing report and a 2× diff-budget overshoot "
               "complete without a person", [47], "test_B3_recovers_in_the_middle"),
    step("B4", "A usage limit pauses with the reset time, and resume keeps partial edits", [18], "test_B4_usage_limit_pause_resume"),
    step("D0", "Push and open a PR whose verification section comes only from plovi's evidence", [49, 48], "test_D0_push_and_pr"),
    step("D1", "The PR's CI readiness is tracked", [23], "test_D1_readiness_tracked"),
    step("D2", "A CI failure is fixed on the same PR", [23], "test_D2_ci_failure_fixed_same_pr"),
    step("D3", "Accepted review comments are fixed", [23], "test_D3_review_comment_fixed"),
    step("D4", "Auto-merge is enabled when green within the risk class after the shadow period; the kill switch disables it",
         [23], "test_D4_auto_merge_policy"),
    step("D5", "Manual-merge configuration: the PR is opened and nothing is merged", [23], "test_D5_manual_merge_untouched"),
    step("J1", "A daily job runs at its time and follows its catch-up rule", [20], "test_J1_daily_job_runs"),
    step("J2", "The QA job tests yesterday's merged changes against a named target", [50], "test_J2_tests_merged_changes_on_target"),
    step("J3", "A found problem becomes one well-formed issue", [50], "test_J3_files_well_formed_issue"),
    step("J4", "Duplicates get a comment instead of a new issue; caps apply; no intake label by default; the loop guard holds",
         [50], "test_J4_dedupe_caps_no_loop"),
    step("J5", "Job budgets and daily caps stop spending", [20], "test_J5_budgets_stop_jobs"),
    step("V1", "`plovi status` and `plovi inbox` show what runs and what waits on the person", [18], "test_V1_status_and_inbox"),
    step("V2", "Pause, resume and cancel any task from the CLI", [18], "test_V2_pause_resume_cancel"),
    step("V3", "The same in the app: Board, Inbox and side-panel actions", [19], "test_V3_app_board_inbox_actions",
         app_test=f'{APP_SPEC} › "V3 …"'),
    step("V4", "Project settings changed in the app", [22], "test_V4_app_settings", app_test=f'{APP_SPEC} › "V4 …"'),
    step("V5", "Take over a task and hand it back", [25], "test_V5_take_over_hand_back"),
    step("V6", "Stop all automation at once: `plovi pause --schedules` and `plovi pause --merges`",
         [20, 23], "test_V6_pause_all_automation"),
    step("V7", "Status explains why a task stopped, what it cost and the next command", [47], "test_V7_status_explains_stop_and_cost"),
    step("X1", "`plovi stats --gate` measures stability", [49], "test_X1_stats_gate"),
]


def load_owners(path=None):
    """Owner issue number -> "done" or "pending"."""
    data = json.loads(Path(path or OWNERS_PATH).read_text(encoding="utf-8"))
    return {int(number): status for number, status in data.items()}


def pending(owners, statuses=None):
    statuses = load_owners() if statuses is None else statuses
    return [number for number in owners if statuses.get(number) != "done"]


def owned_by(*owners):
    """Skip the step until every owner is done. owners.json is read when the test runs."""
    def decorate(function):
        @functools.wraps(function)
        def wrapper(self, *args, **kwargs):
            waiting = pending(owners)
            if waiting:
                raise unittest.SkipTest("owned by " + ", ".join(f"#{n}" for n in waiting) + " (pending)")
            return function(self, *args, **kwargs)
        wrapper.scenario_owners = owners
        return wrapper
    return decorate


def status(row, statuses=None):
    """done when every owner is done, else pending."""
    return "pending" if pending(row["owners"], statuses) else "done"


def validate(steps, statuses, test_class):
    """Every traceability problem: owners, owner status and test methods."""
    problems, seen = [], set()
    for value in statuses.values():
        if value not in STATUSES:
            problems.append(f"owners.json holds {value!r}; use done or pending")
    for row in steps:
        if row["id"] in seen:
            problems.append(f"{row['id']} appears twice")
        seen.add(row["id"])
        if not row.get("owners"):
            problems.append(f"{row['id']} has no owner")
        for number in row.get("owners", []):
            if number not in statuses:
                problems.append(f"{row['id']}: owner #{number} is missing from owners.json")
        method = getattr(test_class, row["test"].split(".", 1)[1], None)
        if method is None:
            problems.append(f"{row['id']}: {row['test']} does not exist")
        elif tuple(getattr(method, "scenario_owners", ())) != tuple(row.get("owners", [])):
            problems.append(f"{row['id']}: {row['test']} is not decorated @owned_by({', '.join(map(str, row.get('owners', [])))})")
    return problems
