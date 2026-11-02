import json
from tests.helpers import HardeningTest
from plovi import runner, state


class PipelineResumeTests(HardeningTest):
    def test_pipeline_resumes_saved_output_without_losing_manifest(self):
        self.fixture([{}]);self.save_plan()
        saved=runner.run(self.project,self.plan)
        saved.update(status='interrupted',completed=[],active_stage='implement',stage_before=saved['baseline'],stage_evidence={})
        state.save(state.directory(self.project,'sample'),saved)
        result=self.task_cli('pipeline','sample','--no-watch','--json')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        watched=self.task_cli('watch','sample','--json')
        self.assertEqual(watched.returncode,0,watched.stdout+watched.stderr)
        self.assertEqual(json.loads(watched.stdout.splitlines()[-1])['status'],'complete')
        self.assertEqual(len(self.calls()),1)
