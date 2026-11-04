"""Every scenario step has owners, a known owner status and a test method decorated with the same owners."""
import json
import unittest
import unittest.mock
from tests.helpers import WorkspaceTest
from tests.scenario import steps
# The module, not the class: importing ScenarioTests here would make discovery run it twice.
from tests.scenario import test_target_scenario as target

IDS = ["U1", "U2", "I1", "I2", "I3", "I4", "P1", "P2", "P3", "P4", "B1", "B2", "B3", "B4", "D0", "D1", "D2", "D3", "D4", "D5",
       "J1", "J2", "J3", "J4", "J5", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "X1"]


class Fixture:
    """Stand-in test class for validator cases; not a TestCase, so discovery never runs it."""

    @steps.owned_by(49)
    def check_A1_owned(self):
        pass

    def check_A2_undecorated(self):
        pass


class TraceabilityTests(WorkspaceTest):
    def owners(self, **changes):
        value = steps.load_owners()
        value.update({int(k.removeprefix("n")): v for k, v in changes.items()})
        return value

    def test_every_step_is_traceable(self):
        self.assertEqual(steps.validate(steps.SCENARIO_STEPS, steps.load_owners(), target.ScenarioTests), [])

    def test_the_table_has_exactly_the_scenario_rows(self):
        self.assertEqual([row["id"] for row in steps.SCENARIO_STEPS], IDS)
        for row in steps.SCENARIO_STEPS:
            self.assertTrue(row["test"].startswith(f"ScenarioTests.test_{row['id']}_"), row)

    def test_only_finished_owners_are_done(self):
        done = sorted(number for number, value in steps.load_owners().items() if value == "done")
        self.assertEqual(done, [18, 46, 47, 49])

    def test_an_unowned_step_fails_validation(self):
        rows = [{"id": "A1", "text": "Owned", "owners": [49], "test": "Fixture.check_A1_owned"},
                {"id": "A9", "text": "Deliberately unowned", "owners": [], "test": "Fixture.check_A1_owned"}]
        problems = steps.validate(rows, self.owners(), Fixture)
        self.assertIn("A9 has no owner", problems)

    def test_a_missing_test_method_fails_validation(self):
        rows = [{"id": "A3", "text": "No test", "owners": [49], "test": "Fixture.check_A3_missing"}]
        self.assertEqual(steps.validate(rows, self.owners(), Fixture), ["A3: Fixture.check_A3_missing does not exist"])

    def test_an_owner_missing_from_owners_json_fails_validation(self):
        rows = [{"id": "A1", "text": "Owned", "owners": [49, 77], "test": "Fixture.check_A1_owned"}]
        problems = steps.validate(rows, self.owners(), Fixture)
        self.assertIn("A1: owner #77 is missing from owners.json", problems)

    def test_an_unknown_owner_status_fails_validation(self):
        rows = [{"id": "A1", "text": "Owned", "owners": [49], "test": "Fixture.check_A1_owned"}]
        self.assertEqual(steps.validate(rows, self.owners(n49="started"), Fixture), ["owners.json holds 'started'; use done or pending"])

    def test_a_method_without_matching_owners_fails_validation(self):
        rows = [{"id": "A2", "text": "Undecorated", "owners": [49], "test": "Fixture.check_A2_undecorated"}]
        self.assertEqual(steps.validate(rows, self.owners(), Fixture), ["A2: Fixture.check_A2_undecorated is not decorated @owned_by(49)"])

    def test_pending_steps_skip_with_their_owner(self):
        result = unittest.TestResult()
        target.ScenarioTests("test_I1_only_allowed_labels_count").run(result)
        self.assertEqual([reason for _, reason in result.skipped], ["owned by #21 (pending)"])
        result = unittest.TestResult()
        target.ScenarioTests("test_V6_pause_all_automation").run(result)
        self.assertEqual([reason for _, reason in result.skipped], ["owned by #20, #23 (pending)"])

    def test_a_flipped_owner_without_a_test_fails(self):
        flipped = {str(k): v for k, v in steps.load_owners().items()}
        flipped["21"] = "done"
        path = self.root / "owners.json"
        path.write_text(json.dumps(flipped))
        with unittest.mock.patch.object(steps, "OWNERS_PATH", path):
            result = unittest.TestResult()
            target.ScenarioTests("test_I1_only_allowed_labels_count").run(result)
        self.assertEqual(len(result.failures), 1, result.failures)
        self.assertIn("not implemented", result.failures[0][1])
