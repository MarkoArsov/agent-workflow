#!/usr/bin/env python3
"""Owned discovery wrapper. Project skill bodies are never stored here."""
# bootstrap:include
SKILL_NAME = None
ALIAS_NOTE = None
if ALIAS_NOTE:
    print(ALIAS_NOTE, file=sys.stderr)
start = Path.cwd().resolve()
project, profile, candidates, linked = bootstrap(start)
for candidate in candidates:
    runtime = bootstrap_runtime(candidate, profile, linked)
    if runtime:
        resolve = importlib.import_module(runtime + ".project").resolve
        resolve_skill = importlib.import_module(runtime + ".extensions").resolve_skill
        WorkflowError = importlib.import_module(runtime + ".util").WorkflowError
        try:
            context = resolve(start)
        except WorkflowError as exc:
            if SKILL_NAME not in {"project-setup", "setup", "update-models", "publish-workflow"} or project:
                raise
            context = None
        print(resolve_skill(SKILL_NAME, context, candidate))
        break
else:
    raise SystemExit("No matching workflow runtime. Install the project's pinned version or run project-setup after a global installation.")
