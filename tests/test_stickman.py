from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from backend.assets import prepare_scene_assets, render_plan_readiness
from backend.plan import finalize_scene_plan, script_hash
from backend.planner import _prompt, _response_schema
from backend.production import build_production_catalog
from backend.production import require_active_production
from backend.schemas import JobCreate, ProductionConfigUpdate, Scene, SceneUpdate, VersionAction


BOARD = {
    "setting": "camp", "framing": "wide", "camera_move": "static",
    "characters": [{"x": 36, "y": 78, "pose": "gather", "expression": "happy", "outfit": "prehistoric"}],
    "props": [{"kind": "fire", "x": 65, "y": 80, "scale": 1, "enter": 0}],
}
SCENE = {"narration": "Eine Figur sammelt Holz am Lagerfeuer.", "visual": "Figur sammelt Holz am Lagerfeuer.",
         "visual_type": "stickman", "stickman": BOARD}


class StickmanContractTests(unittest.TestCase):
    def test_board_survives_validation_and_single_scene_edit(self):
        scene = Scene.model_validate(SCENE).model_dump()
        self.assertEqual(scene["stickman"]["characters"][0]["pose"], "gather")
        edit = SceneUpdate(expected_version=1, stickman=BOARD).model_dump(exclude_none=True)
        self.assertEqual(edit["stickman"]["setting"], "camp")

    def test_untrusted_geometry_and_code_are_rejected(self):
        for changes in ({"x": -1}, {"x": float("nan")}, {"pose": "<script>"}, {"svg": "<svg onload=alert(1)>"}):
            bad = copy.deepcopy(SCENE)
            bad["stickman"]["characters"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                Scene.model_validate(bad)
        bad = copy.deepcopy(SCENE)
        bad["stickman"]["props"] = [{"kind": "https://evil.example/x.svg"}]
        with self.assertRaises(ValidationError):
            Scene.model_validate(bad)
        for field in ("characters", "props"):
            bad = copy.deepcopy(SCENE)
            bad["stickman"][field] *= 9
            with self.subTest(field=field), self.assertRaises(ValidationError):
                Scene.model_validate(bad)

    def test_frozen_production_cannot_be_bypassed_with_a_custom_profile(self):
        for config in ({"video_type":"explainer","media_provider":"pexels_stock","editor":"remotion"},
                       {"video_type":"stickman","media_provider":"pexels_stock","editor":"remotion"},
                       {"video_type":"stickman","media_provider":"procedural_stickman","editor":"moneyprinter"}):
            with self.subTest(config=config), self.assertRaisesRegex(ValueError,"eingefroren"):
                require_active_production(config)
        require_active_production({"video_type":"stickman","media_provider":"procedural_stickman","editor":"remotion"})

    def test_api_rejects_frozen_jobs_before_generating_editing_or_queueing(self):
        from backend import main
        frozen = {"profile_id": "stock_explainer", "video_type": "explainer", "media_provider": "pexels_stock"}
        with patch.object(main, "generate_script") as generate, patch.object(main, "db") as database:
            with self.assertRaises(HTTPException) as raised:
                main.create_job(JobCreate(topic="Stockfilm", production_config=frozen))
            self.assertEqual(raised.exception.status_code, 422)
            with self.assertRaises(HTTPException) as raised:
                main.update_production_config("job", ProductionConfigUpdate(expected_version=1, production_config=frozen))
            self.assertEqual(raised.exception.status_code, 422)
            with patch.object(main, "require_job", return_value={"production_config": frozen}):
                with self.assertRaises(HTTPException) as raised:
                    main.queue_render("job", VersionAction(expected_version=1, expected_hash="a" * 64))
            self.assertEqual(raised.exception.status_code, 409)
            generate.assert_not_called()
            database.create_job.assert_not_called()
            database.update_production_config.assert_not_called()
            database.queue_render.assert_not_called()

    def test_draw_plan_changes_approval_hash(self):
        script = finalize_scene_plan({"title": "Zeichenplan", "scenes": [SCENE]}, 8)
        changed = copy.deepcopy(script)
        changed["scenes"][0]["stickman"]["setting"] = "office"
        self.assertNotEqual(script_hash(script), script_hash(changed))

    def test_prop_cannot_disappear_before_its_reveal(self):
        bad = copy.deepcopy(SCENE)
        bad["stickman"]["props"][0].update(enter=0.6, exit=0.2)
        with self.assertRaises(ValidationError):
            Scene.model_validate(bad)

    def test_motion_cues_require_real_ordered_text_and_existing_props(self):
        for cue in ({"on":"fliegt", "pose":"walk"},
                    {"on":"sammelt", "pose":"gather", "target_prop":7}):
            bad = copy.deepcopy(SCENE)
            bad['stickman']['characters'][0]['cues'] = [cue]
            with self.subTest(cue=cue), self.assertRaises(ValidationError):
                Scene.model_validate(bad)
        good = copy.deepcopy(SCENE)
        good['stickman']['characters'][0]['cues'] = [{'on':'sammelt', 'pose':'gather', 'target_prop':0}]
        self.assertEqual(Scene.model_validate(good).stickman.characters[0].cues[0].on, 'sammelt')

    def test_no_generic_presenter_fallback_for_old_plans(self):
        issues = render_plan_readiness([{key: value for key, value in SCENE.items() if key != "stickman"}])
        self.assertTrue(any("Zeichenplan" in issue for issue in issues))
        self.assertEqual(render_plan_readiness([SCENE]), [])

    def test_procedural_manifest_binds_draw_plan_and_renderer_version(self):
        with tempfile.TemporaryDirectory() as directory:
            first = prepare_scene_assets(Path(directory), [copy.deepcopy(SCENE)], "16:9")["assets"][0]
            changed = copy.deepcopy(SCENE)
            changed["stickman"]["characters"][0]["pose"] = "sleep"
            second = prepare_scene_assets(Path(directory), [changed], "16:9")["assets"][0]
            self.assertNotEqual(first["fingerprint"], second["fingerprint"])
            self.assertEqual(first["renderer"], "ink-story-v4")

    def test_prompt_and_model_schema_have_executable_direction(self):
        prompt = _prompt(JobCreate(topic="Ein Tag im Lager", video_type="stickman", aspect_ratio="16:9"))
        self.assertIn("stickman", _response_schema()["properties"]["scenes"]["items"]["properties"])
        self.assertIn("characters", prompt)
        self.assertIn("white", prompt)

    def test_other_profiles_stay_frozen_even_with_all_providers_available(self):
        catalog = build_production_catalog(qwen_ready=True, gemini_cli_ready=True, antigravity_ready=True,
            pexels_ready=True, piper_ready=True, gemini_tts_ready=True, remotion_ready=True, moneyprinter_ready=True)
        for profile in catalog["profiles"]:
            if profile["config"]["video_type"] != "stickman":
                self.assertFalse(profile["available"])
                self.assertTrue(profile["frozen"])
                self.assertIn("eingefroren", profile["reason"])


if __name__ == "__main__":
    unittest.main()
