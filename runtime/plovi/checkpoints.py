"""Explicit legacy handoff: preserve authored tests only with renewed proof."""
import copy
import sys
import tempfile
import time
import uuid
from pathlib import Path
from . import claims, git_ops, manifest, policy, runner, state, verification
from .identity import expected, fingerprint
from .process import CleanupFailure
from .progress import Reporter, active
from .util import WorkflowError, digest, json_text, read_json, write_json, redact


def validate(project, task, root):
    saved = read_json(root / 'state.json')
    if not saved:
        raise WorkflowError('No saved task to migrate')
    plan = manifest.load(Path(saved['manifest_path']), project)
    checkpoint = plan.get('recovery', {}).get('test_checkpoint')
    if not checkpoint:
        raise WorkflowError('Review recovery.test_checkpoint before migrating a completed test stage')
    saved = copy.deepcopy(saved)
    execution = saved['execution']
    if execution['permission_mode'] == 'restricted':
        refreshed = policy.execution(project, plan, unattended=True)
        if refreshed['permission_mode'] != 'restricted':
            raise WorkflowError('Review the changed permission policy separately before migration')
        configured = project.profile['execution'].get('provider_settings', {}).get('claude', {})
        if not configured.get('allowed_tools') and 'claude' in refreshed.get('provider_settings', {}):
            execution.setdefault('provider_settings', {}).setdefault('claude', {})['allowed_tools'] = refreshed['provider_settings']['claude']['allowed_tools']
    bound = runner.binding(project, plan, execution=execution)
    new_hash = digest(json_text(bound))
    current = git_ops.snapshot(project, saved['checkouts'])
    prior = saved.get('checkpoint_migration', {})
    if prior.get('status') == 'complete' and saved['binding_sha256'] == new_hash:
        if prior['fingerprint'] != git_ops.fingerprint(current) or prior['heads'] != {k:v['head'] for k,v in current.items()}:
            raise WorkflowError('Migrated artifacts changed; inspect foreign edits before continuation')
        return saved, plan, bound, current, True
    if saved.get('status') not in {'escalated', 'failed', 'interrupted'}:
        raise WorkflowError('Migration requires a stopped task; cancellation and pending decisions remain explicit')
    if (saved.get('cleanup') or {}).get('status') == 'unconfirmed' or saved.get('pending_input') or saved.get('pending_approvals'):
        raise WorkflowError('Resolve owned cleanup, input or diff approval before migration')
    old = read_json(root / 'binding.json')
    pending = prior.get('status') == 'repairing' and prior.get('original_binding') == checkpoint['binding_sha256']
    if pending:
        old = read_json(root / 'migrations' / checkpoint['binding_sha256'] / 'binding.json')
    if not old or digest(json_text(old)) != checkpoint['binding_sha256']:
        raise WorkflowError('Checkpoint does not match the original saved binding')
    if not pending and saved['binding_sha256'] != checkpoint['binding_sha256']:
        raise WorkflowError('Checkpoint does not match the saved task')
    if pending and saved['binding_sha256'] != new_hash:
        raise WorkflowError('Pending migration inputs changed; inspect its saved journal')
    if saved.get('completed') != ['implement-tests'] or saved.get('active_stage') != 'implement':
        raise WorkflowError('Only an authored-test checkpoint before implementation can be migrated')
    proof = saved.get('stage_evidence', {}).get('implement-tests', {})
    if not proof.get('passed') or not proof.get('checks') or not all(c.get('passed') for c in proof['checks']):
        raise WorkflowError('No passing test-stage evidence to preserve')
    escalation = saved.get('escalation', {})
    if (escalation.get('kind') not in {'spec_conflict', 'fixture_setup'}
            or digest(escalation.get('reason', '')) != checkpoint['escalation_sha256']):
        raise WorkflowError('The exact fixture escalation must be reviewed before migration')
    if old['plans']['requirements.md'] != bound['plans']['requirements.md']:
        raise WorkflowError('Changed requirements require a new test contract, not checkpoint migration')
    if any(bound['plans'].get(name) != text for name,text in old['plans'].items()):
        raise WorkflowError('Changed frozen plan files require a reviewed test contract')
    if old['profile'] != bound['profile'] or any(old.get(k) != bound.get(k) for k in ('rules','references','connectors','stages')):
        raise WorkflowError('Project profile or extension changes require separate review')
    old_policy = copy.deepcopy(old.get('policy', {}).get('values', {}))
    new_policy = copy.deepcopy(bound['policy']['values'])
    for value in (old_policy, new_policy): value.get('execution', {}).pop('tracking_mode', None)
    if old_policy and old_policy != new_policy:
        raise WorkflowError('Changed policy requires separate review before checkpoint migration')
    previous = old['manifest']
    for key in ('stages', 'routes', 'model_selection', 'approved_no_red_reason'):
        if previous.get(key) != plan.get(key):
            raise WorkflowError('Checkpoint migration cannot change stages, routes or red-proof policy')
    for outcome in previous['outcomes']:
        if outcome not in plan['outcomes']:
            raise WorkflowError('Checkpoint migration cannot change existing outcomes')
    by_id = {c['id']:c for c in plan['checks']}
    if any(by_id.get(c['id']) != c for c in previous['checks']):
        raise WorkflowError('Checkpoint migration cannot change existing checks')
    new_checks = [c for c in plan['checks'] if c['id'] not in {x['id'] for x in previous['checks']}]
    if any('setup' not in c.get('phases', []) or 'red' in c.get('phases', []) for c in new_checks):
        raise WorkflowError('Only additive fixture-health checks are allowed during migration')
    identity = lambda rows: [{k:v for k,v in row.items() if k not in {'paths','test_paths'}} for row in rows]
    if identity(previous['repositories']) != identity(plan['repositories']):
        raise WorkflowError('Repository ownership or branch changed; migration refused')
    for row in previous['repositories']:
        new = next(r for r in plan['repositories'] if r['id'] == row['id'])
        if not set(row.get('test_paths', [])) <= set(new.get('test_paths', [])):
            raise WorkflowError('Migration cannot remove frozen test paths')
    working = copy.deepcopy(saved)
    # Preview uses a temporary journal; no live baseline is edited by validation.
    with tempfile.TemporaryDirectory(prefix='plovi-checkpoint-') as temporary:
        runner.recover_resume(project, plan, working, Path(temporary), rebind=True, replay=False)
    if not saved.get('red_test_files'):
        raise WorkflowError('No frozen test hashes exist for this checkpoint')
    source_updates = []
    from .repairs import contract
    for repo, files in saved['red_test_files'].items():
        authored = set(proof.get('changes', {}).get(repo, []))
        for name, value in files.items():
            actual = current[repo]['files'].get(name)
            if actual == value: continue
            original = saved['baseline'][repo]['files'].get(name)
            adopted = working['baseline'][repo]['files'].get(name)
            if name in authored or value != original or actual != adopted or actual is None:
                raise WorkflowError('A frozen authored test changed; preserve and review its diff before migration')
            checkout = Path(saved['checkouts'][repo])
            old_text = git_ops.git(checkout, 'show', saved['baseline'][repo]['head'] + ':' + name)
            new_text = (checkout / name).read_text(encoding='utf-8')
            if contract(old_text, Path(name).suffix) != contract(new_text, Path(name).suffix):
                raise WorkflowError('An upstream frozen baseline test changed its assertion contract')
            source_updates.append({'repository':repo,'path':name,'previous':value,'current':actual})
    working['_source_test_updates'] = source_updates
    if working.get('stage_before') != current:
        raise WorkflowError('Foreign edits exist beyond the exact approved repairs and authored tests')
    return working, plan, bound, current, False


