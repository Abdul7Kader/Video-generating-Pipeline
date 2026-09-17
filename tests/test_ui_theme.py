from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ThemeUiContractTests(unittest.TestCase):
    def test_accessible_toggle_and_early_theme_initialization_are_present(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="theme-toggle"', html)
        self.assertIn('aria-pressed="false"', html)
        self.assertLess(html.index('src="/theme.js"'), html.index('href="/styles.css"'))

    def test_theme_logic_restores_choice_and_respects_system_preference(self):
        script = (ROOT / "web" / "theme.js").read_text(encoding="utf-8")
        self.assertIn("video-pipeline-theme", script)
        self.assertIn("localStorage.getItem", script)
        self.assertIn("localStorage.setItem", script)
        self.assertIn("prefers-color-scheme: dark", script)
        self.assertIn("dataset.theme", script)
        self.assertIn("aria-pressed", script)

    def test_dark_palette_and_native_control_scheme_are_defined(self):
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        self.assertIn(':root[data-theme="dark"]', css)
        self.assertIn("color-scheme:dark", css.replace(" ", ""))
        self.assertIn("@media(prefers-color-scheme:dark)", css.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
