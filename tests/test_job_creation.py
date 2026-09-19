from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from backend.db import Database
from backend.main import create_job, health
from backend.plan import finalize_scene_plan
from backend.planner import ScriptProviderUnavailable
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

ANTIGRAVITY_CONFIG = {
    "profile_id": "cloud_stickman",
    "video_type": "stickman",
    "script_provider": "antigravity",
    "media_provider": "procedural_stickman",
    "voice_provider": "piper",
    "editor": "remotion",
}


class JobCreationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "pipeline.sqlite3")
        self.db.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def test_health_reports_ready_preferred_antigravity_provider(self):
        status = {"ready": True, "provider": "antigravity", "model": "gemini-3.1-pro-high"}
        with patch("backend.main.antigravity_status", return_value=status), \
             patch("backend.main.script_provider_status") as local_status:
            result = health()

        self.assertEqual(result["script_generation"], status)
        local_status.assert_not_called()

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

    def test_antigravity_retry_creates_one_job_and_persists_actual_provider(self):
        payload = JobCreate(
            topic="Antigravity sicher wiederholen",
            duration_seconds=30,
            generation_id="75da97ce-02a5-4eb5-b313-b92cfbb8cbd1",
            production_config=ANTIGRAVITY_CONFIG,
        )
        script = {
            **SCRIPT,
            "metadata": {"provider": "antigravity", "model": "gemini-3.1-pro-high"},
        }
        with patch("backend.main.db", self.db), patch(
            "backend.main.generate_script", return_value=script
        ) as generate:
            first = create_job(payload)
            second = create_job(payload)

        expected_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"video-pipeline:antigravity:{payload.generation_id}"))
        self.assertEqual(first["id"], expected_id)
        self.assertEqual(second["id"], expected_id)
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(first["actual_script_provider"], "antigravity")

    def test_antigravity_failure_leaves_no_partial_job(self):
        payload = JobCreate(
            topic="Fehler ohne Teilauftrag",
            duration_seconds=30,
            generation_id="fb0b08bf-2689-49cb-8748-57951d63e2dc",
            production_config=ANTIGRAVITY_CONFIG,
        )
        with patch("backend.main.db", self.db), patch(
            "backend.main.generate_script",
            side_effect=ScriptProviderUnavailable("Antigravity ist nicht angemeldet."),
        ):
            with self.assertRaises(HTTPException) as raised:
                create_job(payload)

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(self.db.list_jobs(), [])


if __name__ == "__main__":
    unittest.main()
