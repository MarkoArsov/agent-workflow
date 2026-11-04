"""Independent, receipt-owned mirrors and task worktrees. All Git writes stay on host."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
import re
import time
from .state import lock, directory
from .util import WorkflowError, common_dir, git, identifier, read_json, run, same_path, user_data, write_json


def root(project):
    return safe(user_data().resolve(), 'projects', identifier(project.profile['project']['id']))


def safe(base, *parts):
    """Reject even in-root symlinks: ownership paths must have one spelling."""
    path = Path(base)
    for part in parts:
        if part in {'.', '..'} or Path(part).name != part:
            raise WorkflowError('Invalid factory ownership path component')
        path = path / part
        if path.is_symlink():
            raise WorkflowError('Factory path is a symlink; restore the owned directory before retrying')
    if not path.resolve().is_relative_to(Path(base).resolve()):
        raise WorkflowError('Factory path leaves its ownership root')
    return path


def receipt_path(project, task):
    return safe(root(project), 'allocations', identifier(task) + '.json')


def _url(value, cwd):
    if not value or any(ord(c) < 32 for c in value) or value.startswith('-'):
        raise WorkflowError('Configure a valid factory remote URL')
    parsed = urlsplit(value)
    if (parsed.password is not None or (parsed.scheme in {'http', 'https'} and parsed.username is not None)
            or parsed.query or parsed.fragment):
        raise WorkflowError('Factory remote contains credentials or URL parameters; use a credential helper and a clean remote URL')
    if '://' not in value and not re.match(r'(?:[^/@:]+@)?[^/:]+:.+', value):
        value = str((cwd / Path(value).expanduser()).resolve())
    return value


def identities(project, names):
    result = {}
    for name in names:
        repo = project.repository(identifier(name)); cwd = project.repo_path(name)
        if common_dir(cwd) is None:
            raise WorkflowError('Factory source must be a registered Git repository')
        def urls(push=False):
            rows = git(cwd, 'remote', 'get-url', *(['--push'] if push else []), '--all', repo['remote']).splitlines()
            if len(rows) != 1:
                raise WorkflowError('Factory requires one effective fetch URL and one push URL per repository')
            return _url(rows[0], cwd)
        result[name] = {'fetch': urls(), 'push': urls(True)}
    return result


def _register(project, names):
    path = safe(root(project), 'origin.json')
    wanted = identities(project, names)
    saved = read_json(path, {'project': project.profile['project']['id'], 'repositories': {}})
    if saved.get('project') != project.profile['project']['id']:
        raise WorkflowError('Factory project identity mismatch; select the original project ID')
    for name, urls in wanted.items():
        if name in saved['repositories'] and saved['repositories'][name] != urls:
            raise WorkflowError('Factory remote identity changed; review the project ID and remote URLs before retrying')
    saved['repositories'].update(wanted)
    write_json(path, saved)
    return wanted


def _mirror(project, name, urls):
    base = root(project)
    target = safe(base, 'mirrors', identifier(name) + '.git')
    creation = safe(base, 'mirrors', name + '.json')
    saved = read_json(creation)
    if saved is not None:
        if not saved.get('complete') or saved.get('identity') != urls or saved.get('path') != str(target):
            raise WorkflowError('Factory mirror creation is incomplete or changed; preserve it and repair the mirror receipt')
        if not target.is_dir() or common_dir(target) != target.resolve():
            raise WorkflowError('Factory mirror is missing or has different ownership')
    else:
        if target.exists():
            raise WorkflowError('Unowned factory mirror exists; no existing files were adopted')
        target.parent.mkdir(parents=True, exist_ok=True)
        saved = {'complete': False, 'identity': urls, 'path': str(target)}
        write_json(creation, saved)
        # --no-local prevents hardlinks/alternates to a user's clone, including local remotes.
        run(['git', 'clone', '--mirror', '--no-local', urls['fetch'], str(target)], target.parent)
        git(target, 'config', '--replace-all', 'remote.origin.fetch', '+refs/heads/*:refs/remotes/origin/*')
        git(target, 'config', 'remote.origin.mirror', 'false')
        git(target, 'fetch', '--prune', 'origin')
        saved['complete'] = True
        write_json(creation, saved)
    for component in ('objects', 'refs', 'config'):
        safe(target, component)
    if git(target, 'remote', 'get-url', 'origin') != urls['fetch'] or (target / 'objects/info/alternates').exists():
        raise WorkflowError('Factory mirror origin or independent object ownership changed; repair it before fetching')
    # Migrate the initial --mirror namespace; never fetch/prune task heads.
    git(target, 'config', '--replace-all', 'remote.origin.fetch', '+refs/heads/*:refs/remotes/origin/*')
    git(target, 'config', 'remote.origin.mirror', 'false')
    git(target, 'fetch', '--prune', 'origin')
    return target


def refresh(project, repository):
    with lock(project.config / 'local/repo-ops.lock', wait=True), lock(safe(root(project), 'repo-ops.lock'), wait=True):
        urls = _register(project, [repository])
        return str(_mirror(project, repository, urls[repository]))


def receipt(project, task, *, validate_git=True, check_branch=True):
    saved = read_json(receipt_path(project, task))
    if saved is None:
        return None
    if (saved.get('task') != task or saved.get('project') != project.profile['project']['id']
            or saved.get('configuration_root') != str(project.root) or not saved.get('complete')):
        if saved.get('configuration_root') and saved.get('configuration_root') != str(project.root) and saved.get('complete'):
            raise WorkflowError(f"Factory allocation for {task} belongs to the project at {saved['configuration_root']}, "
                                f"not {project.root}; run plovi with --project {saved['configuration_root']}")
        raise WorkflowError('Factory allocation is incomplete or belongs to another project; resume its original task')
    registered = read_json(safe(root(project), 'origin.json'), {})
    for row in saved['repositories']:
        name = identifier(row['repository'])
        expected = safe(root(project), 'worktrees', identifier(task), name)
        mirror = safe(root(project), 'mirrors', name + '.git')
        if (row.get('strategy') != 'factory' or row['path'] != str(expected) or row['mirror'] != str(mirror)
                or not expected.is_dir() or registered.get('repositories', {}).get(name) != row.get('identity')):
            raise WorkflowError('Factory checkout ownership changed; preserve the allocation for recovery')
        if validate_git:
            if common_dir(expected) != mirror.resolve():
                raise WorkflowError('Factory worktree has different Git ownership')
            registered_paths = [x[9:] for x in git(mirror, 'worktree', 'list', '--porcelain', '-z').split('\0') if x.startswith('worktree ')]
            if not any(same_path(expected, path) for path in registered_paths):
                raise WorkflowError('Factory worktree is no longer registered')
            if check_branch and git(expected, 'branch', '--show-current') != (row['branch'] or ''):
                raise WorkflowError('Factory task branch changed; restore the approved branch before resuming')
    return saved


def owns(project, repository, path):
    """Membership requires an exact complete receipt, never merely a mirror common dir."""
    path = Path(path).resolve()
    base = safe(root(project), 'worktrees')
    if not path.is_relative_to(base) or len(path.relative_to(base).parts) != 2:
        return False
    task, name = path.relative_to(base).parts
    if name != repository:
        return False
    saved = receipt(project, task)
    return bool(saved and any(r['repository'] == name and same_path(r['path'], path) for r in saved['repositories']))


def strategies(project, manifest, *, unattended=False, prior=None):
    if prior:
        # Legacy resume keeps its original semantics even on a non-TTY host.
        return prior.get('checkout_strategies', prior.get('execution', {}).get('checkout_strategies',
            {r['id']: project.repository(r['id'])['checkout_strategy'] for r in manifest['repositories']}))
    # Unattended runs use the task's own worktree unless policy opts into factory checkouts.
    from .policy import effective
    factory_checkouts = unattended and effective(project, manifest)['values']['isolation']['checkout'] == 'factory'
    return {r['id']: 'factory' if factory_checkouts else project.repository(r['id'])['checkout_strategy']
            for r in manifest['repositories']}


def allocate(project, task, *, unattended=False, manifest=None):
    task = identifier(task)
    rows = manifest['repositories'] if manifest else [
        {'id': r['id'], 'access': 'write', 'branch': project.profile['git']['branch_template'].format(task=task)}
        for r in project.profile['repositories'] if r['task_policy'] != 'never']
    if not unattended:
        from .git_ops import prepare
        if manifest is None:
            for row in rows:
                if project.repository(row['id'])['checkout_strategy'] == 'current-checkout':
                    row['branch'] = git(project.repo_path(row['id']), 'branch', '--show-current')
            if not any(project.repository(r['id'])['checkout_strategy'] == 'factory' for r in rows):
                from .tasks import start, receipt_path as local_receipt
                return start(project, task, repositories=[r['id'] for r in rows if r['access'] == 'write'],
                             resume=local_receipt(project, task).exists())['checkouts']
        return prepare(project, manifest or {'task': task, 'repositories': rows})
    with lock(project.config / 'local/repo-ops.lock', wait=True), lock(safe(root(project), 'repo-ops.lock'), wait=True):
        urls = _register(project, [r['id'] for r in rows])
        path = receipt_path(project, task)
        if path.exists():
            saved = receipt(project, task)
            if {(r['repository'], r['access'], r['branch']) for r in saved['repositories']} != {
                    (r['id'], r['access'], r.get('branch') if r['access'] == 'write' else None) for r in rows}:
                raise WorkflowError('Factory task repository/branch selection changed; use the original allocation')
            return {r['repository']: r['path'] for r in saved['repositories']}
        prepared = []
        for row in rows:
            name = identifier(row['id']); repo = project.repository(name)
            mirror = _mirror(project, name, urls[name])
            target = safe(root(project), 'worktrees', task, name)
            branch = row.get('branch') if row['access'] == 'write' else None
            if row['access'] == 'write' and not branch:
                raise WorkflowError('Unattended factory execution requires an approved feature branch in the manifest')
            if branch:
                git(mirror, 'check-ref-format', '--branch', branch)
                if branch == repo['base_branch'] or git(mirror, 'branch', '--list', branch):
                    raise WorkflowError('Factory task branch already exists; resume the original task')
            if target.exists():
                raise WorkflowError('Factory task path already exists; no existing files were adopted')
            base = repo['base_branch']
            if base.startswith('-'):
                raise WorkflowError('Invalid factory base branch')
            commit = git(mirror, 'rev-parse', '--verify', 'refs/remotes/origin/' + base + '^{commit}')
            prepared.append({'repository': name, 'access': row['access'], 'branch': branch, 'base': base,
                             'base_commit': commit, 'path': str(target), 'mirror': str(mirror),
                             'identity': urls[name], 'strategy': 'factory', 'ready': False,
                             **(_task_branch(project, task, name, branch, mirror, base, commit) if branch else {})})
        saved = {'schema_version': 1, 'project': project.profile['project']['id'], 'configuration_root': str(project.root),
                 'task': task, 'complete': False, 'repositories': prepared}
        write_json(path, saved)
        for row in prepared:
            target = Path(row['path']); target.parent.mkdir(parents=True, exist_ok=True)
            git(Path(row['mirror']), 'worktree', 'add', *(['-b', row['branch']] if row['branch'] else ['--detach']), str(target),
                row.get('task_head') or row['base_commit'])
            row['ready'] = True; write_json(path, saved)
        saved['complete'] = True; write_json(path, saved)
        return {r['repository']: r['path'] for r in prepared}


def _task_branch(project, task, name, branch, mirror, base, remote_base):
    """Start from the committed head of this task's own task-start branch, so planning commits are delivered."""
    from .tasks import receipt_path as local_receipt
    saved = read_json(local_receipt(project, task))
    if not saved or saved.get('task') != task or saved.get('configuration_root') != str(project.root) or not saved.get('complete'):
        return {}
    row = next((r for r in saved.get('repositories', []) if r.get('repository') == name and r.get('branch') == branch), None)
    if row is None:
        return {}
    source = project.repo_path(name)
    head = git(source, 'rev-parse', '--verify', 'refs/heads/' + branch + '^{commit}')
    plans = project.profile['planning']['directory'].rstrip('/') + '/' + task
    checkout = Path(row['path'])
    if checkout.is_dir() and git(checkout, 'status', '--porcelain', '--', plans):
        raise WorkflowError(f'The task plan in {checkout / plans} has uncommitted changes; commit the plan first '
                            'so the background run includes it')
    ref = f'refs/plovi/tasks/{task}/{name}'
    # Outside the mirror's fetch destinations, so remote refreshes never move it.
    git(mirror, 'fetch', '--no-tags', str(source), f'+refs/heads/{branch}:{ref}')
    if git(mirror, 'rev-parse', ref) != head:
        raise WorkflowError('The task branch moved while it was copied; retry the run')
    started = row.get('base_commit')
    on_remote = started and run(['git', '-C', mirror, 'merge-base', '--is-ancestor', started, remote_base], mirror, check=False).returncode == 0
    if not on_remote:
        raise WorkflowError(f'The task branch {branch} starts from {str(started)[:12]}, which is not on origin/{base}; '
                            f'push that base commit or start the task again from origin/{base}')
    return {'task_head': head, 'source': 'task-branch'}


