from __future__ import annotations

import json
import base64
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from backend.captions import add_scene_captions, write_srt
from backend.plan import file_sha256
from backend.quality import QualityGateError, run_quality_gate
from backend.rendering import _synthesize_gemini, normalize_narration_audio, prepare_scene_audio, synthesize


def write_wav(path: Path, *, silent: bool = False, duration: float = 1.0) -> None:
    rate = 24000
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        samples = []
        for index in range(int(rate * duration)):
            value = 0 if silent else int(4000 * math.sin(2 * math.pi * 220 * index / rate))
            samples.append(struct.pack("<h", value))
        output.writeframes(b"".join(samples))


class CaptionTests(unittest.TestCase):
    def test_captions_cover_each_scene_and_write_srt(self):
        scenes = [{
            "scene_id": "scene-one",
            "narration": "Das ist der Einstieg. Danach folgt die konkrete Erklärung in wenigen Worten.",
            "start": 2.0,
            "duration": 8.0,
        }]
        add_scene_captions(scenes)
        captions = scenes[0]["captions"]
        self.assertGreater(len(captions), 1)
        self.assertAlmostEqual(sum(item["duration"] for item in captions), 8.0, places=2)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "subtitles.srt"
            count = write_srt(scenes, path)
            text = path.read_text()
        self.assertEqual(count, len(captions))
        self.assertIn("00:00:02,000 -->", text)


