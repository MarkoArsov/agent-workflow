#!/usr/bin/env python3
"""Local/offline installer entry point."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "runtime"))
from stageway.install import main
if __name__ == "__main__":
    main()

