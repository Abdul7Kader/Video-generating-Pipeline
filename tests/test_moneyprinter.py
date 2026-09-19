from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.moneyprinter import (
    MoneyPrinterError,
    _run_process,
    _safe_environment,
    build_batch_manifest,
    moneyprinter_status,
    render_with_moneyprinter,
    write_render_comparison,
)


def adapter_settings(root: Path, python: Path, *, enabled: bool = True):
    return SimpleNamespace(
        moneyprinter_enabled=enabled,
        moneyprinter_root=root,
        moneyprinter_python=python,
        moneyprinter_timeout_seconds=900,
    )


class MoneyPrinterAdapterTests(unittest.TestCase):
    def test_status_is_disabled_until_explicitly_configured(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            status = moneyprinter_status(adapter_settings(root, root / "python.exe", enabled=False))

        self.assertFalse(status["ready"])
        self.assertEqual(status["reason"], "MoneyPrinterTurbo ist nicht aktiviert.")

    def test_status_requires_fixed_cli_and_python_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            python = root / ".venv" / "Scripts" / "python.exe"
            python.parent.mkdir(parents=True)
            python.write_bytes(b"python")
            (root / "cli.py").write_text("print('ok')", encoding="utf-8")

            status = moneyprinter_status(adapter_settings(root, python))

        self.assertTrue(status["ready"])
        self.assertEqual(status["mode"], "local_batch_cli")

    def test_status_rejects_installation_inside_application_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            application_root = Path(temp)
            root = application_root / "MoneyPrinterTurbo"
            python = root / ".venv" / "Scripts" / "python.exe"
            python.parent.mkdir(parents=True)
            python.write_bytes(b"python")
            (root / "cli.py").write_text("", encoding="utf-8")
            fake_module_path = application_root / "backend" / "moneyprinter.py"

            with patch("backend.moneyprinter.__file__", str(fake_module_path)):
                status = moneyprinter_status(adapter_settings(root, python))

        self.assertFalse(status["ready"])
        self.assertIn("außerhalb dieses Repositories", status["reason"])

    def test_subprocess_environment_drops_provider_credentials(self):
        with patch.dict(os.environ, {
            "PATH": "safe-path",
            "GEMINI_API_KEY": "secret-one",
            "OPENAI_API_KEY": "secret-two",
            "PEXELS_API_KEY": "secret-three",
        }, clear=True):
            environment = _safe_environment()

        self.assertEqual(environment["PATH"], "safe-path")
        self.assertNotIn("GEMINI_API_KEY", environment)
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("PEXELS_API_KEY", environment)

    def test_subprocess_rejects_oversized_stdout_without_persisting_stderr(self):
        with tempfile.TemporaryDirectory() as temp:
            command = [sys.executable, "-c", "import sys; sys.stderr.write('private'); print('x' * 2200000)"]
            with self.assertRaisesRegex(MoneyPrinterError, "große Antwort"):
                _run_process(command, Path(temp), 30)

    def test_batch_manifest_reuses_approved_script_media_and_voice_without_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "narration.wav"
            asset = root / "scene.mp4"
            audio.write_bytes(b"wave")
            asset.write_bytes(b"video")
            job = {
                "topic": "Sicherer Pilot",
                "language": "de",
                "aspect_ratio": "9:16",
                "script": {"scenes": [
                    {"narration": "Erster Satz."},
                    {"narration": "Zweiter Satz."},
                ]},
            }

            manifest = build_batch_manifest(job, audio, [asset])

        self.assertEqual(len(manifest), 1)
        task = manifest[0]
        self.assertEqual(task["video_script"], "Erster Satz.\n\nZweiter Satz.")
        self.assertEqual(task["video_source"], "local")
        self.assertEqual(task["video_materials"], [{"provider": "local", "url": str(asset.resolve()), "duration": 0}])
        self.assertEqual(task["custom_audio_file"], str(audio.resolve()))
        self.assertEqual(task["bgm_type"], "")
        self.assertFalse(task["subtitle_enabled"])
        self.assertNotIn("target_platforms", task)
        self.assertNotIn("api_key", json.dumps(task).lower())

    def test_adapter_uses_batch_file_not_script_arguments_and_accepts_only_task_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "MoneyPrinterTurbo"
            python = root / ".venv" / "Scripts" / "python.exe"
            python.parent.mkdir(parents=True)
            python.write_bytes(b"python")
            (root / "cli.py").write_text("", encoding="utf-8")
            task_id = "1bc1ae60-8071-4fc8-8df0-87d755e4167c"
            task_output = root / "storage" / "tasks" / task_id / "final-1.mp4"
            task_output.parent.mkdir(parents=True)
            task_output.write_bytes(b"0" * 20_000)
            job_dir = base / "jobs" / "job-one" / "v1"
            job_dir.mkdir(parents=True)
            audio = job_dir / "narration.wav"
            asset = job_dir / "assets" / "scene.mp4"
            asset.parent.mkdir()
            audio.write_bytes(b"wave")
            asset.write_bytes(b"video")
            result = {"total": 1, "succeeded": 1, "failed": 0, "tasks": [{
                "index": 1,
                "task_id": task_id,
                "status": "succeeded",
                "result": {"videos": [str(task_output)]},
                "failed_stage": None,
                "error": None,
            }]}

            def fake_run(command, process_root, timeout_seconds):
                self.assertEqual(command[:2], [str(python.resolve()), str((root / "cli.py").resolve())])
                self.assertEqual(command[2], "--batch-file")
                self.assertNotIn("Erster Satz.", " ".join(command))
                self.assertEqual(command[-2:], ["--stop-at", "video"])
                self.assertEqual(process_root, root.resolve())
                self.assertEqual(timeout_seconds, 900)
                return 0, json.dumps(result)

            job = {
                "id": "job-one",
                "topic": "Pilot",
                "language": "de",
                "aspect_ratio": "9:16",
                "render_script_hash": "a" * 64,
                "script": {"scenes": [{"narration": "Erster Satz."}]},
            }
            with patch("backend.moneyprinter._run_process", side_effect=fake_run):
                output = render_with_moneyprinter(
                    job,
                    job_dir,
                    audio,
                    [asset],
                    adapter_settings(root, python),
                )

            self.assertEqual(output, job_dir / "video.mp4")
            self.assertEqual(output.stat().st_size, 20_000)
            provenance = json.loads((job_dir / "moneyprinter-provenance.json").read_text(encoding="utf-8"))
            self.assertEqual(provenance["adapter"], "MoneyPrinterTurbo")
            self.assertEqual(provenance["script_hash"], "a" * 64)
            self.assertNotIn("Erster Satz", json.dumps(provenance))
            self.assertNotIn("private diagnostics", json.dumps(provenance))

    def test_adapter_rejects_output_outside_reported_task_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "MoneyPrinterTurbo"
            python = root / ".venv" / "Scripts" / "python.exe"
            python.parent.mkdir(parents=True)
            python.write_bytes(b"python")
            (root / "cli.py").write_text("", encoding="utf-8")
            outside = base / "outside.mp4"
            outside.write_bytes(b"0" * 20_000)
            job_dir = base / "job"
            job_dir.mkdir()
            audio = job_dir / "narration.wav"
            asset = job_dir / "scene.mp4"
            audio.write_bytes(b"wave")
            asset.write_bytes(b"video")
            result = {"total": 1, "succeeded": 1, "failed": 0, "tasks": [{
                "task_id": "56666810-f7fe-4fd6-a477-62a1384f3656", "status": "succeeded", "result": {"videos": [str(outside)]}
            }]}
            job = {
                "id": "job-one", "topic": "Pilot", "language": "de", "aspect_ratio": "16:9",
                "render_script_hash": "b" * 64, "script": {"scenes": [{"narration": "Text"}]},
            }

            with patch("backend.moneyprinter._run_process", return_value=(0, json.dumps(result))):
                with self.assertRaisesRegex(MoneyPrinterError, "außerhalb"):
                    render_with_moneyprinter(job, job_dir, audio, [asset], adapter_settings(root, python))

    def test_comparison_uses_only_prior_render_with_same_script_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "v1"
            current = root / "v2"
            first.mkdir()
            current.mkdir()
            (first / "video.mp4").write_bytes(b"1" * 20_000)
            (current / "video.mp4").write_bytes(b"2" * 24_000)
            (first / "render-props.json").write_text(
                json.dumps({"scriptHash": "a" * 64}), encoding="utf-8"
            )
            probe = {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "format": {"duration": "12.5"},
            }

            with patch("backend.moneyprinter.probe_media", return_value=probe):
                report = write_render_comparison(current, current / "video.mp4", "moneyprinter", "a" * 64)

        self.assertEqual(report["status"], "ready")
        self.assertTrue(report["same_script_hash"])
        self.assertEqual(report["candidate"]["editor"], "moneyprinter")
        self.assertFalse(report["candidate"]["subtitles_embedded"])
        self.assertEqual(report["baseline"]["editor"], "remotion")
        self.assertTrue(report["baseline"]["subtitles_embedded"])
        self.assertEqual(report["baseline"]["relative_path"], "v1/video.mp4")
        self.assertEqual(report["limits"], "Technische Messwerte ersetzen keine redaktionelle Sichtprüfung.")

    def test_comparison_does_not_use_render_from_different_script(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "v1"
            current = root / "v2"
            first.mkdir()
            current.mkdir()
            (first / "video.mp4").write_bytes(b"1" * 20_000)
            (current / "video.mp4").write_bytes(b"2" * 24_000)
            (first / "render-props.json").write_text(
                json.dumps({"scriptHash": "b" * 64}), encoding="utf-8"
            )
            probe = {"streams": [], "format": {"duration": "12.5"}}

            with patch("backend.moneyprinter.probe_media", return_value=probe):
                report = write_render_comparison(current, current / "video.mp4", "moneyprinter", "a" * 64)

        self.assertEqual(report["status"], "baseline_missing")
        self.assertNotIn("baseline", report)


if __name__ == "__main__":
    unittest.main()
