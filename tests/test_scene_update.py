from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from backend.db import Database
from backend.main import update_scene
from backend.plan import finalize_scene_plan
from backend.schemas import SceneUpdate


class SceneUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "db.sqlite3")
        self.db.initialize()
        script = finalize_scene_plan({
            "title": "Gezielte Änderung",
            "description": "Zwei Szenen",
            "scenes": [
                {"scene_id": "scene-one", "narration": "Erster Sprechertext.", "visual": "Ein Wald im Morgenlicht."},
                {"scene_id": "scene-two", "narration": "Zweiter Sprechertext.", "visual": "Eine Stadt bei Nacht."},
            ],
        }, 30)
        self.job_id = self.db.create_job({
            "topic": "Szenen ändern", "language": "de", "duration_seconds": 30,
            "aspect_ratio": "16:9", "video_type": "explainer", "target_platform": "download",
        }, script)

    def tearDown(self):
        self.temp.cleanup()

    def test_only_selected_scene_changes_and_creates_new_version(self):
        payload = SceneUpdate(expected_version=1, narration="Verbesserter zweiter Sprechertext.")
        with patch("backend.main.db", self.db):
            updated = update_scene(self.job_id, "scene-two", payload)
        self.assertEqual(updated["script_version"], 2)
        self.assertEqual(updated["script"]["scenes"][0]["narration"], "Erster Sprechertext.")
        self.assertEqual(updated["script"]["scenes"][1]["narration"], "Verbesserter zweiter Sprechertext.")
        self.assertEqual(updated["script"]["scenes"][1]["scene_id"], "scene-two")
        self.assertEqual(updated["script"]["metadata"]["changed_scene_id"], "scene-two")

    def test_unchanged_scene_is_rejected(self):
        payload = SceneUpdate(expected_version=1, narration="Zweiter Sprechertext.")
        with patch("backend.main.db", self.db), self.assertRaises(HTTPException) as raised:
            update_scene(self.job_id, "scene-two", payload)
        self.assertEqual(raised.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
