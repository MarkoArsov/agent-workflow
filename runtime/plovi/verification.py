"""Execute checks and classify observed results, not agent claims."""
from __future__ import annotations
import os
import re
from pathlib import Path
from .manifest import command_for
from .isolation import execute
from .util import WorkflowError, contained, redact

SETUP_ERROR = re.compile(r"ModuleNotFoundError|ImportError|SyntaxError|IndentationError|"
                         r"command not found|No module named|error CS\d+|error: could not compile|"
                         r"ERROR collecting|Failed to load|Cannot find module|Bail out!", re.I)

SKIP_COUNTS = {
    "unittest": r"skipped=(\d+)",
    "pytest": r"\b(\d+) skipped\b",
    "dotnet": r"Skipped:\s*(\d+)",
    "jest": r"Tests:[^\n]*?\b(\d+) skipped\b",
}


def skip_count(parser, output):
    """Skipped, pending or todo tests the output reports; 0 when it reports none."""
    if parser == "tap":
        return len(re.findall(r"#\s*(?:SKIP|TODO)\b", output, re.I))
    match = re.search(SKIP_COUNTS.get(parser, r"\b(\d+)\s+(?:skipped|pending|todo)\b"), output, re.I)
    return int(match[1]) if match else 0


def skipped_identities(identities, output):
    """Planned tests named on a per-test line that says skipped (unittest -v, pytest -v)."""
    return [name for name in identities
            if re.search(r"^[^\n]*(?<![\w.])" + re.escape(name) + r"(?![\w])[^\n]*\b(?:skipped|SKIPPED)\b", output, re.M)]


def parse(check, output, code, phase="green"):
    """Green: exit 0, no parser failures, every identity present, and success_pattern when set.
    Skips are advisory unless a planned identity was skipped or the check sets skips = "fail"."""
    parser = check.get("parser", "generic")
    failures = []
    if SETUP_ERROR.search(output):
        failures.append("setup/compile failure is not assertion evidence")
    if check.get("identities") and not all(re.search(re.escape(name), output) for name in check["identities"]):
        failures.append("expected test identity is absent from output")
    skipped = skip_count(parser, output)
    for name in skipped_identities(check.get("identities", []), output):
        failures.append(f"planned test {name} was skipped")
    if skipped and check.get("skips") == "fail":
        failures.append(f"{skipped} skipped; this check sets skips = \"fail\"")
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
        pattern = check.get("success_pattern")
        success = not pattern or bool(re.search(pattern, output, re.M))
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
    counts = None
    if parser == "unittest":
        ran = re.search(r"^Ran ([1-9]\d*) tests?", output, re.M)
        if ran and (success or assertion):
            counts = {"tests": int(ran[1])}
            for key, pattern in (("failures", r"failures=(\d+)"), ("errors", r"errors=(\d+)"), ("skipped", r"skipped=(\d+)")):
                match = re.search(pattern, output)
                counts[key] = int(match[1]) if match else 0
    if parser == "pytest" and (success or assertion):
        found = {key: int(m[1]) for key in ("passed", "failed", "skipped", "error")
                 for m in [re.search(r"\b(\d+) " + key + r"(?:s|ed)?\b", output)] if m}
        if found:
            counts = {"tests": sum(found.values()), "failures": found.get("failed", 0),
                      "errors": found.get("error", 0), "skipped": found.get("skipped", 0)}
    result = {"passed": not failures, "problems": failures, "parser": parser, "counts": counts,
              "phase": phase, "identities": check.get("identities", []), "skipped": skipped}
    if check.get("approved_skip_reason"):
        result["approved_skip_reason"] = check["approved_skip_reason"]
    return result

from contextlib import contextmanager


