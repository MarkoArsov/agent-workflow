"""A small, explicit task contract; no implicit repository or delivery selection."""
from __future__ import annotations
import fnmatch
from pathlib import Path
from .profile import BASE_STAGES, PROVIDERS, validate_command
from .util import WorkflowError, contained, digest, identifier, json_text, read_json

PUBLISH = {"commit-and-push", "draft-pr"}
PARSERS = {"unittest", "pytest", "dotnet", "jest", "tap", "generic"}

def load(path, project):
    path = Path(path).resolve()
    value = read_json(path)
    validate(value, project)
    value["_directory"] = str(path.parent)
    value["_path"] = str(path)
    return value

def route_for(project, manifest, stage):
    routes = manifest.get("routes", project.profile["pipeline"]["routes"])
    return routes.get(stage, routes.get("default", []))

def custom_stages(project):
    rows = read_json(contained(project.root, project.profile["extensions"]["stages"]), [])
    result = {}
    for stage in rows:
        name = identifier(stage.get("id", ""))
        if name in BASE_STAGES or name in result:
            raise WorkflowError("Custom stage IDs must be unique and cannot replace built-in stages")
        if bool(stage.get("skill")) == bool(stage.get("command")):
            raise WorkflowError(f"{name}: declare exactly one skill or command")
        if stage.get("command"):
            validate_command(stage["command"])
        if not isinstance(stage.get("inputs"), list) or not isinstance(stage.get("outputs"), list) or not stage.get("checks"):
            raise WorkflowError(f"{name}: declare inputs, outputs, and completion checks")
        if bool(stage.get("before")) == bool(stage.get("after")):
            raise WorkflowError(f"{name}: declare exactly one before or after stage")
        result[name] = stage
    return result

