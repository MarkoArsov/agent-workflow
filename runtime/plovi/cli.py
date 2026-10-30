"""The common CLI used by host skills and automated fixtures."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from . import __version__
from .util import WorkflowError, json_text, read_json, atomic_write

def context(args):
    from .project import resolve
    return resolve(Path(args.project or "."))

def parser():
    p = argparse.ArgumentParser(prog="plovi", description="One workflow, customized for each project.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--project", help="Configured project root; defaults to the current location")
    sub = p.add_subparsers(dest="command", required=True)
    from .model_policy.commands import arguments as model_arguments
    model_arguments(sub.add_parser("models", help="Refresh, review and evaluate workflow-local model routes"))
    policy = sub.add_parser("policy", help="Review project policy")
    policy_sub = policy.add_subparsers(dest="action", required=True)
    policy_sub.add_parser("show").add_argument("--json", action="store_true")
    edit = policy_sub.add_parser("set")
    edit.add_argument("key"); edit.add_argument("value"); edit.add_argument("--yes", action="store_true")
    setup = sub.add_parser("setup", help="Detect and preview configuration, then apply the approved proposal")
    setup.add_argument("path", nargs="?", default=".")
    setup.add_argument("--answers", type=Path)
    setup.add_argument("--output", type=Path)
    setup.add_argument("--apply", type=Path)
    setup.add_argument("--approve")
    sub.add_parser("inspect", help="Show the project and effective skill sources")
    sub.add_parser("refresh", help="Preview updated host discovery entries")
    skill = sub.add_parser("skill", help="List, resolve, copy, or create project-owned skills")
    skill.add_argument("action", choices=["list", "resolve", "copy", "new"])
    skill.add_argument("name", nargs="?")
    skill.add_argument("--description", default="A project-specific workflow.")
    for name in ("validate-plan", "preflight", "run", "verify"):
        command = sub.add_parser(name)
        command.add_argument("manifest", type=Path)
        if name == "verify":
            command.add_argument("--phase", choices=["red", "green"], default="green")
        if name in {"run", "preflight"}:
            command.add_argument("--trusted", action="store_true")
        if name == "run":
            command.add_argument("--no-wait", action="store_true")
            command.add_argument("--unattended", action="store_true", help=argparse.SUPPRESS)
            command.add_argument("--detach", action="store_true")
            command.add_argument("--dry-run", action="store_true")
    for name in ("status", "watch", "resume", "answer", "cancel", "retry", "approve"):
        command = sub.add_parser(name)
        command.add_argument("task")
        if name in ("resume", "answer", "retry", "approve"):
            command.add_argument("--rebind", action="store_true")
        if name == "retry":
            command.add_argument("--note", type=Path)
        if name == "approve":
            gate = command.add_mutually_exclusive_group(required=True)
            gate.add_argument("--size", action="store_true"); gate.add_argument("--paths", action="store_true")
            command.add_argument("--actor"); command.add_argument("--reason")
        if name == "answer":
            command.add_argument("--file", type=Path, required=True)
        if name == "watch":
            command.add_argument("--seconds", type=int, default=60)
    command = sub.add_parser("sync-base")
    command.add_argument("repositories", nargs="+")
    sub.add_parser("worktrees")
    command = sub.add_parser("rule")
    command.add_argument("action", choices=["list", "record"])
    command.add_argument("name", nargs="?")
    command.add_argument("--detail")
    command = sub.add_parser("connector")
    command.add_argument("action", choices=["list", "read", "preview", "apply"])
    command.add_argument("--name")
    command.add_argument("--capability")
    command.add_argument("--file", type=Path)
    command.add_argument("--target", type=Path)
    command.add_argument("--approve")
    command = sub.add_parser("github")
    command.add_argument("action", choices=["comments", "issue", "checks", "failure-log", "bots"])
    command.add_argument("repository")
    command.add_argument("value")
    command = sub.add_parser("environment")
    command.add_argument("action", choices=["status", "release"])
    command.add_argument("name")
    for name in ("update", "uninstall", "doctor"):
        command = sub.add_parser(name)
        command.add_argument("--global", dest="global_install", action="store_true")
        command.add_argument("--target", type=Path, help="Explicit project installation root")
        command.add_argument("--dry-run", action="store_true")
        command.add_argument("--backend", choices=["standalone", "claude-plugin"], default="standalone")
        if name == "update":
            command.add_argument("--local-source", type=Path)
    return p

def execute(args):
    if args.command == "policy":
        from . import policy
        project = context(args)
        return policy.effective(project) if args.action == "show" else policy.set_value(project, args.key, args.value, yes=args.yes)
    if args.command == "models":
        from .model_routing import execute as models_execute
        return models_execute(args)
    if args.command in {"update", "uninstall", "doctor"}:
        from . import install
        if args.global_install and args.target:
            raise WorkflowError("Choose either --global or --target")
        if args.backend == "claude-plugin":
            from .util import run
            verb = {"update": "update", "uninstall": "uninstall", "doctor": "list"}[args.command]
            argv = ["claude", "plugin", verb]
            if verb != "list":
                argv += ["plovi@plovi", "--scope", "user" if args.global_install else "project"]
            if args.dry_run:
                return {"argv": argv, "cwd": str(args.target or Path.cwd())}
            return {"output": run(argv, args.target or Path.cwd()).stdout}
        target = None if args.global_install else (args.target or context(args).root)
        if args.command == "doctor":
            result = install.doctor(target)
            if target:
                from .project import load
                from .policy import diagnostics
                from .migration import configuration
                if (configuration(Path(target)) / "project.json").is_file():
                    result["policy"] = diagnostics(load(Path(target)))
            return result
        if args.command == "uninstall":
            return install.uninstall(project=target, dry_run=args.dry_run)
        if not args.local_source:
            raise WorkflowError("Select a reviewed release checkout with --local-source (or use its pinned bootstrap)")
        return install.install(args.local_source, project=target, dry_run=args.dry_run)
    if args.command == "environment":
        from . import environments
        function = environments.status if args.action == "status" else environments.release
        return function(context(args), args.name)
    if args.command in {"validate-plan", "preflight", "run", "verify"}:
        from . import manifest, runner
        project = context(args)
        plan = manifest.load(args.manifest, project)
        if args.command == "verify":
            from . import verification, state
            saved = read_json(state.directory(project, plan["task"]) / "state.json", {})
            checkouts = saved.get("checkouts", {row["id"]: str(project.repo_path(row["id"])) for row in plan["repositories"]})
            checks = verification.run_checks(project, plan, checkouts, phase=args.phase)
            return {"status": "complete" if all(c["passed"] for c in checks) else "failed", "checks": checks}
        if args.command == "validate-plan":
            runner.binding(project, plan)
            return {"valid": True, "task": plan["task"]}
        if args.command == "preflight" or args.dry_run:
            from . import policy
            return runner.preflight(project, plan, execution=policy.execution(project, plan, trusted=args.trusted,
                                                                             unattended=getattr(args, "detach", False) or not sys.stdin.isatty()))
        return runner.detach(project, args.manifest, trusted=args.trusted, no_wait=args.no_wait) if args.detach else runner.run(
            project, plan, trusted=args.trusted, no_wait=args.no_wait, unattended=args.unattended or not sys.stdin.isatty())
    if args.command in {"status", "watch", "resume", "answer", "cancel", "retry", "approve"}:
        from . import state, runner, manifest
        project = context(args)
        if args.command == "cancel":
            return state.cancel(project, args.task)
        result = state.read(project, args.task)
        if args.command in {"resume", "answer", "retry", "approve"}:
            approval = None
            if args.command == "approve":
                from .util import git
                actor = args.actor or git(project.root, "config", "user.name", check=False)
                if not actor.strip():
                    raise WorkflowError("Configure git user.name or pass --actor to record the approval")
                kind = "size" if args.size else "protected_paths"
                approval = (kind, actor, args.reason or "Explicit --size approval" if args.size else args.reason or "Explicit --paths approval")
            plan = manifest.load(result["manifest_path"], project)
            return runner.run(project, plan, resume=True, rebind=args.rebind,
                              answer=args.file.read_text() if args.command == "answer" else None,
                              retry=args.command == "retry", note=args.note.read_text() if args.command == "retry" and args.note else None,
                              approval=approval)
        if args.command == "watch":
            import time
            deadline = time.monotonic() + min(max(args.seconds, 1), 3600)
            previous = None
            while time.monotonic() < deadline:
                result = state.read(project, args.task)
                current = {k: result.get(k) for k in ("status", "stage", "completed", "pending_input", "error")}
                if current != previous:
                    print(json.dumps(current), flush=True); previous = current
                if result["status"] not in {"starting", "running", "waiting"}:
                    break
                time.sleep(1)
        return result
    if args.command == "sync-base":
        from .git_ops import sync_base
        return sync_base(context(args), args.repositories)
    if args.command == "worktrees":
        from .git_ops import worktrees
        return worktrees(context(args))
    if args.command == "rule":
        from .rules import definitions, record
        if args.action == "list":
            return definitions(context(args))
        if not args.name or not args.detail:
            raise WorkflowError("Rule recording requires a name and --detail")
        return record(context(args), args.name, args.detail)
    if args.command == "connector":
        from .integrations import connectors
        if args.action == "list":
            return connectors.catalog(context(args))
        if args.action == "read":
            return connectors.invoke(context(args), args.name, args.capability, read_json(args.file, {}) if args.file else {})
        if args.action == "preview":
            if not args.target or not args.file or not args.name:
                raise WorkflowError("Connector preview needs --target, --name, and --file")
            return connectors.patch_proposal(args.target, args.name, read_json(args.file))
        if not args.file or not args.approve:
            raise WorkflowError("Connector apply needs a reviewed --file and --approve digest")
        return connectors.apply_patch(read_json(args.file), args.approve)
    if args.command == "github":
        from .integrations import github
        project = context(args); root = project.repo_path(args.repository); repo = project.repository(args.repository)
        functions = {"comments": github.comments, "issue": github.issue, "checks": github.checks,
                     "failure-log": github.failure_log, "bots": github.wait_bots}
        return functions[args.action](root, repo, args.value)
    if args.command == "setup":
        from .setup import propose, apply
        if args.apply:
            if not args.approve:
                raise WorkflowError("Review the proposal and supply its --approve digest")
            return apply(read_json(args.apply), args.approve)
        result = propose(Path(args.path), read_json(args.answers, {}) if args.answers else {})
        if args.output:
            atomic_write(args.output, json_text(result))
            return {"proposal": str(args.output), "approval": result["approval"], "questions": result["questions"],
                    "conflicts": result["conflicts"], "changed_files": [x["path"] for x in result["changes"]]}
        return result
    if args.command == "refresh":
        from .setup import propose
        return propose(context(args).root)
    if args.command == "inspect":
        from .extensions import catalog
        project = context(args)
        return {"root": str(project.root), "profile": project.profile, "skills": catalog(project)}
    if args.command == "skill":
        from .extensions import catalog, resolve_skill, copy_skill, new_skill
        project = context(args)
        if args.action == "list":
            return catalog(project)
        if not args.name:
            raise WorkflowError("Provide a skill name")
        if args.action == "resolve":
            return {"path": str(resolve_skill(args.name, project))}
        if args.action == "copy":
            return {"path": str(copy_skill(project, args.name)), "next": "Edit the project copy, then run refresh."}
        return {"path": str(new_skill(project, args.name, args.description)), "next": "Complete the procedure, then run refresh."}
    raise WorkflowError("Unknown command")

def main(argv=None):
    try:
        result = execute(parser().parse_args(argv))
        if result is not None:
            print(json_text(result), end="")
        return 1 if isinstance(result, dict) and result.get("status") in {"failed", "cancelled", "escalated"} else 0
    except (WorkflowError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
