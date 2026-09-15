from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.planner import ScriptProviderUnavailable, _prompt, generate_script, script_provider_status
from backend.schemas import JobCreate


REQUEST = JobCreate(
    topic="Warum Moore für den Klimaschutz wichtig sind",
    language="de",
    duration_seconds=60,
    aspect_ratio="16:9",
    video_type="explainer",
    target_platform="download",
)


def settings(**overrides):
    values = {
        "script_provider": "auto",
        "allow_template_script": False,
        "gemini_api_key": "",
        "gemini_model": "gemini-3.8-flash",
        "openai_api_key": "",
        "openai_model": "gpt-5.6-terra",
        "openai_base_url": "https://api.openai.com/v1",
        "openrouter_api_key": "",
        "openrouter_model": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def model_response() -> dict:
    scenes = []
    for index in range(3):
        scenes.append({
            "narration": f"Konkreter Sprechertext für Szene {index + 1}.",
            "visual": f"Luftaufnahme eines wiedervernässten Moores, Einstellung {index + 1}.",
            "visual_type": "generated_image",
            "asset_prompt": "Documentary aerial photograph of a rewetted peatland, natural light, no text",
            "on_screen_text": "",
            "camera": "Langsame Vorwärtsfahrt",
            "transition": "cut",
            "action": "explain",
            "accent": "#38bdf8",
        })
    payload = {
        "title": "Moore: unterschätzte Klimaschützer",
        "description": "Ein konkreter Erklärfilm über intakte und entwässerte Moore.",
        "audience": "Allgemein interessierte Erwachsene",
        "tone": "Sachlich und anschaulich",
        "fact_check_notes": ["Aktuelle Emissionswerte vor Produktion mit einer Primärquelle prüfen."],
        "scenes": scenes,
    }
    return {"output_text": json.dumps(payload)}


class PlannerTests(unittest.TestCase):
    def test_no_ai_configuration_fails_instead_of_using_template(self):
        with patch("backend.planner.settings", settings()):
            with self.assertRaises(ScriptProviderUnavailable):
                generate_script(REQUEST)
            self.assertFalse(script_provider_status()["ready"])

    def test_style_prompt_is_specific_and_visual_is_not_on_screen_text(self):
        explainer = _prompt(REQUEST)
        generated = _prompt(REQUEST.model_copy(update={"video_type": "generated"}))
        self.assertIn("never default to a presenter or stick figure", explainer)
        self.assertIn("cinematic AI-generated shots", generated)
        self.assertIn("Never copy the visual instruction", generated)
        self.assertNotEqual(explainer, generated)

    def test_revision_contains_request_and_existing_draft(self):
        previous = {"title": "Alt", "description": "Alt", "scenes": [{"narration": "Alt"}], "metadata": {"provider": "gemini"}}
        prompt = _prompt(REQUEST, previous, "Szene zwei konkreter machen")
        self.assertIn("Szene zwei konkreter machen", prompt)
        self.assertIn('"title": "Alt"', prompt)
        self.assertNotIn('"provider": "gemini"', prompt)

    def test_gemini_uses_structured_schema_and_records_provenance(self):
        configured = settings(gemini_api_key="secret")
        with patch("backend.planner.settings", configured), patch("backend.planner._post_json", return_value=model_response()) as post:
            result = generate_script(REQUEST)
        url, payload, headers = post.call_args.args
        self.assertNotIn("secret", url)
        self.assertEqual(headers["x-goog-api-key"], "secret")
        self.assertTrue(url.endswith("/v1beta/interactions"))
        self.assertEqual(payload["model"], "gemini-3.8-flash")
        self.assertEqual(payload["response_format"]["mime_type"], "application/json")
        self.assertEqual(result["metadata"]["provider"], "gemini")
        self.assertEqual(result["metadata"]["model"], "gemini-3.8-flash")
        self.assertEqual(result["scenes"][0]["visual_type"], "generated_image")
        self.assertTrue(result["metadata"]["fact_check_notes"])

    def test_template_requires_explicit_development_opt_in(self):
        with patch("backend.planner.settings", settings(script_provider="template")):
            with self.assertRaises(ScriptProviderUnavailable):
                generate_script(REQUEST)
        with patch("backend.planner.settings", settings(script_provider="template", allow_template_script=True)):
            result = generate_script(REQUEST)
        self.assertEqual(result["metadata"]["model"], "development-template")


if __name__ == "__main__":
    unittest.main()