def validate(value, project):
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise WorkflowError("Expected pipeline schema_version 1")
    identifier(value.get("task", ""))
    stages = value.get("stages", [])
    if not isinstance(stages, list) or len(stages) != len(set(stages)) or "implement" not in stages:
        raise WorkflowError("Declare unique ordered stages, including implement")
    custom = custom_stages(project)
    if set(stages) - set(BASE_STAGES) - set(custom):
        raise WorkflowError("Unknown pipeline stage")
    builtin = [x for x in stages if x in BASE_STAGES]
    if builtin != sorted(builtin, key=BASE_STAGES.index):
        raise WorkflowError("Built-in stages are out of order")
    for name in stages:
        if name in custom:
            stage = custom[name]
            for direction in ("before", "after"):
                if direction in stage:
                    anchor = stage[direction]
                    if anchor not in stages or (stages.index(name) < stages.index(anchor)) != (direction == "before"):
                        raise WorkflowError(f"{name}: invalid {direction} dependency")
            if any(x in PUBLISH for x in stages[:stages.index(name)]):
                raise WorkflowError("Custom stages must precede publication")
    repositories = value.get("repositories", [])
    ids = set()
    for row in repositories:
        name = row.get("id")
        repo = project.repository(name)
        if name in ids or row.get("access") not in {"read", "write"}:
            raise WorkflowError("Task repositories need unique IDs and explicit read/write access")
        ids.add(name)
        if row["access"] == "write":
            if repo["task_policy"] == "never":
                raise WorkflowError(f"{name}: task policy forbids changes")
            if not row.get("paths"):
                raise WorkflowError(f"{name}: writable paths are required")
        for pattern in row.get("paths", []) + row.get("test_paths", []):
            if not isinstance(pattern, str) or Path(pattern).is_absolute() or ".." in Path(pattern).parts:
                raise WorkflowError("Task paths must stay inside their repository")
    if not any(x["access"] == "write" for x in repositories):
        raise WorkflowError("Select at least one writable repository")
    for repo in project.profile["repositories"]:
        if repo["task_policy"] == "always" and repo["id"] not in ids:
            raise WorkflowError(f"Always-participating repository is missing: {repo['id']}")
    checks = {}
    for check in value.get("checks", []):
        name = identifier(check.get("id", ""))
        if name in checks or check.get("repository") not in ids:
            raise WorkflowError("Check IDs must be unique and use participating repositories")
        command = command_for(project, check)
        validate_command(command)
        if check.get("parser", "generic") not in PARSERS:
            raise WorkflowError(f"{name}: unknown check parser")
        if check.get("parser", "generic") == "generic" and not check.get("success_pattern", command.get("success_pattern")):
            raise WorkflowError(f"{name}: generic checks need an explicit success_pattern")
        phases = check.get("phases", ["green"])
        if set(phases) - {"red", "green"} or not phases:
            raise WorkflowError("Checks require red and/or green phases")
        if "red" in phases and not check.get("identities"):
            raise WorkflowError(f"{name}: red proof needs expected test identities")
        if "red" in phases and check.get("parser", "generic") == "generic" and not check.get("failure_pattern"):
            raise WorkflowError(f"{name}: generic red proof needs an assertion failure_pattern")
        checks[name] = check
    outcomes = value.get("outcomes", [])
    if not checks or not outcomes:
        raise WorkflowError("Map each planned outcome to executable checks")
    for outcome in outcomes:
        identifier(outcome.get("id", ""))
        if not outcome.get("checks") or set(outcome["checks"]) - set(checks):
            raise WorkflowError("Every outcome must reference existing checks")
        if not any("green" in checks[x].get("phases", ["green"]) for x in outcome["checks"]):
            raise WorkflowError("Every outcome needs a green check")
    if "implement-tests" in stages and not any("red" in c.get("phases", []) for c in checks.values()):
        raise WorkflowError("Test-authoring stage requires assertion-level red checks")
    for name in stages:
        if name in custom and set(custom[name]["checks"]) - set(checks):
            raise WorkflowError(f"{name}: unknown completion check")
        if name in PUBLISH or (name in custom and custom[name].get("command")):
            continue
        routes = route_for(project, value, name)
        if not routes:
            raise WorkflowError(f"Choose a provider/model route for {name} during setup or in the plan")
        for route in routes:
            if route.get("provider") not in PROVIDERS or route["provider"] not in project.profile["agents"] or not route.get("model"):
                raise WorkflowError(f"{name}: route needs an enabled provider and explicit model")
            if route.get("reasoning") and route["provider"] == "cursor":
                raise WorkflowError("Cursor effort belongs in its model expression, not a reasoning flag")
    for key in ("prompt.md", "requirements.md", "implementation.md", "deferred.md"):
        if key not in value.get("plan_files", []):
            raise WorkflowError(f"Full plans must include {key}")
    for name in value["plan_files"]:
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise WorkflowError("Plan files must be relative to the manifest")
    if PUBLISH.intersection(stages):
        delivery = value.get("delivery", {})
        if not delivery.get("commit_message"):
            raise WorkflowError("Delivery needs an approved commit_message")
        if "draft-pr" in stages and not {"title", "body_file"} <= delivery.keys():
            raise WorkflowError("Draft PR delivery needs an approved title and body_file")
        if "draft-pr" in stages and "commit-and-push" not in stages:
            raise WorkflowError("Draft PR delivery follows commit-and-push")
        for row in repositories:
            if row["access"] == "write":
                branch = row.get("branch")
                if not branch or branch == project.repository(row["id"])["base_branch"] or branch.startswith("-"):
                    raise WorkflowError("Delivery requires an explicit non-base task branch")
    for key, default, maximum in (("attempts_per_route", 2, 5), ("timeout_seconds", 1800, 86400),
                                  ("inactivity_seconds", 300, 3600), ("tool_timeout_seconds", 600, 7200)):
        val = value.get("limits", {}).get(key, default)
        if not isinstance(val, int) or not 1 <= val <= maximum:
            raise WorkflowError(f"Invalid runner limit: {key}")
    return value

def command_for(project, check):
    command = check.get("command")
    if isinstance(command, str):
        commands = project.repository(check["repository"])["commands"]
        if command not in commands:
            raise WorkflowError(f"Unknown repository command: {command}")
        return commands[command]
    return command

def matches(path, patterns):
    return any(fnmatch.fnmatchcase(path, p) or (p.endswith("/**") and path == p[:-3]) for p in patterns)

def digest_manifest(value):
    return digest(json_text({k: v for k, v in value.items() if not k.startswith("_")}))
