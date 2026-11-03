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
    limit = {'files': settings['max_changed_files'], 'lines': settings['max_changed_lines']}
    # Tasks bound before the ceiling existed keep the size gate at the limit itself.
    factor = settings.get('ceiling_factor', 1)
    if value['files'] > limit['files'] * factor or value['lines'] > limit['lines'] * factor:
        pending.append({'kind': 'size', 'files': value['files'], 'lines': value['lines'], 'limit': limit,
                        'ceiling': {'files': limit['files'] * factor, 'lines': limit['lines'] * factor}})
        state.pop('diff_advisory', None)
    elif value['files'] > limit['files'] or value['lines'] > limit['lines']:
        # Over the limit but under the ceiling: recorded for the PR and the ledger, never a stop.
        state['diff_advisory'] = {'files': value['files'], 'lines': value['lines'], 'limit': limit,
                                  'fingerprint': value['fingerprint']}
    else:
        state.pop('diff_advisory', None)
    # Protected paths the approved plan declares are approved with the plan.
    declared = manifest.get('protected_paths', [])
    undeclared = [item for item in value['protected_paths'] if not matches(item['path'], declared)]
    if undeclared:
        pending.append({'kind': 'protected_paths', 'paths': undeclared})
    approved = {x['kind'] for x in state.get('approvals', []) if x['fingerprint'] == value['fingerprint']}
    pending = [x | {'fingerprint': value['fingerprint']} for x in pending if x['kind'] not in approved]
    state['pending_approvals'] = pending
    if pending:
        state['approval'] = pending[0]; state['status'] = 'needs_approval'
    else:
        state.pop('approval', None)
    return bool(pending)
