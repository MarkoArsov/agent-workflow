"""Provider commands and event normalization; no fabricated usage or cost."""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import re
import shutil
from ..util import WorkflowError, read_json, run

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
        if prompt is not None and execution.get('isolation', {}).get('mode') != 'container':
            argv += [prompt]
    return argv

def claude_environment(project, cwd, *, inherited=None):
    """Honor an optional project-local, private Claude identity guard."""
    from ..identity import assert_unchanged
    assert_unchanged(project)
    path = project.config / "local" / "claude-account.json"
    if not path.exists():
        if (project.config / "local" / "claude-account.required").exists():
            raise WorkflowError("Claude account guard is required but its local configuration is missing")
        return None
    config = read_json(path)
    if not isinstance(config, dict) or set(config) != {"config_dir", "email"}:
        raise WorkflowError("Invalid local Claude account configuration")
    directory, email = config["config_dir"], config["email"]
    if (not isinstance(directory, str) or not Path(directory).is_absolute() or not Path(directory).is_dir()
            or not isinstance(email, str) or not email.strip()):
        raise WorkflowError("Invalid local Claude account configuration")
    env = dict(os.environ if inherited is None else inherited)
    overrides = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
                 "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK",
                 "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")
    if any(env.get(name) for name in overrides):
        raise WorkflowError("Claude account verification cannot use credential or backend overrides; remove them and retry")
    env["CLAUDE_CONFIG_DIR"] = directory
    try:
        result = run([BINARIES["claude"], "auth", "status"], cwd, timeout=15, env=env, check=False)
        status = json.loads(result.stdout) if result.returncode == 0 else {}
    except (WorkflowError, ValueError):
        raise WorkflowError("Cannot verify the configured Claude account; check its login and retry") from None
    if (not isinstance(status, dict) or status.get("loggedIn") is not True
            or status.get("authMethod") != "claude.ai" or status.get("apiProvider") != "firstParty"
            or not isinstance(status.get("email"), str) or status["email"].casefold() != email.strip().casefold()):
        raise WorkflowError("Claude login does not match the configured personal account; sign in to that account and retry")
    return env

def preflight(route, execution, cwd, *, project=None, context=None):
    argv = command(route, execution)
    if context and context.get('mode') == 'container':
        from ..isolation import run_contained
        args = [argv[0], 'exec', '--help'] if route['provider'] == 'codex' else [argv[0], '--help']
        result = run_contained(context, args)
        if result.returncode or any(a not in result.stdout for a in argv[1:] if a.startswith('--')):
            raise WorkflowError('Container harness is missing or lacks required flags; rebuild the selected image')
        return {'provider': route['provider'], 'binary': argv[0], 'model': route['model'],
                'permission_mode': execution['permission_mode'], 'boundary': 'container',
                'model_validation': 'passed to provider; account availability is verified on first request'}
    binary = shutil.which(argv[0])
    if not binary:
        raise WorkflowError(f"Install/authenticate {argv[0]} or choose another configured route")
    args = [binary, "exec", "--help"] if route["provider"] == "codex" else [binary, "--help"]
    from ..identity import environment
    env = environment(project, cwd) if project is not None else None
    result = run(args, cwd, env=env)
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
        self.terminal_result = None
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
            self.terminal_result = event["result"]
            self.text.append(event["result"])
        if kind in {"turn.completed", "result"}:
            if isinstance(event.get("usage"), dict):
                self.usage = event["usage"]
            if type(event.get("total_cost_usd")) in (int, float) and math.isfinite(event["total_cost_usd"]) and event["total_cost_usd"] >= 0:
                self.cost_usd = event["total_cost_usd"]
        return None

    def report(self):
        texts = [self.terminal_result] if self.terminal_result is not None else reversed(self.text)
        for text in texts:
            stripped = re.sub(r"^" + re.escape(chr(96) * 3) + r"(?:json)?\s*|\s*" + re.escape(chr(96) * 3) + r"$", "", text.strip())
            terminal = re.search(r"(?:^|\n)```json[ \t]*\r?\n((?:(?!\r?\n```)[\s\S])*?)\r?\n```[ \t]*\Z", text.strip(), re.IGNORECASE)
            if terminal:
                stripped = terminal.group(1)
            try:
                value = json.loads(stripped)
                if isinstance(value, dict) and "status" in value and (not isinstance(value["status"], str) or value["status"] not in {"complete", "needs_input", "blocked", "spec_conflict", "impossible", "test_fixture_repair"}):
                    return None
                if isinstance(value, dict) and value.get("status") in {"complete", "needs_input", "blocked", "spec_conflict", "impossible", "test_fixture_repair"}:
                    status = value["status"]
                    required = "question" if status == "needs_input" else "reason" if status != "complete" else None
                    if required and (not isinstance(value.get(required), str) or not value[required].strip()):
                        return None
                    if status == "test_fixture_repair" and (not isinstance(value.get("test_paths"), list) or not isinstance(value.get("checks"), list) or not all(isinstance(x, str) for x in value.get("checks", []))):
                        return None
                    if "assumptions" in value and (not isinstance(value["assumptions"], list) or not all(isinstance(x, str) for x in value["assumptions"])):
                        return None
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



def failure_kind(classification):
    return {'authentication':'provider_authentication','quota':'provider_quota',
            'model':'unsupported_model','transient':'transient_transport',
            'cancelled':'cancelled','cancellation_failure':'cancellation_failure',
            'inactive':'provider_inactive','tool-stalled':'tool_stalled',
            'timeout':'timeout'}.get(classification, classification)
