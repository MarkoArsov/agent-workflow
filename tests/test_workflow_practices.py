"""Exercise actual context delivery and planning-time checkout reuse in isolation."""
from pathlib import Path
from tests.helpers import PACKAGE, WorkspaceTest
from plovi import runner, git_ops
from plovi.extensions import catalog, resolve_skill
from plovi.project import resolve
from plovi.util import WorkflowError


class WorkflowPracticesTests(WorkspaceTest):
    def test_shared_reference_is_frozen_for_all_ai_stages(self):
        project=self.setup_project(self.repo('app'))
        reference=project.config/'references/quality.md'
        reference.parent.mkdir(parents=True,exist_ok=True)
        reference.write_text('ORIGINAL_SELECTED_GUIDANCE')
        checklist=reference.parent/'quality-guidance.md'
        checklist.write_text('FROZEN_SHARED_CHECKLIST')
        (reference.parent/'unselected.md').write_text('UNSELECTED_GUIDANCE')
        plans=self.root/'plans';plans.mkdir()
        names=['prompt.md','requirements.md','implementation.md','deferred.md']
        for name in names: (plans/name).write_text('PRIVATE_REASONING' if name=='implementation.md' else 'Required behavior')
        manifest={'_directory':str(plans),'plan_files':names,'references':['quality.md','quality-guidance.md'],
                  'repositories':[{'id':'app','access':'write'}]}
        bound=runner.binding(project,manifest)
        reference.write_text('LIVE_REPLACEMENT')
        checklist.write_text('LIVE_CHECKLIST')
        roots={'app':str(project.root)}
        before=git_ops.snapshot(project,roots)
        for stage in ('implement-tests','implement','review'):
            prompt=runner.prompt_for(bound,manifest,stage,roots,before)
            self.assertIn('ORIGINAL_SELECTED_GUIDANCE',prompt)
            self.assertIn('FROZEN_SHARED_CHECKLIST',prompt)
            self.assertNotIn('LIVE_CHECKLIST',prompt)
            self.assertNotIn('LIVE_REPLACEMENT',prompt)
            self.assertNotIn('UNSELECTED_GUIDANCE',prompt)
            if stage=='review': self.assertNotIn('PRIVATE_REASONING',prompt)
        missing=dict(manifest,references=['absent.md'])
        with self.assertRaisesRegex(WorkflowError,'Missing requested reference'):
            runner.prompt_for(bound,missing,'implement',roots,before)

    def test_retro_discovery_is_overridable_and_project_local(self):
        a=self.setup_project(self.repo('a'));b=self.setup_project(self.repo('b'))
        self.assertEqual(resolve_skill('session-retro',a),PACKAGE/'skills/session-retro/SKILL.md')
        custom=a.config/'skills/session-retro/SKILL.md';custom.parent.mkdir(parents=True)
        custom.write_text('---\nname: session-retro\ndescription: Fixture retrospective.\n---\nPROJECT_ONLY\n')
        self.assertEqual(resolve_skill('session-retro',a),custom)
        self.assertNotEqual(resolve_skill('session-retro',b),custom)
        self.assertEqual(catalog(a)['session-retro']['origin'],'project')

    def test_task_checkout_can_precede_manifest_and_is_reused(self):
        root=self.repo('app')
        project=self.setup_project(root,{'repositories':[{'id':'app','path':'.','checkout_strategy':'worktree','base_branch':'main'}]})
        self.git(root,'add','.');self.git(root,'commit','-m','Configure fixture')
        task={'task':'planned','repositories':[{'id':'app','access':'write','branch':'codex/planned'}]}
        first=git_ops.prepare(project,task)
        checkout=Path(first['app'])
        self.assertEqual(resolve(checkout, explicit=project.root).root,project.root)
        self.assertEqual(resolve(checkout).profile["project"]["id"],project.profile["project"]["id"])
        plans=checkout/'ai-plans/planned';plans.mkdir(parents=True)
        (plans/'requirements.md').write_text('Task-owned plan')
        self.assertEqual(self.git(checkout,'branch','--show-current'),'codex/planned')
        self.assertEqual(self.git(root,'branch','--show-current'),'main')
        self.assertEqual(git_ops.prepare(project,task),first)
        self.assertEqual((plans/'requirements.md').read_text(),'Task-owned plan')
        other={'task':'other','repositories':[{'id':'app','access':'write','branch':'codex/other'}]}
        second=Path(git_ops.prepare(project,other)['app'])
        self.assertNotEqual(checkout,second)
        self.assertFalse((second/'ai-plans/planned/requirements.md').exists())
