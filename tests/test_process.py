from __future__ import annotations
import os
import signal
import sys
import time
from tests.helpers import WorkspaceTest
from scorebook.process import execute

class ProcessTests(WorkspaceTest):
    def test_cancel_cleans_descendants_after_leader_exit_including_term_resistant_child(self):
        for ignore_term in (False, True):
            with self.subTest(ignore_term=ignore_term):
                heartbeat = self.root / (str(ignore_term) + ".heartbeat")
                child = ("import signal,time; from pathlib import Path; "
                         + ("signal.signal(signal.SIGTERM, signal.SIG_IGN); " if ignore_term else "")
                         + f"p=Path({str(heartbeat)!r}); "
                         + "exec('while True:\\n p.write_text(str(time.monotonic()))\\n time.sleep(0.02)')")
                parent = ("import subprocess,sys,time; from pathlib import Path; "
                          + f"subprocess.Popen([sys.executable,'-c',{child!r}]); p=Path({str(heartbeat)!r}); "
                          + "exec('while not p.exists(): time.sleep(0.01)')")
                groups = []
                ready_at = []
                def cancelled():
                    if heartbeat.exists() and not ready_at:
                        ready_at.append(time.monotonic())
                    return bool(ready_at and time.monotonic() - ready_at[0] > 0.3)
                try:
                    result = execute([sys.executable, "-c", parent], self.root, timeout=20,
                                     cancel=cancelled, on_start=groups.append)
                    self.assertEqual(result["reason"], "cancelled")
                    self.assertLess(result["duration_seconds"], 20)
                    before = heartbeat.read_text()
                    time.sleep(0.15)
                    self.assertEqual(heartbeat.read_text(), before, "Owned child survived process cleanup")
                finally:
                    for group in groups:
                        try:
                            os.killpg(group, signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            pass
