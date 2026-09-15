from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.plan import canonical_script_hash, file_sha256, finalize_scene_plan


class PlanTests(unittest.TestCase):
    def test_plan_gets_unique_ids_sources_and_exact_duration(self):
        script = {
            "title": "Test",
            "description": "Plan",
            "scenes": [
                {"narration": "Kurzer Einstieg", "visual": "Moor", "visual_type": "generated_image", "duration_seconds": 3},
                {"narration": "Längere Erklärung mit mehreren Worten", "visual": "Diagramm", "visual_type": "motion_graphics", "duration_seconds": 7},
            ],
        }
        result = finalize_scene_plan(script, 30)
        ids = [scene["scene_id"] for scene in result["scenes"]]
        self.assertEqual(len(set(ids)), 2)
        self.assertAlmostEqual(sum(scene["duration_seconds"] for scene in result["scenes"]), 30)
        self.assertEqual(result["scenes"][0]["source_strategy"], "generate")
        self.assertEqual(result["scenes"][1]["source_strategy"], "procedural")

    def test_revision_preserves_existing_scene_ids_by_position(self):
        previous = {
            "scenes": [
                {"scene_id": "scene-first", "narration": "Alt eins"},
                {"scene_id": "scene-second", "narration": "Alt zwei"},
            ]
        }
        revised = {
            "title": "Neu",
            "description": "Neu",
            "scenes": [
                {"narration": "Neu eins", "visual": "A"},
                {"narration": "Neu zwei", "visual": "B"},
            ],
        }
        result = finalize_scene_plan(revised, 20, previous)
        self.assertEqual([scene["scene_id"] for scene in result["scenes"]], ["scene-first", "scene-second"])

    def test_hash_is_canonical_and_changes_with_plan(self):
        scenes = [{"scene_id": "scene-one", "narration": "Text", "visual": "Bild"}]
        first = canonical_script_hash("Titel", "Beschreibung", scenes)
        same = canonical_script_hash("Titel", "Beschreibung", [{"visual": "Bild", "narration": "Text", "scene_id": "scene-one"}])
        changed = canonical_script_hash("Titel", "Beschreibung", [{**scenes[0], "visual": "Anderes Bild"}])
        self.assertEqual(first, same)
        self.assertNotEqual(first, changed)

    def test_file_hash_uses_file_content(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "video.mp4"
            path.write_bytes(b"video-version-one")
            first = file_sha256(path)
            path.write_bytes(b"video-version-two")
            self.assertNotEqual(first, file_sha256(path))


if __name__ == "__main__":
    unittest.main()
