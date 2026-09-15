from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.assets import _search_pexels, prepare_scene_assets, render_plan_readiness


def asset_settings(**overrides):
    values = {
        "pexels_api_key": "test-key",
        "media_download_max_mb": 150,
        "allow_paid_media": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class AssetTests(unittest.TestCase):
    def test_readiness_blocks_missing_provider_and_generated_media(self):
        scenes = [
            {"scene_id": "scene-stock", "visual_type": "stock_video", "asset_query": "rewetted peatland"},
            {"scene_id": "scene-generated", "visual_type": "generated_video", "asset_query": ""},
        ]
        with patch("backend.assets.settings", asset_settings(pexels_api_key="")):
            issues = render_plan_readiness(scenes)
        self.assertTrue(any("PEXELS_API_KEY" in issue for issue in issues))
        self.assertTrue(any("kostenpflichtigen Medienadapter" in issue for issue in issues))

    def test_video_search_prefers_matching_orientation_and_resolution(self):
        response = {
            "videos": [{
                "id": 42,
                "url": "https://www.pexels.com/video/42/",
                "duration": 10,
                "user": {"name": "Filmer", "url": "https://www.pexels.com/@filmer"},
                "video_files": [
                    {"width": 1920, "height": 1080, "file_type": "video/mp4", "link": "https://videos.pexels.com/wide.mp4"},
                    {"width": 1080, "height": 1920, "file_type": "video/mp4", "link": "https://videos.pexels.com/tall.mp4"},
                ],
            }]
        }
        with patch("backend.assets.settings", asset_settings()), patch("backend.assets._get_json", return_value=response):
            selected = _search_pexels("stock_video", "peatland", "9:16", 8)
        self.assertEqual(selected["download_url"], "https://videos.pexels.com/tall.mp4")
        self.assertEqual(selected["creator"], "Filmer")

    def test_asset_manifest_contains_source_license_and_hash(self):
        scenes = [{
            "scene_id": "scene-peatland",
            "visual_type": "stock_image",
            "asset_query": "rewetted peatland aerial",
            "duration_seconds": 5,
        }]
        selection = {
            "download_url": "https://images.pexels.com/photo.jpg",
            "page_url": "https://www.pexels.com/photo/123/",
            "creator": "Photographer",
            "creator_url": "https://www.pexels.com/@photographer",
            "media_id": "123",
            "kind": "image",
        }

        def fake_download(_url: str, destination: Path) -> str:
            destination.write_bytes(b"x" * 2048)
            return "image/jpeg"

        with tempfile.TemporaryDirectory() as temp, \
             patch("backend.assets.settings", asset_settings()), \
             patch("backend.assets._search_pexels", return_value=selection), \
             patch("backend.assets._download_media", side_effect=fake_download):
            manifest = prepare_scene_assets(Path(temp), scenes, "16:9")
            stored = json.loads((Path(temp) / "asset-manifest.json").read_text())
        asset = manifest["assets"][0]
        self.assertEqual(asset["provider"], "pexels")
        self.assertEqual(asset["creator"], "Photographer")
        self.assertEqual(asset["license_url"], "https://www.pexels.com/license/")
        self.assertEqual(len(asset["sha256"]), 64)
        self.assertEqual(stored["assets"][0]["page_url"], "https://www.pexels.com/photo/123/")
        self.assertEqual(scenes[0]["asset_kind"], "image")

    def test_unchanged_scene_asset_is_reused_without_provider_call(self):
        scene = {
            "scene_id": "scene-peatland",
            "visual_type": "stock_image",
            "source_strategy": "stock",
            "source_ref": "",
            "asset_query": "rewetted peatland aerial",
            "asset_prompt": "Aerial view",
            "duration_seconds": 5,
        }
        selection = {
            "download_url": "https://images.pexels.com/photo.jpg",
            "page_url": "https://www.pexels.com/photo/123/",
            "creator": "Photographer",
            "creator_url": "https://www.pexels.com/@photographer",
            "media_id": "123",
            "kind": "image",
        }

        def fake_download(_url: str, destination: Path) -> str:
            destination.write_bytes(b"x" * 2048)
            return "image/jpeg"

        with tempfile.TemporaryDirectory() as temp, \
             patch("backend.assets.settings", asset_settings()), \
             patch("backend.assets._search_pexels", return_value=selection) as search, \
             patch("backend.assets._download_media", side_effect=fake_download):
            root = Path(temp)
            prepare_scene_assets(root / "v1", [dict(scene)], "16:9")
            second_scene = dict(scene)
            manifest = prepare_scene_assets(root / "v2", [second_scene], "16:9")
        self.assertEqual(search.call_count, 1)
        self.assertIn("reused_from", manifest["assets"][0])
        self.assertEqual(second_scene["asset_kind"], "image")


if __name__ == "__main__":
    unittest.main()
