"""Host-neutral tracking descriptors and explicit terminal capability negotiation."""
from pathlib import Path
import shlex
from .util import WorkflowError, read_json, write_json
from .state import lock

CAPABILITIES = {'open_and_run', 'open_only', 'current_terminal', 'command_only', 'unavailable'}
MODES = {'auto', 'current-terminal', 'app-terminal', 'command-only', 'off'}


def describe(project, task, runtime, run_id=None):
    import sys
    from .policy import effective
    mode = effective(project)['values']['execution']['tracking_mode']
    return {'schema_version': 1, 'task': task, 'run_id': run_id, 'mode': mode,
            'argv': [sys.executable, str(Path(runtime['path']) / 'bin/plovi'), '--project', str(project.root), 'watch', task],
            'cwd': str(project.root), 'runtime_digest': runtime['digest']}


def host_capability(host, offered=(), *, tty=False):
    # Offered capabilities come from the foreground host adapter, never a model ID.
    if host not in {'codex', 'claude-cli', 'claude-vscode', 'cursor', 'headless'}:
        return 'command_only'
    for capability in ('open_and_run', 'open_only'):
        if capability in offered: return capability
    return 'current_terminal' if tty else 'command_only'


def attach(descriptor, capability, opener, receipt, *, probe=None):
    if capability not in CAPABILITIES:
        raise WorkflowError('Unsupported tracker capability')
    if descriptor.get('mode') == 'off': return {'status':'disabled','running':False}
    if descriptor.get('mode') == 'command-only': capability='command_only'
    if descriptor.get('mode') == 'current-terminal': capability='current_terminal'
    if descriptor.get('mode') == 'app-terminal' and capability == 'current_terminal': capability='command_only'
    receipt = Path(receipt)
    with lock(receipt.with_suffix('.lock'), wait=True):
        previous = read_json(receipt, {})
        identity = {k: descriptor.get(k) for k in ('task', 'run_id', 'argv', 'cwd', 'mode')}
        identity['capability'] = capability
        if previous.get('identity') == identity and previous.get('status') in {'attached', 'opened'}:
            # A saved handle proves an earlier attachment, not that it is still alive.
            try:
                observed = probe(previous['session_id']) if probe else None
            except Exception:
                observed = None
            if observed is True:
                return {k: v for k, v in previous.items() if k != 'identity'}
            if observed is not False:
                return {'status':'unverified', 'running':False, 'session_id':previous['session_id'],
                        'argv':descriptor['argv'], 'cwd':descriptor['cwd'],
                        'warning':'Existing tracker cannot be verified; inspect or close it before opening another'}
        result = {'status': 'command_only', 'running': False, 'argv': descriptor['argv'], 'cwd': descriptor['cwd']}
        if capability == 'current_terminal': result['status'] = 'current_terminal'
        if capability in {'open_and_run', 'open_only'} and opener:
            try:
                answer = opener(dict(descriptor))
                if isinstance(answer, dict) and isinstance(answer.get('session_id'), str) and answer['session_id']:
                    result.update(status='opened', session_id=answer['session_id'])
                    if capability == 'open_and_run' and answer.get('running') is True:
                        result.update(status='attached', running=True)
            except Exception:
                result['warning'] = 'Tracker could not attach; the worker is unaffected'
        write_json(receipt, dict(result, identity=identity))
        return result


def command_text(descriptor):
    import os, subprocess
    return subprocess.list2cmdline(descriptor['argv']) if os.name == 'nt' else shlex.join(descriptor['argv'])


def host_attach(descriptor, host, receipt, *, offered=(), opener=None, probe=None, tty=False):
    """Foreground host bridge. Callbacks must be real host tools, not shell guesses."""
    capability = host_capability(host, offered, tty=tty)
    return attach(descriptor, capability, opener, receipt, probe=probe)
