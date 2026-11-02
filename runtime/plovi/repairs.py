"""Bounded independent fixture correction; never unfreeze implementation's tests."""
import ast
import difflib
from pathlib import Path
import re
import time
from . import git_ops, providers, verification
from .identity import environment as identity_environment
from .manifest import matches, route_for
from .process import execute
from .util import WorkflowError, contained, json_text, read_json, write_json


def contract(text, suffix):
    """A conservative syntactic guard, supplemented by independent semantic review."""
    if suffix != '.py':
        return [line.strip() for line in text.splitlines() if re.search(r'assert|expect|\btest\b|skip|pending|todo',line,re.I)]
    tree=ast.parse(text); identities=[]; assertions=[]; skips=[]
    def visit(node, scope=(), controls=()):
        if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
            scope=(*scope,node.name)
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test'):
                identities.append((scope,ast.dump(node.args),[ast.dump(x) for x in node.decorator_list]))
        if isinstance(node,ast.If): controls=(*controls,('if',ast.dump(node.test)))
        if isinstance(node,ast.While): controls=(*controls,('while',ast.dump(node.test)))
        if isinstance(node,(ast.For,ast.AsyncFor)):controls=(*controls,('for',ast.dump(node.iter)))
        if isinstance(node,ast.Try):controls=(*controls,('try',tuple(ast.dump(x.type) if x.type else 'all' for x in node.handlers)))
        if isinstance(node,ast.Assert): assertions.append((scope,controls,ast.dump(node)))
        if isinstance(node,ast.Call):
            name=node.func.attr if isinstance(node.func,ast.Attribute) else node.func.id if isinstance(node.func,ast.Name) else ''
            if name.startswith('assert') or name in {'raises','fail'}: assertions.append((scope,controls,ast.dump(node)))
            if name in {'skip','skipTest','xfail'}:skips.append(ast.dump(node))
        for child in ast.iter_child_nodes(node): visit(child,scope,controls)
    visit(tree)
    return identities,assertions,skips


def budget(manifest, state):
    limit=manifest.get('corrections',{}).get('max_known_cost_usd')
    if limit is not None and sum(a.get('cost_usd') or 0 for a in state.get('attempts',[]))>=limit:
        raise WorkflowError('Known provider usage budget exhausted; inspect usage before another request')


def invoke(project, manifest, state, root, save, cancel, stage, prompt, route):
    from .progress import active
    budget(manifest,state)
    primary=next(r['id'] for r in manifest['repositories'] if r['access']=='write')
    cwd=Path(state['checkouts'][primary]); env=identity_environment(project,cwd)
    events=providers.Events(); reporter=active.get()
    if reporter:reporter.emit('repair_attempt',stage=stage,provider=route['provider'],model=route['model'])
    result=execute(providers.command(route,state['execution'],prompt=prompt),cwd,env=env,
                   input_text=None if route['provider']=='cursor' else prompt,
                   timeout=manifest.get('limits',{}).get('timeout_seconds',1800),
                   inactivity=manifest.get('limits',{}).get('inactivity_seconds',300),
                   tool_timeout=manifest.get('limits',{}).get('tool_timeout_seconds',600),cancel=cancel,on_line=events.line,
                   on_start=lambda pid:(state.update(child_pid=pid),save()))
    report=events.report(); classification=providers.classify(result,events)
    if classification!='cancellation_failure':state.pop('child_pid',None)
    else:state['cleanup']={'status':'unconfirmed','child_pid':state.get('child_pid'),'stage':stage}
    index=len(state['attempts'])
    entry={'id':index,'run_id':state.get('run_id'),'stage':stage,'route':route,'classification':classification,'session':events.session,'report':report,
           'failure_kind':providers.failure_kind(classification) if classification!='complete' else None,
           'cost_usd':events.cost_usd,'usage':events.usage,'exit_code':result['exit_code'],'duration_seconds':result['duration_seconds']}
    state['attempts'].append(entry);write_json(root/'attempts'/f'{index:04d}.json',entry|{'output':result['output']});save()
    return classification,report



def invoke_routes(project, manifest, state, root, save, cancel, stage, prompt, routes, guard):
    for route in routes:
        before=git_ops.snapshot(project,state['checkouts'])
        classification,report=invoke(project,manifest,state,root,save,cancel,stage,prompt,route)
        after=git_ops.snapshot(project,state['checkouts'])
        git_ops.guard(before,after,manifest,stage,custom={'outputs':guard})
        if classification=='complete' and report and report.get('status')=='complete':return report
        # Failed requests that wrote files need inspection rather than another author.
        if (classification not in {'authentication','quota','model','transient','timeout','inactive','tool-stalled'}
                or git_ops.fingerprint(before)!=git_ops.fingerprint(after)):
            raise WorkflowError('Fixture correction stopped ('+classification+'); inspect the saved attempt before retrying')
    raise WorkflowError('Fixture correction exhausted approved routes; inspect attempts and correct the provider configuration')


