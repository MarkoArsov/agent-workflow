#!/usr/bin/env python3
"""Export/check a standalone policy snapshot; never link another workflow's runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

SOURCE = Path(__file__).resolve().parents[1] / 'runtime/agentflow/model_policy'


def export(target, check=False):
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.iterdir() if p.is_file() and p.suffix in {'.py', '.json'}}
    manifest = {'schema_version': 1, 'component': 'model-policy', 'files': files}
    if check:
        observed = json.loads((target / 'export.json').read_text())
        if observed != manifest or any(not (target / name).is_file() or hashlib.sha256((target / name).read_bytes()).hexdigest() != digest for name, digest in files.items()):
            raise ValueError('Export differs from the reviewed source snapshot')
        return manifest
    if target.exists() and any(target.iterdir()):
        previous = json.loads((target / 'export.json').read_text())
        for name, digest in previous['files'].items():
            if Path(name).name != name or not (target / name).is_file() or hashlib.sha256((target / name).read_bytes()).hexdigest() != digest:
                raise ValueError('Export has local edits; review them before replacing it')
        for name in previous['files']:
            if name not in files:
                (target / name).unlink()
    target.mkdir(parents=True, exist_ok=True)
    for name in files:
        shutil.copyfile(SOURCE / name, target / name)
    (target / 'export.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('target', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    export(args.target, args.check)
    print('Policy snapshot verified' if args.check else 'Policy snapshot exported')
