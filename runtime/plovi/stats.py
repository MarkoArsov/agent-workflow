"""Run statistics from the ledger, and the stable-enough gate (docs/stability-gate.md)."""
from __future__ import annotations
import json
import re
import statistics
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .util import WorkflowError, read_json, run

# Stops a person may need to act on; each is listed with its reason and next command.
STOPS = ("escalation.raised", "run.paused", "approval.requested", "question.asked")
# Person-actor events that are interventions. plan.approved never is: approving a plan is the normal start.
PERSON_INTERVENTIONS = ("question.answered", "approval.granted", "plan.rebound", "checkpoint.migrated", "handoff.started")
RESUMED_AFTER = {"failed", "escalated", "interrupted"}
WORKFLOW = ".github/workflows/verify.yml"
LOCAL_RECORD = ".plovi/local/stats/local-suite.json"
DONE_OWNERS = {18, 46, 47, 48, 49}


def moment(at):
    return datetime.fromisoformat(at.replace("Z", "+00:00"))


def _person(event):
    return event.get("actor", {}).get("kind") == "person"


def _plovi_author(author):
    return author == "plovi" or isinstance(author, dict) and author.get("kind") == "plovi"


# ---- logical runs -------------------------------------------------------------------

def _open(event):
    return {"task": event["subject"]["id"], "started": event["at"], "finished": None, "last": event["at"], "result": "running",
            "attempts": {}, "challenges": 0, "fix_rounds": 0, "tokens": None, "cost_usd": None, "stops": [],
            "interventions": [], "providers": [], "red_proof": False, "files_changed": None, "_paused_by": None}


def _intervention(run_row, event):
    run_row["interventions"].append({"type": event["type"], "at": event["at"], "actor": event["actor"].get("name", ""),
                                     "reason": event.get("reason", "")})


def _add(run_row, event):
    kind, data = event["type"], event["data"]
    run_row["last"] = event["at"]
    if kind == "run.started":
        run_row["red_proof"] = run_row["red_proof"] or data.get("red_proof") is True
        run_row["result"] = "running"
    elif kind == "attempt.finished":
        name = data.get("kind") or "attempt"
        run_row["attempts"][name] = run_row["attempts"].get(name, 0) + 1
        run_row["challenges"] += name == "challenge"
        run_row["fix_rounds"] += name == "fix"
        usage = data.get("usage") or {}
        if any(type(usage.get(key)) is int for key in ("input_tokens", "output_tokens")):
            run_row["tokens"] = (run_row["tokens"] or 0) + sum(usage.get(key) or 0 for key in ("input_tokens", "output_tokens"))
        if type(data.get("cost_usd")) in (int, float):
            run_row["cost_usd"] = round((run_row["cost_usd"] or 0) + data["cost_usd"], 6)
        if data.get("provider") and data["provider"] not in run_row["providers"]:
            run_row["providers"].append(data["provider"])
    elif kind in STOPS:
        run_row["stops"].append({"type": kind, "at": event["at"], "reason": event.get("reason", ""),
                                 "detail": data.get("detail") or data.get("question") or data.get("reason") or data.get("kind") or "",
                                 "next": data.get("next")})
        if kind == "run.paused":
            run_row["result"] = "paused"
    elif kind in {"run.finished", "run.interrupted"}:
        run_row["result"] = data.get("status") or "interrupted"
    elif kind == "pause.requested" and _person(event):
        run_row["_paused_by"] = event["actor"].get("name")
    elif kind == "run.resumed":
        if _person(event) and data.get("status") in RESUMED_AFTER and run_row["_paused_by"] != event["actor"].get("name"):
            _intervention(run_row, event)
        run_row["_paused_by"] = None
    elif kind in PERSON_INTERVENTIONS and _person(event):
        if not (kind == "approval.granted" and data.get("kind") == "plan"):
            _intervention(run_row, event)
    elif kind == "commits.adopted" and not _plovi_author(data.get("author")):
        _intervention(run_row, event)
    elif kind == "pr.opened" and type(data.get("files_changed")) is int:
        run_row["files_changed"] = max(run_row["files_changed"] or 0, data["files_changed"])


def _close(run_row, at, result):
    run_row.update(finished=at, last=at, result=result)