def repair(project, manifest, state, bound, root, stage, request, save, cancel):
    from .runner import prompt_for, test_files
    from .progress import active
    records=state.setdefault('test_repairs',[])
    maximum=manifest.get('corrections',{}).get('fixture_rounds',2)
    epoch=state.get('fixture_repair_epoch',0)
    def rounds():return sum(r['stage']==stage and r.get('at',0)>=epoch for r in records)
    if rounds()>=maximum:
        raise WorkflowError('Fixture repair budget exhausted; inspect the attempted corrections')
    specs=request.get('test_paths',[]); checks=request.get('checks',[])
    if not specs or not checks:raise WorkflowError('Fixture repair requires explicit test paths and setup check IDs')
    selected={r['id']:r for r in manifest['repositories']}
    for item in specs:
        if not isinstance(item,dict) or set(item)!={'repository','path'}:raise WorkflowError('Invalid fixture repair path')
        row=selected.get(item['repository'],{})
        if row.get('access')!='write' or not isinstance(item['path'],str) or not matches(item['path'],row.get('test_paths',[])):
            raise WorkflowError('Fixture repair is outside declared test paths')
        contained(Path(state['checkouts'][item['repository']]),item['path'])
    definitions={c['id']:c for c in manifest['checks']}
    if any(c not in definitions or 'setup' not in definitions[c].get('phases',[]) for c in checks):
        raise WorkflowError('Fixture reproduction must reference declared setup checks')
    reproduction_before=git_ops.snapshot(project,state['checkouts'])
    reproduced=verification.run_checks(project,manifest,state['checkouts'],phase='setup',names=checks,cancel=cancel)
    git_ops.guard(reproduction_before,git_ops.snapshot(project,state['checkouts']),manifest,'review',custom={'outputs':[]})
    if all(c['passed'] for c in reproduced):raise WorkflowError('Fixture failure was not reproduced; expected behavior needs review')
    routes=route_for(project,manifest,'implement-tests'); reviewers=route_for(project,manifest,'review')
    if not routes or not reviewers:raise WorkflowError('Configure test authoring and review routes for fixture repair')
    originals={}; modes={}
    for item in specs:
        path=contained(Path(state['checkouts'][item['repository']]),item['path'])
        if item['path'] in state.get('initial_dirty',{}).get(item['repository'],[]):
            raise WorkflowError('Fixture repair cannot modify pre-existing user edits')
        if not path.is_file():raise WorkflowError('Fixture repair must target an existing test or helper file')
        try:originals[(item['repository'],item['path'])]=path.read_text(encoding='utf-8')
        except UnicodeError:raise WorkflowError('Fixture repair requires UTF-8 text test/helper files') from None
        modes[(item['repository'],item['path'])]=path.stat().st_mode & 0o777
    feedback=None; reporter=active.get()
    while rounds()<maximum:
        if cancel():raise WorkflowError('Fixture correction cancelled; explicitly resume when ready')
        before=git_ops.snapshot(project,state['checkouts'])
        number=rounds()+1
        record={'stage':stage,'round':number,'status':'repairing','request':request,'reproduction':reproduced,'at':time.time()}
        records.append(record); index=len(records)-1
        write_json(root/'test-repairs'/f'{index:04d}-before.json',{'files':{r+'/'+p:t for (r,p),t in originals.items()},'snapshot':before});save()
        if reporter:reporter.emit('repair_started',stage=stage,repair_round=number)
        packet='\n\nFIXTURE REPAIR ONLY. Preserve test identities, assertions, skips and expected product behavior. Fix only the requested setup defect. Return complete.\n'+json_text({'request':request,'feedback':feedback})
        prompt=prompt_for(bound,manifest,'implement-tests',state['checkouts'],state['baseline'])+packet
        outputs=[{'repository':item['repository'],'path':item['path']} for item in specs]
        invoke_routes(project,manifest,state,root,save,cancel,'test-repair',prompt,routes,outputs)
        after=git_ops.snapshot(project,state['checkouts'])
        git_ops.guard(before,after,manifest,'implement-tests',custom={'outputs':outputs})
        differences=[]; unchanged=True
        for (repo,name),old in originals.items():
            path=contained(Path(state['checkouts'][repo]),name)
            if not path.is_file():raise WorkflowError('Fixture repair deleted a protected test file')
            new=path.read_text(encoding='utf-8')
            differences.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=name,tofile=name)))
            try:unchanged=unchanged and contract(old,path.suffix)==contract(new,path.suffix)
            except (SyntaxError,ValueError):unchanged=False
        record['diff']='\n'.join(differences);save()
        if not unchanged:
            record.update(status='rejected',reason='Assertion or test identity contract changed');save()
            raise WorkflowError('Fixture repair changed the assertion or test identity contract; inspect the retained diff')
        review=prompt_for(bound,manifest,'review',state['checkouts'],state['baseline'])+'\n\nIndependently review this fixture correction against requirements and the reproduction. Do not edit files. Return complete with repair_approved=true only if behavior/assertions/cases are preserved and the setup correction is justified.\n'+json_text({'request':request,'diff':record['diff'],'reproduction':reproduced})
        decision=invoke_routes(project,manifest,state,root,save,cancel,'test-repair-review',review,reviewers,[])
        current=git_ops.snapshot(project,state['checkouts']);git_ops.guard(after,current,manifest,'review',custom={'outputs':[]})
        record['review']=decision
        setup=verification.run_checks(project,manifest,state['checkouts'],phase='setup',names=checks,cancel=cancel)
        final=git_ops.snapshot(project,state['checkouts']);git_ops.guard(current,final,manifest,'review',custom={'outputs':[]})
        if decision.get('repair_approved') is not True or not all(c['passed'] for c in setup):
            record.update(status='rejected',checks=setup,reason='Independent review or fixture setup did not accept correction');save()
            write_json(root/'test-repairs'/f'{index:04d}-rejected.json',record)
            # Restore only this attempt's owned files, after ruling out any foreign change.
            if git_ops.snapshot(project,state['checkouts'])!=final:
                raise WorkflowError('Files changed during fixture repair rollback; inspect before continuing')
            for (repo,name),old in originals.items():
                path=contained(Path(state['checkouts'][repo]),name)
                path.write_text(old,encoding='utf-8');path.chmod(modes[(repo,name)])
            feedback={'review':decision,'checks':setup};save()
            if reporter:reporter.emit('repair_rejected',stage=stage,repair_round=number,reason=record['reason'])
            continue
        product_changed=any(not matches(p,row.get('test_paths',[])) for row in manifest['repositories'] for p in git_ops.changes(state['baseline'],final).get(row['id'],[]))
        phase='green' if product_changed or 'implement-tests' not in state['completed'] else 'red'
        proof=verification.run_checks(project,manifest,state['checkouts'],phase=phase,cancel=cancel)
        checked=git_ops.snapshot(project,state['checkouts']);git_ops.guard(final,checked,manifest,'review',custom={'outputs':[]})
        if phase=='red' and not all(c['passed'] for c in proof):raise WorkflowError('Repaired tests lack valid red evidence')
        state['red_test_files']=test_files(manifest,checked);state.pop('green',None)
        for repo,name in originals:
            if repo in state.get('stage_before',{}):state['stage_before'][repo]['files'][name]=checked[repo]['files'][name]
        record.update(status='accepted',checks=setup+proof,fingerprint=git_ops.fingerprint(checked))
        write_json(root/'test-repairs'/f'{index:04d}-accepted.json',record);save()
        if reporter:reporter.emit('repair_accepted',stage=stage,repair_round=number)
        return {'fixture_repair':record['diff'],'checks':proof}
    raise WorkflowError('Fixture repair budget exhausted; inspect rejected corrections and approve a specific revision before retrying')


