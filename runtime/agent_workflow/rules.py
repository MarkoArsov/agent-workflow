"""Deterministic checks block; recurring prose findings request a corrective review."""
from __future__ import annotations
import json
import re
from pathlib import Path
from .manifest import matches
from .process import execute
from .profile import validate_command
from .util import WorkflowError, contained, identifier, read_json, write_json
from .verification import command_environment

SECRET = re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|"
                    r"\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b|"
                    r"\bsk-[A-Za-z0-9]{30,}\b")

def definitions(project):
    directory = contained(project.root, project.profile["extensions"]["rules"])
    result = []
    for path in sorted(directory.glob("*.json")):
        rule = read_json(path)
        identifier(rule.get("id", ""))
        if rule.get("enforcement") not in {"blocking", "advisory", "prose"} or not rule.get("guidance"):
            raise WorkflowError(f"Invalid rule: {path.name}")
        if rule["enforcement"] == "blocking" and not rule.get("command") and not rule.get("forbidden_pattern"):
            raise WorkflowError("Blocking rules require a deterministic detector")
        if rule.get("command"):
            validate_command(rule["command"])
        if rule.get("forbidden_pattern"):
            re.compile(rule["forbidden_pattern"])
        result.append(rule)
    return result

def evaluate(project, changed, checkouts, *, cancel=None):
    findings = []
    rules = definitions(project)
    for repo, paths in changed.items():
        root = Path(checkouts.get(repo, project.repo_path(repo.split(":")[0])))
        for name in paths:
            path = root / name
            if path.is_symlink() and not path.resolve().is_relative_to(root.resolve()):
                findings.append({"rule": "external-symlink", "enforcement": "blocking", "path": f"{repo}/{name}"})
            if not path.is_file() or path.is_symlink():
                continue
            content = path.read_bytes().decode(errors="replace")
            if SECRET.search(content):
                findings.append({"rule": "secret-material", "enforcement": "blocking", "path": f"{repo}/{name}"})
            for rule in rules:
                if rule.get("repositories") and repo not in rule["repositories"]:
                    continue
                if not matches(name, rule.get("paths", ["**"])):
                    continue
                if rule.get("forbidden_pattern") and re.search(rule["forbidden_pattern"], content):
                    findings.append({"rule": rule["id"], "enforcement": rule["enforcement"], "path": f"{repo}/{name}"})
        for rule in rules:
            if not rule.get("command") or not any(matches(name, rule.get("paths", ["**"])) for name in paths):
                continue
            if rule.get("repositories") and repo not in rule["repositories"]:
                continue
            command = rule["command"]
            result = execute(command["argv"], contained(root, command.get("cwd", ".")),
                             timeout=command.get("timeout_seconds", 300), env=command_environment(command), cancel=cancel)
            if result["exit_code"] or result["reason"]:
                findings.append({"rule": rule["id"], "enforcement": rule["enforcement"], "repository": repo,
                                 "detail": result["output"]})
    return findings

def record(project, rule_id, detail):
    rule = next((r for r in definitions(project) if r["id"] == rule_id), None)
    if not rule:
        raise WorkflowError("Unknown project rule")
    path = project.config / "local/rule-history.json"
    history = read_json(path, {})
    entries = history.setdefault(rule_id, [])
    entries.append(detail)
    write_json(path, history)
    proposal = None
    if len(entries) >= rule.get("review_after", 3):
        proposal = {"rule": rule_id, "occurrences": len(entries),
                    "next": "Review the repeated examples. Propose a reliable detector if possible; otherwise clarify scope, examples, or the workflow checkpoint.",
                    "enforcement_change": "none; requires a reviewed rule edit"}
    return {"recorded": rule_id, "corrective_review": proposal}

