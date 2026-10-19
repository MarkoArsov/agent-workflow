"""Agent Flow adapter for the independently distributable policy component."""
from pathlib import Path
from .model_policy.storage import Store
from .util import user_data


def store(project=None):
    return Store(user_data() / "models", project.config / "models.json" if project else None,
                 project.profile["agents"] if project else ("codex", "claude", "cursor"),
                 project.profile["pipeline"]["routes"] if project else {}, "agentflow")


def execute(args):
    from .model_policy.commands import execute as dispatch
    from .project import resolve
    from .util import WorkflowError
    project = None
    try:
        project = resolve(Path(args.project or "."))
    except WorkflowError:
        if args.project or args.scope in {"project", "both"}:
            raise
    return dispatch(args, store(project), project.root if project else Path.cwd())
