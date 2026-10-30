"""Task ownership with short repository-operation critical sections."""
from contextlib import contextmanager, ExitStack
from pathlib import Path
import os
import re
import time
from . import state
from .migration import lock_held
from .util import WorkflowError, git, read_json, write_json

def identity(project, name):
    root = project.repo_path(name)
    common = Path(git(root, 'rev-parse', '--git-common-dir'))
    return os.path.normcase(str((root / common).resolve()))

def overlap(left, right):
    from .manifest import matches
    # Distinct literal prefixes prove separation, including future names.
    def prefix(pattern):
        return re.split(r'[*?\[]', os.path.normcase(Path(pattern).as_posix()), maxsplit=1)[0]
    for a in left:
        for b in right:
            pa, pb = prefix(a), prefix(b)
            if pa.startswith(pb) or pb.startswith(pa):
                return True
            if matches(pa, [b]) or matches(pb, [a]):
                return True
    return False

@contextmanager
def acquire(project, manifest, *, no_wait=False):
    local = project.config / 'local'
    path = local / 'claims.json'
    task = manifest['task']
    (state.directory(project, task) / 'cancel.json').unlink(missing_ok=True)
    def patterns(name, paths):
        root = project.repo_path(name)
        alternate = root.with_name(root.name.swapcase())
        insensitive = alternate != root and alternate.exists() and alternate.samefile(root)
        return [p.casefold() for p in paths] if insensitive else paths
    from .manifest import custom_stages
    custom = custom_stages(project)
    def writable(row):
        paths = list(row['paths'])
        if 'implement-tests' in manifest['stages']:
            paths.extend(row.get('test_paths', []))
        for stage in manifest['stages']:
            paths.extend(item['path'] for item in custom.get(stage, {}).get('outputs', [])
                         if item['repository'] == row['id'])
        return list(dict.fromkeys(paths))
    rows = [{'repository': identity(project, r['id']), 'strategy': project.repository(r['id'])['checkout_strategy'],
             'paths': patterns(r['id'], writable(r))}
            for r in manifest['repositories'] if r['access'] == 'write']
    deadline = time.monotonic() + manifest.get('limits', {}).get('timeout_seconds', 1800)
    registered = False
    try:
        while not registered:
            if lock_held(local / 'runner.lock'):
                raise WorkflowError('A legacy runner owns the project lock; finish or cancel it first')
            existing = read_json(path, {})
            # Hold successful nonblocking ownership probes through claim removal.
            # A new owner cannot reuse an identical claim between probe and mutation.
            with ExitStack() as probes:
                stale = set()
                for name in existing:
                    if name == task:
                        continue
                    try:
                        probes.enter_context(state.lock(state.directory(project, name) / 'runner.lock'))
                    except WorkflowError:
                        continue
                    stale.add(name)
                with state.lock(local / 'repo-ops.lock', wait=True):
                    claims = read_json(path, {})
                    for name in stale:
                        if claims.get(name) == existing.get(name): claims.pop(name, None)
                    conflicts = []
                    for name, claim in claims.items():
                        if name == task: continue
                        for a in rows:
                            for b in claim['repositories']:
                                if a['repository'] == b['repository'] and (a['strategy'] != 'worktree' or b['strategy'] != 'worktree' or overlap(a['paths'], b['paths'])):
                                    conflicts.append(name)
                    if not conflicts:
                        claims[task] = {'task': task, 'repositories': rows}
                        write_json(path, claims); registered = True
            if not registered:
                if no_wait:
                    raise WorkflowError('Repository claim conflict with tasks: ' + ', '.join(sorted(set(conflicts))))
                root = state.directory(project, task)
                saved = read_json(root / 'state.json', {})
                state.save(root, saved | {'task': task, 'status': 'waiting', 'waiting_for': sorted(set(conflicts))})
                if (root / 'cancel.json').exists():
                    state.save(root, saved | {'task': task, 'status': 'cancelled'})
                    raise WorkflowError('Task cancelled while waiting for repository claims')
                if time.monotonic() >= deadline:
                    state.save(root, saved | {'task': task, 'status': 'failed', 'error': 'Timed out waiting for repository claims'})
                    raise WorkflowError('Timed out waiting for repository claims')
                time.sleep(0.1)
        yield
    finally:
        if registered:
            with state.lock(local / 'repo-ops.lock', wait=True):
                claims = read_json(path, {}); claims.pop(task, None); write_json(path, claims)
