from __future__ import annotations

import copy
import tempfile
import unittest
import wave
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from backend import main, rendering
from backend.db import Database
from backend.plan import finalize_scene_plan
from backend.planner import _prompt
from backend.production import normalize_production_config, legacy_production_config
from backend.schemas import JobCreate, ProductionConfig, ProductionConfigUpdate, ScriptRevision, VoicePreview
from backend.voices import validate_voice_language


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = replace(main.settings, data_dir=Path(self.temp.name))
        self.db = Database(self.settings.database_path)
        self.db.initialize()
        self.script = finalize_scene_plan({"title": "Mila liest", "description": "Ein konkretes Beispiel", "scenes": [
            {"scene_id": "scene-one", "narration": "Mila öffnet ein Buch.", "visual": "Mila mit einem Buch.", "visual_type": "stickman", "stickman": {"characters": [{"id": "mila"}], "props": [{"kind": "book"}]}, "duration_seconds": 5},
            {"scene_id": "scene-two", "narration": "Sie zeigt Ben ihre Idee.", "visual": "Mila zeigt auf eine Idee.", "visual_type": "stickman", "stickman": {"characters": [{"id": "mila"}], "props": [{"kind": "lightbulb"}]}, "duration_seconds": 5},
        ]}, 30)
        self.job_id = self.db.create_job({"topic": "Mila liest ein Buch", "language": "de", "duration_seconds": 30, "aspect_ratio": "16:9", "video_type": "stickman", "target_platform": "download"}, self.script)

    def tearDown(self):
        self.temp.cleanup()

    def test_scene_revision_preserves_other_scenes_even_when_model_changes_them(self):
        original = self.db.get_job(self.job_id)
        generated = copy.deepcopy(original["script"])
        generated["title"] = "Unerwünschter neuer Titel"
        generated["scenes"][0]["narration"] = "Unerwünschte Änderung."
        generated["scenes"][1]["narration"] = "Mila erklärt Ben ihren Einfall."
        generated["scenes"][1]["duration_seconds"] = 29
        with patch("backend.main.db", self.db), patch("backend.main.generate_script", return_value=generated) as generate:
            result = main.revise_script(self.job_id, ScriptRevision(expected_version=1, scene_id="scene-two", instructions="Zeige die Folge der Handlung."))
        self.assertIn("Revise ONLY scene_id=scene-two", generate.call_args.kwargs["instructions"])
        self.assertEqual(result["script"]["scenes"][0], original["script"]["scenes"][0])
        self.assertEqual(result["script"]["title"], original["script"]["title"])
        self.assertEqual(result["script"]["scenes"][1]["duration_seconds"], original["script"]["scenes"][1]["duration_seconds"])
        self.assertEqual(result["script_version"], 2)

    def test_stale_or_missing_scene_is_rejected_before_generation(self):
        with patch("backend.main.db", self.db), patch("backend.main.generate_script") as generate:
            for version, identifier, status in [(2, "scene-two", 409), (1, "scene-missing", 404)]:
                with self.assertRaises(HTTPException) as raised:
                    main.revise_script(self.job_id, ScriptRevision(expected_version=version, scene_id=identifier, instructions="Verbessern"))
                self.assertEqual(raised.exception.status_code, status)
            generate.assert_not_called()

    def test_missing_selected_id_in_response_never_saves(self):
        generated = copy.deepcopy(self.script)
        generated["scenes"][1]["scene_id"] = "scene-replacement"
        with patch("backend.main.db", self.db), patch("backend.main.generate_script", return_value=generated), self.assertRaises(HTTPException) as raised:
            main.revise_script(self.job_id, ScriptRevision(expected_version=1, scene_id="scene-two", instructions="Verbessern"))
        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(self.db.get_job(self.job_id)["script_version"], 1)

    def test_voice_change_is_versioned_and_invalidates_approval(self):
        current = self.db.get_job(self.job_id)
        self.db.approve_script(self.job_id, 1, current["script"]["content_hash"])
        config = ProductionConfig(**{**current["production_config"], "voice_id": "kerstin", "voice_speed": 1.1})
        with patch("backend.main.db", self.db):
            changed = main.update_production_config(self.job_id, ProductionConfigUpdate(expected_version=1, production_config=config))
        self.assertEqual(changed["production_config"]["voice_id"], "kerstin")
        self.assertEqual(changed["production_config"]["voice_speed"], 1.1)
        self.assertEqual(changed["script_version"], 2)
        self.assertIsNone(changed["approved_script_version"])
        self.assertEqual(changed["script"]["production_config"], changed["production_config"])

    def test_voice_validation_blocks_paths_language_mismatch_and_nonfinite_speed(self):
        for identifier, speed in [("../outside", 1), ("thorsten", float("nan")), ("thorsten", 10)]:
            with self.assertRaises(ValidationError):
                VoicePreview(voice_id=identifier, text="Ein Hörvergleich", speed=speed)
        with self.assertRaises(ValueError):
            validate_voice_language({"voice_id": "ljspeech", "voice_provider": "piper"}, "de")
        legacy = legacy_production_config("stickman")
        self.assertEqual(normalize_production_config({**legacy, "voice_id": None, "voice_speed": 1}, legacy_video_type="stickman", legacy_script_provider="qwen"), legacy)

    def test_audio_cache_separates_voice_and_speed(self):
        scene = {"narration": "Derselbe Text."}
        fingerprints = {rendering._voice_fingerprint(scene, "de", "piper", continuous=True, voice_id=voice, speed=speed)
                        for voice, speed in [("thorsten", 1), ("thorsten_amused", 1), ("kerstin", 1), ("thorsten", 1.1)]}
        self.assertEqual(len(fingerprints), 4)

    def test_script_budget_uses_selected_voice_and_tempo(self):
        config = ProductionConfig(voice_id="thorsten_amused", voice_speed=1.1)
        prompt = _prompt(JobCreate(topic="Mila liest ein Buch", duration_seconds=60, production_config=config))
        self.assertIn("Approximate narration target: 198 words", prompt)

    def test_wrong_language_voice_never_changes_job(self):
        with patch("backend.main.db", self.db), self.assertRaises(HTTPException) as raised:
            main.update_production_config(self.job_id, ProductionConfigUpdate(expected_version=1, production_config=ProductionConfig(voice_id="ljspeech")))
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(self.db.get_job(self.job_id)["script_version"], 1)

    def test_preview_caches_identical_text_and_restricts_media_ids(self):
        def synthesize(text, path, language, **options):
            with wave.open(str(path), "wb") as wav:
                wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                wav.writeframes(b'\x00\x10' * 16000)
            return "piper", 1
        with patch("backend.main.settings", self.settings), patch("backend.main.synthesize", side_effect=synthesize) as synth:
            request = VoicePreview(voice_id="kerstin", text="Mila liest ein Buch.", speed=1.1)
            first = main.create_voice_preview(request)
            second=main.create_voice_preview(request)
            self.assertEqual(second['url'], first['url'])
            self.assertTrue(second['cached'])
            self.assertEqual(synth.call_count, 1)
            media = main.get_voice_preview(first["url"].split('/')[-1])
            self.assertEqual(media.media_type, "audio/wav")
            self.assertIn("private", media.headers["cache-control"])
            with self.assertRaises(HTTPException) as raised:
                main.get_voice_preview("../outside")
            self.assertEqual(raised.exception.status_code, 404)

    def test_busy_preview_is_rejected_without_synthesis(self):
        main._voice_preview_slot.acquire()
        try:
            with patch("backend.main.synthesize") as synth, self.assertRaises(HTTPException) as raised:
                main.create_voice_preview(VoicePreview(voice_id="thorsten", text="Ein Hörvergleich"))
            self.assertEqual(raised.exception.status_code, 429)
            synth.assert_not_called()
        finally:
            main._voice_preview_slot.release()
