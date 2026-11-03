"""plovi stats: runs, interventions and stops from the ledger, and the stable-enough gate."""
from __future__ import annotations
from .. import ledger, stats
from ..util import identifier
from . import Text, register, task_subject
from .tasks import project_for


@register("stats", "Report runs, interventions, stops, time, attempts and tokens from the ledger; --gate checks the stable-enough gate",
          "plovi stats [--since DATE|DURATION] [--task ID] [--json] [--gate]",
          arguments={"since": {"type": "string", "description": "ISO date or time, or a duration such as 7d"},
                     "task": {"type": "string", "description": "Task ID"},
                     "json": {"type": "boolean", "description": "Print JSON"},
                     "gate": {"type": "boolean", "description": "Evaluate G1-G5; exit 0 only when all pass"}},
          mutates=False, risk="none")
def report(args):
    project = project_for(args)
    subject = task_subject(identifier(args["task"])) if args.get("task") else None
    rows = stats.runs(ledger.events(project, subject=subject))
    if args.get("since"):
        rows = stats.since(rows, args["since"])
    summary = stats.totals(rows)
    results = stats.gate(project, rows) if args.get("gate") else None
    passed = results is None or all(item["passed"] for item in results)
    if args.get("json"):
        value = {"runs": rows, "totals": summary}
        if results is not None:
            value.update(gate=results, passed=passed)
            if not passed:
                value["status"] = "failed"
        return value
    output = Text(stats.render(rows, summary, results))
    output.exit_code = 0 if passed else 1
    return output
