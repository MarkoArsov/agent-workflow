#!/usr/bin/env python3
"""Scan deliverables without committing the private denylist itself."""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path

IGNORED = {".git", "__pycache__", ".venv", ".build", ".dist", "node_modules"}
PATTERNS = {
    "personal path": re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/"),
    "credential": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)"),
    "email": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
}

def violations(text, deny):
    result = []
    for term in deny:
        if re.search(term, text, re.I):
            result.append("private term: " + term)
    for label, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            if label == "email" and (match[0].endswith((".invalid", "@example.com", "@example.org")) or match[0].startswith("git@")):
                continue
            result.append(label)
    return sorted(set(result))

def scan(root, deny, history=False):
    findings, count = [], 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(x in IGNORED for x in relative.parts):
            continue
        if path.is_symlink():
            text = str(relative) + "\n" + str(path.readlink())
        elif path.is_file():
            text = str(relative) + "\n" + path.read_bytes().decode("utf-8", errors="replace")
        else:
            continue
        count += 1
        for reason in violations(text, deny):
            findings.append((str(relative), reason))
    if history:
        commits = subprocess.check_output(["git", "-C", str(root), "rev-list", "--all"], text=True).splitlines()
        for commit in commits:
            paths = subprocess.check_output(["git", "-C", str(root), "ls-tree", "-r", "--name-only", commit], text=True).splitlines()
            for name in paths:
                data = subprocess.check_output(["git", "-C", str(root), "show", f"{commit}:{name}"])
                count += 1
                for reason in violations(name + "\n" + data.decode("utf-8", errors="replace"), deny):
                    findings.append((commit[:8] + ":" + name, reason))
            message = subprocess.check_output(["git", "-C", str(root), "show", "-s", "--format=%B", commit], text=True)
            findings += [(commit[:8] + ":message", reason) for reason in violations(message, deny)]
    return count, findings

def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path, nargs="?", default=Path("."))
    p.add_argument("--deny-file", type=Path)
    p.add_argument("--history", action="store_true")
    args = p.parse_args()
    deny = [x.strip() for x in args.deny_file.read_text().splitlines() if x.strip() and not x.startswith("#")] if args.deny_file else []
    count, findings = scan(args.root.resolve(), deny, args.history)
    for name, reason in findings:
        print(f"{name}: {reason}")
    print(f"Scanned {count} items; {len(findings)} findings; private denylist {'enabled' if deny else 'not supplied'}.")
    return bool(findings)

if __name__ == "__main__":
    raise SystemExit(main())

