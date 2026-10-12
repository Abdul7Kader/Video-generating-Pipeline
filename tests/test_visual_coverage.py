import unittest
from pydantic import ValidationError
from backend.stickman import StickmanBoard
from backend.visual_coverage import visual_coverage_issues


class CoverageTests(unittest.TestCase):
    def test_cat_cannot_be_replaced_by_its_bed_or_a_heart(self):
        scene = {'scene_id': 'adopt', 'narration': 'Die Katze kommt nach Hause.', 'stickman': {'characters': [{'id': 'lead'}], 'props': [{'kind': 'pet_bed'}, {'kind': 'heart'}]}}
        self.assertTrue(visual_coverage_issues([scene]))
        scene['stickman']['characters'].append({'id': 'luna', 'species': 'cat'})
        self.assertFalse(visual_coverage_issues([scene]))

    def test_pet_equipment_requires_literal_drawings_and_animal_references_keep_cat_visible(self):
        scene = {'narration': 'Das Tier schnuppert am Napf neben der Transportbox.', 'stickman': {'characters': [], 'props': [{'kind': 'basket'}]}}
        issues = visual_coverage_issues([scene], 'Katze adoptieren')
        self.assertTrue(any('cat' in issue for issue in issues))
        self.assertTrue(any('carrier' in issue for issue in issues))
        self.assertTrue(any('bowl' in issue for issue in issues))
        scene['stickman'] = {'characters': [{'id': 'luna', 'species': 'cat'}], 'props': [{'kind': 'carrier'}, {'kind': 'bowl'}]}
        self.assertFalse(visual_coverage_issues([scene], 'Katze adoptieren'))

    def test_invalid_species_or_interaction_target_is_rejected(self):
        for actors in [[{'species': '<svg>'}], [{'id': 'lead', 'cues': [{'on': 'streichelt', 'pose': 'pet', 'target_character': 'missing'}]}], [{'id': 'same'}, {'id': 'same'}]]:
            with self.assertRaises(ValidationError):
                StickmanBoard.model_validate({'characters': actors})

    def test_pet_interaction_has_valid_literal_speech_anchor(self):
        board = StickmanBoard.model_validate({'characters': [
            {'id': 'lead', 'cues': [{'on': 'streichelt', 'pose': 'pet', 'target_character': 'luna'}]},
            {'id': 'luna', 'species': 'cat', 'pose': 'sit'}]})
        board.validate_narration('Mila streichelt die Katze.')

    def test_animals_cannot_use_unrendered_human_poses_or_leave_before_entry(self):
        for actor in [{'species': 'cat', 'pose': 'work'}, {'species': 'dog', 'cues': [{'on': 'liest', 'pose': 'read'}]}, {'id': 'luna', 'enter': 0.7, 'exit': 0.3}]:
            with self.assertRaises(ValidationError):
                StickmanBoard.model_validate({'characters': [actor]})