def push(project, task, repository, branch):
    with lock(project.config / 'local/repo-ops.lock', wait=True), lock(safe(root(project), 'repo-ops.lock'), wait=True):
        saved = receipt(project, task, check_branch=False)
        if not saved:
            raise WorkflowError('Factory delivery requires a complete allocation receipt')
        row = next((r for r in saved['repositories'] if r['repository'] == repository and r['access'] == 'write'), None)
        if not row or git(Path(row['path']), 'branch', '--show-current') != branch or branch == project.repository(repository)['base_branch']:
            raise WorkflowError('Factory delivery branch is not the active task branch')
        urls = _register(project, [repository])
        git(Path(row['path']), '-c', 'remote.origin.mirror=false', 'push', urls[repository]['push'], 'HEAD:refs/heads/' + branch)


def worktrees(project):
    result = []
    locations = [(project.config / 'local/tasks', 'local'), (safe(root(project), 'allocations'), 'factory')]
    for folder, mode in locations:
        for path in sorted(folder.glob('*.json')):
            saved = read_json(path, {})
            if saved.get('configuration_root') != str(project.root):
                continue
            for row in saved.get('repositories', []):
                result.append(dict(row, task=saved.get('task'), mode=mode, owned=bool(saved.get('complete'))))
    return result


def clean(project, *, older_than=None):
    from contextlib import ExitStack
    from .tasks import owned_checkout
    seconds = None
    if older_than is not None:
        match = re.fullmatch(r'(\d+)([dhm])', older_than)
        if not match:
            raise WorkflowError('Choose an age such as 7d, 24h or 30m')
        seconds = int(match[1]) * {'d': 86400, 'h': 3600, 'm': 60}[match[2]]
    removed = []
    for task in sorted({r['task'] for r in worktrees(project)}):
        with ExitStack() as stack:
            try:
                stack.enter_context(lock(directory(project, task) / 'runner.lock'))
            except WorkflowError:
                continue
            saved = read_json(directory(project, task) / 'state.json', {})
            if saved.get('status') not in {'cancelled', 'merged', 'closed'}:
                continue
            if seconds is not None:
                terminal = saved.get('terminal_at')
                try:
                    if isinstance(terminal, str):
                        parsed = datetime.fromisoformat(terminal.replace('Z', '+00:00'))
                        if parsed.tzinfo is None:
                            continue
                        at = parsed.timestamp()
                    elif type(terminal) in (int, float):
                        at = float(terminal)
                    else:
                        continue
                except (TypeError, ValueError, AttributeError):
                    continue
                if time.time() - at < seconds:
                    continue
            stack.enter_context(lock(project.config / 'local/repo-ops.lock', wait=True))
            stack.enter_context(lock(safe(root(project), 'repo-ops.lock'), wait=True))
            if task in read_json(project.config / 'local/claims.json', {}):
                continue
            owned_rows = [r for r in worktrees(project) if r['task'] == task]
            if any(r['mode'] == 'factory' and Path(r['path']).exists() for r in owned_rows):
                receipt(project, task)
            for row in owned_rows:
                if not row['owned'] or row.get('strategy') not in {'worktree', 'factory'}:
                    continue
                target = Path(row['path'])
                if not target.exists():
                    continue
                if row['mode'] == 'factory':
                    mirror = Path(row['mirror'])
                else:
                    if owned_checkout(project, task, row['repository'], row['branch']) != str(target):
                        continue
                    mirror = project.repo_path(row['repository'])
                if git(target, 'status', '--porcelain'):
                    continue
                # Keep commits not reachable from the recorded remote base or any remote head.
                if git(target, 'rev-list', 'HEAD', '--not', row['base_commit'], '--remotes'):
                    delivered = saved.get('delivery', {}).get(row['repository'], {})
                    if not delivered.get('pushed') or delivered.get('commit') != git(target, 'rev-parse', 'HEAD'):
                        continue
                info = git(mirror, 'worktree', 'list', '--porcelain')
                # Git prints C:/ paths on Windows; compare paths, not text.
                block = next((b for b in info.split('\n\n')
                              if b.startswith('worktree ') and same_path(target, b.split('\n', 1)[0][9:])), '')
                if not block or '\nlocked' in block:
                    continue
                git(mirror, 'worktree', 'remove', str(target)); git(mirror, 'worktree', 'prune')
                removed.append(str(target))
    return removed
