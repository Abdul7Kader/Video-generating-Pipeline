from __future__ import annotations

import tempfile
import unittest
import asyncio
import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from backend import main as main_module
from backend.config import settings as default_settings
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
        self.script_hash = self.db.get_job(self.job_id)["script"]["content_hash"]

    def tearDown(self):
        self.temp.cleanup()

    def test_desktop_interrupted_render_keeps_approval_without_automatic_restart(self):
        self.db.approve_script(self.job_id, 1, self.script_hash)
        self.db.queue_render(self.job_id, 1, self.script_hash)
        self.db.claim_render()
        self.db.recover_interrupted(resume_rendering=False)
        job = self.db.get_job(self.job_id)
        self.assertEqual(job['status'], 'render_failed')
        self.assertEqual(job['approved_script_hash'], self.script_hash)
        self.assertIsNone(self.db.claim_render())
        self.db.queue_render(self.job_id, 1, self.script_hash)
        self.assertIsNotNone(self.db.claim_render())

    def test_edit_invalidates_every_approval(self):
        self.db.approve_script(self.job_id, 1, self.script_hash)
        self.db.queue_render(self.job_id, 1, self.script_hash)
        self.assertEqual(self.db.claim_render()["status"], "rendering")
        self.db.finish_render(self.job_id, 1, f"{self.job_id}/v1/video.mp4", "a" * 64, "piper")
        self.db.approve_video(self.job_id, 1, "a" * 64, False)

        changed = {**SCRIPT, "title": "Neue Fassung"}
        job = self.db.update_script(self.job_id, 1, changed)
        self.assertEqual(job["script_version"], 2)
        self.assertEqual(job["status"], "script_review")
        self.assertIsNone(job["approved_script_version"])
        self.assertIsNone(job["approved_render_version"])
        self.assertIsNone(job["output_path"])
        self.assertIsNone(job["approved_script_hash"])
        self.assertIsNone(job["output_sha256"])

    def test_only_current_approved_script_can_render(self):
        with self.assertRaises(ValueError):
            self.db.queue_render(self.job_id, 1, self.script_hash)
        self.db.approve_script(self.job_id, 1, self.script_hash)
        first = self.db.queue_render(self.job_id, 1, self.script_hash)
        second = self.db.queue_render(self.job_id, 1, self.script_hash)
        self.assertEqual(first["status"], "render_queued")
        self.assertEqual(second["status"], "render_queued")
        self.assertIsNotNone(self.db.claim_render())
        self.assertIsNone(self.db.claim_render())

    def test_interrupted_publish_is_not_retried(self):
        self.db.approve_script(self.job_id, 1, self.script_hash)
        self.db.queue_render(self.job_id, 1, self.script_hash)
        self.db.claim_render()
        self.db.finish_render(self.job_id, 1, f"{self.job_id}/v1/video.mp4", "b" * 64, "piper")
        with self.db.connect() as conn:
            conn.execute("UPDATE jobs SET target_platform='youtube' WHERE id=?", (self.job_id,))
            conn.commit()
        self.db.approve_video(self.job_id, 1, "b" * 64, True)
        self.assertEqual(self.db.claim_publish()["status"], "publishing")
        self.db.recover_interrupted()
        self.assertEqual(self.db.get_job(self.job_id)["status"], "publish_failed")
        self.assertIsNone(self.db.claim_publish())

    def test_approval_requires_exact_script_hash(self):
        with self.assertRaisesRegex(ValueError, "hash_conflict"):
            self.db.approve_script(self.job_id, 1, "0" * 64)
        approved = self.db.approve_script(self.job_id, 1, self.script_hash)
        self.assertEqual(approved["approved_script_hash"], self.script_hash)
        self.assertEqual(approved["events"][0]["metadata"]["script_hash"], self.script_hash)

    def test_modified_stored_plan_fails_integrity_check(self):
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE script_versions SET title='Manipuliert' WHERE job_id=? AND version=1",
                (self.job_id,),
            )
            conn.commit()
        self.assertFalse(self.db.get_job(self.job_id)["script"]["integrity_verified"])
        with self.assertRaisesRegex(ValueError, "script_integrity_error"):
            self.db.approve_script(self.job_id, 1, self.script_hash)

    def test_video_approval_requires_exact_output_hash(self):
        self.db.approve_script(self.job_id, 1, self.script_hash)
        self.db.queue_render(self.job_id, 1, self.script_hash)
        self.db.claim_render()
        output_hash = "c" * 64
        self.db.finish_render(self.job_id, 1, f"{self.job_id}/v1/video.mp4", output_hash, "piper")
        with self.assertRaisesRegex(ValueError, "video_not_ready"):
            self.db.approve_video(self.job_id, 1, "d" * 64, False)
        approved = self.db.approve_video(self.job_id, 1, output_hash, False)
        self.assertEqual(approved["approved_output_sha256"], output_hash)

    def test_external_video_requires_current_approved_script(self):
        with self.assertRaisesRegex(ValueError, "script_not_approved"):
            self.db.attach_imported_video(
                self.job_id, 1, self.script_hash, f"{self.job_id}/v1/imported-video.mp4", "e" * 64, "notebooklm"
            )

        self.db.approve_script(self.job_id, 1, self.script_hash)
        imported = self.db.attach_imported_video(
            self.job_id, 1, self.script_hash, f"{self.job_id}/v1/imported-video.mp4", "e" * 64, "notebooklm"
        )
        self.assertEqual(imported["status"], "video_review")
        self.assertEqual(imported["render_version"], 1)
        self.assertEqual(imported["render_script_hash"], self.script_hash)
        self.assertEqual(imported["output_sha256"], "e" * 64)
        self.assertEqual(imported["tts_mode"], "import:notebooklm")
        self.assertEqual(imported["events"][0]["event_type"], "external_video_imported")
        self.assertEqual(imported["events"][0]["metadata"]["source"], "notebooklm")

    def test_multiple_publication_targets_have_independent_status(self):
        multi_values = {
            **VALUES,
            "target_platform": "youtube",
            "target_platforms": ["youtube", "mastodon", "tiktok", "spotify_podcast", "download"],
        }
        job_id = self.db.create_job(multi_values, SCRIPT)
        script_hash = self.db.get_job(job_id)["script"]["content_hash"]
        self.db.approve_script(job_id, 1, script_hash)
        self.db.queue_render(job_id, 1, script_hash)
        self.db.claim_render()
        output_hash = "f" * 64
        self.db.finish_render(job_id, 1, f"{job_id}/v1/video.mp4", output_hash, "piper")

        approved = self.db.approve_video(job_id, 1, output_hash, {"youtube", "mastodon"})
        statuses = {target["platform"]: target["status"] for target in approved["publication_targets"]}
        self.assertEqual(statuses["youtube"], "queued")
        self.assertEqual(statuses["mastodon"], "queued")
        self.assertEqual(statuses["tiktok"], "setup_required")
        self.assertEqual(statuses["spotify_podcast"], "setup_required")
        self.assertEqual(statuses["download"], "ready")

        first = self.db.claim_publication()
        second = self.db.claim_publication()
        self.assertEqual({first["publication_target"]["platform"], second["publication_target"]["platform"]}, {"youtube", "mastodon"})
        youtube = first if first["publication_target"]["platform"] == "youtube" else second
        mastodon = second if youtube is first else first
        self.db.finish_publication(job_id, "youtube", "youtube-id", "https://youtube.example/watch/youtube-id")
        self.db.fail_publication(job_id, "mastodon", "Netzwerkstatus unbekannt")
        result = self.db.get_job(job_id)
        statuses = {target["platform"]: target["status"] for target in result["publication_targets"]}
        self.assertEqual(statuses["youtube"], "published")
        self.assertEqual(statuses["mastodon"], "failed")
        self.assertEqual(result["status"], "publish_failed")
        self.assertIsNone(self.db.claim_publication())

    def test_interrupted_target_is_unknown_and_not_retried(self):
        multi_values = {**VALUES, "target_platform": "mastodon", "target_platforms": ["mastodon"]}
        job_id = self.db.create_job(multi_values, SCRIPT)
        script_hash = self.db.get_job(job_id)["script"]["content_hash"]
        self.db.approve_script(job_id, 1, script_hash)
        self.db.queue_render(job_id, 1, script_hash)
        self.db.claim_render()
        self.db.finish_render(job_id, 1, f"{job_id}/v1/video.mp4", "9" * 64, "piper")
        self.db.approve_video(job_id, 1, "9" * 64, {"mastodon"})
        self.assertEqual(self.db.claim_publication()["publication_target"]["status"], "publishing")
        self.db.recover_interrupted()
        target = self.db.get_job(job_id)["publication_targets"][0]
        self.assertEqual(target["status"], "unknown")
        self.assertIsNone(self.db.claim_publication())

    def test_formats_are_stored_without_early_publication_targets(self):
        values = {**VALUES, "aspect_ratios": ["16:9", "9:16"], "target_platforms": []}
        job_id = self.db.create_job(values, SCRIPT)
        job = self.db.get_job(job_id)
        self.assertEqual(job["aspect_ratios"], ["16:9", "9:16"])
        self.assertEqual(job["target_platforms"], [])
        self.db.initialize()
        self.assertEqual(self.db.get_job(job_id)["target_platforms"], [])

    def test_legacy_database_backfills_output_format_and_target_once(self):
        old_path = Path(self.temp.name) / "legacy.sqlite3"
        with closing(sqlite3.connect(old_path)) as conn:
            conn.execute(
                """CREATE TABLE jobs (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                topic TEXT NOT NULL, language TEXT NOT NULL, duration_seconds INTEGER NOT NULL,
                aspect_ratio TEXT NOT NULL, video_type TEXT NOT NULL,
                production_config_json TEXT NOT NULL, target_platform TEXT NOT NULL,
                status TEXT NOT NULL, script_version INTEGER NOT NULL,
                actual_script_provider TEXT, script_fallback_json TEXT NOT NULL,
                output_path TEXT, output_sha256 TEXT)"""
            )
            conn.execute(
                """INSERT INTO jobs VALUES
                ('legacy','2026-01-01','2026-01-01','Alt','de',30,'16:9','stickman','{}',
                'youtube','video_review',1,NULL,'{}','legacy/v1/video.mp4',?)""",
                ("a" * 64,),
            )
            conn.commit()
        # The oldest local databases predate stored output digests.
        with closing(sqlite3.connect(old_path)) as conn:
            conn.execute("ALTER TABLE jobs DROP COLUMN output_sha256")
            conn.commit()
        legacy = Database(old_path)
        legacy.initialize()
        legacy.initialize()
        with legacy.connect() as conn:
            row = conn.execute("SELECT aspect_ratios_json,output_variants_json FROM jobs WHERE id='legacy'").fetchone()
            targets = conn.execute("SELECT platform FROM publication_targets WHERE job_id='legacy'").fetchall()
        self.assertEqual(json.loads(row["aspect_ratios_json"]), ["16:9"])
        self.assertIsNone(json.loads(row["output_variants_json"])["16:9"]["sha256"])
        self.assertEqual([item["platform"] for item in targets], ["youtube"])

    def test_late_platform_selection_uses_matching_rendered_format(self):
        values = {**VALUES, "aspect_ratio": "16:9", "aspect_ratios": ["16:9", "9:16"], "target_platforms": []}
        job_id = self.db.create_job(values, SCRIPT)
        digest = self.db.get_job(job_id)["script"]["content_hash"]
        self.db.approve_script(job_id, 1, digest)
        self.db.queue_render(job_id, 1, digest)
        self.db.claim_render()
        outputs = {
            "16:9": {"path": f"{job_id}/v1/video.mp4", "sha256": "1" * 64},
            "9:16": {"path": f"{job_id}/v1/formats/9x16/video.mp4", "sha256": "2" * 64},
        }
        self.db.finish_render_variants(job_id, 1, outputs, "piper")
        job = self.db.get_job(job_id)
        self.assertEqual(job["render_outputs"], outputs)
        approved = self.db.approve_video(job_id, 1, "1" * 64, {"tiktok"}, ["linkedin", "tiktok"])
        targets = {item["platform"]: item for item in approved["publication_targets"]}
        self.assertEqual(targets["linkedin"]["aspect_ratio"], "16:9")
        self.assertEqual(targets["tiktok"]["aspect_ratio"], "9:16")
        self.assertEqual(targets["tiktok"]["approved_output_sha256"], "2" * 64)
        self.assertEqual(approved["target_platforms"], ["linkedin", "tiktok"])
        claimed = self.db.claim_publication()
        self.assertEqual(claimed["publication_output"], outputs["9:16"])

    def test_render_worker_creates_each_selected_format(self):
        values = {**VALUES, "aspect_ratios": ["9:16", "16:9"], "target_platforms": []}
        job_id = self.db.create_job(values, SCRIPT)
        digest = self.db.get_job(job_id)["script"]["content_hash"]
        self.db.approve_script(job_id, 1, digest)
        self.db.queue_render(job_id, 1, digest)
        isolated = replace(default_settings, data_dir=Path(self.temp.name))
        rendered = []

        def fake_render(job, *, job_dir_override=None):
            rendered.append(job["aspect_ratio"])
            folder = job_dir_override or isolated.jobs_dir / job["id"] / "v1"
            folder.mkdir(parents=True, exist_ok=True)
            output = folder / "video.mp4"
            output.write_bytes(("video:" + job["aspect_ratio"]).encode())
            return str(output), "piper"

        async def run():
            stop = asyncio.Event()
            original = self.db.finish_render_variants

            def finish(*args):
                original(*args)
                stop.set()

            with patch.object(main_module, "settings", isolated), patch.object(main_module, "db", self.db), \
                 patch("backend.operations.Operation.run", side_effect=lambda kind,payload: fake_render(payload["job"],job_dir_override=Path(payload["directory"]) if payload["directory"] else None)), \
                 patch.object(main_module, "unload_script_model"), \
                 patch.object(self.db, "finish_render_variants", side_effect=finish):
                await asyncio.wait_for(main_module.render_worker(stop), timeout=5)

        asyncio.run(run())
        self.assertEqual(rendered, ["9:16", "16:9"])
        result = self.db.get_job(job_id)
        self.assertEqual(result["status"], "video_review")
        self.assertEqual(set(result["render_outputs"]), {"9:16", "16:9"})

    def test_late_platform_selection_rejects_missing_format(self):
        values = {**VALUES, "target_platforms": []}
        job_id = self.db.create_job(values, SCRIPT)
        digest = self.db.get_job(job_id)["script"]["content_hash"]
        self.db.approve_script(job_id, 1, digest)
        self.db.queue_render(job_id, 1, digest)
        self.db.claim_render()
        self.db.finish_render(job_id, 1, f"{job_id}/v1/video.mp4", "3" * 64, "piper")
        with self.assertRaisesRegex(ValueError, "format_unavailable"):
            self.db.approve_video(job_id, 1, "3" * 64, set(), ["linkedin"])
        self.assertEqual(self.db.get_job(job_id)["target_platforms"], [])

    def test_late_target_selection_cannot_change_after_approval(self):
        values = {**VALUES, "target_platforms": []}
        job_id = self.db.create_job(values, SCRIPT)
        digest = self.db.get_job(job_id)["script"]["content_hash"]
        self.db.approve_script(job_id, 1, digest)
        self.db.queue_render(job_id, 1, digest)
        self.db.claim_render()
        self.db.finish_render(job_id, 1, f"{job_id}/v1/video.mp4", "4" * 64, "piper")
        first = self.db.approve_video(job_id, 1, "4" * 64, set(), ["download"])
        again = self.db.approve_video(job_id, 1, "4" * 64, set(), ["download"])
        self.assertEqual(first["target_platforms"], again["target_platforms"])
        with self.assertRaisesRegex(ValueError, "publication_already_approved"):
            self.db.approve_video(job_id, 1, "4" * 64, set(), ["tiktok"])


if __name__ == "__main__":
    unittest.main()
