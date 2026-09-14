from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.db import Database


SCRIPT = {
    "title": "Testvideo",
    "description": "Ein Test",
    "scenes": [{"narration": "Hallo Welt.", "visual": "Eine Figur erscheint.", "action": "intro", "accent": "#ff6b4a"}],
}
VALUES = {
    "topic": "Workflow testen",
    "language": "de",
    "duration_seconds": 30,
    "aspect_ratio": "9:16",
    "video_type": "stickman",
    "target_platform": "download",
}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "db.sqlite3")
        self.db.initialize()
        self.job_id = self.db.create_job(VALUES, SCRIPT)

    def tearDown(self):
        self.temp.cleanup()

    def test_edit_invalidates_every_approval(self):
        self.db.approve_script(self.job_id, 1)
        self.db.queue_render(self.job_id, 1)
        self.assertEqual(self.db.claim_render()["status"], "rendering")
        self.db.finish_render(self.job_id, 1, f"{self.job_id}/v1/video.mp4", "piper")
        self.db.approve_video(self.job_id, 1, False)

        changed = {**SCRIPT, "title": "Neue Fassung"}
        job = self.db.update_script(self.job_id, 1, changed)
        self.assertEqual(job["script_version"], 2)
        self.assertEqual(job["status"], "script_review")
        self.assertIsNone(job["approved_script_version"])
        self.assertIsNone(job["approved_render_version"])
        self.assertIsNone(job["output_path"])

    def test_only_current_approved_script_can_render(self):
        with self.assertRaises(ValueError):
            self.db.queue_render(self.job_id, 1)
        self.db.approve_script(self.job_id, 1)
        first = self.db.queue_render(self.job_id, 1)
        second = self.db.queue_render(self.job_id, 1)
        self.assertEqual(first["status"], "render_queued")
        self.assertEqual(second["status"], "render_queued")
        self.assertIsNotNone(self.db.claim_render())
        self.assertIsNone(self.db.claim_render())

    def test_interrupted_publish_is_not_retried(self):
        self.db.approve_script(self.job_id, 1)
        self.db.queue_render(self.job_id, 1)
        self.db.claim_render()
        self.db.finish_render(self.job_id, 1, f"{self.job_id}/v1/video.mp4", "piper")
        with self.db.connect() as conn:
            conn.execute("UPDATE jobs SET target_platform='youtube' WHERE id=?", (self.job_id,))
            conn.commit()
        self.db.approve_video(self.job_id, 1, True)
        self.assertEqual(self.db.claim_publish()["status"], "publishing")
        self.db.recover_interrupted()
        self.assertEqual(self.db.get_job(self.job_id)["status"], "publish_failed")
        self.assertIsNone(self.db.claim_publish())


if __name__ == "__main__":
    unittest.main()
