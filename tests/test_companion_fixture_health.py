"""Exercise companion setup without claiming factory behavior is implemented."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from tests import test_factory_checkouts as cases


class ReachedProduct(Exception):
    pass


class CompanionFixtureHealthTests(unittest.TestCase):
    def test_companion_fixture_reaches_factory(self):
        case = cases.FactoryCheckoutTests('test_read_companion_uses_factory_base')
        case.setUp()
        try:
            def allocate(*args, **kwargs):
                raise ReachedProduct()
            with patch.object(case, '_require_factory', return_value=SimpleNamespace(allocate=allocate)):
                with self.assertRaises(ReachedProduct):
                    case.test_read_companion_uses_factory_base()
        finally:
            case.doCleanups()
