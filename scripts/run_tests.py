#!/usr/bin/env python3
"""Run the tests in parallel workers, a deterministic CI batch, a tier, or only what a change affects.

Every run happens in worker processes. A test that exceeds the per-test timeout
prints the stack of every thread, is recorded as failed, and stops only its worker.
"""
from __future__ import annotations
import argparse
import ast
import faulthandler
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_TESTS = ROOT / "tests"
DEFAULT_TIMEOUT = 120
TIMEOUT_EXIT = 3
# faulthandler ends a worker whose watchdog cannot run, for example while a C call holds the GIL.
HARD_STOP_GRACE = 10
# Documentation and task plans; changing only these selects no tests.
DOCS_ONLY = ("docs/", "design/", "ai-plans/")


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


def module_of(test):
    """The test module a case belongs to; import failures carry the module name as their method."""
    if type(test).__name__ == "_FailedTest":
        return test._testMethodName
    return type(test).__module__


def discover(start, pattern):
    loader = unittest.TestLoader()
    return sorted(cases(loader.discover(str(start), pattern=pattern)), key=lambda test: test.id())


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_tiers(start):
    data = load_json(Path(start) / "tiers.json") or {}
    return {name: list(data.get(name, [])) for name in ("smoke", "slow")}


# Worker

class TimedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.durations = []

    def startTest(self, test):
        super().startTest(test)
        self.started = time.perf_counter()

    def stopTest(self, test):
        self.durations.append({"test": test.id(), "module": module_of(test),
                               "seconds": time.perf_counter() - self.started})
        super().stopTest(test)


class WorkerResult(TimedResult):
    """Watches each test; on timeout dumps every thread, records the test and ends the worker."""
    timeout = DEFAULT_TIMEOUT
    report = None

    def startTest(self, test):
        super().startTest(test)
        self.current = test
        faulthandler.dump_traceback_later(self.timeout + HARD_STOP_GRACE, repeat=False, file=sys.__stderr__, exit=True)
        self.watchdog = threading.Timer(self.timeout, self.expire, args=(test,))
        self.watchdog.daemon = True
        self.watchdog.start()

    def stopTest(self, test):
        self.watchdog.cancel()
        faulthandler.cancel_dump_traceback_later()
        super().stopTest(test)

    def expire(self, test):
        print(f"\nTimeout: {test.id()} exceeded {self.timeout:g} s. Stacks of every thread:", file=sys.__stderr__, flush=True)
        faulthandler.dump_traceback(file=sys.__stderr__, all_threads=True)
        self.errors.append((test, f"TimeoutError: test exceeded {self.timeout:g} s\n"))
        self.durations.append({"test": test.id(), "module": module_of(test),
                               "seconds": time.perf_counter() - self.started})
        self.report(self, timed_out=test.id())
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(TIMEOUT_EXIT)

    def printErrors(self):
        """The parent prints every failure once, after all workers finish."""


def entries(items):
    return [{"test": test.id(), "description": str(test), "traceback": text} for test, text in items]


def run_worker(args):
    wanted = json.loads(Path(args.tests_file).read_text(encoding="utf-8"))
    by_id = {test.id(): test for test in discover(args.start_directory, args.pattern)}
    selected = [by_id[name] for name in wanted if name in by_id]
    missing = [name for name in wanted if name not in by_id]
    started = set()

    def report(result, timed_out=None):
        ran = {item["test"] for item in result.durations}
        data = {"testsRun": result.testsRun, "failures": entries(result.failures + result.unexpectedSuccesses_entries()),
                "errors": entries(result.errors), "skipped": [{"test": t.id(), "reason": r} for t, r in result.skipped],
                "durations": result.durations, "timedOut": timed_out,
                "notRun": [name for name in wanted if name not in ran and name not in started and name != timed_out],
                "missing": missing}
        temporary = Path(args.result).with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, args.result)

    class Result(WorkerResult):
        timeout = args.per_test_timeout

        def startTest(self, test):
            started.add(test.id())
            super().startTest(test)

        def unexpectedSuccesses_entries(self):
            return [(test, "Unexpected success\n") for test in self.unexpectedSuccesses]

    Result.report = staticmethod(report)
    runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=Result)
    result = runner.run(unittest.TestSuite(selected))
    report(result)
    return 0 if result.wasSuccessful() and not missing else 1


