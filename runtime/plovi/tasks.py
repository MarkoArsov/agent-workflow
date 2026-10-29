"""Allocate task-owned worktrees before specification, without switching shared files."""
from __future__ import annotations
from pathlib import Path
from .state import lock
from .util import WorkflowError, contained, common_dir, git, identifier, read_json, write_json


def receipt_path(project, task):
    return project.config / 'local/tasks' / (identifier(task) + '.json')


def _branch_exists(root, branch):
    return bool(git(root, 'branch', '--list', branch))


def _validate_checkout(project, row):
    root = project.repo_path(row['repository'])
    target = Path(row['path'])
    if not target.is_dir() or common_dir(target) != common_dir(root):
        raise WorkflowError('Task worktree is missing or belongs to another repository')
    if git(target, 'branch', '--show-current') != row['branch']:
        raise WorkflowError('Task worktree branch changed; preserve it and resolve ownership')
    registrations = git(root, 'worktree', 'list', '--porcelain', '-z').split('\0')
    registered_paths = {Path(field[len('worktree '):]).resolve()
                        for field in registrations if field.startswith('worktree ')}
    if target.resolve() not in registered_paths:
        raise WorkflowError('Task worktree is not registered at its owned path')
    return str(target)


def owned_checkout(project, task, repository, branch):
    """Return only a validated, complete allocation, or None for legacy manifests."""
    saved = read_json(receipt_path(project, task))
    if saved is None:
        return None
    if saved.get('task') != task or saved.get('configuration_root') != str(project.root) or not saved.get('complete'):
        raise WorkflowError('Task allocation is incomplete; resume task start before execution')
    row = next((r for r in saved['repositories'] if r['repository'] == repository), None)
    if row is None or branch != row['branch']:
        raise WorkflowError('Task manifest branch/repository differs from its owned allocation')
    expected = contained(project.root, project.profile['git']['worktree_directory']) / task / repository
    if row['path'] != str(expected):
        raise WorkflowError('Task worktree directory changed; inspect its ownership before execution')
    return _validate_checkout(project, row)


def start(project, task, *, repositories=None, base=None, resume=False):
    task = identifier(task)
    candidates = [r['id'] for r in project.profile['repositories'] if r['task_policy'] != 'never']
    if repositories is None:
        if len(candidates) != 1:
            raise WorkflowError('Select writable repositories with --repository; read-only companions need no branch')
        repositories = candidates
    if not repositories or len(set(repositories)) != len(repositories):
        raise WorkflowError('Select unique writable repositories')
    if any(name not in candidates for name in repositories):
        raise WorkflowError('A selected repository is unknown or forbids task changes')
    if base is not None and (not base or base.startswith('-')):
        raise WorkflowError('Select an explicit valid base ref')
    directory = contained(project.root, project.profile['git']['worktree_directory'])
    path = receipt_path(project, task)
    with lock(project.config / 'local/task-start.lock'):
        saved = read_json(path)
        if saved is not None:
            if not resume:
                raise WorkflowError('Task already exists; use --resume only for this same task')
            if (saved.get('task') != task or saved.get('configuration_root') != str(project.root)
                    or {r['repository'] for r in saved.get('repositories', [])} != set(repositories)):
                raise WorkflowError('Task ownership or repository selection differs from the saved allocation')
            if base is not None and any(r['base'] != base for r in saved['repositories']):
                raise WorkflowError('Task base changed; do not silently revise an existing allocation')
        else:
            if resume:
                raise WorkflowError('No task allocation exists to resume')
            rows, commons = [], set()
            for name in repositories:
                repo = project.repository(name)
                root = project.repo_path(name)
                common = common_dir(root)
                if common is None or common in commons:
                    raise WorkflowError('Writable task repositories must be distinct Git repositories')
                commons.add(common)
                branch = project.profile['git']['branch_template'].format(task=task)
                git(root, 'check-ref-format', '--branch', branch)
                if branch == repo['base_branch'] or _branch_exists(root, branch):
                    raise WorkflowError('Task branch already exists; choose a new task or resume its owned allocation')
                target = directory / task / name
                if target.exists() or target.is_symlink():
                    raise WorkflowError('Task worktree path already exists; no existing files were adopted')
                selected_base = base or repo['base_branch']
                if selected_base.startswith('-'):
                    raise WorkflowError('Invalid base ref')
                commit = git(root, 'rev-parse', '--verify', selected_base + '^{commit}')
                rows.append({'repository': name, 'branch': branch, 'base': selected_base,
                             'base_commit': commit, 'path': str(target), 'ready': False})
            saved = {'schema_version': 1, 'task': task, 'configuration_root': str(project.root),
                     'complete': False, 'repositories': rows}
            write_json(path, saved)
        for row in saved['repositories']:
            root = project.repo_path(row['repository'])
            target = directory / task / row['repository']
            if row['path'] != str(target):
                raise WorkflowError('Task path changed; preserve the existing allocation')
            if row['ready']:
                _validate_checkout(project, row)
                continue
            # Recover an interrupted worktree add only at this recorded path/base.
            if target.exists():
                _validate_checkout(project, row)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                if _branch_exists(root, row['branch']):
                    if git(root, 'rev-parse', row['branch']) != row['base_commit']:
                        raise WorkflowError('Partially allocated task branch moved; inspect ownership')
                    git(root, 'worktree', 'add', str(target), row['branch'])
                else:
                    git(root, 'worktree', 'add', '-b', row['branch'], str(target), row['base_commit'])
                _validate_checkout(project, row)
            row['ready'] = True
            write_json(path, saved)
        saved['complete'] = True
        write_json(path, saved)
    return {'task': task, 'configuration_root': str(project.root),
            'checkouts': {r['repository']: r['path'] for r in saved['repositories']},
            'branches': {r['repository']: r['branch'] for r in saved['repositories']},
            'plans': {r['repository']: str(Path(r['path']) / project.profile['planning']['directory'] / task)
                      for r in saved['repositories']},
            'detail': 'New tasks always use owned worktrees, including manual tasks and legacy current-checkout profiles. No plans or product files were written.'}
