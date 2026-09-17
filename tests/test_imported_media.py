from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from backend import main as main_module
from backend.config import settings as default_settings
from backend.db import Database
from backend.imported_media import ImportedMediaError, inspect_imported_video, save_stream, write_provenance_manifest


class ImportedMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_stream_is_bounded_and_partial_file_is_removed(self):
        target = self.root / "video.uploading"

        async def chunks():
            yield b"1234"
            yield b"5678"

        with self.assertRaisesRegex(ImportedMediaError, "größer"):
            asyncio.run(save_stream(chunks(), target, max_bytes=6))
        self.assertFalse(target.exists())

    def test_video_requires_audio_and_video_streams(self):
        target = self.root / "video.mp4"
        target.write_bytes(b"x" * 10_000)

        with self.assertRaisesRegex(ImportedMediaError, "Audiospur"):
            inspect_imported_video(
                target,
                probe=lambda _: {
                    "streams": [{"codec_type": "video", "codec_name": "h264"}],
                    "format": {"duration": "12.5", "size": "10000"},
                },
            )

    def test_manifest_records_source_hash_and_probe(self):
        target = self.root / "video.mp4"
        target.write_bytes(b"x" * 10_000)
        info = inspect_imported_video(
            target,
            probe=lambda _: {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "format": {"duration": "12.5", "size": "10000"},
            },
        )
        manifest_path = self.root / "external-media-manifest.json"
        manifest = write_provenance_manifest(
            manifest_path,
            media_path=target,
            source="notebooklm",
            original_filename="../Mein Überblick.mp4",
            script_version=2,
            script_hash="a" * 64,
            inspection=info,
        )

        self.assertEqual(manifest["source"], "notebooklm")
        self.assertEqual(manifest["original_filename"], "Mein Überblick.mp4")
        self.assertEqual(manifest["script_version"], 2)
        self.assertEqual(len(manifest["sha256"]), 64)
        self.assertEqual(json.loads(manifest_path.read_text(encoding="utf-8")), manifest)

    def test_unknown_source_is_rejected(self):
        target = self.root / "video.mp4"
        target.write_bytes(b"x" * 10_000)
        with self.assertRaisesRegex(ImportedMediaError, "Quelle"):
            write_provenance_manifest(
                self.root / "manifest.json",
                media_path=target,
                source="irgendein_scraper",
                original_filename="video.mp4",
                script_version=1,
                script_hash="a" * 64,
                inspection={"duration_seconds": 1, "streams": []},
            )

    def test_api_imports_into_existing_review_flow(self):
        isolated_settings = replace(default_settings, data_dir=self.root / "data")
        database = Database(isolated_settings.database_path)
        database.initialize()
        script = {
            "title": "Externes Video",
            "description": "Test",
            "scenes": [{"narration": "Hallo.", "visual": "Ein Bild.", "action": "intro", "accent": "#ff6b4a"}],
        }
        job_id = database.create_job(
            {
                "topic": "Import",
                "language": "de",
                "duration_seconds": 30,
                "aspect_ratio": "16:9",
                "video_type": "generated",
                "target_platform": "download",
            },
            script,
        )
        script_hash = database.get_job(job_id)["script"]["content_hash"]
        database.approve_script(job_id, 1, script_hash)
        inspection = {
            "duration_seconds": 12.5,
            "size_bytes": 10_000,
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }

        class RequestBody:
            headers = {"content-type": "video/mp4", "content-length": "10000"}

            async def stream(self):
                yield b"x" * 10_000

        with (
            patch.object(main_module, "settings", isolated_settings),
            patch.object(main_module, "db", database),
            patch.object(main_module, "inspect_imported_video", return_value=inspection),
        ):
            response = asyncio.run(
                main_module.import_external_video(
                    job_id,
                    RequestBody(),  # type: ignore[arg-type]
                    source="gemini_app",
                    expected_version=1,
                    expected_hash=script_hash,
                    filename="Gemini Ergebnis.mp4",
                )
            )

        self.assertEqual(response["status"], "video_review")
        manifests = list((isolated_settings.jobs_dir / job_id / "v1").glob("*.manifest.json"))
        self.assertEqual(len(manifests), 1)
        self.assertEqual(json.loads(manifests[0].read_text(encoding="utf-8"))["source"], "gemini_app")


if __name__ == "__main__":
    unittest.main()