def record_migration(project, task, binding):
    """Record the person who applied the migration; a ledger failure never undoes a finished migration."""
    from . import ledger
    from .operations import actor
    try:
        ledger.append(project, {"subject": {"kind": "task", "id": task}, "type": "checkpoint.migrated",
                                "actor": actor({}, project.root), "reason": "Legacy test checkpoint migrated with plovi migrate --apply",
                                "data": {"binding_sha256": binding}})
    except (WorkflowError, OSError) as exc:
        print(f"Warning: plovi could not write the ledger ({exc}); the migration is complete.", file=sys.stderr)


def migrate(project, task, *, apply=False):
    root = state.directory(project, task)
    with state.lock(root / 'launch.lock'), state.lock(root / 'runner.lock'):
        saved, plan, bound, current, reused = validate(project, task, root)
        result = {'task':task, 'status':'migration_ready', 'completed':saved['completed'], 'reused':reused}
        if reused or not apply:
            return dict(result, status='migration_complete' if reused else result['status'])
        runner.preflight(project, plan, execution=saved['execution'])
        checkpoint = plan['recovery']['test_checkpoint']
        original_hash = checkpoint['binding_sha256']
        backup = root / 'migrations' / original_hash
        if not backup.exists():
            write_json(backup / 'state.json', read_json(root / 'state.json'))
            write_json(backup / 'binding.json', read_json(root / 'binding.json'))
            write_json(backup / 'runtime.json', read_json(root / 'runtime.json'))
        reporter = Reporter(root, uuid.uuid4().hex)
        reporter.live['task'] = task
        token = active.set(reporter); identity_token = expected.set(fingerprint(project))
        saved['run_id'] = reporter.run_id
        def save():
            state.save(root, saved)
        try:
            with claims.acquire(project, plan, no_wait=True):
                if git_ops.snapshot(project, saved['checkouts']) != current:
                    raise WorkflowError('Foreign edits appeared during migration preflight')
                actual = read_json(root / 'state.json')
                source_updates = saved.pop('_source_test_updates', [])
                actual['execution'] = saved['execution']
                runner.recover_resume(project, plan, actual, root, rebind=True, replay=False)
                saved = actual
                saved['run_id'] = reporter.run_id
                saved['policy'] = bound['policy']
                saved['binding_sha256'] = digest(json_text(bound))
                saved['checkpoint_migration'] = {'status':'repairing', 'original_binding':original_hash, 'source_test_updates':source_updates}
                request = checkpoint.get('fixture_request')
                if request:
                    from .repairs import repair
                    write_json(root / 'binding.json', bound)
                    saved['status'] = 'running'; save()
                    reporter.emit('migration_started', stage='implement', status='running')
                    repair(project, plan, saved, bound, root, 'implement', request, save,
                           lambda:(root / 'cancel.json').exists())
                before_checks = git_ops.snapshot(project, saved['checkouts'])
                checks = []
                if any('setup' in c.get('phases', []) for c in plan['checks']):
                    checks += verification.run_checks(project, plan, saved['checkouts'], phase='setup')
                phase = 'green' if plan.get('approved_no_red_reason') else 'red'
                checks += verification.run_checks(project, plan, saved['checkouts'], phase=phase)
                after = git_ops.snapshot(project, saved['checkouts'])
                git_ops.guard(before_checks, after, plan, 'review', custom={'outputs':[]})
                if not all(c['passed'] for c in checks):
                    raise WorkflowError('Migration lacks passing fixture setup and renewed red proof')
                saved['red_test_files'] = runner.test_files(plan, after)
                saved['stage_evidence']['implement-tests'] = dict(saved['stage_evidence']['implement-tests'],
                    checks=checks, fingerprint=git_ops.fingerprint(after), passed=True, migration=True)
                saved.setdefault('escalation_history', []).append(saved.pop('escalation'))
                saved.pop('error', None); saved.pop('green', None); saved.pop('retained_output', None)
                saved['status'] = 'interrupted'; saved['stage'] = 'implement'
                saved['checkpoint_migration'].update(status='complete', at=time.time(),
                    fingerprint=git_ops.fingerprint(after), heads={k:v['head'] for k,v in after.items()})
                write_json(root / 'binding.json', bound)
                save(); reporter.emit('migration_complete', stage='implement', status='interrupted')
                record_migration(project, task, saved['binding_sha256'])
                return dict(result, status='migration_complete', checks=[{'id':c['id'],'phase':c['phase'],'passed':c['passed']} for c in checks])
        except (WorkflowError, OSError, KeyboardInterrupt) as exc:
            # Keep the original escalation until every proof has succeeded.
            if read_json(root / 'binding.json') == bound:
                saved['status'] = 'escalated'; saved['error'] = 'Migration stopped: ' + redact(str(exc))
                if isinstance(exc, CleanupFailure):
                    saved['cleanup'] = {'status':'unconfirmed','child_pid':exc.pid}
                save(); reporter.emit('migration_stopped', status='escalated', reason=str(exc))
            raise
        finally:
            active.reset(token); expected.reset(identity_token)
