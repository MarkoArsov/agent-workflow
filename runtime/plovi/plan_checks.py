"""validate-plan --run-checks: run every named check once in the task checkout and say whether it can pass.

A check passes planning when it `ran`: the tool started, finished in time, left the checkout unchanged
and printed output its parser understands, whatever the test result. Tests the plan adds don't exist
yet, so a failing or missing test module still counts as ran."""
from __future__ import annotations
import json
import os
import re
import shutil
from pathlib import Path
from . import verification
from .manifest import command_for
from .util import WorkflowError, atomic_write, contained, read_json, run as run_command, write_json

RESULTS = "planning-checks.json"
RECOGNISED = {
    "unittest": r"^Ran \d+ tests?\b",
    "pytest": r"\b\d+ (?:passed|failed|errors?|skipped|deselected)\b|\bno tests ran\b|ERROR: (?:file or directory )?not found",
    "dotnet": r"Passed!|Failed!|Total tests:|error CS\d+|Build FAILED",
    "jest": r"^Tests:\s|No tests found",
    "tap": r"^1\.\.\d+|^(?:not )?ok\b",
}


def checkouts_for(project, plan):
    """The task's own checkouts: the task-start receipt, then a saved run. Never the person's main checkout."""
    from .state import directory
    from .tasks import receipt_path
    task = plan["task"]
    receipt = read_json(receipt_path(project, task), {})
    found = {row["repository"]: row["path"] for row in receipt.get("repositories", []) if row.get("path")}
    if not found:
        found = read_json(directory(project, task) / "state.json", {}).get("checkouts", {})
    needed = {row["id"] for row in plan["repositories"]}
    if not found or needed - set(found) or any(not Path(found[name]).is_dir() for name in needed):
        raise WorkflowError(f"No task checkout for {task}. Run plovi task start {task}, then validate again.")
    return {name: found[name] for name in needed}


def changed_paths(root):
    # Unstripped: the first porcelain line may start with a space.
    return set(run_command(["git", "-C", root, "status", "--porcelain", "--untracked-files=all"], root).stdout.splitlines())


def resolvable(argv0, cwd, env):
    if os.path.dirname(argv0):
        path = Path(argv0) if Path(argv0).is_absolute() else cwd / argv0
        return path.exists() or (os.name == "nt" and path.with_suffix(".exe").exists())
    return shutil.which(argv0, path=env.get("PATH")) is not None


def classify(project, plan, definition, checkouts):
    name, repository = definition["id"], definition["repository"]
    command = command_for(project, definition)
    argv = [str(arg) for arg in command["argv"]]
    root = Path(checkouts[repository])

    def row(result, fix=None, seconds=0.0, code=None):
        return {"id": name, "result": result, "seconds": round(seconds, 1),
                "detail": fix or f"exit {code}", "fix": fix}

    relative = command.get("cwd", ".")
    try:
        cwd = contained(root, relative)
    except WorkflowError:
        cwd = None
    if cwd is None or not cwd.is_dir():
        return row("bad-cwd", f"{name}: bad-cwd: {relative} does not exist in {repository}. "
                              "Fix the check's cwd; it is relative to the repository.")
    from .isolation import active
    if (active.get() or {}).get("mode") != "container":
        if not resolvable(argv[0], cwd, verification.command_environment(command)):
            if os.path.dirname(argv[0]):
                return row("missing-tool", f"{name}: missing-tool: {argv[0]} does not exist in {repository}'s task checkout. "
                                           "Use the project's documented interpreter as it exists there, or a named command that has it.")
            return row("missing-tool", f"{name}: missing-tool: {argv[0]} is not on PATH. Install it, "
                                       "or use a named repository command that has it.")
    before = changed_paths(root)
    result = verification.run_checks(project, plan, checkouts, names=[name])[0]
    seconds, code, output = result.get("duration_seconds") or 0.0, result["exit_code"], result.get("output") or ""
    after = changed_paths(root)
    if result.get("reason") in {"timeout", "inactive"}:
        limit = command.get("timeout_seconds", 300)
        return row("timeout", f"{name}: timeout: still running after {limit} s. Raise timeout_seconds, "
                              "or narrow the check and run the full command as a final check.", seconds)
    program = Path(argv[0]).name
    if (len(argv) > 2 and argv[1] == "-m" and verification.PYTHON.search(program) and code != 0
            and re.search(r"No module named '?" + re.escape(argv[2].split(".")[0]) + r"\b", output)):
        return row("missing-tool", f"{name}: missing-tool: {program} has no {argv[2]}. Use the project's documented "
                                   "interpreter (for example .venv/bin/python) or a named command that has it.", seconds)
    if after != before:
        paths = ", ".join(sorted(line[3:] for line in after ^ before))
        return row("modifies-files", f"{name}: modifies-files: changed {paths}. Write its output outside the "
                                     "repository or to an ignored path; plovi doesn't clean it up.", seconds)
    parser = definition.get("parser", "generic")
    if parser in RECOGNISED and not re.search(RECOGNISED[parser], output, re.M):
        return row("unparseable", f"{name}: unparseable: exit {code} but the {parser} parser found no result line. "
                                  "Use the parser that matches the tool's real output, or generic.", seconds)
    pattern = definition.get("success_pattern", command.get("success_pattern"))
    if pattern and code == 0 and not re.search(pattern, output, re.M):
        return row("unparseable", f'{name}: unparseable: exit 0 but success_pattern "{pattern}" never appeared. '
                                  "Remove the pattern (exit code is authoritative) or match the tool's real output.", seconds)
    return row("ran", seconds=seconds, code=code)


def bind(manifest_path):
    """Add planning-checks.json to plan_files so plan_sha256, and so plan approval, covers the results."""
    raw = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if RESULTS not in raw.get("plan_files", []):
        raw.setdefault("plan_files", []).append(RESULTS)
        atomic_write(Path(manifest_path), json.dumps(raw, indent=2, ensure_ascii=False) + "\n")


def run(project, plan):
    """Classify every check, write planning-checks.json beside the manifest and bind it into the plan."""
    checkouts = checkouts_for(project, plan)
    with verification.checks_context(project, plan, checkouts):
        rows = [classify(project, plan, definition, checkouts) for definition in plan["checks"]]
    directory = Path(plan["_directory"])
    write_json(directory / RESULTS, {"version": 1, "checks": [{k: row[k] for k in ("id", "result", "seconds", "detail")}
                                                              for row in rows]})
    bind(plan["_path"])
    return rows


def table(task, rows):
    failed = [row for row in rows if row["result"] != "ran"]
    width = max([len("Check")] + [len(row["id"]) for row in rows])
    lines = [f"{'Check':<{width}}  {'Result':<14}  Seconds"]
    lines += [f"{row['id']:<{width}}  {row['result']:<14}  {row['seconds']:.1f}" for row in rows]
    if failed:
        lines += ["", f"{len(failed)} of {len(rows)} checks can't pass as planned for {task}. Fix the plan, then validate again:"]
        lines += [row["fix"] for row in failed]
    else:
        lines += ["", f"All {len(rows)} checks ran. Results are in {RESULTS}, bound into the plan."]
    return "\n".join(lines) + "\n"
