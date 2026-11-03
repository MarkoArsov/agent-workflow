"""state.json is a cache that plovi rebuilds from ledger checkpoints."""
from __future__ import annotations
import json
import re
from tests.helpers import HardeningTest
from tests.fixtures.control_plane import ControlPlaneMixin
from plovi import runner, state

VOLATILE = {"updated_at", "pid", "child_pid", "heartbeat_at", "activity", "activity_at"}


def elapsed_free(text):
    """Human status reports seconds since start; only that clock-relative number may move."""
    return re.sub(r"\d+s\b", "Ns", text)


class RebuildStateTests(ControlPlaneMixin, HardeningTest):
    def completed_task(self):
        self.fixture([{}], stages=["implement"])
        self.save_plan()
        result = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(result["status"], "complete")
        self.evidence = state.directory(self.project, "sample")
        return result

    def outputs(self):
        human = self.ok(self.task_cli("status", "sample")).stdout
        machine = self.ok(self.task_cli("status", "sample", "--json")).stdout
        return elapsed_free(human), json.loads(machine)

    def remove_cache(self):
        (self.evidence / "state.json").unlink()
        (self.evidence / "status.json").unlink()

    def test_rebuilt_state_gives_identical_status(self):
        self.completed_task()
        original = json.loads((self.evidence / "state.json").read_text())
        before = self.outputs()
        self.remove_cache()
        rebuilt = self.task_cli("rebuild-state", "sample")
        self.assertEqual(rebuilt.returncode, 0, rebuilt.stdout + rebuilt.stderr)
        restored = json.loads((self.evidence / "state.json").read_text())
        self.assertEqual({k: v for k, v in restored.items() if k not in VOLATILE},
                         {k: v for k, v in original.items() if k not in VOLATILE})
        self.assertEqual(restored["updated_at"], original["updated_at"], "rebuild preserves the recorded updated_at")
        self.assertTrue((self.evidence / "status.json").is_file())
        self.assertEqual(self.outputs(), before)
        # A missing cache is rebuilt by status itself.
        self.remove_cache()
        self.assertEqual(self.outputs(), before)
        self.assertTrue((self.evidence / "state.json").is_file())

    def checkpoint_blob(self):
        checkpoints = self.of_type("state.checkpoint")
        self.assertTrue(checkpoints, "the run recorded state checkpoints")
        sha = checkpoints[-1]["data"]["keys"]["status"]
        blob = self.ledger_directory() / "blobs" / sha[:2] / (sha + ".json")
        self.assertTrue(blob.is_file(), "checkpoint values live in the content-addressed blob store")
        return blob

    def assert_refused(self, task="sample"):
        response = self.task_cli("rebuild-state", task)
        self.assertEqual(response.returncode, 2, response.stdout + response.stderr)
        self.assertTrue(response.stderr.startswith("Error: "), response.stderr)
        self.assertFalse((state.directory(self.project, task) / "state.json").exists(),
                         "a refused rebuild writes no cache")
        return response

    def test_rebuild_rejects_tampered_blob(self):
        self.completed_task()
        blob = self.checkpoint_blob()
        blob.write_text(json.dumps("failed"))
        self.remove_cache()
        self.assert_refused()
        blob.unlink()
        self.assert_refused()

    def test_rebuild_without_history_fails_clearly(self):
        self.fixture([{}], stages=["implement"])
        response = self.assert_refused("ghost")
        self.assertIn("ghost", response.stderr)
        result = runner.run(self.project, self.plan, unattended=False)
        self.assertEqual(result["status"], "complete")
        self.evidence = state.directory(self.project, "sample")
        for path in self.month_files():
            path.unlink()
        self.remove_cache()
        self.assert_refused()