# Selection

def changed_modules(root, ref):
    def lines(*command):
        output = subprocess.run(["git", "-C", str(root), *command], capture_output=True, text=True, check=True).stdout
        return [line.strip() for line in output.splitlines() if line.strip()]
    files = set(lines("diff", "--name-only", f"{ref}...HEAD"))
    files.update(lines("diff", "--name-only"))
    files.update(lines("diff", "--name-only", "--cached"))
    files.update(lines("ls-files", "--others", "--exclude-standard"))
    return sorted(files)


def default_ref(root):
    present = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", "origin/main"],
                             capture_output=True, text=True).returncode == 0
    return "origin/main" if present else "main"


def is_docs(path):
    return (path.startswith(DOCS_ONLY) or path.endswith(".md") and not path.startswith(("skills/", "tests/", "runtime/"))
            or path.startswith("skills/") and path.endswith("/SKILL.md"))


def imported_modules(path):
    """Every plovi module a test file names in an import statement."""
    names = set()
    for node in ast.walk(ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names if alias.name.split(".")[0] == "plovi")
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and node.module.split(".")[0] == "plovi":
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def related(imported, changed):
    return imported == changed or changed.startswith(imported + ".") or imported.startswith(changed + ".")


def test_modules(start):
    """Dotted module name -> file for every test module, including nested packages such as scenario."""
    return {path.relative_to(start).with_suffix("").as_posix().replace("/", "."): path
            for path in Path(start).rglob("test_*.py") if "__pycache__" not in path.parts}


def select_changed(start, ref, tiers):
    """Return (module names or None for every module, explanation lines)."""
    root = Path(subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True, check=True).stdout.strip())
    ref = ref or default_ref(root)
    files = changed_modules(root, ref)
    tests_dir = Path(start).resolve().relative_to(root.resolve()).as_posix()
    if not files:
        return set(), [f"No changes against {ref}."]
    if all(is_docs(path) for path in files):
        return set(), ["No tests affected; run the docs checks."]
    changed, direct, everything = set(), set(), []
    for path in files:
        if is_docs(path):
            continue
        if path.startswith("runtime/plovi/") and path.endswith(".py"):
            dotted = path[len("runtime/"):-len(".py")].replace("/", ".")
            changed.add(dotted.removesuffix(".__init__"))
        elif path.startswith(f"{tests_dir}/") and Path(path).name.startswith("test_") and path.endswith(".py"):
            direct.add(path[len(tests_dir) + 1:-len(".py")].replace("/", "."))
        elif path.startswith(".github/"):
            direct.add("test_ci_workflow")
        elif path.startswith(f"{tests_dir}/"):
            everything.append(path)
        else:
            # A script, schema, template or skill file: select the test modules that name it.
            naming = {name for name, test in test_modules(start).items()
                      if Path(path).name in test.read_text(encoding="utf-8")}
            if not naming:
                everything.append(path)
            direct.update(naming)
    if everything:
        return None, [f"{path} changed; selecting every test." for path in everything[:5]]
    modules = test_modules(start)
    selected = {name for name in direct if name in modules}
    for name, path in sorted(modules.items()):
        if any(related(imported, module) for imported in imported_modules(path) for module in changed):
            selected.add(name)
    selected.update(tiers["smoke"])
    return selected, [f"Changed against {ref}: {', '.join(sorted(changed | direct))}"]


