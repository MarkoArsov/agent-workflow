#!/usr/bin/env python3
"""Local/offline installer entry point."""
import sys
from pathlib import Path
if sys.platform == "win32" and not sys.flags.utf8_mode:
    # Package files are UTF-8; Windows Python otherwise reads text in the ANSI code page.
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, "-X", "utf8", *sys.orig_argv[1:]]))
sys.path.insert(0, str(Path(__file__).resolve().parent / "runtime"))
from agentflow.install import main
if __name__ == "__main__":
    main()

