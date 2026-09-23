#!/usr/bin/env python3
"""A deterministic local test process, never an actual model provider."""
import json
import os
import sys
import time
from pathlib import Path

if "--help" in sys.argv:
    print("--json --model --sandbox --dangerously-bypass-approvals-and-sandbox --print --verbose --output-format --dangerously-skip-permissions --permission-mode --allowedTools --effort --max-budget-usd --trust --force")
    raise SystemExit()
scenario = Path(os.environ["WORKFLOW_TEST_SCENARIO"])
data = json.loads(scenario.read_text())
calls_path = scenario.with_suffix(".calls.json")
calls = json.loads(calls_path.read_text()) if calls_path.exists() else []
prompt = sys.argv[-1] if Path(sys.argv[0]).name == "agent" else sys.stdin.read()
calls.append({"argv": sys.argv, "prompt": prompt, "pid": os.getpid(), "cwd": str(Path.cwd())})
calls_path.write_text(json.dumps(calls))
step = data[min(len(calls) - 1, len(data) - 1)]
session = step.get("session", "fixture-session-" + str(len(calls)))
print(json.dumps({"type": "thread.started", "thread_id": session}), flush=True)
for path, value in step.get("writes", {}).items():
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value)
if step.get("tool_stall"):
    print(json.dumps({"type": "item.started", "item": {"type": "command_execution"}}), flush=True)
    for _ in range(50):
        print(json.dumps({"type": "heartbeat"}), flush=True); time.sleep(0.1)
if step.get("sleep"):
    time.sleep(step["sleep"])
if step.get("error"):
    print(json.dumps({"type": "error", "message": step["error"]}), flush=True)
    raise SystemExit(1)
report = step.get("report", {"status": "complete", "summary": "Fixture stage"})
print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(report)}}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 5}}))

