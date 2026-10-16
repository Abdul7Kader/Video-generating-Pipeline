from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import wave
from fastapi import HTTPException
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend import main, qwen_tts, rendering
from backend.db import Database
from backend.production import legacy_production_config, normalize_production_config
from backend.schemas import ProductionConfig, VoicePreview
from backend.voices import validate_voice_language


class QwenVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.settings = replace(qwen_tts.settings, data_dir=self.root,
                                qwen_tts_model_dir=self.root / "model", qwen_tts_python=self.root / "python.exe")
        diagnostics_db = Database(self.root / 'test.sqlite3')
        diagnostics_db.initialize()
        isolated_db = patch.object(main,'db',diagnostics_db)
        isolated_db.start()
        self.addCleanup(isolated_db.stop)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write_audio(path):
        with wave.open(str(path), "wb") as audio:
            audio.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x00\x10" * 24000)

    def test_fixed_voice_requires_correct_provider_and_language(self):
        config = ProductionConfig(voice_provider="qwen_tts", voice_id="qwen_narrator").model_dump()
        validate_voice_language(config, "de")
        for invalid, language in [({**config, "voice_provider": "piper"}, "de"),
                                  (config, "en"), ({**config, "voice_id": None}, "de"),
                                  ({**config, "voice_id": "thorsten"}, "de")]:
            with self.assertRaises(ValueError):
                validate_voice_language(invalid, language)
        normalized = normalize_production_config(config, legacy_video_type="stickman", legacy_script_provider="qwen")
        self.assertEqual(normalized["voice_provider"], "qwen_tts")
        self.assertEqual(normalized["voice_id"], "qwen_narrator")
        self.assertEqual(legacy_production_config("stickman")["voice_provider"], "piper")

    def test_readiness_requires_complete_pinned_install_and_untampered_reference(self):
        model = self.settings.qwen_tts_model_dir
        model.mkdir()
        (model / "speech_tokenizer").mkdir()
        self.settings.qwen_tts_python.touch()
        for filename in ("config.json", "model.safetensors", "speech_tokenizer/config.json", "speech_tokenizer/model.safetensors"):
            (model / filename).touch()
        (model / "pipeline-install.json").write_text(json.dumps({
            "model": qwen_tts.MODEL_ID, "revision": qwen_tts.MODEL_REVISION, "runtime": "qwen-tts==0.1.1",
        }))
        with patch("backend.qwen_tts.settings", self.settings):
            self.assertTrue(qwen_tts.voice_status()["ready"])
            with patch("backend.qwen_tts.voice_fingerprint", return_value={"reference": "tampered"}):
                self.assertFalse(qwen_tts.voice_status()["ready"])
            (model / "speech_tokenizer/model.safetensors").unlink()
            self.assertFalse(qwen_tts.voice_status()["ready"])

    # Worker protocol/timeout fixtures need a fixed budget; the resource-block test below verifies denial.
    def test_worker_uses_stdin_and_fixed_isolated_executable(self):
        output = self.root / "test.wav"
        narration = 'Mila sagt: "$() & python ../outside".'
        def run(request):
            self.assertEqual(request["text"], narration)
            self.write_audio(request["output"])
        with patch("backend.qwen_tts.settings", self.settings), patch("backend.qwen_tts.voice_status", return_value={"ready": True}), patch("backend.qwen_tts._run_worker", side_effect=run), patch("backend.device.device_info", return_value={}), patch("backend.device.recommendation", return_value={"qwen_suitable":True}):
            self.assertEqual(qwen_tts.synthesize(narration, output, "de", 1), ("qwen_tts", 1))
        self.assertTrue(output.is_file())
        self.assertFalse((self.root / "test.qwen-raw.wav").exists())

    def test_timeout_cleans_audio_and_never_uses_another_provider(self):
        output = self.root / "failed.wav"
        output.touch()
        raw = self.root / "failed.qwen-raw.wav"
        raw.touch()
        with patch("backend.qwen_tts.settings", self.settings), patch("backend.qwen_tts.voice_status", return_value={"ready": True}), patch("backend.qwen_tts._run_worker", side_effect=subprocess.TimeoutExpired("worker", 60)), patch("backend.device.device_info", return_value={}), patch("backend.device.recommendation", return_value={"qwen_suitable":True}):
            with self.assertRaises(RuntimeError):
                qwen_tts.synthesize("Mila liest ein Buch.", output, "de", 1)
        self.assertFalse(output.exists())
        self.assertFalse(raw.exists())

    def test_invalid_requests_are_rejected_before_starting_worker(self):
        with patch("backend.qwen_tts._run_worker") as run:
            for text, language, speed in [("xx", "de", 1), ("x" * 1201, "de", 1), ("Text", "en", 1), ("Text", "de", float("nan")), ("Text", "de", 100)]:
                with self.assertRaises(ValueError):
                    qwen_tts.synthesize(text, self.root / "invalid.wav", language, speed)
            run.assert_not_called()

    def test_worker_isolated_arguments_environment_and_process_tree_timeout(self):
        process = MagicMock()
        process.__enter__.return_value = process
        process.returncode = 0
        process.communicate.return_value = ("", "")
        request = {"text": '$() & python ../outside', "model": "fixed"}
        with patch("backend.qwen_tts.settings", self.settings), patch("backend.qwen_tts.subprocess.Popen", return_value=process) as launch, patch.dict("os.environ", {"PRIVATE_API_TOKEN": "test-only-marker"}):
            qwen_tts._run_worker(request)
            command = launch.call_args.args[0]
            self.assertEqual(command[0], str(self.settings.qwen_tts_python))
            self.assertEqual(command[1], "-I")
            self.assertNotIn(request["text"], command)
            self.assertNotIn("PRIVATE_API_TOKEN", launch.call_args.kwargs["env"])
            self.assertNotIn("shell", launch.call_args.kwargs)
            self.assertEqual(json.loads(process.communicate.call_args.args[0]), request)
            process.communicate.side_effect = subprocess.TimeoutExpired("worker", 60)
            with patch("backend.qwen_tts._terminate_process_tree") as terminate, self.assertRaises(subprocess.TimeoutExpired):
                qwen_tts._run_worker(request)
            terminate.assert_called_once_with(process)

    def test_cache_changes_when_voice_reference_or_policy_changes(self):
        scene = {"narration": "Mila liest ein Buch."}
        with patch("backend.qwen_tts.voice_fingerprint", return_value={"reference": "one"}):
            first = rendering._voice_fingerprint(scene, "de", "qwen_tts", voice_id="qwen_narrator")
        with patch("backend.qwen_tts.voice_fingerprint", return_value={"reference": "two"}):
            second = rendering._voice_fingerprint(scene, "de", "qwen_tts", voice_id="qwen_narrator")
        self.assertNotEqual(first, second)

    def test_preview_dispatches_qwen_and_reuses_cache(self):
        def synthesize(text, path, language, **options):
            self.assertEqual(options["provider"], "qwen_tts")
            self.write_audio(path)
            return 'qwen_tts', 1
        with patch("backend.main.settings", self.settings), patch("backend.main.synthesize", side_effect=synthesize) as synth, patch("backend.main.unload_script_model") as unload:
            request = VoicePreview(voice_id="qwen_narrator", text="Mila liest ein Buch.")
            first = main.create_voice_preview(request)
            second=main.create_voice_preview(request)
            self.assertEqual(first['url'],second['url'])
            self.assertFalse(first['cached'])
            self.assertTrue(second['cached'])
            self.assertEqual(second['voice_provider'],'qwen_tts')
            self.assertEqual(synth.call_count, 1)
            self.assertEqual(unload.call_count, 1)

    def test_preview_rejects_an_unselected_provider_and_regenerates_a_broken_cache(self):
        def generated(text,path,language,**options):
            self.write_audio(path)
            return 'piper',1
        with patch('backend.main.settings',self.settings),patch('backend.main.synthesize',side_effect=generated) as synth,patch('backend.main.normalize_narration_audio',return_value=1) as normalize,patch('backend.main.unload_script_model'):
            payload=VoicePreview(voice_id='thorsten',text='Mila öffnet ein Buch.')
            first=main.create_voice_preview(payload)
            destination=self.settings.data_dir/'voice-previews'/(first['url'].split('/')[-1]+'.wav')
            destination.write_bytes(b'broken')
            repaired=main.create_voice_preview(payload)
            self.assertFalse(repaired['cached'])
            self.assertEqual(synth.call_count,2)
            self.assertEqual(normalize.call_count,2)
            with self.assertRaises(HTTPException) as mismatch:
                main.create_voice_preview(VoicePreview(voice_id='qwen_narrator',text=payload.text))
            self.assertEqual(mismatch.exception.status_code,503)

    def test_installed_qwen_is_unavailable_when_current_free_memory_is_insufficient(self):
        with patch('backend.qwen_tts.voice_status',return_value={'ready':True,'message':''}),patch('backend.device.device_info',return_value={}),patch('backend.device.recommendation',return_value={'qwen_suitable':False}):
            voice=next(item for item in main.voice_catalog() if item['id']=='qwen_narrator')
        self.assertTrue(voice['installed'])
        self.assertFalse(voice['available'])
        self.assertIn('Arbeitsspeicher',voice['reason'])


if __name__ == "__main__":
    unittest.main()
