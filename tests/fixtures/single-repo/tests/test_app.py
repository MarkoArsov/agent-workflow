import unittest
from app import greeting

class GreetingTests(unittest.TestCase):
    def test_greeting(self):
        self.assertEqual(greeting("world"), "Hello, world!")

