#!/bin/sh
# Install Agent Flow.
#
#   curl -fsSL https://agentic.markoarsov.com/install.sh | sh
#
# Options (after `sh -s --`):
#   --project PATH       install into one project instead of for your user account
#   --agents claude ...  choose agent CLIs instead of detecting them
# Other:
#   AGENTFLOW_REF=v0.1.0 pin a release tag or branch (default: latest release, else main)
#   --local-source PATH  install from a checkout without downloading (first argument)
set -eu

repo="MarkoArsov/agent-workflow"

fail() {
  printf 'agentflow: %s\n' "$1" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || fail "Python 3.11 or newer is required. Install it from https://www.python.org/downloads/ and run this again."
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' || fail "Python 3.11 or newer is required; found $(python3 -V 2>&1)."
command -v git >/dev/null 2>&1 || fail "Git is required. Install it from https://git-scm.com/downloads and run this again."

if [ "${1:-}" = "--local-source" ]; then
  workflow_source=$2
  shift 2
  exec python3 "$workflow_source/install.py" --local-source "$workflow_source" "$@"
fi

command -v curl >/dev/null 2>&1 || fail "curl is required to download Agent Flow."

workflow_ref="${AGENTFLOW_REF:-}"
if [ -z "$workflow_ref" ]; then
  # /releases/latest redirects to /releases/tag/<tag> once a release exists.
  latest=$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$repo/releases/latest" 2>/dev/null || true)
  case "$latest" in
    */releases/tag/*) workflow_ref=${latest##*/} ;;
    *) workflow_ref=main ;;
  esac
fi

workflow_temp=$(mktemp -d)
trap 'rm -rf "$workflow_temp"' EXIT HUP INT TERM
printf 'Downloading Agent Flow (%s)...\n' "$workflow_ref"
curl -fsSL "https://github.com/$repo/archive/$workflow_ref.tar.gz" -o "$workflow_temp/package.tar.gz" \
  || fail "Could not download $workflow_ref from github.com/$repo."
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