class QualityTests(unittest.TestCase):
    def _files(self, directory: Path, *, silent: bool = False):
        audio = directory / "narration.wav"
        output = directory / "video.mp4"
        subtitles = directory / "subtitles.srt"
        manifest = directory / "asset-manifest.json"
        voice_manifest = directory / "voice-manifest.json"
        report = directory / "quality-report.json"
        write_wav(audio, silent=silent)
        output.write_bytes(b"0" * 20_000)
        subtitles.write_text("1\n00:00:00,000 --> 00:00:01,000\nTest\n", encoding="utf-8")
        manifest.write_text(json.dumps({"assets": [{"scene_id": "scene-one", "status": "procedural"}]}), encoding="utf-8")
        voice_manifest.write_text(json.dumps({"segments": [{
            "scene_id": "scene-one", "file": "narration.wav", "sha256": file_sha256(audio),
        }]}), encoding="utf-8")
        return audio, output, subtitles, manifest, voice_manifest, report

    def test_gate_accepts_audio_video_duration_subtitles_and_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self._files(Path(temp))
            probe = {"streams": [{"codec_type": "video", "codec_name": "h264"}, {"codec_type": "audio", "codec_name": "aac"}], "format": {"duration": "1.0", "size": "20000"}}
            with patch("backend.quality._probe", return_value=probe):
                report = run_quality_gate(
                    output_path=paths[1], audio_path=paths[0], subtitles_path=paths[2],
                    asset_manifest_path=paths[3], voice_manifest_path=paths[4], expected_duration=1.0,
                    expected_script_hash="a" * 64, report_path=paths[5],
                )
            self.assertTrue(report["passed"])
            self.assertTrue(json.loads(paths[5].read_text())["passed"])

    def test_gate_rejects_silent_voice_even_when_video_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self._files(Path(temp), silent=True)
            probe = {"streams": [{"codec_type": "video"}, {"codec_type": "audio"}], "format": {"duration": "1.0"}}
            with patch("backend.quality._probe", return_value=probe):
                with self.assertRaises(QualityGateError):
                    run_quality_gate(
                        output_path=paths[1], audio_path=paths[0], subtitles_path=paths[2],
                        asset_manifest_path=paths[3], voice_manifest_path=paths[4], expected_duration=1.0,
                        expected_script_hash="a" * 64, report_path=paths[5],
                    )
            report = json.loads(paths[5].read_text())
            self.assertFalse(report["passed"])
            self.assertFalse(next(check for check in report["checks"] if check["name"] == "voice_audio")["passed"])

    def test_missing_piper_voice_fails_instead_of_creating_silence(self):
        voice_settings = type("VoiceSettings", (), {"tts_provider": "piper"})()
        with tempfile.TemporaryDirectory() as temp, \
             patch("backend.rendering.settings", voice_settings), \
             patch("backend.rendering.ensure_voice", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "stumme Ersatzvideos sind deaktiviert"):
                synthesize("Test", Path(temp) / "voice.wav", "de")

    def test_gemini_tts_requires_explicit_cloud_permission(self):
        voice_settings = type("VoiceSettings", (), {"allow_cloud_tts": False, "gemini_api_key": "key"})()
        with tempfile.TemporaryDirectory() as temp, patch("backend.rendering.settings", voice_settings):
            with self.assertRaisesRegex(RuntimeError, "nicht freigegeben"):
                _synthesize_gemini("Test", Path(temp) / "voice.wav", "de")

    def test_saved_voice_provider_overrides_the_global_default(self):
        voice_settings = type("VoiceSettings", (), {"tts_provider": "piper"})()
        with tempfile.TemporaryDirectory() as temp, \
             patch("backend.rendering.settings", voice_settings), \
             patch("backend.rendering._synthesize_gemini", return_value=("gemini:test", 1.0)) as cloud_voice:
            result = synthesize("Test", Path(temp) / "voice.wav", "de", provider="gemini_tts")

        self.assertEqual(result, ("gemini:test", 1.0))
        cloud_voice.assert_called_once()

    def test_gemini_tts_writes_returned_pcm_as_wave(self):
        pcm = b"\x10\x00" * 2400
        response_data = json.dumps({"output_audio": {"data": base64.b64encode(pcm).decode()}}).encode()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return response_data

        voice_settings = type("VoiceSettings", (), {
            "allow_cloud_tts": True,
            "gemini_api_key": "secret",
            "gemini_tts_style": "Natural",
            "gemini_tts_model": "gemini-3.1-flash-tts-preview",
            "gemini_tts_voice": "Iapetus",
        })()
        with tempfile.TemporaryDirectory() as temp, \
             patch("backend.rendering.settings", voice_settings), \
             patch("backend.rendering.urllib.request.urlopen", return_value=Response()) as request:
            path = Path(temp) / "voice.wav"
            mode, duration = _synthesize_gemini("Guten Tag.", path, "de")
            with wave.open(str(path), "rb") as audio:
                self.assertEqual(audio.getframerate(), 24000)
                self.assertEqual(audio.getnframes(), 2400)
        self.assertTrue(mode.startswith("gemini:"))
        self.assertAlmostEqual(duration, 0.1)
        sent_request = request.call_args.args[0]
        self.assertNotIn("secret", sent_request.full_url)

    def test_unchanged_scene_voice_is_reused(self):
        voice_settings = type("VoiceSettings", (), {
            "tts_provider": "piper",
            "piper_voice": "test-voice",
            "gemini_tts_model": "",
            "gemini_tts_voice": "",
            "gemini_tts_style": "",
        })()
        calls: list[str] = []

        def fake_synthesize(text: str, output: Path, _language: str):
            calls.append(text)
            write_wav(output)
            return "piper", 1.0

        first = [
            {"scene_id": "scene-one", "narration": "Erster Text."},
            {"scene_id": "scene-two", "narration": "Zweiter Text."},
        ]
        second = [
            {"scene_id": "scene-one", "narration": "Erster Text."},
            {"scene_id": "scene-two", "narration": "Geänderter zweiter Text."},
        ]
        with tempfile.TemporaryDirectory() as temp, \
             patch("backend.rendering.settings", voice_settings), \
             patch("backend.rendering.synthesize", side_effect=fake_synthesize):
            root = Path(temp)
            prepare_scene_audio(root / "v1", first, "de")
            prepare_scene_audio(root / "v2", second, "de")
            manifest = json.loads((root / "v2" / "voice-manifest.json").read_text())
        self.assertEqual(calls, ["Erster Text.", "Zweiter Text.", "Geänderter zweiter Text."])
        self.assertIn("reused_from", manifest["segments"][0])
        self.assertNotIn("reused_from", manifest["segments"][1])

    def test_narration_is_normalized_for_cross_platform_loudness(self):
        with tempfile.TemporaryDirectory() as temp:
            audio = Path(temp) / "narration.wav"
            write_wav(audio)

            def fake_run(command, **_kwargs):
                self.assertIn("loudnorm=I=-16:TP=-1.5:LRA=11", command)
                write_wav(Path(command[-1]))

            with patch("backend.rendering.find_ffmpeg", return_value="ffmpeg"), patch("backend.rendering._run", side_effect=fake_run):
                duration = normalize_narration_audio(audio)

        self.assertAlmostEqual(duration, 1.0)


if __name__ == "__main__":
    unittest.main()
