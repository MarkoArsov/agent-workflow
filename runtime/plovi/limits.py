"""Cumulative diff measurements and approvals bound to content, mode and path."""
from pathlib import Path
from . import git_ops, policy
from .manifest import matches
from .util import digest, json_text, run

def measure(project, manifest, state):
    current = git_ops.snapshot(project, state['checkouts'])
    changes = git_ops.changes(state['baseline'], current)
    settings = (state.get('policy') or policy.effective(project, manifest))['values']
    counts = {'files': 0, 'lines': 0}
    protected = []
    owned = {}
    for row in manifest['repositories']:
        if row['access'] != 'write': continue
        name = row['id']; root = Path(state['checkouts'][name])
        owned[name] = {}
        for path in changes[name]:
            before = state['baseline'][name]['files'].get(path)
            after = current[name]['files'].get(path)
            owned[name][path] = {'before': before, 'after': after}
            if matches(path, settings['paths']['protected']):
                protected.append({'repository': name, 'path': path})
            if matches(path, settings['limits']['size_exempt']): continue
            counts['files'] += 1
            if before is None:
                # git diff --no-index gives Git's text/binary and line semantics
                result = run(['git', 'diff', '--no-index', '--numstat', '--', __import__('os').devnull, str(root / path)], root, check=False)
            else:
                result = run(['git', 'diff', '--numstat', '--no-renames', state['baseline'][name]['head'], '--', path], root)
            for line in result.stdout.splitlines():
                a, b, _ = line.split('\t', 2)
                counts['lines'] += 1 if a == '-' else int(a) + int(b)
    return counts | {'protected_paths': protected, 'fingerprint': digest(json_text(owned))}

def gate(project, manifest, state):
    value = measure(project, manifest, state)
    state['diff'] = value
    settings = state['policy']['values']['limits']
    pending = []
    if value['files'] > settings['max_changed_files'] or value['lines'] > settings['max_changed_lines']:
        pending.append({'kind': 'size', 'files': value['files'], 'lines': value['lines'],
                        'limit': {'files': settings['max_changed_files'], 'lines': settings['max_changed_lines']}})
    if value['protected_paths']:
        pending.append({'kind': 'protected_paths', 'paths': value['protected_paths']})
    approved = {x['kind'] for x in state.get('approvals', []) if x['fingerprint'] == value['fingerprint']}
    pending = [x | {'fingerprint': value['fingerprint']} for x in pending if x['kind'] not in approved]
    state['pending_approvals'] = pending
    if pending:
        state['approval'] = pending[0]; state['status'] = 'needs_approval'
    else:
        state.pop('approval', None)
    return bool(pending)
