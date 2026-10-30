"""New tasks get owned worktrees before plans exist; fixtures never use real homes."""
import json
from pathlib import Path
from unittest.mock import patch
from tests.helpers import WorkspaceTest
from plovi import git_ops
from plovi.util import WorkflowError


class TaskIsolationTests(WorkspaceTest):
    def configured(self, strategy=None):
        root=self.repo('app')
        overrides = {'repositories': [{'id': 'app', 'path': '.', 'checkout_strategy': strategy}]} if strategy else None
        project=self.setup_project(root, overrides)
        self.git(root,'add','.');self.git(root,'commit','-m','Configure fixture')
        return project,root

    def test_new_specification_tasks_have_distinct_owned_worktrees(self):
        project,root=self.configured()
        before=self.git(root,'rev-parse','HEAD')
        first=self.cli('task','start','first',cwd=root,check=False)
        self.assertEqual(first.returncode,0,first.stderr)
        one=json.loads(first.stdout)
        two=json.loads(self.cli('task','start','second',cwd=root).stdout)
        a=Path(one['checkouts']['app']);b=Path(two['checkouts']['app'])
        self.assertNotEqual(a,b);self.assertNotEqual(a,root)
        self.assertNotEqual(one['branches']['app'],two['branches']['app'])
        self.assertEqual(self.git(root,'rev-parse','HEAD'),before)
        self.assertEqual(self.git(root,'branch','--show-current'),'main')
        self.assertFalse((Path(one['plans']['app'])/'pipeline.json').exists())

    def test_manual_and_legacy_current_checkout_cannot_bypass_isolation(self):
        from plovi.tasks import start
        project,root=self.configured('current-checkout')
        project.repository('app').pop('checkout_strategy_explicit', None)  # Legacy profile.
        (root/'uncommitted.txt').write_text('user work')
        (root/'staged.txt').write_text('staged user work');self.git(root,'add','staged.txt')
        before=git_ops.snapshot(project)
        result=start(project,'manual')
        target=Path(result['checkouts']['app'])
        self.assertEqual(project.repository('app')['checkout_strategy'],'current-checkout')
        self.assertFalse((target/'uncommitted.txt').exists())
        self.assertFalse((target/'staged.txt').exists())
        self.assertEqual(git_ops.snapshot(project),before)
        task={'task':'manual','repositories':[{'id':'app','access':'write','branch':result['branches']['app']}]}
        self.assertEqual(git_ops.prepare(project,task),result['checkouts'])

    def test_repeat_requires_explicit_resume_and_checks_ownership(self):
        from plovi.tasks import start
        project,root=self.configured()
        first=start(project,'one')
        with self.assertRaisesRegex(WorkflowError,'resume'):start(project,'one')
        self.assertEqual(start(project,'one',resume=True)['checkouts'],first['checkouts'])
        target=Path(first['checkouts']['app'])
        self.git(target,'switch','-c','feature/unrelated')
        with self.assertRaisesRegex(WorkflowError,'branch'):start(project,'one',resume=True)
        with self.assertRaisesRegex(WorkflowError,'branch'):
            git_ops.prepare(project,{'task':'one','repositories':[{'id':'app','access':'write','branch':first['branches']['app']}]})

    def test_existing_branch_or_path_is_not_adopted(self):
        from plovi.tasks import start
        project,root=self.configured()
        self.git(root,'branch','feature/collision')
        with self.assertRaisesRegex(WorkflowError,'exists'):start(project,'collision')
        occupied=root/'.plovi/local/worktrees/occupied/app'
        occupied.mkdir(parents=True);(occupied/'keep').write_text('user file')
        with self.assertRaisesRegex(WorkflowError,'exists'):start(project,'occupied')
        self.assertEqual((occupied/'keep').read_text(),'user file')
        self.assertEqual(self.git(root,'branch','--show-current'),'main')

    def test_explicit_base_and_plan_location_are_recorded(self):
        from plovi.tasks import start
        project,root=self.configured()
        self.git(root,'branch','feature/dependency')
        result=start(project,'followup',base='feature/dependency')
        target=Path(result['checkouts']['app'])
        self.assertEqual(result['plans']['app'],str(target/'ai-plans/followup'))
        self.assertEqual(self.git(target,'rev-parse','HEAD'),self.git(root,'rev-parse','feature/dependency'))
        self.assertEqual(result['configuration_root'],str(project.root))
        with self.assertRaises(WorkflowError):start(project,'bad-base',base='--all')

    def test_partial_multi_repo_start_resumes_only_its_owned_paths(self):
        from plovi import tasks
        a=self.repo('workspace/app');b=self.repo('workspace/checks')
        project=self.setup_project(a.parent)
        for path in (a,b):
            self.git(path,'add','.');self.git(path,'commit','-m','Configure fixture')
        real=tasks.git
        def fail_second(root,*args,**kwargs):
            if root==b and args[:2]==('worktree','add'):
                raise WorkflowError('simulated failure')
            return real(root,*args,**kwargs)
        with patch.object(tasks,'git',side_effect=fail_second):
            with self.assertRaisesRegex(WorkflowError,'simulated'):
                tasks.start(project,'batch',repositories=['app','checks'])
        result=tasks.start(project,'batch',repositories=['app','checks'],resume=True)
        self.assertEqual(set(result['checkouts']),{'app','checks'})
        for path in (a,b):self.assertEqual(self.git(path,'branch','--show-current'),'main')


    def test_preflight_rejects_an_allocation_with_changed_branch(self):
        import sys
        from plovi import tasks, runner
        project,root=self.configured()
        project.profile['pipeline']['routes']={'default':[{'provider':'codex','model':'fixture'}]}
        result=tasks.start(project,'preflight')
        target=Path(result['checkouts']['app'])
        plans=Path(result['plans']['app']);plans.mkdir(parents=True)
        files=['prompt.md','requirements.md','implementation.md','deferred.md']
        for name in files:(plans/name).write_text('Fixture plan')
        plan={'schema_version':1,'task':'preflight','_directory':str(plans),'plan_files':files,
              'repositories':[{'id':'app','access':'write','branch':result['branches']['app'],'paths':['value.py']}],
              'stages':['implement'],'checks':[{'id':'value','repository':'app','parser':'generic',
              'success_pattern':'ok','command':{'argv':[sys.executable,'-c','print("ok")']}}],
              'outcomes':[{'id':'value','checks':['value']}],'references':[],'connectors':[]}
        runner.preflight(project,plan,check_providers=False)
        self.git(target,'switch','-c','feature/not-this-task')
        with self.assertRaisesRegex(WorkflowError,'branch'):
            runner.preflight(project,plan,check_providers=False)

    def test_registration_compares_canonical_paths_instead_of_literal_text(self):
        from plovi import tasks
        project,root=self.configured()
        allocated=tasks.start(project,'path-format')
        target=Path(allocated['checkouts']['app'])
        row={'repository':'app','path':str(target),'branch':allocated['branches']['app']}
        original=tasks.git
        def alternate_representation(directory,*args,**kwargs):
            if args==('worktree','list','--porcelain','-z'):
                path=target.as_posix()+'/.'
                return 'worktree '+path+'\0HEAD fixture\0branch refs/heads/'+row['branch']+'\0\0'
            return original(directory,*args,**kwargs)
        with patch.object(tasks,'git',side_effect=alternate_representation):
            try:
                actual=tasks._validate_checkout(project,row)
            except WorkflowError as error:
                self.fail('A registered equivalent path must be accepted: '+str(error))
            self.assertEqual(actual,str(target))


    def test_registration_accepts_windows_slashes_and_case_without_relaxing_ownership(self):
        from pathlib import PureWindowsPath
        from types import SimpleNamespace
        from plovi import tasks
        root=PureWindowsPath('C:/fixture/repo')
        target=PureWindowsPath('C:/fixture/task')
        project=SimpleNamespace(repo_path=lambda name:root)
        row={'repository':'app','path':str(target),'branch':'feature/windows'}
        class WindowsPath:
            def __init__(self,value): self.path=PureWindowsPath(value)
            def is_dir(self): return True
            def resolve(self): return self.path
            def __str__(self): return str(self.path)
        def answer(directory,*args):
            if args==('branch','--show-current'):return row['branch']
            return 'worktree c:/FIXTURE/task\0HEAD fixture\0branch refs/heads/feature/windows\0\0'
        with patch.object(tasks,'Path',WindowsPath),patch.object(tasks,'common_dir',return_value=root),patch.object(tasks,'git',side_effect=answer):
            self.assertEqual(tasks._validate_checkout(project,row),str(target))
        def unrelated(directory,*args):
            if args==('branch','--show-current'):return row['branch']
            return 'worktree C:/fixture/other\0HEAD fixture\0\0'
        with patch.object(tasks,'Path',WindowsPath),patch.object(tasks,'common_dir',return_value=root),patch.object(tasks,'git',side_effect=unrelated):
            with self.assertRaisesRegex(WorkflowError,'not registered'):
                tasks._validate_checkout(project,row)

    def test_setup_checkout_override_applies_to_new_task(self):
        from plovi.tasks import start
        for strategy in ('current-checkout', 'feature-branch'):
            with self.subTest(strategy=strategy):
                root=self.repo('override-'+strategy)
                project=self.setup_project(root, {'repositories':[{'id': 'override-'+strategy, 'checkout_strategy':strategy}]})
                self.git(root,'add','.');self.git(root,'commit','-m','Configure fixture')
                result=start(project,'selected')
                self.assertEqual(Path(result['checkouts']['override-'+strategy]),root)
                expected='main' if strategy=='current-checkout' else 'feature/selected'
                self.assertEqual(self.git(root,'branch','--show-current'),expected)
                self.assertEqual(result['branches']['override-'+strategy],expected)
                self.assertEqual(start(project,'selected',resume=True)['checkouts'],result['checkouts'])
                with self.assertRaisesRegex(WorkflowError, 'another unfinished task'):
                    start(project,'other')

    def test_explicit_feature_override_preserves_unrelated_current_branch(self):
        from plovi.tasks import start
        root=self.repo('guard')
        project=self.setup_project(root, {'repositories':[{'id':'guard','checkout_strategy':'feature-branch'}]})
        self.git(root,'add','.');self.git(root,'commit','-m','Configure fixture')
        self.git(root,'switch','-c','feature/unrelated')
        with self.assertRaisesRegex(WorkflowError, 'not on its selected base'):
            start(project,'new')
        self.assertEqual(self.git(root,'branch','--show-current'),'feature/unrelated')