def reconcile(project, manifest, state, bound, root, stage, request, save, cancel):
    """Review a reported conflict; only unchanged-contract test corrections proceed."""
    from .runner import prompt_for, test_files
    limit=manifest.get('corrections',{}).get('contract_review_rounds',0)
    records=state.setdefault('contract_reviews',[])
    epoch=state.get('fixture_repair_epoch',0)
    if sum(r['stage']==stage and r['at']>=epoch for r in records)>=limit:return None
    record={'stage':stage,'at':time.time(),'status':'reviewing','request':request}
    records.append(record);save()
    reviewers=route_for(project,manifest,'review')
    prompt=prompt_for(bound,manifest,'review',state['checkouts'],state['baseline'])+'\n\nIndependently classify this reported conflict against approved requirements. Do not edit files. A correctable test-input/setup mistake with unchanged assertions and product behavior may return status=complete, repairable=true, reason, and test_paths=[{repository,path}]. Genuine requirement/account/authorization decisions or necessary assertion changes must return repairable=false. Do not guess missing user decisions.\n'+json_text(request)
    decision=invoke_routes(project,manifest,state,root,save,cancel,'contract-review',prompt,reviewers,[])
    record['decision']=decision;save()
    if decision.get('repairable') is not True:
        record['status']='requires_decision';save();return None
    specs=decision.get('test_paths',[])
    selected={r['id']:r for r in manifest['repositories']}
    if not specs:raise WorkflowError('Contract review supplied no correction paths')
    before=git_ops.snapshot(project,state['checkouts']);originals={}
    for item in specs:
        if not isinstance(item,dict) or set(item)!={'repository','path'}:raise WorkflowError('Invalid contract correction path')
        row=selected.get(item['repository'],{})
        if row.get('access')!='write' or not matches(item['path'],row.get('test_paths',[])):
            raise WorkflowError('Contract correction is outside declared test paths')
        if item['path'] in state['initial_dirty'].get(item['repository'],[]):raise WorkflowError('Contract correction touches pre-existing edits')
        path=contained(Path(state['checkouts'][item['repository']]),item['path'])
        originals[(item['repository'],item['path'])]=path.read_text(encoding='utf-8')
    write_json(root/'contract-reviews'/f'{len(records)-1:04d}-before.json',{'files':{r+'/'+p:t for (r,p),t in originals.items()},'review':decision})
    prompt=prompt_for(bound,manifest,'implement-tests',state['checkouts'],state['baseline'])+'\n\nCorrect ONLY the independently reviewed test inputs/setup below. Preserve every assertion, test identity, skip and expected product behavior. Do not implement product code or change requirements. Return complete.\n'+json_text({'conflict':request,'review':decision})
    invoke_routes(project,manifest,state,root,save,cancel,'contract-correction',prompt,route_for(project,manifest,'implement-tests'),specs)
    after=git_ops.snapshot(project,state['checkouts']);git_ops.guard(before,after,manifest,'implement-tests',custom={'outputs':specs})
    differences=[]
    for (repo,name),old in originals.items():
        path=contained(Path(state['checkouts'][repo]),name);new=path.read_text(encoding='utf-8')
        differences.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=name,tofile=name)))
        if contract(old,path.suffix)!=contract(new,path.suffix):raise WorkflowError('Contract correction changed protected assertions or cases')
    record['diff']='\n'.join(differences);save()
    review=prompt_for(bound,manifest,'review',state['checkouts'],state['baseline'])+'\n\nIndependently verify this correction implements the existing approved behavior and preserves assertions/cases. Do not edit. Return complete with repair_approved=true only when justified.\n'+json_text({'conflict':request,'classification':decision,'diff':record['diff']})
    final_decision=invoke_routes(project,manifest,state,root,save,cancel,'contract-correction-review',review,reviewers,[])
    if final_decision.get('repair_approved') is not True:raise WorkflowError('Independent contract correction review did not approve')
    checks=[]
    if any('setup' in c.get('phases',[]) for c in manifest['checks']):checks+=verification.run_checks(project,manifest,state['checkouts'],phase='setup',cancel=cancel)
    product_changed=any(not matches(p,row.get('test_paths',[])) for row in manifest['repositories'] for p in git_ops.changes(state['baseline'],after).get(row['id'],[]))
    phase='green' if product_changed else 'red'
    checks+=verification.run_checks(project,manifest,state['checkouts'],phase=phase,cancel=cancel)
    final=git_ops.snapshot(project,state['checkouts']);git_ops.guard(after,final,manifest,'review',custom={'outputs':[]})
    if any(not c['passed'] for c in checks if c.get('phase')=='setup') or (phase=='red' and not all(c['passed'] for c in checks)):
        raise WorkflowError('Contract correction lacks passing setup and renewed red proof')
    state['red_test_files']=test_files(manifest,final);state.pop('green',None)
    for repo,name in originals:state['stage_before'][repo]['files'][name]=final[repo]['files'][name]
    record.update(status='accepted',checks=checks,review=final_decision)
    state.setdefault('test_repairs',[]).append({'stage':stage,'at':time.time(),'status':'accepted','kind':'contract-input-correction'})
    write_json(root/'contract-reviews'/f'{len(records)-1:04d}-accepted.json',record);save()
    return {'contract_correction':record['diff'],'checks':checks}
