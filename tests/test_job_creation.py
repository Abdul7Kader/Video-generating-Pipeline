from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from backend.db import Database
from backend.main import create_job
from backend.plan import finalize_scene_plan
from backend.schemas import JobCreate


SCRIPT = finalize_scene_plan(
    {
        "title": "Ein sicherer Entwurf",
        "description": "Test für wiederholte Anfragen",
        "scenes": [
            {
                "narration": "Dieser Entwurf wird nur einmal erzeugt.",
                "visual": "Eine einzelne Karte erscheint auf einer ruhigen Fläche.",
            }
        ],
    },
    30,
)


class JobCreationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "pipeline.sqlite3")
        self.db.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def test_qwen_retry_with_same_generation_id_returns_existing_job(self):
        payload = JobCreate(
            topic="Retry sicher testen",
            duration_seconds=30,
            script_generator="qwen",
            generation_id="7b0d53d8-d8bc-4cee-a1e5-10fc90d65c69",
        )
        with patch("backend.main.db", self.db), patch(
            "backend.main.generate_script", return_value=SCRIPT
        ) as generate:
            first = create_job(payload)
            second = create_job(payload)

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(generate.call_count, 1)

    def test_browser_assigns_retry_id_to_every_script_generator(self):
        script = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("script-generation", script)
        self.assertNotIn("if(b.script_generator==='gemini_cli')", script)

    def test_gemini_retry_keeps_the_existing_deterministic_job_id(self):
        generation_id = "b01eb8e6-160c-4489-a495-978905ac5396"
        payload = JobCreate(
            topic="Bestehenden Gemini-Auftrag fortsetzen",
            duration_seconds=30,
            script_generator="gemini_cli",
            generation_id=generation_id,
        )
        job_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"video-pipeline:gemini-cli:{generation_id}"))
        self.db.create_job(payload.model_dump(), SCRIPT, job_id=job_id)

        with patch("backend.main.db", self.db):
            resumed = create_job(payload)

        self.assertEqual(resumed["id"], job_id)


if __name__ == "__main__":
    unittest.main()
