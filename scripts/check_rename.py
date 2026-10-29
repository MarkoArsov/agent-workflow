#!/usr/bin/env python3
"""Reject old product names except reviewed, exact compatibility/history lines."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OLD_NAME = re.compile(r"agent[ ]?flow|\baf-", re.I)
EXCLUSIONS = {".git", ".venv", "node_modules", "__pycache__", ".build", ".dist"}


def scan(root):
    root = root.resolve()
    exceptions = json.loads((ROOT / "scripts/rename-exceptions.json").read_text())
    allowed = {(item["path"], item["sha256"]) for item in exceptions}
    if root == ROOT:
        names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root).decode().split("\0")
        files = [root / name for name in names if name]
    else:
        files = sorted(root.rglob("*"))
    findings = []
    for path in files:
        relative = path.relative_to(root)
        if root == ROOT and relative.as_posix() == "scripts/rename-exceptions.json":
            continue
        if not path.is_file() or path.is_symlink() or any(part in EXCLUSIONS for part in relative.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            continue
        key = relative.as_posix() if root == ROOT else root.name + "/" + relative.as_posix()
        for number, line in enumerate(content.splitlines(), 1):
            if not OLD_NAME.search(line):
                continue
            fingerprint = hashlib.sha256(line.encode()).hexdigest()
            if (key, fingerprint) not in allowed:
                findings.append(f"{relative.as_posix()}:{number}: unreviewed old product name")
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    findings = scan(args.root)
    for finding in findings:
        print(finding)
    print(f"Rename audit: {len(findings)} unreviewed old-name lines.")
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