def assign(selected, jobs, timings, slow):
    """Split tests into at most `jobs` groups of whole modules, longest estimated module first."""
    modules = {}
    for test in selected:
        modules.setdefault(module_of(test), []).append(test)
    known = {}
    for item in (timings or {}).get("tests", []):
        known[item["test"]] = item["seconds"]
    per_test = sorted(known.values())[len(known) // 2] if known else 1.0
    cost = {name: sum(known.get(test.id(), per_test) for test in tests) for name, tests in modules.items()}
    groups = [{"modules": [], "cost": 0.0} for _ in range(max(1, min(jobs, len(modules))))]
    for name in sorted(modules, key=lambda name: (name not in slow, -cost[name], name)):
        group = min(groups, key=lambda group: group["cost"])
        group["modules"].append(name)
        group["cost"] += cost[name]
    for group in groups:
        group["modules"].sort(key=lambda name: (name not in slow, name))
        group["tests"] = [test.id() for name in group["modules"] for test in modules[name]]
    return [group for group in groups if group["tests"]]


# Parent

def run_parallel(groups, args, workdir):
    workers = []
    for number, group in enumerate(groups, 1):
        tests_file = workdir / f"worker-{number}-tests.json"
        tests_file.write_text(json.dumps(group["tests"]), encoding="utf-8")
        temp = workdir / f"worker-{number}-tmp"
        temp.mkdir()
        log = (workdir / f"worker-{number}.log").open("wb")
        env = dict(os.environ, TMPDIR=str(temp), TEMP=str(temp), TMP=str(temp), PYTHONFAULTHANDLER="1")
        command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--start-directory", str(args.start_directory),
                   "--pattern", args.pattern, "--tests-file", str(tests_file), "--per-test-timeout", str(args.per_test_timeout),
                   "--result", str(workdir / f"worker-{number}.json")]
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env)
        workers.append({"number": number, "group": group, "process": process, "log": log,
                        "result": workdir / f"worker-{number}.json"})
    pending = list(workers)
    while pending:
        for worker in list(pending):
            if worker["process"].poll() is None:
                continue
            pending.remove(worker)
            worker["log"].close()
            output = (workdir / f"worker-{worker['number']}.log").read_bytes().decode("utf-8", "replace")
            modules = ", ".join(worker["group"]["modules"])
            print(f"\n--- worker {worker['number']} ({len(worker['group']['tests'])} tests: {modules}) "
                  f"exited {worker['process'].returncode}", file=sys.stderr)
            sys.stderr.write(output)
            sys.stderr.flush()
            worker["data"] = load_json(worker["result"])
        if pending:
            time.sleep(0.05)
    return workers


def merge(workers):
    total = {"testsRun": 0, "failures": [], "errors": [], "skipped": [], "durations": [], "crashed": [], "notRun": []}
    for worker in workers:
        data = worker["data"]
        code = worker["process"].returncode
        if data is None:
            total["crashed"].append({"modules": worker["group"]["modules"], "exit": code})
            continue
        for key in ("failures", "errors", "skipped", "durations", "notRun"):
            total[key].extend(data.get(key, []))
        total["testsRun"] += data.get("testsRun", 0)
        for name in data.get("missing", []):
            total["errors"].append({"test": name, "description": name, "traceback": "Test not found in worker discovery\n"})
        if code not in (0, 1, TIMEOUT_EXIT):
            total["crashed"].append({"modules": worker["group"]["modules"], "exit": code})
    return total


def print_summary(total, seconds):
    rule = "=" * 70
    for kind, key in (("FAIL", "failures"), ("ERROR", "errors")):
        for item in total[key]:
            print(f"{rule}\n{kind}: {item['description']}\n{'-' * 70}\n{item['traceback'].rstrip()}\n", file=sys.stderr)
    for crash in total["crashed"]:
        print(f"{rule}\nWORKER CRASH: exit {crash['exit']} without results; modules: {', '.join(crash['modules'])}\n",
              file=sys.stderr)
    if total["notRun"]:
        print(f"{rule}\nNOT RUN after a timeout stopped their worker ({len(total['notRun'])}):", file=sys.stderr)
        for name in total["notRun"]:
            print(f"  {name}", file=sys.stderr)
    print("\nSlowest tests:", file=sys.stderr)
    for item in sorted(total["durations"], key=lambda item: item["seconds"], reverse=True)[:10]:
        print(f"{item['seconds']:8.3f}s {item['test']}", file=sys.stderr)
    counts = [f"{name}={len(total[key])}" for name, key in (("failures", "failures"), ("errors", "errors"),
              ("skipped", "skipped"), ("crashed", "crashed"), ("not run", "notRun")) if total[key]]
    print(f"\nRan {total['testsRun']} tests in {seconds:.1f}s", file=sys.stderr)
    print("OK" if successful(total) else f"FAILED ({', '.join(counts)})", file=sys.stderr)


