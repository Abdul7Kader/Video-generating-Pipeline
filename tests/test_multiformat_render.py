from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from backend.config import settings as default_settings
from backend.plan import finalize_scene_plan, script_hash
from backend import rendering
from backend.quality import find_ffprobe


@unittest.skipUnless(os.getenv("RUN_RENDER_INTEGRATION") == "1", "Lokalen Remotion-Render nur gezielt ausführen")
class MultiFormatRenderIntegrationTests(unittest.TestCase):
    def test_two_real_local_videos_have_distinct_aspect_ratios(self):
        installed_voice = rendering._voice_model()
        self.assertTrue(installed_voice.is_file(), "Lokale Piper-Stimme fehlt")
        script = finalize_scene_plan({
            "title": "Formatprüfung",
            "description": "Lokaler Render-Test",
            "scenes": [{
                "scene_id": "scene-format-check",
                "narration": "Hallo, dies ist ein kurzer Test.",
                "visual": "Eine Figur steht vor hellem Hintergrund.",
                "visual_type": "stickman",
                "stickman": {"characters": [{"x": 45, "y": 78, "pose": "talk"}], "props": [{"kind": "book", "x": 65, "y": 74}]},
                "source_strategy": "procedural",
                "action": "intro",
                "accent": "#ff6b4a",
                "on_screen_text": "Formatprüfung",
            }],
        }, 4)
        with tempfile.TemporaryDirectory() as directory:
            isolated = replace(default_settings, data_dir=Path(directory))
            job = {
                "id": "render-integration",
                "render_version": 1,
                "render_script_hash": script_hash(script),
                "language": "de",
                "script": script,
                "production_config": {"editor": "remotion", "voice_provider": "piper"},
            }
            dimensions = {}
            from unittest.mock import patch

            with patch.object(rendering, "settings", isolated), patch.object(rendering, "_voice_model", return_value=installed_voice):
                for ratio in ("9:16", "16:9"):
                    variant_dir = isolated.jobs_dir / job["id"] / "v1"
                    if ratio != "9:16":
                        variant_dir = variant_dir / "formats" / "16x9"
                    output, mode = rendering.render_job(
                        {**job, "aspect_ratio": ratio, "script": copy.deepcopy(script)},
                        job_dir_override=variant_dir,
                    )
                    self.assertEqual(mode, "piper")
                    self.assertTrue(Path(output).is_file())
                    probe = subprocess.run(
                        [str(find_ffprobe()), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", output],
                        check=True, capture_output=True, text=True,
                    )
                    video = json.loads(probe.stdout)["streams"][0]
                    dimensions[ratio] = (video["width"], video["height"])
            self.assertLess(dimensions["9:16"][0], dimensions["9:16"][1])
            self.assertGreater(dimensions["16:9"][0], dimensions["16:9"][1])


if __name__ == "__main__":
    unittest.main()
