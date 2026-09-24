from tests.helpers import WorkspaceTest
from stageway.verification import parse

class VerificationTests(WorkspaceTest):
    def test_unittest_red_requires_identity_and_assertion_not_setup(self):
        check = {"parser": "unittest", "identities": ["test_behavior"]}
        red = "FAIL: test_behavior\nAssertionError: 1 != 2\nRan 1 test\nFAILED (failures=1)"
        self.assertTrue(parse(check, red, 1, "red")["passed"])
        for bad in ("ERROR: test_behavior\nModuleNotFoundError\nRan 1 test",
                    "FAIL: test_other\nAssertionError\nRan 1 test",
                    "test_behavior\nCompilation failed"):
            self.assertFalse(parse(check, bad, 1, "red")["passed"])
        self.assertFalse(parse(check, red, 0, "red")["passed"])

    def test_common_green_formats_and_false_success(self):
        examples = [
            ({"parser": "unittest"}, "Ran 1 test\nOK"),
            ({"parser": "pytest"}, "1 passed in 0.03s"),
            ({"parser": "dotnet"}, "Passed!  - Failed: 0, Passed: 2, Skipped: 0"),
            ({"parser": "jest"}, "Tests: 2 passed, 2 total"),
            ({"parser": "tap"}, "ok 1 - behavior\n1..1"),
            ({"parser": "generic", "success_pattern": "^checked: 3$"}, "checked: 3"),
        ]
        for check, output in examples:
            with self.subTest(check=check):
                self.assertTrue(parse(check, output, 0)["passed"])
                self.assertFalse(parse(check, output, 1)["passed"])
        self.assertFalse(parse({"parser": "unittest"}, "Agent says all tests passed", 0)["passed"])
        self.assertFalse(parse({"parser": "pytest"}, "1 passed, 1 skipped", 0)["passed"])
        self.assertFalse(parse({"parser": "generic", "success_pattern": "ok"}, "ok\nImportError: fixture", 0)["passed"])