def successful(total):
    return not (total["failures"] or total["errors"] or total["crashed"] or total["notRun"])


def write_summary(path, total, seconds):
    lines = [f"### Tests: {'passed' if successful(total) else 'failed'}", "",
             f"Ran {total['testsRun']} tests in {seconds:.1f} s.", ""]
    problems = ([f"- FAIL `{item['test']}`" for item in total["failures"]]
                + [f"- ERROR `{item['test']}`" for item in total["errors"]]
                + [f"- WORKER CRASH: {', '.join(crash['modules'])}" for crash in total["crashed"]]
                + [f"- NOT RUN `{name}`" for name in total["notRun"]])
    if problems:
        lines += ["Failing tests:", "", *problems, ""]
    lines += ["Slowest tests:", "", "| Seconds | Test |", "|---:|---|"]
    lines += [f"| {item['seconds']:.1f} | `{item['test']}` |"
              for item in sorted(total["durations"], key=lambda item: item["seconds"], reverse=True)[:10]]
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def write_timings(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_record(path, total, seconds, jobs):
    """The local full-suite time the stable-enough gate reads (G2)."""
    from datetime import date
    write_timings(path, {"schema_version": 1, "cpu_count": os.cpu_count(), "jobs": jobs, "seconds": round(seconds, 1),
                         "tests_run": total["testsRun"], "date": date.today().isoformat()})


def scenario_results(total, selected, start):
    """Each target-scenario step's result, with its owners, for the stable-enough gate (G5)."""
    steps = runpy.run_path(str(Path(start) / "scenario" / "steps.py"))["SCENARIO_STEPS"]
    failed = {item["test"] for item in total["failures"]}
    errors = {item["test"] for item in total["errors"]} | set(total["notRun"])
    skipped = {item["test"] for item in total["skipped"]}
    ran = {item["test"] for item in total["durations"]}
    ids = [test.id() for test in selected if ".test_target_scenario." in "." + test.id()]
    result = {}
    for step in steps:
        name = next((test for test in ids if test.endswith("." + step["test"])), None)
        status = ("not-run" if name is None or name not in ran | failed | errors | skipped else "failed" if name in failed
                  else "error" if name in errors else "skipped" if name in skipped else "passed")
        result[step["id"]] = {"status": status, "owners": step["owners"], "test": step["test"]}
    return {"schema_version": 1, "steps": result}


def parse_jobs(value):
    if value == "auto":
        return min(os.cpu_count() or 1, 8)
    try:
        jobs = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("use a positive number or auto") from None
    if jobs < 1:
        raise argparse.ArgumentTypeError("use a positive number or auto")
    return jobs


def parse_timeout(value):
    try:
        seconds = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("use a positive number of seconds") from None
    if seconds <= 0:
        raise argparse.ArgumentTypeError("use a positive number of seconds")
    return seconds


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--shard", type=int, default=1, help="One-based batch number")
    parser.add_argument("--shards", type=int, default=1, help="Total number of batches")
    parser.add_argument("--jobs", type=parse_jobs, default=1, help="Worker processes, or auto (CPU count, at most 8)")
    parser.add_argument("--tier", choices=("smoke", "default", "all"), default="default",
                        help="smoke runs the modules in tests/tiers.json; default and all run everything")
    parser.add_argument("--changed", action="store_true", help="Run only tests affected by changes, plus smoke")
    parser.add_argument("--base", help="Base ref for --changed; defaults to origin/main, else main")
    parser.add_argument("--per-test-timeout", type=parse_timeout,
                        default=parse_timeout(os.environ.get("PLOVI_TEST_TIMEOUT", str(DEFAULT_TIMEOUT))),
                        help=f"Seconds before a test fails as hung (default {DEFAULT_TIMEOUT}, or PLOVI_TEST_TIMEOUT)")
    parser.add_argument("--start-directory", type=Path, default=DEFAULT_TESTS)
    parser.add_argument("--pattern", default="test*.py")
    parser.add_argument("--timings", type=Path, help="Write this run's per-test timings here")
    parser.add_argument("--results-dir", type=Path, help="Keep worker logs and result files here")
    parser.add_argument("--summary", type=Path, help="Append a Markdown summary, such as $GITHUB_STEP_SUMMARY")
    parser.add_argument("--list", action="store_true", help="Print selected test IDs without running them")
    parser.add_argument("--record", nargs="?", type=Path, const=ROOT / ".plovi/local/stats/local-suite.json",
                        help="After a passing full run, write the suite time here (default .plovi/local/stats/local-suite.json)")
    parser.add_argument("--scenario-results", type=Path, help="Write each target-scenario step's result here")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--tests-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--result", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        return run_worker(args)
    if args.shards < 1 or not 1 <= args.shard <= args.shards:
        parser.error("require 1 <= shard <= shards")
    if args.record and (args.changed or args.tier == "smoke" or args.shards != 1):
        parser.error("--record needs a full run: drop --changed, --tier smoke and --shards")
    tiers = load_tiers(args.start_directory)
    discovered = discover(args.start_directory, args.pattern)
    selected = discovered[args.shard - 1::args.shards]
    if args.tier == "smoke":
        selected = [test for test in selected if module_of(test) in tiers["smoke"]]
    if args.changed:
        modules, notes = select_changed(args.start_directory, args.base, tiers)
        for note in notes:
            print(note)
        if modules is not None:
            if not modules:
                return 0
            selected = [test for test in selected if module_of(test) in modules]
            print("Selected modules: " + ", ".join(sorted({module_of(test) for test in selected})))
    if not selected:
        parser.error("selected batch contains no tests")
    if args.list:
        print(json.dumps([test.id() for test in selected], indent=2))
        return 0
    default_timings = ROOT / ".plovi/local/test-timings.json"
    tracked = args.start_directory.resolve() == DEFAULT_TESTS.resolve()
    history = load_json(default_timings) if tracked else load_json(args.timings) if args.timings else None
    groups = assign(selected, args.jobs, history, set(tiers["slow"]))
    print(f"Batch {args.shard}/{args.shards}: {len(selected)} of {len(discovered)} discovered tests "
          f"in {len(groups)} worker(s); per-test timeout {args.per_test_timeout:g} s", file=sys.stderr, flush=True)
    started = time.perf_counter()
    workdir = Path(tempfile.mkdtemp(prefix="plovi-tests-"))
    try:
        total = merge(run_parallel(groups, args, workdir))
        if args.results_dir:
            args.results_dir.mkdir(parents=True, exist_ok=True)
            for path in workdir.glob("worker-*.*"):
                if path.is_file():
                    shutil.copy2(path, args.results_dir / path.name)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    seconds = time.perf_counter() - started
    print_summary(total, seconds)
    if args.summary:
        write_summary(args.summary, total, seconds)
    timings = {"schema_version": 1, "shard": args.shard, "shards": args.shards, "jobs": len(groups),
               "discovered": len(discovered), "selected": len(selected), "tests_run": total["testsRun"],
               "successful": successful(total), "seconds": seconds, "tests": total["durations"]}
    if args.timings:
        write_timings(args.timings, timings)
    if args.scenario_results:
        write_timings(args.scenario_results, scenario_results(total, selected, args.start_directory))
    if args.record:
        if successful(total):
            write_record(args.record, total, seconds, len(groups))
        else:
            print("Not recorded: the suite failed. Fix the failures and run with --record again.", file=sys.stderr)
    if tracked:
        previous = {item["test"]: item for item in (history or {}).get("tests", [])}
        previous.update({item["test"]: item for item in total["durations"]})
        write_timings(default_timings, dict(timings, tests=sorted(previous.values(), key=lambda item: item["test"])))
    return 0 if successful(total) else 1


if __name__ == "__main__":
    raise SystemExit(main())
