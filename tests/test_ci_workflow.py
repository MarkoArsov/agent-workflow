from __future__ import annotations
import os
import re
import subprocess
import textwrap
from pathlib import Path
from unittest.mock import patch
from tests.helpers import PACKAGE, WorkspaceTest


class CIWorkflowTests(WorkspaceTest):
    def workflow(self):
        return (PACKAGE / '.github/workflows/verify.yml').read_text()

    def job(self, name):
        match = re.search(r'^  ' + re.escape(name) + r':\n(.*?)(?=^  [\w-]+:|\Z)',
                          self.workflow(), re.M | re.S)
        self.assertIsNotNone(match, name)
        return match[1]

    def test_verification_events_and_concurrency_do_not_duplicate_feature_pushes(self):
        events = self.workflow().split('permissions:', 1)[0]
        self.assertRegex(events, r'push:\s*\n\s+branches: \[main\]')
        self.assertIn('pull_request:', events)
        self.assertIn('workflow_dispatch:', events)
        self.assertIn('github.workflow', events)
        self.assertIn('github.event.pull_request.number || github.ref', events)
        self.assertIn('cancel-in-progress: true', events)

    def test_history_and_generated_checks_run_once_outside_matrix(self):
        text = self.workflow()
        self.assertEqual(text.count('python scripts/check_public_content.py --history'), 1)
        self.assertEqual(text.count('python scripts/generate_docs.py --check'), 1)
        self.assertNotIn('--history', self.job('core'))
        self.assertNotIn('fetch-depth: 0', self.job('core'))
        self.assertIn('fetch-depth: 0', self.job('audit'))
        self.assertIn('--history', self.job('audit'))
        self.assertIn('os: [ubuntu-latest, macos-latest, windows-latest]', self.job('core'))
        self.assertIn('python: ["3.11", "3.14"]', self.job('core'))
        self.assertNotIn('continue-on-error', text)
        self.assertNotIn('contents: write', text)

    def test_failed_jobs_retain_logs_with_timeouts(self):
        for name in ['core', 'audit', 'windows-install', 'docs']:
            with self.subTest(job=name):
                job = self.job(name)
                self.assertRegex(job, r'timeout-minutes: \d+')
                self.assertIn('if: failure()', job)
                self.assertIn('actions/upload-artifact@', job)
                self.assertIn('retention-days: 7', job)
        self.assertIn('pipefail', self.job('core'))

    def smoke_code(self):
        match = re.search(r'shell: python\s*\n\s+run: \|\n(.*?)(?=^      - |\Z)',
                          self.job('windows-install'), re.M | re.S)
        self.assertIsNotNone(match, 'Windows check must run the isolated local-source harness')
        return textwrap.dedent(match[1]).rstrip()

    def test_windows_smoke_installs_and_reinstalls_in_isolated_child_homes(self):
        code = self.smoke_code()
        calls = []
        def run(argv, **kwargs):
            env = kwargs['env']
            calls.append(argv)
            self.assertNotIn('GH_TOKEN', env)
            self.assertNotIn('GITHUB_TOKEN', env)
            self.assertEqual(env['AGENTFLOW_NO_MODIFY_PATH'], '1')
            self.assertEqual(env['HOME'], env['USERPROFILE'])
            self.assertTrue(Path(env['HOME']).is_relative_to(self.root))
            command = argv[-1]
            if 'install.ps1' in command:
                self.assertIn('--local-source', command)
                self.assertNotIn('Invoke-Expression', command)
                self.assertNotIn('AGENTFLOW_REF', env)
                discovery = Path(env['HOME']) / '.agents/skills/af-setup/SKILL.md'
                discovery.parent.mkdir(parents=True, exist_ok=True)
                discovery.write_text('fixture discovery')
            return subprocess.CompletedProcess(argv, 0, '0.1.0\n', '')
        with patch.dict(os.environ, {'RUNNER_TEMP': str(self.root), 'GH_TOKEN': 'test-only'}, clear=False), \
             patch('subprocess.run', side_effect=run):
            before = dict(os.environ)
            exec(compile(code, '<Windows smoke>', 'exec'), {'__name__': '__main__'})
            self.assertEqual(dict(os.environ), before)
        self.assertEqual([c[0] for c in calls], ['powershell', 'pwsh', 'pwsh'])
        self.assertFalse(any(p.name.startswith('agentflow-install-') for p in self.root.iterdir()))

    def test_windows_native_failure_is_not_hidden_by_logging(self):
        code = self.smoke_code()
        def fail(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 1, 'fixture failure\n', '')
        with patch.dict(os.environ, {'RUNNER_TEMP': str(self.root)}), patch('subprocess.run', side_effect=fail):
            with self.assertRaises((RuntimeError, subprocess.CalledProcessError)):
                exec(compile(code, '<Windows smoke>', 'exec'), {'__name__': '__main__'})
        self.assertIn('fixture failure', (self.root / 'windows-install.log').read_text())
