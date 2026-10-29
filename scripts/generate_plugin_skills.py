#!/usr/bin/env python3
"""Generate native prefixed discovery wrappers from the shared adapter source."""
from pathlib import Path
import argparse
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
from plovi.adapters import entry_names, skill_files
from plovi.extensions import catalog

def generate(check=False):
    expected = {}
    for name, info in catalog().items():
        for public in entry_names(name):
            for relative, text in skill_files(name, info, public).items():
                path = ROOT / "templates/plugin-skills" / public / relative
                if relative == "scripts/dispatch.py":
                    from plovi.adapters import entry_name
                    note = f"{public} is now {entry_name(name)}; use {entry_name(name)} (alias available until 1.0)." if public != entry_name(name) else None
                    text = ("#!/usr/bin/env python3\nfrom pathlib import Path\n"
                            "root = Path(__file__).resolve().parents[4]\n"
                            "source = (root / 'templates/adapters/dispatch.py').read_text()\n"
                            "source = source.replace('# bootstrap:include', (root / 'templates/adapters/bootstrap.py').read_text())\n"
                            f"source = source.replace('SKILL_NAME = None', {('SKILL_NAME = ' + repr(name))!r})\n"
                            f"source = source.replace('ALIAS_NOTE = None', {('ALIAS_NOTE = ' + repr(note))!r})\n"
                            "source = source.replace('for candidate in candidates:', 'candidates.append(root)' + chr(10) + 'for candidate in candidates:')\n"
                            "exec(compile(source, str(root / 'templates/adapters/dispatch.py'), 'exec'))\n")
                expected[path] = text
    stale = [p for p, text in expected.items() if not p.is_file() or p.read_text() != text]
    obsolete = set(p for p in (ROOT / "templates/plugin-skills").rglob("*") if p.is_file()) - set(expected)
    if check:
        if stale or obsolete:
            raise SystemExit("Native discovery wrappers are stale; run scripts/generate_plugin_skills.py")
    else:
        for path in obsolete:
            path.unlink()
        for path in stale:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected[path], encoding="utf-8", newline="")
    print("Native discovery wrappers are current.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--check", action="store_true")
    generate(parser.parse_args().check)
