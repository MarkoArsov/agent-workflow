#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[3]
name = Path(__file__).resolve().parents[1].name
source = (root / "templates/adapters/dispatch.py").read_text()
source = source.replace("SKILL_NAME = None", "SKILL_NAME = " + repr(name))
source = source.replace("for candidate in candidates:", "candidates.append(root)\nfor candidate in candidates:")
exec(compile(source, str(root / "templates/adapters/dispatch.py"), "exec"))