def _finish(run_row):
    run_row.pop("_paused_by", None)
    end = run_row["finished"] or run_row["last"]
    run_row["duration_seconds"] = round((moment(end) - moment(run_row["started"])).total_seconds())
    run_row.pop("last")
    return run_row


def runs(events):
    """Fold task events into logical runs.

    A run opens at a run.started when its task has none open. It closes at the first
    complete run.finished, the first pr.opened, or a run.cancelled. Resumes, retries and
    answers start new runner invocations inside the same logical run.
    """
    open_runs, rows, cancelled = {}, [], {}
    for event in events:
        if event.get("subject", {}).get("kind") != "task":
            continue
        task, kind, data = event["subject"]["id"], event["type"], event.get("data", {})
        current = open_runs.get(task)
        if kind == "run.started" and current is None:
            if task in cancelled:
                _intervention(cancelled.pop(task), dict(event, type="run.cancelled", reason="The task was cancelled and run again"))
            current = open_runs[task] = _open(event)
            rows.append(current)
        if current is None:
            continue
        _add(current, event)
        if kind == "pr.opened" or kind == "run.finished" and data.get("status") == "complete":
            _close(current, event["at"], "pull-request" if kind == "pr.opened" else "complete")
            del open_runs[task]
        elif kind == "run.cancelled":
            _close(current, event["at"], "cancelled")
            cancelled[task] = current
            del open_runs[task]
    for row in rows:
        _finish(row)
    return rows


def totals(rows):
    durations = [row["duration_seconds"] for row in rows if row["finished"]]
    tokens = [row["tokens"] for row in rows if row["tokens"] is not None]
    attempts = [sum(row["attempts"].values()) for row in rows]
    return {"runs": len(rows), "interventionless": sum(1 for row in rows if not row["interventions"]),
            "median_duration_seconds": statistics.median(durations) if durations else None,
            "attempts_per_run": round(sum(attempts) / len(rows), 2) if rows else None,
            "tokens_per_run": round(sum(tokens) / len(tokens)) if tokens else None}


def since(rows, value, now=None):
    """Runs that started at or after an ISO date or time, or within a duration such as 7d, 12h or 30m."""
    match = re.fullmatch(r"(\d+)([dhm])", value or "")
    if match:
        unit = {"d": "days", "h": "hours", "m": "minutes"}[match.group(2)]
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(**{unit: int(match.group(1))})
    else:
        try:
            cutoff = moment(value)
        except ValueError:
            raise WorkflowError(f"Use an ISO date or time, or a duration such as 7d, 12h or 30m, for --since, not {value!r}") from None
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
    return [row for row in rows if moment(row["started"]) >= cutoff]


# ---- the stable-enough gate -----------------------------------------------------------

def _gh(project, *args):
    result = run(["gh", *args], project.root, check=False, timeout=120)
    if result.returncode:
        raise WorkflowError(result.stderr.strip() or f"gh exited with {result.returncode}")
    return result.stdout


def _slug(project):
    from .integrations.github import slug
    repos = project.profile.get("repositories", [])
    return slug(project.root, repos[0] if repos else {})


def timeouts(text):
    """The tightest timeout-minutes in each top-level job of a workflow file, read without a YAML parser."""
    result, job, inside = {}, None, False
    for line in text.splitlines():
        if line.rstrip() == "jobs:":
            inside = True
            continue
        if not inside or not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            break
        if indent == 2 and line.rstrip().endswith(":"):
            job = line.strip()[:-1]
            continue
        found = re.match(r"\s+(?:- )?timeout-minutes:\s*(\d+)\s*$", line)
        if job and found:
            result[job] = min(result.get(job, 1 << 30), int(found.group(1)))
    return result


def _seconds(job):
    if not job.get("started_at") or not job.get("completed_at"):
        return None
    return (moment(job["completed_at"]) - moment(job["started_at"])).total_seconds()


def _ci(project):
    """The last 10 completed Verify runs on main, newest first, with their job durations."""
    slug = _slug(project)
    data = json.loads(_gh(project, "api", f"repos/{slug}/actions/workflows/{Path(WORKFLOW).name}/runs?branch=main&per_page=20"))
    completed = [r for r in data.get("workflow_runs", []) if r.get("status") == "completed"][:10]
    for item in completed:
        item["_jobs"] = json.loads(_gh(project, "api", f"repos/{slug}/actions/runs/{item['id']}/jobs")).get("jobs", [])
    return completed


