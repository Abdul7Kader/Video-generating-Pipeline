import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException

from backend import main, story
from backend.db import Database
from backend.plan import finalize_scene_plan
from backend.schemas import JobCreate, ProductionConfig, ScriptRevision, VersionAction


class StoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / 'test.sqlite3')
        self.db.initialize()
        self.request = JobCreate(topic='Katze adoptieren', production_config=ProductionConfig(script_provider='antigravity'), script_mode='story')
        self.text = 'Mila besucht das Tierheim. Sie streichelt die Katze. Die Katze geht nach Hause.'
        response = {'title': 'Eine Katze adoptieren', 'description': 'Mila lernt die Katze kennen.', 'narration': self.text,
                    'visual_summary': 'Mila begrüßt die Katze im Tierheim, streichelt sie und begleitet sie nach Hause.', 'fact_check_notes': []}
        with patch('backend.story.generate_structured', return_value=(response, {})):
            self.draft = story.generate_story(self.request)
        self.id = self.db.create_job(self.request.model_dump(), self.draft)
        self.current = self.db.get_job(self.id)
        self.action = VersionAction(expected_version=1, expected_hash=self.current['script']['content_hash'])
        self.plan = finalize_scene_plan({'title': self.draft['title'], 'description': self.draft['description'], 'scenes': [
            {'scene_id': 'visit', 'narration': 'Mila besucht das Tierheim.', 'visual': 'Mila betritt das Tierheim.', 'visual_type': 'stickman', 'duration_seconds': 4, 'stickman': {'characters': [{'id': 'mila'}]}},
            {'scene_id': 'pet-cat', 'narration': 'Sie streichelt die Katze.', 'visual': 'Mila streichelt die Katze.', 'visual_type': 'stickman', 'duration_seconds': 6, 'stickman': {'characters': [{'id': 'mila', 'cues': [{'on': 'streichelt', 'pose': 'pet', 'target_character': 'luna'}]}, {'id': 'luna', 'species': 'cat', 'pose': 'sit'}]}},
            {'scene_id': 'go-home', 'narration': 'Die Katze geht nach Hause.', 'visual': 'Die Katze geht durch die Tür.', 'visual_type': 'stickman', 'duration_seconds': 8, 'stickman': {'characters': [{'id': 'luna', 'species': 'cat', 'pose': 'walk', 'end_x': 65}]}}
        ], 'metadata': {}}, 60)

    def tearDown(self):
        self.temp.cleanup()

    def test_creation_stores_one_hashed_narration_without_fake_drawings(self):
        self.assertEqual(len(self.draft['scenes']), 1)
        self.assertEqual(story.spoken_story(self.draft), self.text)
        self.assertEqual(self.draft['metadata']['workflow'], 'story_draft')
        self.assertNotIn('stickman', self.draft['scenes'][0])
        self.assertTrue(self.current['script']['integrity_verified'])

    def test_storyboard_retries_missing_animal_and_does_not_rewrite_approved_words(self):
        missing = copy.deepcopy(self.plan)
        for scene in missing['scenes']:
            scene['stickman']['characters'] = [{'id': 'mila'}]
        with patch('backend.story.planner.generate_script', side_effect=[missing, copy.deepcopy(self.plan)]) as generate:
            plan = story.generate_storyboard(self.request, self.current['script'])
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(story.spoken_story(plan), self.text)
        self.assertIn('cat', generate.call_args.kwargs['instructions'])
        self.assertEqual(plan['metadata']['approved_story_hash'], self.action.expected_hash)
        wrong = copy.deepcopy(self.plan)
        wrong['scenes'][0]['narration'] = 'Ein unfreigegebener anderer Text.'
        with patch('backend.story.planner.generate_script', return_value=wrong), self.assertRaises(ValueError):
            story.generate_storyboard(self.request, self.current['script'])

    def test_approval_plans_and_queues_automatically_and_retry_is_idempotent(self):
        with patch('backend.main.db', self.db), patch('backend.main.require_active_production'), patch('backend.story.planner.generate_script', return_value=copy.deepcopy(self.plan)) as generate:
            queued = main.approve_story_and_render(self.id, self.action)
            repeated = main.approve_story_and_render(self.id, self.action)
        self.assertEqual(queued['status'], 'render_queued')
        self.assertEqual(queued['script_version'], 2)
        self.assertEqual(repeated['script_version'], 2)
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(story.spoken_story(queued['script']), self.text)

    def test_invalid_drawing_can_be_corrected_without_rewriting_the_story(self):
        with patch('backend.story.planner.generate_script', side_effect=[ValueError('invalid anchors'), copy.deepcopy(self.plan)]):
            plan = story.generate_storyboard(self.request, self.current['script'])
        self.assertEqual(story.spoken_story(plan), self.text)

    def test_visual_revision_can_keep_the_spoken_words(self):
        revised = copy.deepcopy(self.draft)
        revised['metadata']['visual_summary'] += ' Die Katze betritt sichtbar die Transportbox.'
        with patch('backend.main.db', self.db), patch('backend.main.generate_story', return_value=revised):
            result = main.revise_script(self.id, ScriptRevision(expected_version=1, instructions='Nur die Bildidee genauer machen', story_mode=True))
        self.assertEqual(result['script_version'], 2)
        self.assertEqual(story.spoken_story(result['script']), self.text)
        self.assertIn('Transportbox', result['script']['metadata']['visual_summary'])

    def test_stale_approval_and_changed_words_are_blocked_before_render(self):
        wrong = copy.deepcopy(self.plan)
        wrong['scenes'][0]['narration'] = 'Andere Worte.'
        with patch('backend.main.db', self.db), patch('backend.main.generate_storyboard', return_value=wrong), patch('backend.main.require_active_production'):
            with self.assertRaises(HTTPException) as raised:
                main.approve_story_and_render(self.id, self.action)
            self.assertEqual(raised.exception.status_code, 502)
            with self.assertRaises(HTTPException) as stale:
                main.approve_story_and_render(self.id, self.action.model_copy(update={'expected_version': 99}))
            self.assertEqual(stale.exception.status_code, 409)
        self.assertEqual(self.db.get_job(self.id)['script_version'], 1)
        self.assertEqual(self.db.get_job(self.id)['status'], 'script_review')

    def test_concurrent_edit_during_planning_cannot_be_approved(self):
        def edit(*args):
            changed = copy.deepcopy(self.draft)
            changed['scenes'][0]['narration'] += ' Eine neue Aussage.'
            self.db.update_script(self.id, 1, changed)
            return self.plan
        with patch('backend.main.db', self.db), patch('backend.main.generate_storyboard', side_effect=edit), patch('backend.main.require_active_production'), self.assertRaises(HTTPException) as result:
            main.approve_story_and_render(self.id, self.action)
        self.assertEqual(result.exception.status_code, 409)
        self.assertEqual(self.db.get_job(self.id)['status'], 'script_review')

    def test_ai_revision_returns_a_new_readable_draft(self):
        revised = copy.deepcopy(self.draft)
        revised['scenes'][0]['narration'] += ' Die Katze schnuppert neugierig.'
        with patch('backend.main.db', self.db), patch('backend.main.generate_story', return_value=revised):
            result = main.revise_script(self.id, ScriptRevision(expected_version=1, instructions='Mehr Details zur Katze', story_mode=True))
        self.assertEqual(result['script_version'], 2)
        self.assertEqual(result['status'], 'script_review')
        self.assertIn('schnuppert', story.spoken_story(result['script']))
