import importlib.util
from tests.helpers import PACKAGE, WorkspaceTest

class FakeRuntimeIdentityTests(WorkspaceTest):
    def test_reinspecting_pinned_image_preserves_identity(self):
        spec=importlib.util.spec_from_file_location('fake_docker',PACKAGE/'tests/fixtures/fake_docker.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        first=module._handle_inspect(['inspect','plovi/runner:test'])[0]['Id']
        second=module._handle_inspect(['inspect',first])[0]['Id']
        self.assertEqual(second,first)
