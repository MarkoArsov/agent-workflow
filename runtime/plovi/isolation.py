"""Experimental Docker/Podman boundary for explicit stage/check execution only."""
from __future__ import annotations
from contextvars import ContextVar
from pathlib import Path
import json
import os
import platform
import re
import shutil
import subprocess
import uuid
from . import factory, policy
from .util import WorkflowError, package_root, read_json, run, write_json

active = ContextVar('plovi_execution_context', default=None)


class CleanupFailure(WorkflowError):
    """Owned engine resources could not be confirmed removed."""


class Unavailable(WorkflowError):
    """Only runtime/image availability permits a restricted host fallback."""


def configuration(value):
    value = value.get('values', value)
    policy.validate({'isolation': value.get('isolation', {})})
    return dict(policy.isolation_defaults(), **value.get('isolation', {}))


def runtime_environment(config, inherited=None):
    source = os.environ if inherited is None else inherited
    # These are for the engine client, not variables forwarded to the container.
    names = {'PATH', 'HOME', 'LANG', 'TMPDIR', 'XDG_RUNTIME_DIR', 'DOCKER_HOST', 'DOCKER_CONTEXT',
             'DOCKER_CONFIG', 'DOCKER_CERT_PATH', 'DOCKER_TLS_VERIFY', 'CONTAINER_HOST',
             'SYSTEMROOT', 'WINDIR'}
    names.update(config.get('api_key_env', []))
    names.update(config.get('service_names', []))
    # The isolated fake-engine protocol has no effect on the inner allowlist.
    names.update({'PLOVI_TEST_CONTAINER_RECORD', 'PLOVI_TEST_CONTAINER_EXIT', 'PLOVI_TEST_CONTAINER_INSPECT_INVALID'})
    return {k: v for k, v in source.items() if k in names}


def build_container_argv(*, runtime, image, workdir, env_names=(), mounts=(), network='on', stdin=True,
                         name=None, network_name=None):
    argv = [runtime, 'run', '--rm', '--pull=never']
    if stdin:
        argv += ['-i']
    if name:
        argv += ['--name', name, '--label', 'plovi.owned=' + name]
    argv += ['--workdir', str(workdir)]
    if network == 'off':
        argv += ['--network=none']
    elif network_name:
        argv += ['--network', network_name]
    if platform.system() == 'Linux':
        argv += ['--user', f'{os.getuid()}:{os.getgid()}']
        if Path(runtime).name == 'podman':
            argv += ['--userns=keep-id']
    argv += ['--tmpfs', '/tmp/plovi-home:rw,mode=1777', '--env', 'HOME=/tmp/plovi-home']
    # PATH comes from the image, never the host process environment.
    for key in env_names:
        argv += ['--env', key]
    for mount in mounts:
        if isinstance(mount, dict):
            src, dst = mount['source'], mount['target']
            if ',' in src or ',' in dst:
                raise WorkflowError('Container bind paths cannot contain commas; choose another factory data directory')
            argv += ['--mount', f'type=bind,source={src},target={dst}' + (',readonly' if mount['readonly'] else '')]
        else:
            argv += ['--volume', mount]
    argv += ['--env', 'GIT_OPTIONAL_LOCKS=0', '--env', 'GIT_CONFIG_NOSYSTEM=1', '--env', 'GIT_CONFIG_GLOBAL=/dev/null']
    directories = [m['target'] for m in mounts if isinstance(m, dict) and m.get('git_safe')]
    argv += ['--env', 'GIT_CONFIG_COUNT=' + str(len(directories))]
    for i, path in enumerate(directories):
        argv += ['--env', f'GIT_CONFIG_KEY_{i}=safe.directory', '--env', f'GIT_CONFIG_VALUE_{i}=' + path]
    argv += [image]
    return argv


def _ownership(project, task, checkouts=None):
    if task is None:
        raise WorkflowError('Container mode requires a factory-owned task; allocate a fresh task first')
    saved = factory.receipt(project, task, validate_git=False)
    if not saved:
        raise WorkflowError('Container mode requires factory-owned checkout metadata; start a fresh factory task')
    expected = {r['repository']: r['path'] for r in saved['repositories']}
    if checkouts is not None and checkouts != expected:
        raise WorkflowError('Container checkout map differs from its factory receipt; preserve the original task')
    return saved


def _runtime(config):
    candidates = ['docker', 'podman'] if config['runtime'] == 'auto' else [config['runtime']]
    for name in candidates:
        binary = shutil.which(name)
        if not binary:
            continue
        try:
            result = run([binary, 'info'], Path.cwd(), timeout=5, env=runtime_environment({}), check=False)
        except WorkflowError:
            continue
        if result.returncode == 0:
            return name, binary
    raise Unavailable('Container runtime is unavailable; start Docker/Podman or choose isolation.mode=none in a reviewed policy')


