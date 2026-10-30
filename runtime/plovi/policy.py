"""Reviewed project policy, explicit-key precedence and conservative TOML edits."""
from __future__ import annotations
import copy
import difflib
import json
import math
import re
import sys
import tomllib
from pathlib import Path, PureWindowsPath
from .util import WorkflowError, atomic_write

_DEFAULTS = {
    'limits': {'running_tasks': 2, 'waiting_for_review': 3, 'attempts_per_stage': 2,
               'max_changed_files': 40, 'max_changed_lines': 1500,
               'size_exempt': ['**/package-lock.json', '**/*.lock']},
    'paths': {'protected': ['.github/workflows/**', '**/migrations/**']},
    'execution': {'unattended_permission_mode': 'restricted'},
    'autonomy': {'level': 'assisted'}, 'grants': {}}

def defaults():
    return copy.deepcopy(_DEFAULTS)

def validate(value):
    if type(value) is not dict:
        raise WorkflowError('Policy must contain tables')
    for section, entries in value.items():
        if section not in _DEFAULTS:
            _unknown(section, _DEFAULTS)
        if type(entries) is not dict:
            raise WorkflowError(f'{section} must be a table')
        for key, val in entries.items():
            path = f'{section}.{key}'
            if key not in _DEFAULTS[section]:
                _unknown(path, [f'{section}.{x}' for x in _DEFAULTS[section]])
            example = _DEFAULTS[section][key]
            if type(val) is not type(example):
                raise WorkflowError(f'{path}: expected {type(example).__name__}')
            if type(val) is int and not 1 <= val <= (5 if key == 'attempts_per_stage' else 10000000):
                raise WorkflowError(f'{path}: positive bounded integer required')
            if type(val) is list:
                for item in val:
                    if (not isinstance(item, str) or not item or Path(item).is_absolute()
                            or PureWindowsPath(item).drive or '\\' in item or '..' in item.split('/')):
                        raise WorkflowError(f'{path}: repository-relative string globs required')
            if key == 'level' and val not in {'assisted', 'ready', 'auto'}:
                raise WorkflowError(f'{path}: choose assisted, ready or auto')
            if key == 'unattended_permission_mode' and val not in {'restricted', 'trusted'}:
                raise WorkflowError(f'{path}: choose restricted or trusted')
    return value

def _unknown(path, choices):
    close = difflib.get_close_matches(path, choices, n=1)
    raise WorkflowError(f'Unknown policy key {path}' + (f'; did you mean {close[0]}?' if close else ''))

def load(project):
    path = project.root / 'plovi.toml'
    try:
        value = tomllib.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    except (tomllib.TOMLDecodeError, UnicodeError) as exc:
        raise WorkflowError(f'plovi.toml: {exc}') from exc
    return validate(value)

def effective(project, manifest=None):
    values = defaults()
    sources = {s: {k: 'built-in' for k in row} for s, row in values.items()}
    profile = project.profile
    for section in values:
        for key in values[section]:
            old_key = 'attempts_per_route' if key == 'attempts_per_stage' else key
            if old_key in profile.get(section, {}):
                values[section][key] = copy.deepcopy(profile[section][old_key])
                sources[section][key] = 'profile'
    explicit = load(project)
    for section, row in explicit.items():
        for key, val in row.items():
            values[section][key] = val; sources[section][key] = 'plovi.toml'
    for key, val in (manifest or {}).get('limits', {}).items():
        dest = 'attempts_per_stage' if key == 'attempts_per_route' else key
        if dest in values['limits']:
            values['limits'][dest] = val; sources['limits'][dest] = 'plan'
    validate(values)
    return {'values': values, 'sources': sources}

def execution(project, manifest, *, trusted=False, unattended=False):
    result = copy.deepcopy(project.profile['execution'])
    resolved = effective(project, manifest)
    if trusted:
        mode, source = 'trusted', '--trusted'
    elif unattended:
        mode = resolved['values']['execution']['unattended_permission_mode']
        source = 'policy' if resolved['sources']['execution']['unattended_permission_mode'] == 'plovi.toml' else 'unattended default'
    else:
        mode, source = result['permission_mode'], 'profile'
    result.update(permission_mode=mode, permission_source=source)
    if mode == 'restricted' and any(r['provider'] == 'claude' for routes in manifest.get('routes', project.profile['pipeline']['routes']).values() for r in routes):
        settings = result.setdefault('provider_settings', {}).setdefault('claude', {})
        if not settings.get('allowed_tools'):
            from .manifest import command_for
            tools = ['Read', 'Edit', 'Write', 'Glob', 'Grep', 'Bash(git status*)', 'Bash(git diff*)']
            for check in manifest['checks']:
                command = command_for(project, check)
                argv = command['argv']
                if command.get('shell') or any(not re.fullmatch(r'[a-zA-Z0-9_./:=+@%\\-]+', arg) for arg in argv):
                    raise WorkflowError('Cannot encode configured check safely; supply execution.provider_settings.claude.allowed_tools')
                tools.append('Bash(' + ' '.join(argv) + ')')
            settings['allowed_tools'] = list(dict.fromkeys(tools))
    return result