@contextmanager
def checks_context(project, plan, checkouts, saved=None):
    """Run named checks the way the task's runs do: on the host, or in its container when isolation selects one."""
    from . import isolation, policy
    saved = saved or {}
    cfg = saved.get("policy") or policy.effective(project, plan)
    ctx = None
    if isolation.configuration(cfg)["mode"] == "container":
        ctx = isolation.build_execution_context(project, cfg, task=plan["task"], checkouts=checkouts,
            trusted=saved.get("execution", project.profile["execution"])["permission_mode"] == "trusted",
            frozen=saved.get("execution", {}).get("isolation"))
        if ctx.get("mode") == "container":
            isolation.verify_account(project, ctx)
    token = isolation.active.set(ctx)
    try:
        yield ctx
    finally:
        try: isolation.cancel_containers(ctx)
        finally: isolation.active.reset(token)


def command_environment(command, inherited=None):
    env = dict(os.environ)
    env.update(inherited or {})
    env.update({str(k): str(v) for k, v in command.get("env", {}).items()})
    for name in command.get("env_refs", []):
        if name not in env:
            raise WorkflowError(f"Command requires environment variable {name}")
    return env

PYTHON = re.compile(r"python(?:\d+(?:\.\d+)?)?(?:\.exe)?$", re.I)
KEYWORDS = {"and", "or", "not"}


def filtered_argv(check, argv):
    """A red-only check's argv narrowed to its identities with -k, or None to run the whole command.

    Checks that also run green keep their whole red run: it is the test-count and skip baseline
    the runner's guards compare later stages against."""
    identities = check.get("identities") or []
    phases = check.get("phases", ["green"])
    if "red" not in phases or "green" in phases or not identities or "-k" in argv:
        return None
    parser = check.get("parser", "generic")
    program = Path(argv[0]).name if argv else ""
    module = argv[2] if len(argv) > 2 and argv[1] == "-m" and PYTHON.search(program) else None
    if parser == "unittest" and module == "unittest":
        return [*argv, *(arg for name in identities for arg in ("-k", name))]
    if parser == "pytest" and (module == "pytest" or re.fullmatch(r"pytest(?:\.exe)?", program, re.I)):
        names = [re.split(r"::|\.", name)[-1] for name in identities]
        if all(name.isidentifier() and name not in KEYWORDS for name in names):
            return [*argv, "-k", " or ".join(names)]
    return None


def cache_key(check_id, argv, phase, fingerprint):
    from .util import digest, json_text
    return digest(json_text([check_id, [str(arg) for arg in argv], phase, fingerprint]))


def planned_argv(project, definition, phase):
    argv = command_for(project, definition)["argv"]
    return (filtered_argv(definition, argv) if phase == "red" else None) or argv


def check(project, definition, checkouts, *, phase="green", cancel=None, environment=None):
    from .progress import active
    reporter = active.get()
    if reporter: reporter.emit("check_started", check=definition["id"], kind=phase)
    command = command_for(project, definition)
    root = Path(checkouts[definition["repository"]])
    cwd = contained(root, command.get("cwd", "."))
    from .isolation import environment as identity_environment
    env = command_environment(command, environment)
    env = identity_environment(project, cwd, inherited=env) or env
    spec = dict(definition)
    if spec.get("parser", "generic") == "generic":
        spec.setdefault("success_pattern", command.get("success_pattern"))

    def attempt(argv):
        result = execute(argv, cwd, env=env,
                         timeout=command.get("timeout_seconds", 300),
                         inactivity=command.get("inactivity_seconds", command.get("timeout_seconds", 300)),
                         cancel=cancel)
        if result["reason"] == "cancellation_failure":
            from .process import CleanupFailure
            raise CleanupFailure(result.get("child_pid"))
        evidence = parse(spec, result["output"], result["exit_code"], phase)
        if result["reason"]:
            evidence["passed"] = False
            evidence["problems"].append(result["reason"])
        return evidence | result | {"command": redact(" ".join(str(arg) for arg in argv))}

    narrowed = filtered_argv(definition, command["argv"]) if phase == "red" else None
    evidence = attempt(narrowed or command["argv"])
    if narrowed and not all(re.search(re.escape(name), evidence["output"]) for name in definition["identities"]):
        # -k matches test IDs; an identity the filter missed gets the whole command once.
        evidence = attempt(command["argv"])
        narrowed = None
    if reporter: reporter.emit("check_finished", check=definition["id"], passed=evidence["passed"], kind=phase)
    return evidence | {"id": definition["id"], "repository": definition["repository"], "filtered": bool(narrowed)}


