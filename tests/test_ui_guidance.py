from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path


PAGE = Path(__file__).resolve().parents[1] / "web" / "index.html"


class Elements(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.nodes: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.nodes.append((tag, dict(attrs)))


class UiGuidanceTests(unittest.TestCase):
    def setUp(self) -> None:
        parser = Elements()
        parser.feed(PAGE.read_text(encoding="utf-8"))
        self.nodes = parser.nodes

    def test_start_page_has_visible_steps_and_an_accessible_info_dialog(self) -> None:
        by_id = {attrs["id"]: (tag, attrs) for tag, attrs in self.nodes if attrs.get("id")}
        self.assertEqual(by_id["help-button"][0], "button")
        self.assertEqual(by_id["help-dialog"][0], "dialog")
        self.assertEqual(by_id["workflow-overview"][0], "ol")
        self.assertEqual(by_id["help-button"][1].get("aria-label"), "Hilfe zur Bedienung öffnen")

    def test_creation_choices_have_hover_and_keyboard_explanations(self) -> None:
        names = {"topic", "language", "duration_seconds", "aspect_ratios", "production_profile"}
        controls = [attrs for tag, attrs in self.nodes if tag in {"input", "select", "textarea"}]
        for name in names:
            with self.subTest(name=name):
                matches = [attrs for attrs in controls if attrs.get("name") == name]
                self.assertTrue(matches)
                self.assertTrue(all(attrs.get("title") for attrs in matches))

    def test_production_choices_explain_locked_profiles_and_refresh_on_open(self) -> None:
        by_id = {attrs["id"]: (tag, attrs) for tag, attrs in self.nodes if attrs.get("id")}
        self.assertEqual(by_id["production-availability"][0], "div")
        self.assertEqual(by_id["production-availability"][1].get("role"), "status")
        script = (PAGE.parent / "app.js").read_text(encoding="utf-8")
        self.assertIn("async function loadProductionOptions()", script)
        self.assertIn("await loadProductionOptions()", script)


if __name__ == "__main__":
    unittest.main()
