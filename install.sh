#!/bin/sh
# Install a pinned release; use --local-source for an offline checkout.
set -eu
if [ "${1:-}" = "--local-source" ]; then
  workflow_source=$2
  shift 2
  exec python3 "$workflow_source/install.py" --local-source "$workflow_source" "$@"
fi
workflow_ref="${SCOREBOOK_REF:-v0.1.0}"
workflow_temp=$(mktemp -d)
trap 'rm -rf "$workflow_temp"' EXIT HUP INT TERM
curl -fsSL "https://github.com/MarkoArsov/agent-workflow/archive/refs/tags/$workflow_ref.tar.gz" -o "$workflow_temp/package.tar.gz"
python3 - "$workflow_temp" <<'PY'
import pathlib
import sys
import tarfile
root = pathlib.Path(sys.argv[1])
with tarfile.open(root / "package.tar.gz", "r:gz") as archive:
    members = archive.getmembers()
    for member in members:
        path = pathlib.PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
            raise SystemExit("Unsafe archive member")
    if hasattr(tarfile, "data_filter"):
        archive.extractall(root / "source", members=members, filter="data")
    else:
        archive.extractall(root / "source", members=members)
packages = list((root / "source").glob("*/workflow-package.json"))
if len(packages) != 1:
    raise SystemExit("Archive does not contain exactly one workflow package")
(root / "package-path").write_text(str(packages[0].parent))
PY
workflow_source=$(cat "$workflow_temp/package-path")
python3 "$workflow_source/install.py" --local-source "$workflow_source" "$@"
