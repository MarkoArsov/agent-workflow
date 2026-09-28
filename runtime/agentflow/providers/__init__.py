"""Provider commands and event normalization; no fabricated usage or cost."""
from __future__ import annotations
import json
import re
import shutil
from ..util import WorkflowError, run

BINARIES = {"codex": "codex", "claude": "claude", "cursor": "agent"}

def command(route, execution, *, session=None, prompt=None):
    provider = route["provider"]
    argv = [BINARIES[provider]]
    trusted = execution["permission_mode"] == "trusted"
    model = route["model"]
    settings = execution.get("provider_settings", {}).get(provider, {})
    if provider == "codex":
        argv += ["exec"]
        if session:
            argv += ["resume"]
        argv += ["--json", "--model", model]
        if trusted:
            argv += ["--dangerously-bypass-approvals-and-sandbox"]
        elif session:
            argv += ["-c", 'sandbox_mode="workspace-write"', "-c", 'approval_policy="never"']
        else:
            argv += ["--sandbox", "workspace-write", "-c", 'approval_policy="never"']
        if route.get("reasoning"):
            argv += ["-c", 'model_reasoning_effort=' + json.dumps(route["reasoning"])]
        if session:
            argv += [session]
        argv += ["-"]
    elif provider == "claude":
        argv += ["--print", "--verbose", "--output-format", "stream-json", "--model", model]
        if trusted:
            argv += ["--dangerously-skip-permissions"]
        else:
            allowed = settings.get("allowed_tools")
            if not allowed:
                raise WorkflowError("Restricted Claude requires explicit provider_settings.claude.allowed_tools")
            argv += ["--permission-mode", "dontAsk", "--allowedTools", ",".join(allowed)]
        if route.get("reasoning"):
            argv += ["--effort", route["reasoning"]]
        if settings.get("max_budget_usd") is not None:
            argv += ["--max-budget-usd", str(settings["max_budget_usd"])]
        if session:
            argv += ["--resume", session]
    else:
        argv += ["--print", "--output-format", "stream-json", "--model", model, "--trust"]
        argv += ["--force", "--sandbox", "disabled"] if trusted else ["--sandbox", "enabled"]
        if session:
            argv += ["--resume", session]
        if prompt is not None:
            argv += [prompt]
    return argv

def preflight(route, execution, cwd):
    argv = command(route, execution)
    binary = shutil.which(argv[0])
    if not binary:
        raise WorkflowError(f"Install/authenticate {argv[0]} or choose another configured route")
    args = [binary, "exec", "--help"] if route["provider"] == "codex" else [binary, "--help"]
    result = run(args, cwd)
    flags = [a for a in argv[1:] if a.startswith("--")]
    if any(flag not in result.stdout for flag in flags):
        missing = [flag for flag in flags if flag not in result.stdout]
        raise WorkflowError(f"{argv[0]} does not support required flags: {missing}")
    return {"provider": route["provider"], "binary": binary, "model": route["model"],
            "permission_mode": execution["permission_mode"],
            "model_validation": "passed to provider; account availability is verified on first request"}

class Events:
    def __init__(self):
        self.session = None
        self.text = []
        self.usage = None
        self.cost_usd = None
        self.error = None

    def line(self, line):
        try:
            event = json.loads(line)
        except ValueError:
            return None
        kind = event.get("type")
        self.session = event.get("thread_id", event.get("session_id", self.session))
        if kind in {"error", "turn.failed"} or event.get("is_error"):
            self.error = str(event.get("error", event.get("result", event.get("message", "Provider error"))))
        if kind == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                self.text.append(item.get("text", ""))
            if item.get("type") in {"command_execution", "mcp_tool_call"}:
                return "tool-end"
        if kind == "item.started" and event.get("item", {}).get("type") in {"command_execution", "mcp_tool_call"}:
            return "tool-start"
        if kind == "assistant":
            message = event.get("message", {})
            for block in message.get("content", []):
                if block.get("type") == "text":
                    self.text.append(block.get("text", ""))
                if block.get("type") == "tool_use":
                    return "tool-start"
        if kind == "user" and any(x.get("type") == "tool_result" for x in event.get("message", {}).get("content", [])):
            return "tool-end"
        if kind == "tool_call":
            return "tool-end" if event.get("subtype") == "completed" else "tool-start"
        if kind == "result" and isinstance(event.get("result"), str):
            self.text.append(event["result"])
        if kind in {"turn.completed", "result"}:
            if isinstance(event.get("usage"), dict):
                self.usage = event["usage"]
            if isinstance(event.get("total_cost_usd"), (int, float)):
                self.cost_usd = event["total_cost_usd"]
        return None

    def report(self):
        for text in reversed(self.text):
            stripped = re.sub(r"^" + re.escape(chr(96) * 3) + r"(?:json)?\s*|\s*" + re.escape(chr(96) * 3) + r"$", "", text.strip())
            try:
                value = json.loads(stripped)
                if isinstance(value, dict) and value.get("status") in {"complete", "needs_input", "blocked"}:
                    return value
            except ValueError:
                continue
        return None

def classify(result, events):
    if result["reason"]:
        return result["reason"]
    text = (events.error or "") + (result["output"] if result["exit_code"] else "")
    if re.search(r"(?i)unauthorized|authentication|invalid.api.key|not.logged.in", text):
        return "authentication"
    if re.search(r"(?i)quota|usage.limit|insufficient.*credit", text):
        return "quota"
    if re.search(r"(?i)model.*(?:not.found|not.available|unsupported|does.not.exist)", text):
        return "model"
    if events.error or result["exit_code"]:
        return "transient"
    return "complete"

