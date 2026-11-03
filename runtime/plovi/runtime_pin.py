"""Content-addressed private runtime snapshots, independent of mutable task source."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from .install import files_in, payload_digest
from .util import WorkflowError, read_json, write_json, user_data
from .state import lock, directory


def verify(receipt):
    if not isinstance(receipt, dict) or not isinstance(receipt.get('path'), str):
        raise WorkflowError('Pinned runtime receipt is invalid')
    path = Path(receipt['path'])
    if not path.is_absolute(): raise WorkflowError('Pinned runtime path must be absolute')
    if not path.is_dir() or not (path/'bin/plovi').is_file() or payload_digest(path) != receipt.get('digest'):
        raise WorkflowError('Pinned runtime is missing or changed; restore it or explicitly upgrade with reviewed rebind')
    return path


def freeze(source, store=None):
    source = Path(source).resolve()
    store = Path(store) if store else user_data()/'runtimes'
    if store.resolve().is_relative_to(source): raise WorkflowError('Pinned runtime storage must be outside mutable source')
    store.mkdir(parents=True, exist_ok=True)
    fingerprint = payload_digest(source)
    target = store/fingerprint
    with lock(store/(fingerprint+'.lock'), wait=True):
        if not target.exists():
            temp = Path(tempfile.mkdtemp(prefix='.runtime-', dir=store))
            try:
                for path in files_in(source):
                    dest = temp/path.relative_to(source); dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dest)
                if payload_digest(temp) != fingerprint:
                    raise WorkflowError('Runtime source changed while snapshotting; retry after changes settle')
                os.replace(temp,target)
            finally:
                if temp.exists(): shutil.rmtree(temp)
    receipt={'schema_version':1,'path':str(target),'digest':fingerprint}
    verify(receipt)
    return receipt


def dispatch(project, task, argv, *, source, create=False, upgrade=False):
    path = directory(project,task)/'runtime.json'
    with lock(path.with_suffix('.lock'),wait=True):
        saved = read_json(path)
        if upgrade or (saved is None and create):
            with ExitStack() as ownership:
                try:
                    ownership.enter_context(lock(path.parent/'launch.lock'))
                    ownership.enter_context(lock(path.parent/'runner.lock'))
                except WorkflowError:
                    raise WorkflowError('Cannot pin or upgrade runtime while a worker owns the task; stop it before a reviewed upgrade') from None
                fresh = freeze(source)
                if saved and fresh != saved:
                    write_json(path.parent/'runtime-history'/((saved.get('digest') or 'legacy')+'.json'),saved)
                write_json(path,fresh); saved=fresh
    if saved is None: return None
    target=verify(saved)
    if target == Path(source).resolve(): return None
    # The launcher already recorded operation events; the pinned process continues the work.
    return subprocess.run([sys.executable,str(target/'bin/plovi'),*argv],env=dict(os.environ,PLOVI_FORWARDED='1')).returncode
