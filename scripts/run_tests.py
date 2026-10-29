#!/usr/bin/env python3
"""Run all tests or a deterministic CI batch, retaining per-test timings."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


class TimedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.durations = []

    def startTest(self, test):
        super().startTest(test)
        self.started = time.perf_counter()

    def stopTest(self, test):
        self.durations.append({"test": test.id(), "seconds": time.perf_counter() - self.started})
        super().stopTest(test)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard", type=int, default=1, help="One-based batch number")
    parser.add_argument("--shards", type=int, default=1, help="Total number of batches")
    parser.add_argument("--start-directory", type=Path, default=ROOT / "tests")
    parser.add_argument("--pattern", default="test*.py")
    parser.add_argument("--timings", type=Path)
    parser.add_argument("--list", action="store_true", help="Print selected test IDs without running them")
    args = parser.parse_args(argv)
    if args.shards < 1 or not 1 <= args.shard <= args.shards:
        parser.error("require 1 <= shard <= shards")
    loader = unittest.TestLoader()
    discovered = sorted(cases(loader.discover(str(args.start_directory), pattern=args.pattern)), key=lambda test: test.id())
    selected = discovered[args.shard - 1::args.shards]
    if not selected:
        parser.error("selected batch contains no tests")
    if args.list:
        print(json.dumps([test.id() for test in selected], indent=2))
        return 0
    print(f"Batch {args.shard}/{args.shards}: {len(selected)} of {len(discovered)} discovered tests", file=sys.stderr, flush=True)
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2, resultclass=TimedResult).run(unittest.TestSuite(selected))
    timings = {"schema_version": 1, "shard": args.shard, "shards": args.shards,
               "discovered": len(discovered), "selected": len(selected), "tests_run": result.testsRun,
               "successful": result.wasSuccessful(), "seconds": time.perf_counter() - started,
               "tests": result.durations}
    print("\nSlowest tests:", file=sys.stderr)
    for item in sorted(result.durations, key=lambda item: item["seconds"], reverse=True)[:10]:
        print(f"{item['seconds']:8.3f}s {item['test']}", file=sys.stderr)
    if args.timings:
        args.timings.parent.mkdir(parents=True, exist_ok=True)
        args.timings.write_text(json.dumps(timings, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
