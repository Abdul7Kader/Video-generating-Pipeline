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
        self.request = JobCreate(topic='Katze adoptieren', duration_seconds=30, production_config=ProductionConfig(script_provider='antigravity'), script_mode='story')
        self.parts = [
            'Mila besucht das Tierheim. Sie setzt sich ruhig auf den Boden und hält ihre Hand still. So kann sie beobachten, was neben ihr geschieht, ohne jemanden zu bedrängen.',
            'Sie streichelt die Katze. Das Tier hat sich ihr von selbst genähert und bleibt entspannt neben ihr sitzen. Mila bewegt ihre Hand langsam und lässt der Katze genügend Platz.',
            'Die Katze geht nach Hause. In einer sicheren Transportbox begleitet Mila sie ins vorbereitete Zimmer. Dort öffnet sie die Tür und wartet, bis das Tier selbst herauskommen möchte.'
        ]
        self.text = ' '.join(self.parts)
        response = {'title': 'Eine Katze adoptieren', 'description': 'Mila lernt die Katze kennen.', 'narration': self.text,
                    'visual_summary': 'Mila begrüßt die Katze im Tierheim, streichelt sie und begleitet sie nach Hause.', 'fact_check_notes': []}
        with patch('backend.story.generate_structured', return_value=(response, {})):
            self.draft = story.generate_story(self.request)
        self.id = self.db.create_job(self.request.model_dump(), self.draft)
        self.current = self.db.get_job(self.id)
        self.action = VersionAction(expected_version=1, expected_hash=self.current['script']['content_hash'])
        self.plan = finalize_scene_plan({'title': self.draft['title'], 'description': self.draft['description'], 'scenes': [
            {'scene_id': 'visit', 'narration': self.parts[0], 'visual': 'Mila betritt das Tierheim.', 'visual_type': 'stickman', 'duration_seconds': 4, 'stickman': {'characters': [{'id': 'mila'}]}},
            {'scene_id': 'pet-cat', 'narration': self.parts[1], 'visual': 'Mila streichelt die Katze.', 'visual_type': 'stickman', 'duration_seconds': 6, 'stickman': {'characters': [{'id': 'mila', 'cues': [{'on': 'streichelt', 'pose': 'pet', 'target_character': 'luna'}]}, {'id': 'luna', 'species': 'cat', 'pose': 'sit'}]}},
            {'scene_id': 'go-home', 'narration': self.parts[2], 'visual': 'Die Katze geht durch die Tür.', 'visual_type': 'stickman', 'duration_seconds': 8, 'stickman': {'characters': [{'id': 'luna', 'species': 'cat', 'pose': 'walk', 'end_x': 65}], 'props': [{'kind': 'carrier', 'x': 55, 'y': 82}]}}
        ], 'metadata': {}}, self.request.duration_seconds)

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
        self.assertEqual(plan['metadata']['story_quality'], self.draft['metadata']['story_quality'])
        wrong = copy.deepcopy(self.plan)
        wrong['scenes'][0]['narration'] = 'Ein unfreigegebener anderer Text.'
        with patch('backend.story.planner.generate_script', return_value=wrong), self.assertRaises(ValueError):
            story.generate_storyboard(self.request, self.current['script'])

    def test_approval_plans_and_queues_automatically_and_retry_is_idempotent(self):
        with patch('backend.main.db', self.db), patch('backend.main.require_active_production'), patch('backend.story.planner.generate_script', return_value=copy.deepcopy(self.plan)) as generate:
            queued = main.approve_story_and_render(self.id, self.action)
            same_approval = self.db.approve_script(self.id, queued['script_version'], queued['script']['content_hash'])
            self.assertEqual(same_approval['status'], 'render_queued')
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

    def test_missing_narrated_interaction_is_repaired_or_blocks_approval(self):
        missing = copy.deepcopy(self.plan)
        missing['scenes'][1]['stickman']['characters'][0]['cues'] = []
        with patch('backend.story.planner.generate_script', side_effect=[missing, copy.deepcopy(self.plan)]) as generate:
            plan = story.generate_storyboard(self.request, self.current['script'])
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(story.spoken_story(plan), self.text)
        self.assertIn('pet', generate.call_args.kwargs['instructions'])
        with patch('backend.main.db', self.db), patch('backend.main.require_active_production'), patch('backend.story.planner.generate_script', return_value=missing), self.assertRaises(HTTPException):
            main.approve_story_and_render(self.id, self.action)
        unchanged = self.db.get_job(self.id)
        self.assertEqual(unchanged['status'], 'script_review')
        self.assertEqual(unchanged['script_version'], 1)
        self.assertEqual(unchanged['script']['content_hash'], self.action.expected_hash)

    def test_known_unsupported_motif_stops_before_any_image_planning_request(self):
        draft = copy.deepcopy(self.current['script'])
        draft['scenes'][0]['narration'] = 'Mila besucht ein Pferd.'
        with patch('backend.story.planner.generate_script') as generate, self.assertRaisesRegex(ValueError, 'Pferd'):
            story.generate_storyboard(self.request, draft)
        generate.assert_not_called()

    def test_changed_recurring_character_is_corrected_without_changing_narration(self):
        bad = copy.deepcopy(self.plan)
        bad['scenes'][1]['stickman']['characters'][0]['outfit'] = 'office'
        with patch('backend.story.planner.generate_script', side_effect=[bad, copy.deepcopy(self.plan)]) as generate:
            result = story.generate_storyboard(self.request, self.current['script'])
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(story.spoken_story(result), self.text)
        self.assertEqual(result['scenes'][1]['stickman']['characters'][0]['outfit'],'plain')
        self.assertEqual(result['scenes'][2]['continuity_policy'],'identity-and-props-v1')

    def test_non_animal_storyboard_preserves_words_and_requires_reading_action(self):
        draft = copy.deepcopy(self.current['script'])
        text = 'Mila nimmt das Buch. Dann liest sie darin. Schließlich legt sie das Buch auf den Tisch.'
        draft['scenes'][0]['narration'] = text
        request = self.request.model_copy(update={'topic': 'Ein Buch lesen'})
        board = {'characters': [{'id': 'mila', 'cues': [
            {'on': 'nimmt', 'pose': 'pick', 'target_prop': 0},
            {'on': 'liest', 'pose': 'read', 'target_prop': 0},
            {'on': 'legt', 'pose': 'place', 'target_prop': 0, 'place_x': 60, 'place_y': 65}]}],
            'props': [{'kind': 'book'}, {'kind': 'desk'}]}
        plan = finalize_scene_plan({'title': 'Lesen', 'scenes': [{'narration': text, 'visual': 'Mila liest und legt das Buch ab.',
            'visual_type': 'stickman', 'stickman': board}], 'metadata': {}}, 30)
        missing = copy.deepcopy(plan)
        missing['scenes'][0]['stickman']['characters'][0]['cues'].pop(1)
        with patch('backend.story.planner.generate_script', side_effect=[missing, plan]) as generate:
            result = story.generate_storyboard(request, draft)
        self.assertEqual(story.spoken_story(result), text)
        self.assertEqual(generate.call_count, 2)
        self.assertIn('read', generate.call_args.kwargs['instructions'])

    def test_visual_revision_can_keep_the_spoken_words(self):
        revised = copy.deepcopy(self.draft)
        revised['metadata']['visual_summary'] += ' Die Katze betritt sichtbar die Transportbox.'
        with patch('backend.main.db', self.db), patch('backend.main.generate_story', return_value=revised):
            result = main.revise_script(self.id, ScriptRevision(expected_version=1, instructions='Nur die Bildidee genauer machen', story_mode=True))
        self.assertEqual(result['script_version'], 2)
        self.assertEqual(story.spoken_story(result['script']), self.text)
        self.assertIn('Transportbox', result['script']['metadata']['visual_summary'])

    def test_fact_note_revision_can_keep_the_spoken_words(self):
        revised = copy.deepcopy(self.draft)
        revised['metadata']['fact_check_notes'] = ['Der Ablauf hängt vom jeweiligen Tierheim ab.']
        with patch('backend.main.db', self.db), patch('backend.main.generate_story', return_value=revised):
            result = main.revise_script(self.id, ScriptRevision(expected_version=1, instructions='Sachliche Hinweise ergänzen', story_mode=True))
        self.assertEqual(result['script_version'], 2)
        self.assertEqual(story.spoken_story(result['script']), self.text)
        self.assertEqual(result['script']['metadata']['fact_check_notes'], revised['metadata']['fact_check_notes'])

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

    def test_atomic_approval_rolls_back_when_queue_event_cannot_be_saved(self):
        event = self.db._event
        def fail_queue(conn, job_id, kind, message, metadata=None):
            if kind == 'render_queued':
                raise ValueError('queue storage failed')
            return event(conn, job_id, kind, message, metadata)
        with patch('backend.main.db', self.db), patch('backend.main.require_active_production'), patch('backend.main.generate_storyboard', return_value=copy.deepcopy(self.plan)), patch.object(self.db, '_event', side_effect=fail_queue):
            with self.assertRaises(HTTPException):
                main.approve_story_and_render(self.id, self.action)
        job = self.db.get_job(self.id)
        self.assertEqual(job['script_version'], 1)
        self.assertEqual(job['status'], 'script_review')
        self.assertIsNone(job['approved_script_hash'])
        with self.db.connect() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM script_versions WHERE job_id=?', (self.id,)).fetchone()[0], 1)
        with patch('backend.main.db', self.db), patch('backend.main.require_active_production'), patch('backend.main.generate_storyboard', return_value=copy.deepcopy(self.plan)):
            self.assertEqual(main.approve_story_and_render(self.id, self.action)['status'], 'render_queued')

    def test_render_retry_reuses_approved_plan_without_another_ai_call(self):
        with patch('backend.main.db', self.db), patch('backend.main.require_active_production'), patch('backend.main.generate_storyboard', return_value=copy.deepcopy(self.plan)) as generate:
            queued = main.approve_story_and_render(self.id, self.action)
            self.db.fail_render(self.id, 'interrupted render')
            repeated = main.approve_story_and_render(self.id, self.action)
            self.db.fail_render(self.id, 'another interrupted render')
            reloaded_action = VersionAction(expected_version=queued['script_version'],expected_hash=queued['script']['content_hash'])
            self.assertEqual(main.approve_story_and_render(self.id,reloaded_action)['script_version'],queued['script_version'])
        self.assertEqual(repeated['status'], 'render_queued')
        self.assertEqual(repeated['script_version'], queued['script_version'])
        self.assertEqual(generate.call_count, 1)

    def test_revision_started_before_approval_cannot_replace_a_queued_plan(self):
        revised = copy.deepcopy(self.draft)
        revised['scenes'][0]['narration'] += ' Eine neue Aussage.'
        def delayed_revision(*args, **kwargs):
            self.db.queue_story_render(self.id, 1, self.action.expected_hash, self.plan)
            return revised
        with patch('backend.main.db', self.db), patch('backend.main.generate_story', side_effect=delayed_revision), self.assertRaises(HTTPException) as result:
            main.revise_script(self.id, ScriptRevision(expected_version=1, instructions='Mehr Details', story_mode=True))
        self.assertEqual(result.exception.status_code, 409)
        self.assertEqual(self.db.get_job(self.id)['status'], 'render_queued')
        self.assertEqual(story.spoken_story(self.db.get_job(self.id)['script']), self.text)

    def test_edits_cannot_invalidate_a_claimed_render(self):
        queued = self.db.queue_story_render(self.id, 1, self.action.expected_hash, self.plan)
        with self.assertRaisesRegex(ValueError, 'job_busy'):
            self.db.update_script(self.id, queued['script_version'], self.draft)
        self.assertEqual(self.db.get_job(self.id)['render_script_hash'], queued['script']['content_hash'])

    def test_revision_of_storyboard_infers_text_workflow_without_client_flag(self):
        queued = self.db.queue_story_render(self.id, 1, self.action.expected_hash, self.plan)
        self.db.fail_render(self.id, 'test-only status; no renderer started')
        revised = copy.deepcopy(self.draft)
        revised['scenes'][0]['narration'] += ' Mila lächelt.'
        with patch('backend.main.db', self.db), patch('backend.main.generate_story', return_value=revised) as text, patch('backend.main.generate_script') as scenes:
            job = main.revise_script(self.id, ScriptRevision(expected_version=queued['script_version'], instructions='Natürlich erzählen'))
        text.assert_called_once()
        scenes.assert_not_called()
        self.assertEqual(job['script']['metadata']['workflow'], 'story_draft')
        self.assertEqual(job['status'], 'script_review')
        self.assertIsNone(job['approved_script_hash'])

    def test_failed_revision_keeps_original_text_and_approval_state(self):
        with patch('backend.main.db', self.db), patch('backend.main.generate_story', side_effect=ValueError('Der Entwurf braucht eine Überarbeitung.')), self.assertRaises(HTTPException) as failure:
            main.revise_script(self.id, ScriptRevision(expected_version=1, instructions='Mehr Handlung', story_mode=True))
        self.assertEqual(failure.exception.status_code, 502)
        job = self.db.get_job(self.id)
        self.assertEqual(job['script_version'], 1)
        self.assertEqual(job['script']['content_hash'], self.action.expected_hash)
        self.assertEqual(job['status'], 'script_review')
