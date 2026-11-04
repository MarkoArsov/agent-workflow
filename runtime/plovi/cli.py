"""The common CLI used by host skills and automated fixtures."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from . import __version__
from .util import WorkflowError, json_text, read_json, atomic_write, is_interactive

def context(args):
    from .project import resolve
    return resolve(Path(args.project or "."))

def actor_flags(command, *, reason=True):
    """Every mutating command records who acted and why."""
    if reason:
        command.add_argument("--reason", help="Why; recorded in the ledger with the actor")
    command.add_argument("--actor-agent", metavar="NAME", help="Record an agent as the actor; agents must always pass it")
    command.add_argument("--via", default="cli", help="Tool the agent acts through (default: cli)")


def output_format(command):
    command.add_argument("--format", choices=["text", "json"], help="Output format")


def parser():
    p = argparse.ArgumentParser(prog="plovi", description="One workflow, customized for each project.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--project", help="Configured project root; defaults to the current location")
    sub = p.add_subparsers(dest="command", required=True)
    command = sub.add_parser("self-update", help="Keep a linked development install current (checkout and skill discovery)")
    command.add_argument("--now", action="store_true", help="Fetch and fast-forward now, then refresh discovery")
    command.add_argument("--follow", choices=["on", "off"], help="Turn automatic updates on or off")
    command.add_argument("--interval", type=int, metavar="MINUTES", help="Minutes between update checks (default 60)")
    command.add_argument("--background", action="store_true", help=argparse.SUPPRESS)
    from .model_policy.commands import arguments as model_arguments
    model_arguments(sub.add_parser("models", help="Refresh, review and evaluate workflow-local model routes"))
    policy = sub.add_parser("policy", help="Review project policy")
    policy_sub = policy.add_subparsers(dest="action", required=True)
    policy_sub.add_parser("show").add_argument("--json", action="store_true")
    edit = policy_sub.add_parser("set", help="Change one policy value; preview first, then apply by digest")
    edit.add_argument("key"); edit.add_argument("value"); edit.add_argument("--yes", action="store_true", help="Person shortcut after reviewing the diff")
    edit.add_argument("--approve", metavar="DIGEST", help="Apply the previewed change with this digest")
    actor_flags(edit)
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
            command.add_argument("--phase", choices=["setup", "red", "green"], default="green")
            command.add_argument('--check', action='append', dest='checks', help='Run only named contract checks')
        if name in {"run", "preflight"}:
            command.add_argument("--trusted", action="store_true")
            command.add_argument('--pull-isolation-image', action='store_true', help='Consent once to pulling the configured container image')
        if name in {"run", "validate-plan"}:
            actor_flags(command)
        if name == "validate-plan":
            command.add_argument("--run-checks", action="store_true",
                                 help="Run every named check once in the task checkout; fail the plan when one can't pass")
            command.add_argument("--json", action="store_true", help="Print JSON")
        if name == "run":
            command.add_argument("--no-wait", action="store_true")
            command.add_argument("--unattended", action="store_true", help=argparse.SUPPRESS)
            command.add_argument("--detach", action="store_true")
            command.add_argument("--dry-run", action="store_true")
    migrate = sub.add_parser("migrate", help="Prepare a reviewed legacy test checkpoint without restarting implementation")
    migrate.add_argument("task")
    migrate.add_argument("--apply", action="store_true")
    pipeline = sub.add_parser("pipeline", help="Start or recover an approved task and attach tracking")
    pipeline.add_argument("target", help="Approved manifest path or saved task ID")
    pipeline.add_argument("--no-watch", action="store_true")
    pipeline.add_argument("--rebind", action="store_true")
    pipeline.add_argument("--upgrade-runtime", action="store_true")
    pipeline.add_argument("--trusted", action="store_true")
    pipeline.add_argument("--no-wait", action="store_true")
    pipeline.add_argument("--json", action="store_true")
    actor_flags(pipeline)
    helps = {"status": "Show a task's progress, or list every task", "pause": "Stop a running task before its next stage",
             "resume": "Continue a stopped task", "answer": "Answer a task's question", "cancel": "Cancel a task",
             "retry": "Retry an escalated task", "approve": "Approve a plan or a diff gate", "watch": "Follow a task"}
    for name in ("status", "watch", "resume", "answer", "cancel", "retry", "approve", "pause"):
        command = sub.add_parser(name, help=helps[name])
        command.add_argument("task", nargs="?" if name == "status" else None)
        if name in ("resume", "answer", "retry", "approve"):
            command.add_argument("--rebind", action="store_true")
            command.add_argument("--upgrade-runtime", action="store_true")
        if name == "resume":
            command.add_argument("--budget-minutes", type=int, help="Raise this task's time budget")
            command.add_argument("--budget-attempts", type=int, help="Raise this task's attempt budget")
            command.add_argument("--budget-cost", type=float, help="Raise this task's known cost budget in US dollars")
        if name == "retry":
            command.add_argument("--note", type=Path)
        if name == "approve":
            gate = command.add_mutually_exclusive_group(required=True)
            gate.add_argument("--plan", action="store_true", help="Approve the task's current plan by its hash")
            gate.add_argument("--size", action="store_true"); gate.add_argument("--paths", action="store_true")
            command.add_argument("--actor", help="Person name to record; defaults to git user.name")
            command.add_argument("--approve", metavar="DIGEST", help="Digest from the preview; required for --plan and for agents")
            command.add_argument("--manifest", type=Path, help="Plan manifest when plovi cannot find it")
        if name == "answer":
            answer = command.add_mutually_exclusive_group(required=True)
            answer.add_argument("--file", type=Path); answer.add_argument("--text")
        if name in {"resume", "answer", "cancel", "retry", "approve", "pause"}:
            actor_flags(command)
        if name in {"status", "watch"}:
            command.add_argument("--json", action="store_true")
            command.add_argument("--verbose", action="store_true")
        if name == "status":
            output_format(command)
        if name == "watch":
            command.add_argument("--seconds", type=int, default=None)
    output_format(sub.add_parser("inbox", help="List what needs you across registered projects"))
    events = sub.add_parser("events", help="List ledger events")
    events.add_argument("--task"); events.add_argument("--since", help="ISO timestamp or event ID")
    output_format(events)
    stats = sub.add_parser("stats", help="Report run statistics from the ledger; --gate checks the stable-enough gate")
    stats.add_argument("--since", help="ISO date or time, or a duration such as 7d, 12h or 30m")
    stats.add_argument("--task"); stats.add_argument("--json", action="store_true"); stats.add_argument("--gate", action="store_true")
    projects = sub.add_parser("projects", help="Register, list and remove projects")
    projects_sub = projects.add_subparsers(dest="action", required=True)
    added = projects_sub.add_parser("add", help="Register a configured project")
    added.add_argument("path", type=Path); actor_flags(added)
    output_format(projects_sub.add_parser("list", help="List registered projects"))
    removed = projects_sub.add_parser("remove", help="Unregister a project; files stay on disk")
    removed.add_argument("id"); actor_flags(removed)
    rebuild = sub.add_parser("rebuild-state", help="Rebuild state.json from the ledger")
    rebuild.add_argument("task"); actor_flags(rebuild)
    commands = sub.add_parser("commands", help="List every operation for agents and the app")
    commands.add_argument("--json", action="store_true"); output_format(commands)
    command = sub.add_parser("sync-base")
    command.add_argument("repositories", nargs="+")
    sub.add_parser("worktrees")
    clean = sub.add_parser('clean', help='Remove owned clean worktrees for recorded cancelled/merged/closed tasks')
    clean.add_argument('--older-than', help='Minimum elapsed terminal age, for example 7d')
    task = sub.add_parser("task", help="Allocate an isolated task worktree before specification")
    task.add_argument("action", choices=["start"])
    task.add_argument("name")
    task.add_argument("--repository", action="append", help="Writable repository ID; required when several exist")
    task.add_argument("--base", help="Explicit local base ref; defaults to each repository's configured base")
    task.add_argument("--resume", action="store_true", help="Resume only this task's existing owned allocation")
    task.add_argument("--issue", help="Issue reference this task implements, for example owner/repo#12")
    task.add_argument("--title", help="Issue title shown in the inbox")
    actor_flags(task)
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

def watch(project, task, *, seconds=None, json_output=False):
    import time
    from . import state
    from .progress import summary, human, read_events, event_text
    deadline = None if seconds is None else time.monotonic() + min(max(seconds, 1), 3600)
    previous = None; last_print = 0
    _, cursor = read_events(state.directory(project, task))
    while True:
        result = state.observe(project, task)
        current = summary(result)
        events, cursor = read_events(state.directory(project, task), cursor)
        for event in events:
            if event.get("run_id") == current.get("run_id"):
                if json_output or event.get("event") != "heartbeat":
                    print(json.dumps(event) if json_output else event_text(dict(event, task=task)), flush=True)
        signature = {k: v for k, v in current.items() if k not in {"heartbeat_at", "activity_at"}}
        now = time.monotonic()
        if signature != previous or now - last_print >= 15:
            print(json.dumps(current) if json_output else human(current), flush=True)
            previous = signature; last_print = now
        if result.get("status") not in {"starting", "running", "waiting"} or (deadline is not None and now >= deadline):
            return current
        time.sleep(.2)


OPERATIONS = {"status", "inbox", "events", "stats", "answer", "approve", "retry", "pause", "resume", "cancel",
              "policy", "projects", "rebuild-state", "commands", "validate-plan"}


def operation_name(args):
    if args.command in {"policy", "projects"}:
        return f"{args.command}.{args.action}"
    return args.command


def execute(args):
    if args.command in OPERATIONS:
        from . import operations
        values = {key: (str(value) if isinstance(value, Path) else value) for key, value in vars(args).items()}
        return operations.call(operation_name(args), values)
    if args.command == "migrate":
        from .checkpoints import migrate
        return migrate(context(args), args.task, apply=args.apply)
    if args.command == "pipeline":
        from .entrypoint import launch
        project = context(args)
        result = launch(project, args.target, rebind=args.rebind, trusted=args.trusted, no_wait=args.no_wait)
        if not args.no_watch and result.get("tracking", {}).get("mode") in {"auto", "current-terminal"} and is_interactive(sys.stdout) and result.get("status") in {"starting", "running", "waiting"}:
            args._watched = True
            return watch(project, result["task"], json_output=args.json)
        return result
    if args.command == "task":
        from .tasks import start
        project = context(args)
        result = start(project, args.name, repositories=args.repository, base=args.base, resume=args.resume)
        if not args.resume:
            from .operations.tasks import task_started
            task_started(project, result, vars(args))
        return result
    if args.command == "self-update":
        from . import selfupdate
        return selfupdate.command(args)
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
            with verification.checks_context(project, plan, checkouts, saved):
                if args.checks and set(args.checks) - {c['id'] for c in plan['checks']}:
                    raise WorkflowError('Unknown named check; choose IDs from the task contract')
                checks = verification.run_checks(project, plan, checkouts, phase=args.phase, names=args.checks)
            return {"status": "complete" if all(c["passed"] for c in checks) else "failed", "checks": checks}
        if args.command == "preflight" or args.dry_run:
            from . import policy
            from . import factory
            unattended = getattr(args, 'detach', False) or not is_interactive()
            saved = read_json(__import__('plovi.state', fromlist=['directory']).directory(project, plan['task']) / 'state.json', {})
            execution = saved.get('execution') or policy.execution(project, plan, trusted=args.trusted, unattended=unattended)
            strategies = factory.strategies(project, plan, unattended=unattended, prior=saved)
            # Report only: checkouts are allocated when a run starts, never by a preview.
            execution['checkout_strategies'] = strategies
            result = runner.preflight(project, plan, execution=execution, pull_isolation_image=args.pull_isolation_image)
            result['checkout_strategies'] = strategies
            if 'factory' in strategies.values() and not saved:
                result['allocation'] = 'Factory checkouts are created when the run starts.'
            return result
        if args.detach:
            return runner.detach(project, args.manifest, trusted=args.trusted, no_wait=args.no_wait, pull_isolation_image=args.pull_isolation_image)
        from . import operations
        from .operations.plans import worker_gate
        # Only the background worker enforces a prior plan approval; explicit runs approved it at launch.
        gate = bool(args.unattended or operations.WORKER) and worker_gate(project, plan)
        return runner.run(project, plan, trusted=args.trusted, no_wait=args.no_wait, unattended=args.unattended or not is_interactive(),
                          pull_isolation_image=args.pull_isolation_image, require_plan_approval=gate)
    if args.command == "watch":
        from . import state
        project = context(args)
        state.observe(project, args.task)
        return watch(project, args.task, seconds=args.seconds, json_output=args.json)
    if args.command == "sync-base":
        from .git_ops import sync_base
        return sync_base(context(args), args.repositories)
    if args.command == 'clean':
        from .factory import clean
        return {'removed': clean(context(args), older_than=args.older_than)}
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

def legacy_argv(command, argv):
    """Arguments an older pinned runtime understands; this process recorded the control-plane flags."""
    valued = {"--reason", "--actor-agent", "--via"} if command in {"run", "pipeline"} else set()
    if command == "status":
        valued.add("--format")
    result, items = [], iter(argv)
    for item in items:
        name, separator, inline = item.partition("=")
        if item == "--upgrade-runtime":
            continue  # Never forward the upgrade into the immutable target recursively.
        if name in valued:
            value = inline if separator else next(items, "")
            if name == "--format" and value == "json":
                result.append("--json")
            continue
        result.append(item)
    return result


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        if args.command != "self-update" and not getattr(args, "unattended", False):
            from . import selfupdate
            selfupdate.maybe_refresh()
        from . import operations
        operations.capture_environment()
        if getattr(args, "upgrade_runtime", False) and not getattr(args, "rebind", False):
            raise WorkflowError("Runtime upgrade requires an explicitly reviewed --rebind")
        if args.command in {"run", "pipeline", "watch", "verify", "migrate"} or (args.command == "status" and args.task):
            from . import runtime_pin, manifest
            from .util import package_root
            project = context(args)
            if args.command in {"run", "verify"}: task = manifest.load(args.manifest, project)["task"]
            elif args.command == "pipeline":
                task = manifest.load(Path(args.target), project)["task"] if Path(args.target).is_file() else args.target
            else: task = args.task
            if args.command in {"run", "pipeline"}:
                from .operations.tasks import before_launch
                before_launch(project, {key: (str(value) if isinstance(value, Path) else value) for key, value in vars(args).items()})
            forwarded = legacy_argv(args.command, list(sys.argv[1:] if argv is None else argv))
            code = runtime_pin.dispatch(project, task, forwarded, source=package_root(),
                                        create=(args.command == "migrate" and args.apply) or args.command == "pipeline" or (args.command == "run" and not args.dry_run),
                                        upgrade=getattr(args, "upgrade_runtime", False))
            if code is not None: return code
        result = execute(args)
        if isinstance(result, int) and not isinstance(result, bool):
            return result  # A pinned runtime continued the task and printed its own result.
        if isinstance(result, operations.Text):
            print(result, end="")
            return result.exit_code
        if result is not None and args.command != "watch" and not getattr(args, "_watched", False):
            if args.command == "status" and not args.json and not args.verbose and args.format != "json":
                from .progress import human
                print(human(result))
            else:
                print(json_text(result), end="")
        stopped = {"failed", "cancelled", "escalated"}
        if args.command in {"watch", "pipeline"}: stopped |= {"needs_input", "needs_approval", "interrupted"}
        return 1 if isinstance(result, dict) and result.get("status") in stopped else 0
    except (WorkflowError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
