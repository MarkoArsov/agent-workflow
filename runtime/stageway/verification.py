"""Execute checks and classify observed results, not agent claims."""
from __future__ import annotations
import os
import re
from pathlib import Path
from .manifest import command_for
from .process import execute
from .util import WorkflowError, contained, redact

SETUP_ERROR = re.compile(r"ModuleNotFoundError|ImportError|SyntaxError|IndentationError|"
                         r"command not found|No module named|error CS\d+|error: could not compile|"
                         r"ERROR collecting|Failed to load|Cannot find module|Bail out!", re.I)

def parse(check, output, code, phase="green"):
    parser = check.get("parser", "generic")
    failures = []
    if SETUP_ERROR.search(output):
        failures.append("setup/compile failure is not assertion evidence")
    if check.get("identities") and not all(re.search(re.escape(name), output) for name in check["identities"]):
        failures.append("expected test identity is absent from output")
    skipped = bool(re.search(r"\b[1-9]\d*\s+(?:skipped|pending|todo)\b|skipped=[1-9]|#\s*(?:SKIP|TODO)\b", output, re.I))
    if skipped and not check.get("approved_skip_reason"):
        failures.append("skipped/pending checks need an explicit plan justification")
    success = assertion = False
    if parser == "unittest":
        success = bool(re.search(r"Ran [1-9]\d* tests?", output) and re.search(r"^OK(?:\s|$)", output, re.M))
        assertion = bool(re.search(r"^FAIL:", output, re.M) and "AssertionError" in output and not re.search(r"^ERROR:", output, re.M))
    elif parser == "pytest":
        success = bool(re.search(r"\b[1-9]\d* passed\b", output)) and not re.search(r"\b[1-9]\d* (?:failed|errors?)\b", output)
        assertion = bool(re.search(r"FAILED .+ - (?:assert|AssertionError)", output)) and not re.search(r"\bERROR\b", output)
    elif parser == "dotnet":
        success = bool(re.search(r"Passed!\s+.*Failed:\s+0.*Passed:\s+[1-9]", output))
        assertion = bool(re.search(r"Failed\s+.+", output) and re.search(r"Assert\.\w+|AssertionException|Expected:.*", output))
    elif parser == "jest":
        success = bool(re.search(r"Tests:\s+.*[1-9]\d* passed", output)) and not re.search(r"[1-9]\d* failed", output)
        assertion = bool(re.search(r"Tests:\s+.*[1-9]\d* failed", output) and re.search(r"Expected:|expect\(", output))
    elif parser == "tap":
        success = bool(re.search(r"^1\.\.[1-9]\d*", output, re.M)) and not re.search(r"^not ok", output, re.M)
        assertion = bool(re.search(r"^not ok", output, re.M) and re.search(r"expected:|operator:", output))
    else:
        success = bool(re.search(check["success_pattern"], output, re.M))
        assertion = bool(check.get("failure_pattern") and re.search(check["failure_pattern"], output, re.M))
    if phase == "red":
        if parser == "unittest" and any(not re.search(r"^FAIL: " + re.escape(name) + r"(?:\s|\(|$)", output, re.M) for name in check.get("identities", [])):
            failures.append("expected tests did not produce the assertion failures")
        if parser == "pytest" and any(not re.search(r"^FAILED [^\n]*" + re.escape(name), output, re.M) for name in check.get("identities", [])):
            failures.append("expected tests did not produce the assertion failures")
        if code == 0 or not assertion:
            failures.append("no observed assertion-level failure")
    elif code != 0 or not success or assertion:
        failures.append("check did not produce successful evidence")
    return {"passed": not failures, "problems": failures, "parser": parser,
            "phase": phase, "identities": check.get("identities", [])}

def command_environment(command, inherited=None):
    env = dict(os.environ)
    env.update(inherited or {})
    env.update({str(k): str(v) for k, v in command.get("env", {}).items()})
    for name in command.get("env_refs", []):
        if name not in env:
            raise WorkflowError(f"Command requires environment variable {name}")
    return env

def check(project, definition, checkouts, *, phase="green", cancel=None, environment=None):
    command = command_for(project, definition)
    root = Path(checkouts[definition["repository"]])
    cwd = contained(root, command.get("cwd", "."))
    result = execute(command["argv"], cwd, env=command_environment(command, environment),
                     timeout=command.get("timeout_seconds", 300),
                     inactivity=command.get("inactivity_seconds", command.get("timeout_seconds", 300)),
                     cancel=cancel)
    spec = dict(definition)
    if spec.get("parser", "generic") == "generic":
        spec.setdefault("success_pattern", command.get("success_pattern"))
    evidence = parse(spec, result["output"], result["exit_code"], phase)
    if result["reason"]:
        evidence["passed"] = False
        evidence["problems"].append(result["reason"])
    return evidence | result | {"id": definition["id"], "repository": definition["repository"],
                                "command": redact(" ".join(command["argv"]))}

def run_checks(project, manifest, checkouts, *, phase="green", names=None, cancel=None):
    selected = [c for c in manifest["checks"] if (c["id"] in names if names is not None else phase in c.get("phases", ["green"]))]
    if not selected:
        raise WorkflowError(f"No {phase} checks selected")
    from contextlib import ExitStack
    from .environments import lease
    with ExitStack() as stack:
        environments = {}
        for definition in selected:
            name = definition.get("environment")
            if name and name not in environments:
                environments[name] = stack.enter_context(lease(project, name, checkouts, cancel))
        return [check(project, c, checkouts, phase=phase,
                      cancel=environments[c["environment"]][1] if c.get("environment") else cancel,
                      environment=environments[c["environment"]][0] if c.get("environment") else None) for c in selected]
