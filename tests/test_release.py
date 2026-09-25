from __future__ import annotations
import importlib.util
import json
import tarfile
from pathlib import Path
from tests.helpers import PACKAGE, WorkspaceTest
from scorebook.install import validate_source
from scorebook.util import WorkflowError

class ReleaseTests(WorkspaceTest):
    def test_payload_is_deterministic_allowlisted_and_checksums_detect_edits(self):
        spec = importlib.util.spec_from_file_location("release", PACKAGE / "scripts/build_release.py")
        release = importlib.util.module_from_spec(spec); spec.loader.exec_module(release)
        archive = release.build(self.root / "release")
        first = archive.read_bytes()
        self.assertEqual(release.build(self.root / "release").read_bytes(), first)
        with tarfile.open(archive) as source:
            names = source.getnames()
            self.assertFalse(any("/tests/" in n or "/.git/" in n or "/local/" in n or "/docs/" in n for n in names))
            source.extractall(self.root / "extracted", filter="data")
        payload = next((self.root / "extracted").iterdir())
        self.assertEqual(validate_source(payload)["version"], "0.1.0")
        with (payload / "skills/review/SKILL.md").open("a") as output:
            output.write("tampered")
        with self.assertRaisesRegex(WorkflowError, "checksum"):
            validate_source(payload)
