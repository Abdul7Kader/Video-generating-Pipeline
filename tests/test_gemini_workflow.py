from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.gemini_workflow import GeminiScriptWorkflow


REQUEST = {
    "topic": "Warum Schlaf das Lernen verbessert",
    "language": "de",
    "duration_seconds": 30,
    "aspect_ratio": "9:16",
    "video_type": "explainer",
    "target_platform": "youtube",
    "target_platforms": ["youtube"],
}

OUTPUTS = {
    "briefing": {
        "topic": REQUEST["topic"],
        "objective": "Den Zusammenhang verständlich erklären.",
        "audience": "Erwachsene ohne Vorwissen",
        "key_points": ["Gedächtniskonsolidierung", "Regelmäßiger Schlaf"],
        "fact_risks": ["Keine exakten Wirkungszahlen ohne Quelle"],
    },
    "outline": {
        "hook": "Was passiert nachts mit neuem Wissen?",
        "sections": [
            {"heading": "Einordnung", "purpose": "Mechanismus erklären", "key_points": ["Konsolidierung"]},
            {"heading": "Fazit", "purpose": "Nutzen zusammenfassen", "key_points": ["Regelmäßigkeit"]},
        ],
        "conclusion": "Schlaf ist Teil des Lernprozesses.",
    },
    "narration": {
        "title": "Lernen im Schlaf",
        "description": "Ein kurzer Erklärfilm.",
        "segments": [
            {"segment_id": "intro", "text": "Nach dem Lernen arbeitet dein Gehirn weiter."},
            {"segment_id": "main", "text": "Im Schlaf werden neue Erinnerungen stabilisiert."},
            {"segment_id": "end", "text": "Darum gehört regelmäßiger Schlaf zum Lernen."},
        ],
    },
    "scene_plan": {
        "title": "Lernen im Schlaf",
        "description": "Ein kurzer Erklärfilm.",
        "audience": "Erwachsene ohne Vorwissen",
        "tone": "ruhig und klar",
        "fact_check_notes": ["Allgemeine Aussage vor Veröffentlichung redaktionell prüfen."],
        "scenes": [
            {
                "scene_id": "scene-intro",
                "narration": "Nach dem Lernen arbeitet dein Gehirn weiter.",
                "visual": "Eine Person legt nach dem Lernen ein Buch beiseite.",
                "visual_type": "motion_graphics",
                "asset_prompt": "person closes study book at night",
                "camera": "Langsame Nahfahrt",
                "duration_seconds": 10,
            },
            {
                "scene_id": "scene-main",
                "narration": "Im Schlaf werden neue Erinnerungen stabilisiert.",
                "visual": "Leuchtende Verbindungen ordnen sich im Gehirn.",
                "visual_type": "motion_graphics",
                "asset_prompt": "abstract memory connections organizing during sleep",
                "camera": "Sanfter Schwenk",
                "duration_seconds": 10,
            },
            {
                "scene_id": "scene-end",
                "narration": "Darum gehört regelmäßiger Schlaf zum Lernen.",
                "visual": "Die Person beginnt morgens konzentriert zu lernen.",
                "visual_type": "motion_graphics",
                "asset_prompt": "focused morning study routine",
                "camera": "Ruhige Totale",
                "duration_seconds": 10,
            },
        ],
    },
}
OUTPUTS["quality_review"] = {
    "approved": True,
    "issues": [{"severity": "info", "category": "facts", "message": "Redaktionelle Quellenprüfung bleibt erforderlich."}],
    "final_script": OUTPUTS["scene_plan"],
}


class FakePool:
    def __init__(self, outputs, fail_on_call=None, profile="primary"):
        self.outputs = list(outputs)
        self.fail_on_call = fail_on_call
        self.profile = profile
        self.inputs = []

    def generate(self, prompt):
        self.inputs.append(prompt)
        if self.fail_on_call == len(self.inputs):
            raise RuntimeError("simulierter Profilabbruch")
        return SimpleNamespace(
            response=json.dumps(self.outputs.pop(0), ensure_ascii=False),
            profile=self.profile,
            model="gemini-test",
            stats={},
        )


class GeminiWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "pipeline.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def test_restart_resumes_at_first_incomplete_step_and_never_duplicates_completed_steps(self):
        first = FakePool([OUTPUTS["briefing"]], fail_on_call=2)
        workflow = GeminiScriptWorkflow(self.path, first)
        with self.assertRaisesRegex(RuntimeError, "Profilabbruch"):
            workflow.run("72a0ebdf-f8e0-4c74-9dfb-01be7c9c7541", REQUEST)
        self.assertEqual(len(first.inputs), 2)
        self.assertEqual(workflow.status("72a0ebdf-f8e0-4c74-9dfb-01be7c9c7541")["steps"][0]["status"], "completed")

        second = FakePool([OUTPUTS[name] for name in ("outline", "narration", "scene_plan", "quality_review")], profile="secondary")
        resumed = GeminiScriptWorkflow(self.path, second)
        script = resumed.run("72a0ebdf-f8e0-4c74-9dfb-01be7c9c7541", REQUEST)
        self.assertEqual(len(second.inputs), 4)
        self.assertEqual(script["metadata"]["profile"], "secondary")
        self.assertEqual(script["metadata"]["quality_issues"][0]["category"], "facts")
        self.assertEqual([step["status"] for step in resumed.status("72a0ebdf-f8e0-4c74-9dfb-01be7c9c7541")["steps"]], ["completed"] * 5)

        no_calls = FakePool([])
        identical = GeminiScriptWorkflow(self.path, no_calls).run(
            "72a0ebdf-f8e0-4c74-9dfb-01be7c9c7541", REQUEST
        )
        self.assertEqual(no_calls.inputs, [])
        self.assertEqual(identical["title"], script["title"])

    def test_request_id_cannot_be_reused_for_different_input(self):
        workflow = GeminiScriptWorkflow(self.path, FakePool([OUTPUTS[name] for name in OUTPUTS]))
        workflow.run("05ec21e5-6cdd-4323-b6b4-7312bfc60b90", REQUEST)
        with self.assertRaisesRegex(ValueError, "anderen Auftrag"):
            workflow.run("05ec21e5-6cdd-4323-b6b4-7312bfc60b90", {**REQUEST, "topic": "Ein anderes Thema"})

    def test_invalid_step_output_is_not_marked_completed(self):
        workflow = GeminiScriptWorkflow(self.path, FakePool([{"topic": "unvollständig"}]))
        with self.assertRaisesRegex(ValueError, "briefing"):
            workflow.run("79ff7633-d15f-48ee-9ea4-af3d8d3bd86d", REQUEST)
        step = workflow.status("79ff7633-d15f-48ee-9ea4-af3d8d3bd86d")["steps"][0]
        self.assertEqual(step["status"], "failed")
        self.assertIsNone(step["output_hash"])


if __name__ == "__main__":
    unittest.main()