def pull_image(project, value, *, runtime=None):
    config = configuration(value)
    name = runtime or config['runtime']
    if name == 'auto':
        name, binary = _runtime(config)
    else:
        binary = shutil.which(name)
    if not binary:
        raise Unavailable('Container runtime is unavailable; install/start the selected runtime before pulling')
    if not config['image']:
        raise WorkflowError('Choose isolation.image before pulling')
    result = run([binary, 'pull', config['image']], project.root, env=runtime_environment({}), timeout=300, check=False)
    if result.returncode:
        raise Unavailable('Container image pull failed; check the image and runtime credentials')


def preflight(project, value, *, trusted=True, unattended=False, task=None, platform_override=None,
              checkouts=None, frozen=None, pull=False):
    config = configuration(value)
    if config['mode'] == 'none':
        return dict(config, degraded=False)
    saved = _ownership(project, task, checkouts)
    if frozen and frozen.get('degraded'):
        return dict(frozen)
    try:
        if (platform_override or platform.system()) == 'Windows':
            raise Unavailable('Container mode is unsupported on Windows; restricted execution can use an explicit degraded host boundary')
        runtime, binary = _runtime(dict(config, runtime=frozen['runtime']) if frozen and frozen.get('mode') == 'container' else config)
        image = frozen.get('image_id', config['image']) if frozen else config['image']
        result = run([binary, 'inspect', '--type', 'image', image], project.root, timeout=10,
                     env=runtime_environment({}), check=False)
        if result.returncode:
            if pull:
                pull_image(project, value, runtime=runtime)
                result = run([binary, 'inspect', '--type', 'image', image], project.root, timeout=10,
                             env=runtime_environment({}), check=False)
            if result.returncode:
                raise Unavailable('Container image is missing locally; build it or explicitly pass --pull-isolation-image once')
        try:
            metadata = json.loads(result.stdout)
            image_id = metadata[0]['Id']
            if len(metadata) != 1 or not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
                raise ValueError()
        except (ValueError, TypeError, KeyError, IndexError):
            raise WorkflowError('Container image metadata has no valid immutable ID; repair the runtime image before retrying') from None
        if frozen and frozen.get('image_id') and image_id != frozen['image_id']:
            raise WorkflowError('Pinned container image changed; restore the recorded image before resuming')
        return dict(config, runtime=runtime, binary=binary, image_id=image_id, degraded=False)
    except Unavailable as exc:
        if trusted:
            raise
        return dict(config, requested_mode='container', mode='none', degraded=True, diagnostic=str(exc),
                    boundary='Degraded: configured container unavailable; restricted provider execution on host')


def _config_mounts(project, config):
    from .identity import policy as identity_policy
    selectors = identity_policy(project)
    guard = read_json(project.config / 'local/claude-account.json', {})
    defaults = {'codex': Path.home() / '.codex', 'claude': Path.home() / '.claude', 'cursor': Path.home() / '.cursor'}
    variables = {'codex': 'CODEX_HOME', 'claude': 'CLAUDE_CONFIG_DIR'}
    mounts = []
    for provider in config['mount_harness_config']:
        variable = variables.get(provider)
        selected = selectors.get(provider, {}).get('config_env', {}).get(variable) if variable else None
        if provider == 'claude' and guard:
            selected = guard['config_dir']
        source = Path(selected or (os.environ.get(variable) if variable else None) or defaults[provider]).expanduser().resolve()
        forbidden = [project.root, package_root(), project.config / 'local', factory.root(project),
                     *(project.repo_path(r['id']) for r in project.profile['repositories'])]
        if (Path.home().resolve().is_relative_to(source)
                or any(source.is_relative_to(Path(p).resolve()) or Path(p).resolve().is_relative_to(source)
                       for p in forbidden)):
            raise WorkflowError('Harness config mount exposes project or home data; select a dedicated provider config directory')
        if not source.is_dir():
            raise WorkflowError('Selected harness config is missing; configure its directory or remove the mount opt-in')
        mounts.append({'source': str(source), 'target': '/tmp/plovi-home/.' + provider, 'readonly': True})
    if guard or (project.config / 'local/claude-account.required').exists() or selectors.get('claude', {}).get('verification') == 'required':
        if not guard or 'claude' not in config['mount_harness_config']:
            raise WorkflowError('Container execution requires the selected Claude account config mount to verify its private account guard')
    for provider, row in selectors.items():
        if provider != 'claude' and row.get('verification') == 'required':
            raise WorkflowError('Selected provider cannot verify the required account identity')
    return mounts