def order(checks, durations=None):
    """Cheapest first: expected_seconds, else the last recorded duration; unknown cost last, in manifest order."""
    durations = durations or {}
    def cost(item):
        index, definition = item
        value = definition.get("expected_seconds", durations.get(definition["id"]))
        return (value is None, value or 0, index)
    return [definition for _, definition in sorted(enumerate(checks), key=cost)]


def run_checks(project, manifest, checkouts, *, phase="green", names=None, cancel=None, when=None,
               cache=None, fingerprint=None, durations=None, fail_fast=False):
    """Run the selected checks. Passing results are reused for the same check, argv, phase and fingerprint."""
    from .manifest import when as check_when
    selected = [c for c in manifest["checks"] if (c["id"] in names if names is not None else phase in c.get("phases", ["green"]))]
    if when is not None:
        selected = order([c for c in selected if when in check_when(c)], durations)
    elif not selected:
        raise WorkflowError(f"No {phase} checks selected")
    from contextlib import ExitStack
    from .environments import lease
    results = []
    with ExitStack() as stack:
        environments = {}
        for definition in selected:
            key = cache_key(definition["id"], planned_argv(project, definition, phase), phase, fingerprint)
            if cache is not None and fingerprint is not None and key in cache:
                results.append(dict(cache[key], reused=True))
            else:
                name = definition.get("environment")
                if name and name not in environments:
                    environments[name] = stack.enter_context(lease(project, name, checkouts, cancel))
                row = check(project, definition, checkouts, phase=phase,
                            cancel=environments[name][1] if name else cancel,
                            environment=environments[name][0] if name else None)
                if durations is not None and row.get("duration_seconds") is not None:
                    durations[definition["id"]] = row["duration_seconds"]
                if cache is not None and fingerprint is not None and row["passed"]:
                    remember(cache, key, row)
                results.append(row)
            if fail_fast and not results[-1]["passed"]:
                break
    return results


CACHE_ENTRIES = 64
CACHED_OUTPUT = 4000


def remember(cache, key, row):
    """Keep a bounded number of passing results, each with the tail of its output, in the run state."""
    cache.pop(key, None)
    cache[key] = dict(row, output=str(row.get("output") or "")[-CACHED_OUTPUT:])
    while len(cache) > CACHE_ENTRIES:
        cache.pop(next(iter(cache)))


def run_green(project, manifest, checkouts, *, cancel=None, cache=None, fingerprint=None, durations=None):
    """Loop checks cheapest first, stopping at the first failure; then final checks once they all pass.

    Returns (results, not_run). A check in both sets runs once: its final run reuses the loop result."""
    from .manifest import when as check_when
    green = [c for c in manifest["checks"] if "green" in c.get("phases", ["green"])]
    options = dict(cancel=cancel, cache=cache if cache is not None else {}, fingerprint=fingerprint or "unsaved",
                   durations=durations)
    loop = run_checks(project, manifest, checkouts, when="loop", fail_fast=True, **options)
    if not all(row["passed"] for row in loop):
        done = {row["id"] for row in loop}
        planned = order([c for c in green if "loop" in check_when(c)], durations) + [c for c in green if "loop" not in check_when(c)]
        return loop, [c["id"] for c in planned if c["id"] not in done]
    final = run_checks(project, manifest, checkouts, when="final", **options)
    merged = {row["id"]: row for row in loop}
    # A check in both sets keeps the row from its loop run, not the reused copy of it.
    merged.update({row["id"]: row for row in final if not (row.get("reused") and row["id"] in merged)})
    return list(merged.values()), []
