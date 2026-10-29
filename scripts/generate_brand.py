#!/usr/bin/env python3
"""Render supplied SVG brand assets with an existing Playwright Chromium install.

Development only. No downloads or package installs are performed. Supply --node,
--node-modules or --chromium when these tools are not on their usual search paths.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", default=shutil.which("node"))
    parser.add_argument("--node-modules", type=Path)
    parser.add_argument("--chromium", type=Path)
    args = parser.parse_args()
    if not args.node:
        parser.error("Node and Playwright are development prerequisites; select an existing Node executable with --node")
    env = dict(os.environ)
    if args.node_modules:
        env["NODE_PATH"] = str(args.node_modules.resolve())
    if args.chromium:
        env["PLOVI_CHROMIUM"] = str(args.chromium.resolve())
    return subprocess.call([args.node, str(Path(__file__).with_suffix('.cjs'))], env=env)


if __name__ == "__main__":
    raise SystemExit(main())