def build_execution_context(project, value, *, task, checkouts=None, trusted=True, unattended=False,
                            frozen=None, pull=False):
    resolved = preflight(project, value, task=task, checkouts=checkouts, trusted=trusted,
                         unattended=unattended, frozen=frozen, pull=pull)
    if resolved['mode'] == 'none':
        roots = checkouts or {r['id']: str(project.repo_path(r['id'])) for r in project.profile['repositories']}
        return dict(resolved, checkouts=roots, workdir=next(iter(roots.values())), host_execution=True)
    saved = _ownership(project, task, checkouts)
    mounts = []
    for row in saved['repositories']:
        mounts.append({'source': row['path'], 'target': row['path'], 'readonly': row['access'] == 'read', 'git_safe': True})
        if not any(m['source'] == row['mirror'] for m in mounts):
            mounts.append({'source': row['mirror'], 'target': row['mirror'], 'readonly': True, 'git_safe': True})
    mounts += _config_mounts(project, resolved)
    name = 'plovi-' + uuid.uuid4().hex
    from .state import directory
    ctx = dict(resolved, task=task, checkouts={r['repository']: r['path'] for r in saved['repositories']},
               workdir=next((r['path'] for r in saved['repositories'] if r['access'] == 'write'), saved['repositories'][0]['path']),
               mounts=mounts, container_name=name, containers=[], network_name=None,
               resources_path=str(directory(project, task) / 'containers' / (name + '.json')), host_execution=False)
    return ctx


def verify_account(project, ctx):
    # A required account is verified inside exactly the same mounted config boundary.
    guard = read_json(project.config / 'local/claude-account.json')
    if guard:
        overrides = {'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'CLAUDE_CODE_OAUTH_TOKEN',
                     'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY'}
        if any(os.environ.get(k) for k in overrides & set(ctx['api_key_env'])):
            raise WorkflowError('Container account verification cannot use credential or backend overrides; remove them and retry')
        result = run_contained(ctx, ['claude', 'auth', 'status'])
        try:
            status = json.loads(result.stdout)
        except ValueError:
            status = {}
        if (result.returncode or status.get('loggedIn') is not True or status.get('authMethod') != 'claude.ai'
                or status.get('apiProvider') != 'firstParty' or str(status.get('email', '')).casefold() != guard['email'].strip().casefold()):
            raise WorkflowError('Container Claude login does not match the selected private account; repair that config and retry')


def build_service_context(project, task, value):
    config = configuration(value)
    _ownership(project, task)
    if config['mode'] == 'container' and config['network'] == 'off':
        raise WorkflowError('Container services require network=on; network=off forbids cross-container services')
    return {'host_execution': config['mode'] == 'none', 'network_name': 'plovi-' + uuid.uuid4().hex}


def _resources(ctx):
    write_json(Path(ctx['resources_path']), {'task': ctx['task'], 'runtime': ctx['runtime'],
        'containers': list(ctx['containers']), 'network': ctx.get('network_name')})


def ensure_network(ctx):
    if ctx.get('mode') != 'container':
        return
    if ctx['network'] == 'off':
        raise WorkflowError('Container services require network=on; cross-container services cannot run with network=off')
    if not ctx.get('network_name'):
        ctx['network_name'] = 'plovi-' + uuid.uuid4().hex
        _resources(ctx)  # Crash recovery owns the name before creation.
        run([ctx['binary'], 'network', 'create', '--label', 'plovi.owned=' + ctx['network_name'], ctx['network_name']],
            Path(ctx['workdir']), env=runtime_environment({}), timeout=10)


def wrap(ctx, argv, cwd, env=None, *, network_alias=None):
    if ctx.get('mode') != 'container':
        return argv, env, None
    cwd = Path(cwd).resolve()
    if not any(cwd.is_relative_to(Path(p)) for p in ctx['checkouts'].values()):
        raise WorkflowError('Contained command cwd must stay inside a selected factory checkout')
    name = ctx['container_name'] if not ctx.get('_used_name') else 'plovi-' + uuid.uuid4().hex
    ctx['_used_name'] = True
    ctx['containers'].append(name); _resources(ctx)
    source = dict(os.environ if env is None else env)
    # Controlled host additions may export service endpoints, never broaden the host allowlist.
    names = ['LANG', *ctx['api_key_env'], *ctx.get('service_names', [])]
    names = [key for key in names if key in source]
    result = build_container_argv(runtime=ctx['binary'], image=ctx['image_id'], workdir=cwd,
                                  env_names=names, mounts=ctx['mounts'], network=ctx['network'],
                                  name=name, network_name=ctx.get('network_name'))
    if network_alias:
        result[-1:-1] = ['--network-alias', network_alias]
    for provider, variable in (('codex', 'CODEX_HOME'), ('claude', 'CLAUDE_CONFIG_DIR')):
        result[-1:-1] = ['--env', variable + '=/tmp/plovi-home/.' + provider]
    return result + list(argv), runtime_environment(ctx, source), name


