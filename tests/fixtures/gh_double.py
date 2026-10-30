#!/usr/bin/env python3
"""Offline GitHub CLI double; every mutation and body is recorded."""
import json
import os
import sys
from pathlib import Path

path = Path(os.environ["PLOVI_TEST_GH_STATE"])
saved = json.loads(path.read_text()) if path.exists() else {"prs": [], "calls": []}
argv = sys.argv[1:]
body = Path(argv[argv.index("--body-file") + 1]).read_text() if "--body-file" in argv else None
saved["calls"].append({"argv": argv, "body": body})
if argv[:2] == ["repo", "view"]:
    output = "example/fixture"
elif argv[:2] == ["pr", "list"]:
    output = json.dumps(saved["prs"])
elif argv[:2] == ["pr", "view"]:
    output = json.dumps(saved["prs"][0])
elif argv[:2] == ["pr", "create"]:
    saved["prs"].append({"url": "https://example.invalid/pull/1", "isDraft": True, "body": body})
    output = saved["prs"][-1]["url"]
elif argv[:2] == ["pr", "edit"]:
    saved["prs"][0]["body"] = body
    output = saved["prs"][0]["url"]
else:
    raise SystemExit("Unsupported fixture gh call: " + repr(argv))
path.write_text(json.dumps(saved))
print(output)
