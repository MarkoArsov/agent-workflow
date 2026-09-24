#!/usr/bin/env python3
"""Build a deterministic allowlisted source payload; never include local project state."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
from stageway.install import files_in, validate_source

def build(destination):
    marker = validate_source(ROOT)
    prefix = "stageway-" + marker["version"]
    paths = list(files_in(ROOT))
    checksums = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    contents = {str(p.relative_to(ROOT)): (p.read_bytes(), p.stat().st_mode & 0o777) for p in paths}
    contents["package-files.json"] = ((json.dumps(checksums, indent=2, sort_keys=True) + "\n").encode(), 0o644)
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / (prefix + ".tar.gz")
    with archive.open("wb") as output, gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as tar:
            for name, (content, mode) in sorted(contents.items()):
                info = tarfile.TarInfo(prefix + "/" + name)
                info.size = len(content); info.mode = mode; info.mtime = 0
                info.uid = info.gid = 0; info.uname = info.gname = ""
                tar.addfile(info, io.BytesIO(content))
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    (destination / (archive.name + ".sha256")).write_text(sha + "  " + archive.name + "\n")
    print(json.dumps({"archive": str(archive), "sha256": sha, "files": len(contents)}))
    return archive

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / ".dist")
    build(parser.parse_args().output)