def remove_container(ctx, name):
    if name not in ctx.get('containers', []):
        raise WorkflowError('Refusing to remove a container without an owned invocation receipt')
    # rm -f stops the engine resource even if its client has already died. A missing
    # --rm container is harmless; other engine failures remain visible.
    result = run([ctx['binary'], 'rm', '-f', name], Path(ctx['workdir']), timeout=10,
                 env=runtime_environment({}), check=False)
    if result.returncode and not re.search(r'no such|not found|does not exist', result.stderr, re.I):
        raise CleanupFailure('Owned container cleanup failed; start the runtime and retry recovery')
    ctx['containers'].remove(name); _resources(ctx)


def cancel_containers(ctx):
    if not ctx or ctx.get('mode') != 'container':
        return
    for name in list(ctx.get('containers', [])):
        remove_container(ctx, name)
    if ctx.get('network_name'):
        result = run([ctx['binary'], 'network', 'rm', ctx['network_name']], Path(ctx['workdir']),
                     timeout=10, env=runtime_environment({}), check=False)
        if result.returncode and not re.search(r'no such|not found|does not exist', result.stderr, re.I):
            raise CleanupFailure('Owned container network cleanup failed; retry recovery')
        ctx['network_name'] = None; _resources(ctx)


def recover(project, task, ctx):
    """Called only by the runner while holding this task's runner lock."""
    from .state import directory
    paths = list((directory(project, task) / 'containers').glob('*.json'))
    legacy = directory(project, task) / 'containers.json'
    if legacy.exists():
        paths.append(legacy)
    for path in paths:
        saved = read_json(path, {})
        if not saved.get('containers') and not saved.get('network'):
            continue
        if saved.get('task') != task or saved.get('runtime') != ctx.get('runtime'):
            raise WorkflowError('Container recovery ownership differs from the saved task')
        names = saved.get('containers', []) + ([saved['network']] if saved.get('network') else [])
        if any(not isinstance(n, str) or not re.fullmatch(r'plovi-[0-9a-f]{32}', n) for n in names):
            raise WorkflowError('Invalid container recovery receipt; inspect ownership before cleanup')
        owned = dict(ctx, containers=saved.get('containers', []), network_name=saved.get('network'), resources_path=str(path))
        cancel_containers(owned)


def redact_output(ctx, text, env=None):
    for name in (ctx or {}).get('api_key_env', []):
        value = (os.environ if env is None else env).get(name)
        if value:
            text = text.replace(value, '[redacted]')
    return text


def execute(argv, cwd, *, context=None, env=None, **options):
    from .process import execute as host_execute
    ctx = context if context is not None else active.get()
    if not ctx or ctx.get('mode') != 'container':
        return host_execute(argv, cwd, env=env, **options)
    wrapped, sanitized, name = wrap(ctx, argv, cwd, env)
    if options.get('on_line'):
        original = options['on_line']
        options['on_line'] = lambda line: original(redact_output(ctx, line, env))
    result = None
    try:
        result = host_execute(wrapped, cwd, env=sanitized, **options)
        # Explicit key values are not retained even if a tool echoes them.
        result['output'] = redact_output(ctx, result['output'], env)
        return result
    finally:
        if result is None or result.get('reason'):
            remove_container(ctx, name)
        else:
            # A completed --rm invocation is removed by the engine itself.
            ctx['containers'].remove(name); _resources(ctx)


def run_contained(ctx, argv, *, cwd=None, **options):
    result = execute(argv, Path(cwd or ctx['workdir']), context=ctx, **options)
    return subprocess.CompletedProcess(argv, result['exit_code'], stdout=result['output'], stderr='')


def environment(project, cwd, *, inherited=None):
    """Host identity guard stays in force; container auth was verified at preflight."""
    if (active.get() or {}).get('mode') == 'container':
        from .identity import assert_unchanged
        assert_unchanged(project)
        return inherited
    from .identity import environment as host_environment
    return host_environment(project, cwd, inherited=inherited)