def _durations(ci):
    by_name = {}
    for item in ci:
        for job in item["_jobs"]:
            seconds = _seconds(job)
            if seconds is not None:
                by_name.setdefault(job["name"], []).append(seconds)
    return {name: statistics.median(values) for name, values in by_name.items()}


def _minutes(seconds):
    return f"{seconds / 60:.1f} min" if seconds >= 120 else f"{seconds:.0f} s"


def _g1(project, ci):
    clean = [r for r in ci if r.get("conclusion") == "success" and r.get("run_attempt", 1) == 1]
    numbers = {"runs": len(ci), "first_time_successes": len(clean)}
    detail = f"{len(clean)} of the last 10 Verify runs on main passed without a rerun"
    path = project.root / WORKFLOW
    limits = timeouts(path.read_text(encoding="utf-8")) if path.is_file() else {}
    worst = None
    for name, median in _durations(ci).items():
        limit = limits.get(name.split(" (")[0])
        if limit:
            share = median / (limit * 60)
            if worst is None or share > worst[1]:
                worst = (name, share, median, limit)
    within = worst is not None and worst[1] <= 0.6
    if worst:
        numbers.update(slowest_job=worst[0], median_seconds=worst[2], timeout_minutes=worst[3], share=round(worst[1], 3))
        detail += f"; slowest job median {worst[0]} {_minutes(worst[2])} of {worst[3]} min ({worst[1]:.0%}, limit 60%)"
    else:
        detail += "; no job durations with a timeout to compare"
    return {"passed": len(clean) == 10 and within, "detail": detail, "numbers": numbers}


def _g2(project, ci):
    medians = [median for name, median in _durations(ci).items() if name.startswith("core (ubuntu")]
    ubuntu = max(medians) if medians else None
    record = read_json(project.root / LOCAL_RECORD, None)
    local = record.get("seconds") if isinstance(record, dict) else None
    numbers = {"ubuntu_median_seconds": ubuntu, "local_seconds": local,
               "local_cpu_count": record.get("cpu_count") if isinstance(record, dict) else None}
    parts = [f"Ubuntu suite median {ubuntu:.0f} s (limit 150 s)" if ubuntu is not None else "no Ubuntu suite job durations"]
    if local is None:
        parts.append("no local record; run python3 scripts/run_tests.py --jobs auto --record")
    else:
        parts.append(f"local suite {local:.0f} s on {record.get('cpu_count')} CPUs (limit 240 s on 4)")
    passed = ubuntu is not None and ubuntu <= 150 and local is not None and local <= 240
    return {"passed": passed, "detail": "; ".join(parts), "numbers": numbers}


def _streak(rows):
    """The trailing run of interventionless pipeline runs that reached a pull request, oldest first."""
    streak = []
    for row in reversed([r for r in rows if r["finished"]]):
        if row["interventions"] or row["result"] != "pull-request":
            break
        streak.append(row)
    return list(reversed(streak))[-5:]


def _g3(rows):
    streak = _streak(rows)
    large = sum(1 for row in streak if (row["files_changed"] or 0) >= 10)
    red = sum(1 for row in streak if row["red_proof"])
    providers = sorted({p for row in streak for p in row["providers"]})
    missing = [p for p in ("claude", "codex") if p not in providers]
    numbers = {"consecutive": len(streak), "large": large, "red_proof": red, "providers": providers}
    detail = (f"{len(streak)} consecutive interventionless runs to a PR (need 5); {large} changed 10 or more files (need 2); "
              f"{red} with red proof (need 1); providers {', '.join(providers) or 'none'}")
    if missing:
        detail += f" (missing {', '.join(missing)})"
    return {"passed": len(streak) == 5 and large >= 2 and red >= 1 and not missing, "detail": detail, "numbers": numbers}


def _g4(rows):
    streak = _streak(rows)
    stops = [stop for row in streak for stop in row["stops"]]
    good = sum(1 for stop in stops if stop["reason"].strip() and stop.get("next"))
    numbers = {"runs": len(streak), "stops": len(stops), "explained": good}
    if not streak:
        return {"passed": False, "detail": "0 qualifying pipeline runs to check stops in", "numbers": numbers}
    return {"passed": good == len(stops), "detail": f"{good} of {len(stops)} stops in the last {len(streak)} runs have a reason and a next command",
            "numbers": numbers}


