#!/usr/bin/env python3
"""Refresh tests/timings.json, the per-test seconds run_tests.py uses to balance CI batches and workers.

Download the test artifacts of a Verify run, then pass their timing files:

    gh run download RUN_ID --pattern 'tests-*' --dir runs
    python3 scripts/update_test_weights.py runs/*/test-timings.json

Each file names its platform; files from one platform replace that platform's weights.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = ROOT / "tests/timings.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path, help="test-timings.json files written by run_tests.py --timings")
    parser.add_argument("--platform", help="Platform for files that do not name one (linux, darwin or win32)")
    parser.add_argument("--output", type=Path, default=WEIGHTS)
    args = parser.parse_args(argv)
    fresh = {}
    for path in args.files:
        data = json.loads(path.read_text(encoding="utf-8"))
        platform = data.get("platform") or args.platform
        if not platform:
            parser.error(f"{path} names no platform; pass --platform")
        fresh.setdefault(platform, {}).update({item["test"]: round(item["seconds"], 2) for item in data["tests"]})
    try:
        current = json.loads(args.output.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        current = {"schema_version": 2, "platforms": [], "tests": {}}
    platforms = sorted(set(current["platforms"]) | set(fresh))
    table = {}
    for test in set(current["tests"]) | {test for tests in fresh.values() for test in tests}:
        old = dict(zip(current["platforms"], current["tests"].get(test, [])))
        row = [fresh[name].get(test) if name in fresh else old.get(name) for name in platforms]
        if any(value is not None for value in row):
            table[test] = row
    # One line per test keeps the file small and its diffs readable.
    lines = [f"  {json.dumps(test)}: {json.dumps(table[test])}" for test in sorted(table)]
    args.output.write_text('{"schema_version": 2, "platforms": ' + json.dumps(platforms) + ', "tests": {\n'
                           + ",\n".join(lines) + "\n}}\n", encoding="utf-8")
    for name, tests in sorted(fresh.items()):
        print(f"{name}: {len(tests)} tests, {sum(tests.values()):.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
