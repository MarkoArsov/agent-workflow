#!/usr/bin/env python3
"""Version-selecting launcher; payloads and project extensions remain separate."""
# bootstrap:include
if sys.platform == "win32" and not sys.flags.utf8_mode:
    try:
        raise SystemExit(subprocess.call([sys.executable, "-X", "utf8", *sys.orig_argv[1:]]))
    except KeyboardInterrupt:
        raise SystemExit(130)

LOCAL_RUNTIME = None
args = sys.argv[1:]
start = Path.cwd().resolve()
if "--project" in args and args.index("--project") + 1 < len(args):
    start = Path(args[args.index("--project") + 1]).expanduser().resolve()
if Path(__file__).stem == "agentflow":
    print("agentflow is now plovi; this alias works until 1.0", file=sys.stderr)
project, profile, candidates, linked = bootstrap(start)
if LOCAL_RUNTIME and not profile:
    local = bootstrap_read(LOCAL_RUNTIME / "active.json", {})
    if local:
        candidates.insert(0, Path(local["path"]))
for candidate in candidates:
    runtime = bootstrap_runtime(candidate, profile, linked)
    if runtime:
        main = importlib.import_module(runtime + ".cli").main
        raise SystemExit(main(args))
raise SystemExit("No matching workflow package. Install the project's pinned version, or install globally before setup.")