# A step runs in one CI batch and is "not-run" in the others; the most telling status wins.
PRECEDENCE = ("failed", "error", "passed", "skipped", "not-run")


def merge_steps(batches):
    """Combine scenario results from several CI batches into one status per step."""
    merged = {}
    for steps in batches:
        for key, value in steps.items():
            rank = lambda item: PRECEDENCE.index(item.get("status")) if item.get("status") in PRECEDENCE else 0
            if key not in merged or rank(value) < rank(merged[key]):
                merged[key] = value
    return merged


def _g5(project, ci):
    if not ci:
        return {"passed": False, "detail": "no completed Verify run on main to read scenario results from", "numbers": {}}
    newest = ci[0]["id"]
    with tempfile.TemporaryDirectory(prefix="plovi-scenario-") as folder:
        _gh(project, "run", "download", str(newest), "--pattern", "scenario-results*", "--dir", folder)
        steps = merge_steps(json.loads(path.read_text(encoding="utf-8")).get("steps", {})
                            for path in sorted(Path(folder).rglob("scenario-results.json")))
    owned = {key: value for key, value in steps.items() if value.get("owners") and set(value["owners"]) <= DONE_OWNERS}
    failing = sorted(key for key, value in owned.items() if value.get("status") != "passed")
    numbers = {"run": newest, "steps": len(owned), "failing": failing}
    detail = f"{len(owned) - len(failing)} of {len(owned)} steps owned by #18, #46, #47, #48 and #49 passed in run {newest}"
    if failing:
        detail += f"; not passing: {', '.join(failing)}"
    return {"passed": bool(owned) and not failing, "detail": detail, "numbers": numbers}


NAMES = {"G1": "CI on main", "G2": "Suite speed", "G3": "Pipeline runs", "G4": "Stop quality", "G5": "Scenario harness"}


def gate(project, rows):
    """Evaluate G1-G5. Missing data is a failure with its reason, never an exception."""
    try:
        ci, error = _ci(project), None
    except (WorkflowError, ValueError, OSError) as exc:
        ci, error = [], f"GitHub data unavailable: {exc}"
    checks = [("G1", lambda: _g1(project, ci), True), ("G2", lambda: _g2(project, ci), True),
              ("G3", lambda: _g3(rows), False), ("G4", lambda: _g4(rows), False), ("G5", lambda: _g5(project, ci), True)]
    results = []
    for key, check, reads_ci in checks:
        try:
            result = check()
        except (WorkflowError, ValueError, OSError, KeyError) as exc:
            result = {"passed": False, "detail": f"could not read the data: {exc}", "numbers": {}}
        if reads_ci and error:
            result["detail"] += f" ({error})"
        results.append(dict(result, id=key, name=NAMES[key]))
    return results


# ---- output ---------------------------------------------------------------------------------

def _cell(value):
    return "-" if value is None else str(value)


def render(rows, summary, results=None):
    lines = []
    if rows:
        header = ("Task", "Started (UTC)", "Result", "Duration", "Attempts", "Interventions", "Stops", "Tokens")
        table = [header] + [(row["task"], row["started"][:16].replace("T", " "), row["result"], _minutes(row["duration_seconds"]),
                             str(sum(row["attempts"].values())), str(len(row["interventions"])), str(len(row["stops"])),
                             _cell(row["tokens"])) for row in rows]
        widths = [max(len(line[i]) for line in table) for i in range(len(header))]
        lines += ["  ".join(cell.ljust(width) for cell, width in zip(line, widths)).rstrip() for line in table]
        lines.append("")
    else:
        lines += ["No runs recorded.", ""]
    median = summary["median_duration_seconds"]
    lines.append(f"Runs: {summary['runs']}. Without interventions: {summary['interventionless']}. "
                 f"Median duration: {_minutes(median) if median is not None else '-'}. "
                 f"Attempts per run: {_cell(summary['attempts_per_run'])}. Tokens per run: {_cell(summary['tokens_per_run'])}.")
    if results is not None:
        lines.append("")
        for item in results:
            lines.append(f"{item['id']} {'PASS' if item['passed'] else 'FAIL'}  {item['name']}: {item['detail']}")
        lines.append("")
        lines.append("The gate is met." if all(i["passed"] for i in results)
                     else "The gate is not met. Keep using the manual lane; see docs/stability-gate.md.")
    return "\n".join(lines) + "\n"
