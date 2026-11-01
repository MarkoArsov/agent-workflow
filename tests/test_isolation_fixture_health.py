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
                target = '_require_factory'
                standin = SimpleNamespace(allocate=allocate, refresh=refresh)
            else:
                def preflight(*args, **kwargs):
                    raise ReachedProduct()
                target = '_require_isolation'
                standin = SimpleNamespace(preflight=preflight)
            with patch.object(case, target, return_value=standin), self.assertRaises(ReachedProduct):
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
