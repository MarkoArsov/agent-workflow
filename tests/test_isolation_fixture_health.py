"""Exercise setup in the authored cases before any new product API exists.

Stand-ins stop at the next product call; they do not establish factory/container
behavior. Every preceding Git/project fixture operation runs normally.
"""
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from tests import test_factory_checkouts as factory_cases
from tests import test_container as container_cases


class ReachedProduct(Exception):
    pass


class FixtureHealthTests(unittest.TestCase):
    def exercise(self, kind, method):
        case = kind(method)
        case.setUp()
        try:
            if kind is factory_cases.FactoryCheckoutTests:
                allocations = []
                def allocate(project, task, **kwargs):
                    if allocations:
                        raise ReachedProduct()
                    path = case.root / 'health-allocation'
                    source = case.git(project.repo_path('app'), 'remote', 'get-url', 'origin')
                    subprocess.run(['git', 'clone', source, str(path)], env=case.env, check=True, capture_output=True)
                    allocations.append(path)
                    return {'app': path}
                def refresh(*args, **kwargs):
                    raise ReachedProduct()
                standin = SimpleNamespace(allocate=allocate, refresh=refresh)
                with patch.object(case, '_require_factory', return_value=standin), self.assertRaises(ReachedProduct):
                    getattr(case, method)()
            else:
                # Container cases now build a real factory-owned checkout (C2)
                # before reaching isolation.preflight; the factory standin must
                # legitimately satisfy that setup, not raise, so the reached
                # boundary stays attributable to isolation.preflight alone.
                def allocate(project, task, **kwargs):
                    path = case.root / f'container-health-allocation-{task}'
                    source = case.git(project.repo_path('app'), 'remote', 'get-url', 'origin')
                    subprocess.run(['git', 'clone', source, str(path)], env=case.env, check=True, capture_output=True)
                    return {'app': path}
                factory_standin = SimpleNamespace(allocate=allocate)
                def preflight(*args, **kwargs):
                    raise ReachedProduct()
                isolation_standin = SimpleNamespace(preflight=preflight)
                with patch.object(case, '_require_factory', return_value=factory_standin), \
                     patch.object(case, '_require_isolation', return_value=isolation_standin), \
                     self.assertRaises(ReachedProduct):
                    getattr(case, method)()
        finally:
            case.doCleanups()

    def test_refresh_base_fixture_reaches_allocation(self):
        self.exercise(factory_cases.FactoryCheckoutTests, 'test_next_task_refreshes_remote_base')

    def test_preserve_branch_fixture_reaches_refresh(self):
        self.exercise(factory_cases.FactoryCheckoutTests, 'test_refresh_preserves_active_task_branch')

    def test_missing_runtime_trusted_fixture_reaches_preflight(self):
        self.exercise(container_cases.ContainerTests, 'test_missing_runtime_refuses_trusted_unattended')

    def test_missing_runtime_restricted_fixture_reaches_preflight(self):
        self.exercise(container_cases.ContainerTests, 'test_missing_runtime_reports_restricted_fallback')


class ContainerProtocolHealthTests(unittest.TestCase):
    def exercise(self, method, *, windows=False):
        case = container_cases.ContainerTests(method)
        case.setUp()
        try:
            if windows:
                with patch('plovi.isolation.platform.system', return_value='Windows'):
                    getattr(case, method)()
            else:
                getattr(case, method)()
            return case._read_calls(case.root / 'container-calls.json')
        finally:
            case.doCleanups()

    def test_missing_image_reaches_runtime_inspect(self):
        calls = self.exercise('test_no_implicit_pull')
        self.assertTrue(any(c['argv'][0] == 'info' for c in calls))
        self.assertTrue(any(c['argv'][0] == 'inspect' for c in calls))
        self.assertFalse(any(c['argv'][0] == 'pull' for c in calls))

    def test_fake_execution_is_portable_on_windows(self):
        self.exercise('test_fake_runtime_runs_stages_and_checks', windows=True)
