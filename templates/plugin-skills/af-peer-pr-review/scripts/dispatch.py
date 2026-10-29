#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[4]
source = (root / 'templates/adapters/dispatch.py').read_text()
source = source.replace('# bootstrap:include', (root / 'templates/adapters/bootstrap.py').read_text())
source = source.replace('SKILL_NAME = None', "SKILL_NAME = 'peer-pr-review'")
source = source.replace('ALIAS_NOTE = None', "ALIAS_NOTE = 'af-peer-pr-review is now plovi-peer-pr-review; use plovi-peer-pr-review (alias available until 1.0).'")
source = source.replace('for candidate in candidates:', 'candidates.append(root)' + chr(10) + 'for candidate in candidates:')
exec(compile(source, str(root / 'templates/adapters/dispatch.py'), 'exec'))
