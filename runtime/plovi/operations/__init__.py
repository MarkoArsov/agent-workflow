"""One command layer: every CLI operation people and agents use, with actor and reason."""
from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from ..util import WorkflowError, digest, json_text

RISKS = ("none", "low", "high")
REGISTRY: dict = {}
# Set by the CLI when this process continues work its launcher already recorded.
FORWARDED = False
WORKER = False


@dataclass(frozen=True)
class Operation:
    name: str
    summary: str
    usage: str
    arguments: dict
    mutates: bool
    risk: str
    apply: Callable
    preview: Callable | None = field(default=None)


def register(name, summary, usage, *, arguments=None, required=(), mutates, risk, preview=None):
    if risk not in RISKS or mutates != (risk != "none"):
        raise ValueError(f"{name}: risk and mutates disagree")
    properties = dict(arguments or {})
    if mutates:
        properties.update(ACTOR_ARGUMENTS)
    schema = {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}

    def wrap(function):
        REGISTRY[name] = Operation(name, summary, usage, schema, mutates, risk, function, preview)
        return function
    return wrap


ACTOR_ARGUMENTS = {
    "reason": {"type": "string", "description": "Why this change is made; recorded in the ledger"},
    "actor_agent": {"type": "string", "description": "Agent name; agents must always pass it"},
    "via": {"type": "string", "description": "Tool the agent acts through", "default": "cli"},
}


def catalog():
    _load()
    return [{"name": op.name, "summary": op.summary, "usage": op.usage, "arguments": op.arguments,
             "mutates": op.mutates, "risk": op.risk} for op in sorted(REGISTRY.values(), key=lambda o: o.name)]


def capture_environment():
    """Read and clear launcher markers so provider subprocesses never inherit them."""
    global FORWARDED, WORKER
    FORWARDED = os.environ.pop("PLOVI_FORWARDED", "") == "1" or FORWARDED
    WORKER = os.environ.pop("PLOVI_WORKER", "") == "1" or WORKER


def suppressed():
    """A forwarded or background process continues work whose operation events were already recorded."""
    return FORWARDED or WORKER


DEFAULT_REASONS = {
    "answer": "Answered with plovi answer",
    "approve": "Approved with plovi approve",
    "retry": "Retried with plovi retry",
    "pause": "Pause requested with plovi pause",
    "resume": "Resumed with plovi resume",
    "cancel": "Cancel requested with plovi cancel",
    "policy.set": "Policy changed with plovi policy set",
    "projects.add": "Project registered with plovi projects add",
    "projects.remove": "Project unregistered with plovi projects remove",
    "rebuild-state": "State rebuilt with plovi rebuild-state",
    "run": "Plan approved by starting it with plovi run",
    "pipeline": "Plan approved by starting it with plovi pipeline",
    "validate-plan": "Plan validated with plovi validate-plan",
    "task.start": "Task started with plovi task start",
    "setup": "Project registered by plovi setup",
}


def _name(value, flag):
    if not isinstance(value, str) or not value.strip() or len(value) > 100 or re.search(r"[\x00-\x1f]", value):
        raise WorkflowError(f"{flag} needs a short single-line name")
    return value.strip()


def person(root):
    from ..util import run
    try:
        name = run(["git", "config", "user.name"], Path(root), check=False).stdout.strip()
    except WorkflowError:
        name = ""
    return name or "local-user"


def actor(args, root):
    """The person or agent behind this call; --actor-agent always wins."""
    if args.get("actor_agent"):
        return {"kind": "agent", "name": _name(args["actor_agent"], "--actor-agent"),
                "via": _name(args.get("via") or "cli", "--via")}
    if args.get("actor"):
        return {"kind": "person", "name": _name(args["actor"], "--actor")}
    return {"kind": "person", "name": person(root)}


def reason(args, command):
    text = args.get("reason")
    if text is None:
        return DEFAULT_REASONS.get(command, f"Requested with plovi {command}")
    if not isinstance(text, str) or not text.strip():
        raise WorkflowError("--reason needs a short sentence")
    return text.strip()


def record(project, subject, kind, data, *, args, command):
    """Append an operation event unless the launching process already recorded it."""
    if suppressed():
        return None
    from .. import ledger
    return ledger.append(project, {"subject": subject, "type": kind, "actor": actor(args, project.root),
                                   "reason": reason(args, command), "data": data})


def task_subject(task):
    return {"kind": "task", "id": task}


def preview_digest(preview):
    return digest(json_text({k: v for k, v in preview.items() if k != "digest"}))


class Text(str):
    """Human output the CLI prints as-is; exit_code sets the process status."""
    exit_code = 0


def call(name, args):
    _load()
    if name not in REGISTRY:
        raise WorkflowError(f"Unknown operation: {name}. Run plovi commands to list them.")
    return REGISTRY[name].apply(dict(args))


def _load():
    from . import commands as _commands, inbox as _inbox, policy as _policy, projects as _projects, stats as _stats, tasks as _tasks  # noqa: F401
