"""Idempotent start/resume using the saved runtime and owned task checkout."""
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid
from . import manifest as contracts, runner, policy, state
from .migration import lock_held
from .process import detached
from .runtime_pin import freeze, verify
from .tracking import describe
from .util import WorkflowError, package_root, read_json, write_json


def launch(project, target, *, rebind=False, trusted=False, no_wait=False):
    supplied=contracts.load(Path(target),project) if Path(target).is_file() else None
    task=supplied['task'] if supplied else str(target)
    root=state.directory(project,task);root.mkdir(parents=True,exist_ok=True)
    runtime=read_json(root/'runtime.json') or freeze(package_root())
    verify(runtime)
    with state.lock(root/'launch.lock',wait=True):
        saved=read_json(root/'state.json',{})
        launch_info=read_json(root/'launch.json',{})
        if lock_held(root/'runner.lock'):
            return {'task':task,'status':'running','reused':True,'tracking':describe(project,task,runtime,(launch_info.get('run_id') if not launch_info.get('claimed_at') else None) or saved.get('run_id'))}
        if saved.get('status') in {'complete','cancelled'} or saved.get('pending_input') or saved.get('pending_approvals') or saved.get('escalation'):
            from .progress import summary
            return dict(summary(saved),reused=True,tracking=describe(project,task,runtime,saved.get('run_id')))
        if not supplied and not saved:raise WorkflowError('No saved task; supply its approved manifest to start')
        plan=supplied or contracts.load(Path(saved['manifest_path']),project)
        if saved and supplied and str(Path(saved['manifest_path']).resolve())!=str(Path(supplied['_path']).resolve()) and not rebind:
            raise WorkflowError('Task already uses another manifest; review it before rebinding')
        execution=saved.get('execution') or policy.execution(project,plan,trusted=trusted,unattended=True)
        from . import factory, git_ops
        strategies = factory.strategies(project, plan, unattended=True, prior=saved)
        if not saved and 'factory' in strategies.values():
            git_ops.prepare(project, plan, strategies=strategies)
        if not saved:
            execution['checkout_strategies'] = strategies
        runner.preflight(project,plan,execution=execution)
        run_id=uuid.uuid4().hex
        launch_info={'run_id':run_id,'task':task,'at':time.time()};write_json(root/'launch.json',launch_info)
        argv=[sys.executable,str(Path(runtime['path'])/'bin/plovi'),'--project',str(project.root)]
        if saved:argv+=['resume',task,*(['--rebind'] if rebind else [])]
        else:argv+=['run',str(Path(plan['_path']).resolve()),'--unattended',*(['--trusted'] if trusted else []),*(['--no-wait'] if no_wait else [])]
        with (root/'runner.log').open('a',encoding='utf-8') as output:
            child=subprocess.Popen(argv,cwd=project.root,stdin=subprocess.DEVNULL,stdout=output,stderr=output,**detached())
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            current=read_json(root/'state.json',{})
            if current.get('run_id')==run_id or child.poll() is not None:break
            time.sleep(.05)
        code=child.poll()
        threading.Thread(target=child.wait,daemon=True).start()
        if code is not None and current.get('run_id')!=run_id:
            return {'task':task,'status':'failed','error':'Worker failed before initialization; inspect runner.log','log':str(root/'runner.log')}
        return {'task':task,'status':current.get('status','starting') if current.get('run_id')==run_id else 'starting',
                'pid':child.pid,'log':str(root/'runner.log'),'tracking':describe(project,task,runtime,run_id)}
