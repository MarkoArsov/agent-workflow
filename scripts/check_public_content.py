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

PUBLIC_COAUTHOR = 'noreply' + '@anthropic.com'


def public_attribution_spans(text):
    """Only exempt the reviewed address inside a final, separated trailer block."""
    block_start = text.rstrip().rfind('\n\n')
    if block_start < 0:
        return set()
    block = text[block_start + 2:].rstrip()
    lines = block.splitlines()
    if not lines or not all(re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*: .+', line) for line in lines):
        return set()
    allowed = set()
    offset = block_start + 2
    for line in lines:
        match = re.fullmatch(r'Co-Authored-By: [^<>\r\n]+ <([^<>]+)>', line, re.I)
        if match and match[1] == PUBLIC_COAUTHOR:
            allowed.add((offset + match.start(1), offset + match.end(1)))
        offset += len(line) + 1
    return allowed


def violations(text, deny, *, commit_message=False):
    result = []
    for term in deny:
        if re.search(term, text, re.I):
            result.append("private term")
    allowed = public_attribution_spans(text) if commit_message else set()
    for label, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            if label == "email" and (match[0].endswith((".invalid", "@example.com", "@example.org")) or match[0].startswith("git@")):
                continue
            if label == 'email' and match.span() in allowed:
                continue
            result.append(label)
    return sorted(set(result))


def history_findings(root, deny):
    """Read reachable objects in two Git calls; inspect unchanged path/blob pairs once.

    Tree objects retain byte-exact names, symlink targets and deleted files. Each
    finding names a representative commit that contains it. Commit messages are
    always inspected individually, independent of file-content deduplication.
    """
    git = ['git', '-C', str(root)]
    listing = subprocess.check_output(git + ['rev-list', '--objects', '--all'])
    ids = list(dict.fromkeys(line.split(b' ', 1)[0] for line in listing.splitlines()))
    if not ids:
        return 0, []
    batch = subprocess.run(git + ['cat-file', '--batch'], input=b'\n'.join(ids) + b'\n',
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    objects, position = {}, 0
    while position < len(batch):
        end = batch.index(b'\n', position)
        oid, kind, size = batch[position:end].split()
        position = end + 1
        length = int(size)
        objects[oid.decode('ascii')] = (kind, batch[position:position + length])
        position += length + 1

    def entries(tree, prefix=''):
        data = objects[tree][1]
        position = 0
        hash_bytes = len(tree) // 2  # SHA-1 and SHA-256 Git repositories.
        while position < len(data):
            end = data.index(b'\0', position)
            mode, name = data[position:end].split(b' ', 1)
            oid = data[end + 1:end + 1 + hash_bytes].hex()
            position = end + 1 + hash_bytes
            path = prefix + name.decode('utf-8', errors='replace')
            if mode == b'40000':
                yield from entries(oid, path + '/')
            elif mode != b'160000':  # Gitlinks belong to a separate repository.
                yield path, oid

    findings, seen, count = [], set(), 0
    for commit, (kind, data) in objects.items():
        if kind != b'commit':
            continue
        headers, message = data.split(b'\n\n', 1)
        tree = headers.splitlines()[0].split()[1].decode('ascii')
        for name, oid in entries(tree):
            if (name, oid) in seen:
                continue
            seen.add((name, oid))
            count += 1
            text = name + '\n' + objects[oid][1].decode('utf-8', errors='replace')
            findings.extend((commit[:8] + ':' + name, reason) for reason in violations(text, deny))
        count += 1
        findings.extend((commit[:8] + ':message', reason) for reason in
                        violations(message.decode('utf-8', errors='replace'), deny, commit_message=True))
    return count, findings

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
        history_count, historical = history_findings(root, deny)
        count += history_count
        findings += historical
    return count, findings


def diagnostic_name(name, deny):
    """Paths can themselves contain secrets; keep log output safe as well."""
    for term in deny:
        name = re.sub(term, '[private term]', name, flags=re.I)
    for label, pattern in PATTERNS.items():
        name = pattern.sub('[' + label + ']', name)
    # A filename with control characters must not inject additional log lines.
    return name.encode('unicode_escape').decode('ascii')


def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path, nargs="?", default=Path("."))
    p.add_argument("--deny-file", type=Path)
    p.add_argument("--history", action="store_true")
    args = p.parse_args()
    deny = [x.strip() for x in args.deny_file.read_text().splitlines() if x.strip() and not x.startswith("#")] if args.deny_file else []
    count, findings = scan(args.root.resolve(), deny, args.history)
    for name, reason in findings:
        print(f"{diagnostic_name(name, deny)}: {reason}")
    print(f"Scanned {count} items; {len(findings)} findings; private denylist {'enabled' if deny else 'not supplied'}.")
    return bool(findings)

if __name__ == "__main__":
    raise SystemExit(main())

