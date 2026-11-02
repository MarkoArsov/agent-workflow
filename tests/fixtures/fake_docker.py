#!/usr/bin/env python3
"""Fake docker/podman for tests.

Records argv and sanitized environment, then executes the inner command locally.
Set PLOVI_TEST_CONTAINER_RECORD to a JSON file path to collect invocation records.
Set PLOVI_TEST_CONTAINER_EXIT to override the exit code (default: execute inner cmd).
Set PLOVI_TEST_CONTAINER_INSPECT_INVALID=1 to make 'inspect' succeed (exit 0) with
metadata that has no usable Id, simulating a runtime that answers but cannot be
pinned to an immutable image identity.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys


def _handle_inspect(argv):
    """Return the fake 'docker/podman inspect <image>' JSON payload, or None."""
    if not argv or argv[0] != "inspect":
        return None
    targets = [a for a in argv[1:] if not a.startswith("-")]
    image = targets[-1] if targets else ""
    if os.environ.get("PLOVI_TEST_CONTAINER_INSPECT_INVALID") == "1":
        return [{"RepoTags": [image]}]
    fake_id = image if image.startswith("sha256:") and len(image) == 71 and all(c in "0123456789abcdef" for c in image[7:]) else "sha256:" + hashlib.sha256(image.encode()).hexdigest()
    return [{"Id": fake_id, "RepoTags": [image]}]


def _parse_inner_cmd(argv):
    """Extract the inner command from docker/podman run argv."""
    if "run" not in argv:
        return None
    run_idx = argv.index("run")
    rest = argv[run_idx + 1:]
    flags_with_values = {
        "--env", "-e", "--volume", "-v", "--workdir", "-w", "--name",
        "--network", "--user", "-u", "--env-file", "--label", "-l",
        "--cidfile", "--entrypoint", "--add-host", "--memory", "--cpus",
        "--tmpfs", "--mount", "--network-alias",
    }
    i = 0
    while i < len(rest):
        arg = rest[i]
        # Check for --flag=value form
        if arg.startswith("-") and "=" not in arg:
            if arg in flags_with_values:
                i += 2
            else:
                i += 1
        elif arg.startswith("-"):
            i += 1
        else:
            # This is the image name; rest is the inner command
            return rest[i + 1:]
    return []


def main():
    argv = sys.argv[1:]
    record_path = os.environ.get("PLOVI_TEST_CONTAINER_RECORD")
    forced_exit = os.environ.get("PLOVI_TEST_CONTAINER_EXIT")
    inner_cmd = _parse_inner_cmd(argv)
    inspect_payload = _handle_inspect(argv)

    if record_path:
        # Sanitize environment: omit values of potential secret keys
        sensitive_patterns = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
        sanitized_env = {
            k: ("<redacted>" if any(p in k.upper() for p in sensitive_patterns) else v)
            for k, v in os.environ.items()
        }
        record = {
            "argv": argv,
            "env": sanitized_env,
            "env_keys": sorted(os.environ.keys()),
            "inner_cmd": inner_cmd,
        }
        existing = []
        if os.path.exists(record_path):
            try:
                with open(record_path) as fh:
                    existing = json.load(fh)
            except (ValueError, OSError):
                existing = []
        existing.append(record)
        with open(record_path, "w") as fh:
            json.dump(existing, fh, indent=2)

    if forced_exit is not None:
        sys.exit(int(forced_exit))

    if argv and argv[0] == "inspect" and argv[-1] == "plovi/runner:missing":
        print("No such image", file=sys.stderr)
        sys.exit(1)

    if inspect_payload is not None:
        print(json.dumps(inspect_payload))
        sys.exit(0)

    if inner_cmd and inner_cmd[0] == "echo":
        # echo is a shell builtin on Windows; emulate it without invoking a shell.
        print(" ".join(inner_cmd[1:]))
        sys.exit(0)

    if inner_cmd:
        result = subprocess.run(inner_cmd)
        sys.exit(result.returncode)

    sys.exit(0)


if __name__ == "__main__":
    main()
