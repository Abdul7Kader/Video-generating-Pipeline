from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.db import Database
from backend.production import build_production_catalog, legacy_production_config, normalize_production_config, production_plan_readiness


LOCAL_CONFIG = {
    "profile_id": "local_stickman",
    "video_type": "stickman",
    "script_provider": "qwen",
    "media_provider": "procedural_stickman",
    "voice_provider": "piper",
    "editor": "remotion",
}

STOCK_CONFIG = {
    "profile_id": "stock_explainer",
    "video_type": "explainer",
    "script_provider": "qwen",
    "media_provider": "pexels_stock",
    "voice_provider": "piper",
    "editor": "remotion",
}

ANTIGRAVITY_CONFIG = {
    "profile_id": "cloud_stickman",
    "video_type": "stickman",
    "script_provider": "antigravity",
    "media_provider": "procedural_stickman",
    "voice_provider": "piper",
    "editor": "remotion",
}

SCRIPT = {
    "title": "Produktionsprofil testen",
    "description": "Ein gespeicherter Produktionsvertrag",
    "scenes": [
        {
            "narration": "Diese Szene prüft den Produktionsvertrag.",
            "visual": "Eine Figur zeigt auf vier klar beschriftete Produktionsschritte.",
            "visual_type": "stickman",
        }
    ],
}


class ProductionCatalogTests(unittest.TestCase):
    def test_legacy_jobs_receive_a_complete_profile(self):
        self.assertEqual(legacy_production_config("stickman"), LOCAL_CONFIG)

    def test_profiles_are_complete_and_unavailable_entries_explain_why(self):
        catalog = build_production_catalog(
            qwen_ready=True,
            gemini_cli_ready=False,
            antigravity_ready=True,
            pexels_ready=False,
            piper_ready=True,
            gemini_tts_ready=False,
            remotion_ready=True,
        )

        required = {"profile_id", "video_type", "script_provider", "media_provider", "voice_provider", "editor"}
        self.assertTrue(catalog["profiles"])
        self.assertTrue(all(required == set(profile["config"]) for profile in catalog["profiles"]))
        unavailable = [
            item
            for choices in catalog["providers"].values()
            for item in choices
            if not item["available"]
        ]
        self.assertTrue(unavailable)
        self.assertTrue(all(item.get("reason") for item in unavailable))
        antigravity = next(item for item in catalog["providers"]["script"] if item["id"] == "antigravity")
        self.assertTrue(antigravity["available"])
        self.assertEqual(catalog["default_profile_id"], "cloud_stickman")
        cloud = next(item for item in catalog["profiles"] if item["id"] == "cloud_stickman")
        self.assertTrue(cloud["available"])

    def test_custom_selection_is_normalized_and_unimplemented_provider_is_rejected(self):
        custom = normalize_production_config(
            {**LOCAL_CONFIG, "profile_id": "local_stickman", "voice_provider": "gemini_tts"},
            legacy_video_type="stickman",
            legacy_script_provider="qwen",
        )
        self.assertEqual(custom["profile_id"], "custom")

        with self.assertRaisesRegex(ValueError, "MoneyPrinterTurbo"):
            normalize_production_config(
                {**LOCAL_CONFIG, "media_provider": "moneyprinter_media"},
                legacy_video_type="stickman",
                legacy_script_provider="qwen",
            )

        self.assertEqual(
            normalize_production_config(
                ANTIGRAVITY_CONFIG,
                legacy_video_type="stickman",
                legacy_script_provider="qwen",
            ),
            ANTIGRAVITY_CONFIG,
        )

    def test_media_contract_rejects_scenes_from_a_different_provider(self):
        self.assertEqual(
            production_plan_readiness(LOCAL_CONFIG, [{"scene_id": "one", "visual_type": "stickman"}]),
            [],
        )
        issues = production_plan_readiness(
            STOCK_CONFIG,
            [{"scene_id": "one", "visual_type": "stickman"}],
        )
        self.assertTrue(any("Pexels" in issue for issue in issues))


class ProductionConfigurationPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "pipeline.sqlite3")
        self.db.initialize()
        self.job_id = self.db.create_job(
            {
                "topic": "Produktionsprofile",
                "language": "de",
                "duration_seconds": 30,
                "aspect_ratio": "16:9",
                "video_type": "stickman",
                "target_platform": "download",
                "production_config": LOCAL_CONFIG,
            },
            SCRIPT,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_configuration_is_stored_on_job_and_script_version(self):
        job = self.db.get_job(self.job_id)

        self.assertEqual(job["production_config"], LOCAL_CONFIG)
        self.assertEqual(job["script"]["production_config"], LOCAL_CONFIG)

    def test_configuration_change_creates_version_and_invalidates_approvals(self):
        job = self.db.get_job(self.job_id)
        script_hash = job["script"]["content_hash"]
        self.db.approve_script(self.job_id, 1, script_hash)
        self.db.queue_render(self.job_id, 1, script_hash)
        self.db.claim_render()
        self.db.finish_render(self.job_id, 1, f"{self.job_id}/v1/video.mp4", "a" * 64, "piper")
        self.db.approve_video(self.job_id, 1, "a" * 64, False)

        changed = self.db.update_production_config(self.job_id, 1, STOCK_CONFIG)

        self.assertEqual(changed["script_version"], 2)
        self.assertEqual(changed["video_type"], "explainer")
        self.assertEqual(changed["production_config"], STOCK_CONFIG)
        self.assertEqual(changed["script"]["production_config"], STOCK_CONFIG)
        self.assertEqual(changed["script"]["content_hash"], script_hash)
        self.assertEqual(changed["status"], "script_review")
        self.assertIsNone(changed["approved_script_version"])
        self.assertIsNone(changed["approved_render_version"])
        self.assertIsNone(changed["approved_output_sha256"])
        self.assertIsNone(changed["output_path"])
        self.assertEqual(changed["events"][0]["event_type"], "production_config_updated")
        with self.db.connect() as conn:
            snapshots = conn.execute(
                "SELECT version,production_config_json FROM script_versions WHERE job_id=? ORDER BY version",
                (self.job_id,),
            ).fetchall()
        self.assertEqual([row["version"] for row in snapshots], [1, 2])
        self.assertEqual(json.loads(snapshots[0]["production_config_json"]), LOCAL_CONFIG)
        self.assertEqual(json.loads(snapshots[1]["production_config_json"]), STOCK_CONFIG)

    def test_script_edit_keeps_the_current_configuration_snapshot(self):
        self.db.update_production_config(self.job_id, 1, STOCK_CONFIG)

        changed_script = {**SCRIPT, "title": "Inhaltlich überarbeitet"}
        changed = self.db.update_script(self.job_id, 2, changed_script)

        self.assertEqual(changed["script_version"], 3)
        self.assertEqual(changed["production_config"], STOCK_CONFIG)
        self.assertEqual(changed["script"]["production_config"], STOCK_CONFIG)

    def test_actual_provider_is_stored_on_job_and_each_script_version(self):
        cloud_script = {
            **SCRIPT,
            "metadata": {"provider": "antigravity", "model": "gemini-3.1-pro-high"},
        }
        cloud_job_id = self.db.create_job(
            {
                "topic": "Cloud-Provenienz",
                "language": "de",
                "duration_seconds": 30,
                "aspect_ratio": "16:9",
                "video_type": "stickman",
                "target_platform": "download",
                "production_config": ANTIGRAVITY_CONFIG,
            },
            cloud_script,
        )

        created = self.db.get_job(cloud_job_id)
        self.assertEqual(created["actual_script_provider"], "antigravity")
        self.assertEqual(created["actual_script_model"], "gemini-3.1-pro-high")
        revised = self.db.update_script(cloud_job_id, 1, {
            **SCRIPT,
            "title": "Cloud-Provenienz überarbeitet",
            "metadata": {
                "provider": "ollama",
                "model": "qwen3.5:9b-q8_0",
                "requested_provider": "antigravity",
                "fallback_from": "antigravity",
                "fallback_reason": "timeout",
            },
        })
        self.assertEqual(revised["actual_script_provider"], "ollama")
        self.assertEqual(revised["actual_script_model"], "qwen3.5:9b-q8_0")
        self.assertEqual(revised["script_fallback"]["reason"], "timeout")
        with self.db.connect() as conn:
            versions = conn.execute(
                "SELECT version,metadata_json FROM script_versions WHERE job_id=? ORDER BY version",
                (cloud_job_id,),
            ).fetchall()
        self.assertEqual(json.loads(versions[0]["metadata_json"])["provider"], "antigravity")
        self.assertEqual(json.loads(versions[1]["metadata_json"])["provider"], "ollama")


class ProductionProfilesUiContractTests(unittest.TestCase):
    def test_simple_profiles_and_four_advanced_slots_are_present(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        script = (root / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('name="production_profile"', html)
        self.assertIn('id="advanced-production"', html)
        for slot in ("script_provider", "media_provider", "voice_provider", "editor"):
            self.assertIn(f'name="{slot}"', html)
        self.assertIn("/api/production-options", script)
        self.assertIn("production_config", script)
        self.assertIn("/production-config", script)
        self.assertIn("option.disabled", script)
        self.assertIn("Kein vollständiges Produktionsprofil verfügbar", script)
        self.assertIn("fallback_from", script)


if __name__ == "__main__":
    unittest.main()
