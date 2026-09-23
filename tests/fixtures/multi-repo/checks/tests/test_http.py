import json
import os
import unittest
from urllib.request import urlopen

class ReadinessTests(unittest.TestCase):
    def test_readiness(self):
        with urlopen(os.environ["SAMPLE_BASE_URL"] + "/", timeout=3) as response:
            self.assertEqual(json.load(response), {"status": "ready"})

