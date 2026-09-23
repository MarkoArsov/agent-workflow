"""Project connector declarations with explicit route availability and local patch previews."""
from __future__ import annotations
import copy
import os
import shutil
from pathlib import Path
from ..profile import validate_command
from ..util import WorkflowError, contained, digest, identifier, json_text, read_json, write_json

def catalog(project):
    result = {}
    root = contained(project.root, project.profile["extensions"]["connectors"])
    for path in sorted(root.glob("*.json")):
        value = read_json(path)
        name = identifier(value.get("id", ""))
        if name in result or value.get("transport") not in {"host", "command"}:
            raise WorkflowError("Connector requires a unique id and host/command transport")
        if not isinstance(value.get("capabilities"), list) or not value.get("providers"):
            raise WorkflowError(f"{name}: declare capabilities and provider availability")
        if value["transport"] == "command":
            validate_command(value["command"])
        if any(key in value for key in ("token", "password", "secret", "api_key")):
            raise WorkflowError("Store connector credentials in the host or environment, never declarations")
        result[name] = value
    return result

def preflight(project, manifest):
    from ..manifest import route_for
    connectors = catalog(project)
    results = []
    for name in manifest.get("connectors", []):
        connector = connectors.get(name)
        if not connector or connector.get("enabled", True) is False:
            raise WorkflowError(f"Enable/configure connector {name}, or choose the Markdown/no-tracker path")
        for stage in manifest["stages"]:
            for route in route_for(project, manifest, stage):
                provider = route["provider"]
                availability = connector["providers"].get(provider, {})
                if availability.get("headless") is not True:
                    raise WorkflowError(f"{name} is not verified for headless {provider}; configure that route or remove the dependency")
        for variable in connector.get("env_refs", []):
            if variable not in os.environ:
                raise WorkflowError(f"{name} requires environment variable {variable}")
        if connector["transport"] == "command" and not shutil.which(connector["command"]["argv"][0]):
            raise WorkflowError(f"{name}: connector executable is missing")
        results.append({"id": name, "transport": connector["transport"], "capabilities": connector["capabilities"]})
    return results

def invoke(project, name, capability, payload):
    from ..process import execute
    from ..verification import command_environment
    connector = catalog(project).get(name)
    if not connector or not connector.get("enabled", True) or capability not in connector["capabilities"]:
        raise WorkflowError("Connector/capability is unavailable")
    if not capability.startswith("read:"):
        raise WorkflowError("Command invocations support read capabilities; draft writes and authorize them in the host")
    if connector["transport"] != "command":
        raise WorkflowError("Use this connector's declared tool in the selected host")
    command = connector["command"]
    result = execute(command["argv"], contained(project.root, command.get("cwd", ".")),
                     input_text=json_text({"capability": capability, "payload": payload}),
                     env=command_environment(command), timeout=command.get("timeout_seconds", 60))
    if result["exit_code"] or result["reason"]:
        raise WorkflowError("Connector command failed: " + result["output"])
    return result["output"]

def patch_proposal(path, server_name, configuration):
    path = Path(path).resolve()
    before = path.read_text() if path.exists() else None
    value = read_json(path, {})
    if not isinstance(value, dict):
        raise WorkflowError("Host MCP configuration must be a JSON object")
    # No credentials are accepted in a generated transport configuration.
    import re
    if re.search(r'(?i)"(?:token|password|secret|api[_-]?key)"\s*:', json_text(configuration)):
        raise WorkflowError("Use host login or environment references in connector settings")
    after = copy.deepcopy(value)
    after.setdefault("mcpServers", {})[server_name] = configuration
    proposal = {"path": str(path), "before_sha256": digest(before) if before is not None else None,
                "content": json_text(after), "before": before}
    proposal["approval"] = digest(json_text(proposal))
    return proposal

def apply_patch(proposal, approval):
    payload = {k: v for k, v in proposal.items() if k != "approval"}
    if digest(json_text(payload)) != approval or proposal.get("approval") != approval:
        raise WorkflowError("Approve the exact connector patch")
    path = Path(proposal["path"])
    current = digest(path.read_bytes()) if path.exists() else None
    if current != proposal["before_sha256"]:
        raise WorkflowError("Host configuration changed; regenerate the proposal")
    from ..util import atomic_write
    atomic_write(path, proposal["content"])
    return {"updated": str(path)}

