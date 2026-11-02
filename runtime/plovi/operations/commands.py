"""The registry itself, for agents and the app."""
from __future__ import annotations
from . import Text, catalog, register


@register("commands", "List every operation with its arguments, whether it changes anything and its risk",
          "plovi commands [--json]", arguments={"json": {"type": "boolean"}, "format": {"enum": ["text", "json"]}},
          mutates=False, risk="none")
def commands(args):
    rows = catalog()
    if args.get("json") or args.get("format") == "json":
        return {"operations": rows}
    width = max(len(row["name"]) for row in rows)
    lines = [f"{row['name'].ljust(width)}  {row['risk'].ljust(4)}  {row['summary']}" for row in rows]
    return Text("\n".join(lines) + "\n\nRisk: none reads only; low changes a task or registry; high needs a preview and --approve DIGEST.\n")