def template():
    return '# Reviewed plovi policy. Uncomment values to override project defaults.\n' + ''.join(
        f'\n[{section}]\n' + ''.join(f'# {key} = {toml(val)}\n' for key, val in entries.items())
        for section, entries in _DEFAULTS.items())

def toml(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if type(value) is bool:
        return str(value).lower()
    if type(value) in (int, float) and (type(value) is int or math.isfinite(value)):
        return str(value)
    if type(value) is list and all(isinstance(x, str) for x in value):
        return '[' + ', '.join(toml(x) for x in value) + ']'
    raise WorkflowError('Unsupported TOML edit')

def set_value(project, dotted, raw, *, yes=False):
    path = project.root / 'plovi.toml'
    before = path.read_bytes() if path.exists() else b''
    text = before.decode('utf-8')
    try:
        value = tomllib.loads('value = ' + raw)['value']
        original = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise WorkflowError(f'plovi.toml: {exc}') from exc
    parts = dotted.split('.')
    if len(parts) != 2:
        raise WorkflowError('Choose a section.key policy value')
    section, key = parts
    validate({section: {key: value}})
    validate(original)
    if original.get(section, {}).get(key) == value and type(original.get(section, {}).get(key)) is type(value):
        return {'changed': False}
    newline = '\r\n' if b'\r\n' in before else '\n'
    lines = text.splitlines(keepends=True)
    start = end = None
    for i, line in enumerate(lines):
        header = re.fullmatch(r'\s*\[([a-z_]+)\]\s*(?:#.*)?(?:\r?\n)?', line)
        if header:
            if start is not None:
                end = i; break
            if header[1] == section:
                start = i + 1
    if start is None:
        if section in original:
            raise WorkflowError('Unsupported TOML table syntax; edit plovi.toml explicitly')
        result = text + (newline if text and not text.endswith('\n') else '') + f'[{section}]' + newline + f'{key} = {toml(value)}' + newline
    else:
        end = len(lines) if end is None else end
        found = False
        for i in range(start, end):
            match = re.match(r'(\s*' + re.escape(key) + r'\s*=\s*)(.*?)(\r?\n)?$', lines[i])
            if match:
                # Locate a comment only outside quoted strings and arrays.
                old = match[2]; quoted = False; escaped = False; comment = ''
                for j, char in enumerate(old):
                    if escaped:
                        escaped = False; continue
                    if char == '\\' and quoted:
                        escaped = True; continue
                    if char == '"': quoted = not quoted
                    if char == '#' and not quoted:
                        comment = ' ' + old[j:]; break
                lines[i] = match[1] + toml(value) + comment + (match[3] or '')
                found = True; break
        if not found:
            if key in original.get(section, {}):
                raise WorkflowError('Unsupported TOML assignment; edit plovi.toml explicitly')
            lines.insert(end, f'{key} = {toml(value)}' + newline)
        result = ''.join(lines)
    expected = copy.deepcopy(original); expected.setdefault(section, {})[key] = value
    try:
        parsed = tomllib.loads(result)
    except tomllib.TOMLDecodeError as exc:
        raise WorkflowError('Unsupported TOML edit; original preserved') from exc
    if parsed != expected:
        raise WorkflowError('Unsupported TOML edit; original preserved')
    diff = ''.join(difflib.unified_diff(text.splitlines(True), result.splitlines(True), fromfile='plovi.toml', tofile='plovi.toml'))
    print(diff)
    if not yes and (not sys.stdin.isatty() or input('Save reviewed policy? [y/N] ') != 'y'):
        raise WorkflowError('Review the diff and pass --yes or enter y interactively')
    from .state import lock
    with lock(project.config / 'local/policy.lock'):
        if (path.read_bytes() if path.exists() else b'') != before:
            raise WorkflowError('plovi.toml changed since preview; retry the edit')
        atomic_write(path, result)
    return {'changed': True}


def diagnostics(project):
    explicit = load(project)
    duplicate = []
    for section, row in explicit.items():
        for key in row:
            profile_key = 'attempts_per_route' if key == 'attempts_per_stage' else key
            if profile_key in project.profile.get(section, {}):
                duplicate.append(f'{section}.{key}')
    return {'missing': not (project.root / 'plovi.toml').exists(), 'duplicate_profile_keys': duplicate,
            'effective': effective(project), 'notice': 'Policy changes require reviewed rebind for existing tasks.'}
