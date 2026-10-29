"""Portable static contracts for the supplied documentation design."""
import json
from pathlib import Path
import re
import unittest
ROOT = Path(__file__).resolve().parents[1]

class DocsDesignTests(unittest.TestCase):
    def test_docs_use_design_colors_and_geist_fonts(self):
        tokens = (ROOT / "docs/assets/css/tokens.css").read_text()
        design = json.loads((ROOT / "design/tokens.json").read_text())
        for item in design["color"]["tokens"]:
            for value in item["value"].values():
                if value.startswith("#"):
                    self.assertIn(value, tokens)
        fonts = ROOT / "docs/assets/fonts"
        self.assertEqual((fonts / "Geist-Variable.woff2").read_bytes(), (ROOT / "design/fonts/Geist-Variable.woff2").read_bytes())
        self.assertEqual((fonts / "GeistMono-Variable.woff2").read_bytes(), (ROOT / "design/fonts/GeistMono-Variable.woff2").read_bytes())
        self.assertFalse(list(fonts.glob("IBMPlex*")))

    def test_css_does_not_introduce_hex_colors_outside_tokens(self):
        findings = []
        for path in (ROOT / "docs/assets/css").glob("*.css"):
            if path.name != "tokens.css" and re.search(r"#[0-9a-fA-F]{3,8}\b", path.read_text()):
                findings.append(path.name)
        self.assertEqual(findings, [])

    def test_theme_initializes_before_styles_and_handles_blocked_storage(self):
        html = (ROOT / "templates/site/main.html").read_text()
        self.assertIn("data-theme", html)
        self.assertLess(html.index("prefers-color-scheme"), html.index('rel="stylesheet"'))
        self.assertIn("try", html)
        self.assertIn("catch", html)
        header = (ROOT / "templates/site/partials/header.html").read_text()
        for label in ("System", "Dark", "Light"):
            self.assertIn(label, header)
        js = (ROOT / "docs/assets/js/site.js").read_text()
        self.assertIn("matchMedia", js)
        self.assertIn("change", js)
        for match in re.finditer(r"localStorage\.", js):
            self.assertIn("try", js[max(0, match.start()-200):match.start()])

    def test_home_matches_design_without_claiming_unshipped_commands(self):
        home = (ROOT / "templates/site/home.html").read_text()
        self.assertIn("Hand off the work. Keep the decisions.", home)
        self.assertIn('class="pl-card', home)
        self.assertNotIn("plovi init", home)
        self.assertIn("plovi setup", home)
        self.assertTrue((ROOT / "docs/cli.md").is_file())

    def test_brand_assets_and_change_callout_are_wired(self):
        self.assertEqual((ROOT / "docs/assets/brand/mark.svg").read_bytes(), (ROOT / "design/brand/plovi-mark-light.svg").read_bytes())
        self.assertIn("pl-callout--change", (ROOT / "scripts/docs_hook.py").read_text())
        self.assertIn("plovi-1", (ROOT / "mkdocs.yml").read_text())
