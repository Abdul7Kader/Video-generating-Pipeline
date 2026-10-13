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

    def test_learning_and_reading_need_literal_objects_and_anchored_actions(self):
        for text, kind, pose, anchor in [('Mila liest ein Buch.', 'book', 'read', 'liest'),
                                          ('Jonas tippt am Laptop.', 'laptop', 'work', 'tippt')]:
            scene = {'narration': text, 'stickman': {'characters': [{'id': 'lead', 'pose': 'talk'}], 'props': [{'kind': kind}]}}
            self.assertTrue(visual_coverage_issues([scene]))
            scene['stickman']['characters'][0]['cues'] = [{'on': anchor, 'pose': pose, 'target_prop': 0}]
            self.assertEqual(visual_coverage_issues([scene]), [])
            scene['stickman']['props'][0]['kind'] = 'heart'
            self.assertTrue(visual_coverage_issues([scene]))

    def test_each_object_action_needs_its_own_matching_anchor_and_target(self):
        scene = {'narration': 'Mila nimmt das Buch, trägt es und legt das Buch ab.', 'stickman': {
            'characters': [{'id': 'lead', 'cues': [{'on': 'nimmt', 'pose': 'pick', 'target_prop': 0}]}], 'props': [{'kind': 'book'}]}}
        self.assertTrue(visual_coverage_issues([scene]))
        scene['stickman']['characters'][0]['cues'] += [
            {'on': 'trägt', 'pose': 'carry', 'target_prop': 0}, {'on': 'legt', 'pose': 'place', 'target_prop': 0}]
        self.assertEqual(visual_coverage_issues([scene]), [])

    def test_action_in_another_sentence_or_on_another_prop_does_not_cover_reading(self):
        scene = {'narration': 'Mila liest das Buch. Dann zeigt sie auf ihr Telefon.', 'stickman': {
            'characters': [{'id': 'lead', 'cues': [{'on': 'zeigt', 'pose': 'read', 'target_prop': 0}]}],
            'props': [{'kind': 'book'}, {'kind': 'phone'}]}}
        self.assertTrue(visual_coverage_issues([scene]))
        scene['stickman']['characters'][0]['cues'][0].update(on='liest', target_prop=1)
        self.assertTrue(visual_coverage_issues([scene]))

    def test_explicit_unsupported_subject_is_reported_before_a_misleading_success(self):
        scene = {'narration': 'Mila füttert ein Pferd.', 'stickman': {'characters': [{'id': 'lead'}], 'props': [{'kind': 'food'}]}}
        self.assertTrue(any('Pferd' in issue and 'nicht' in issue for issue in visual_coverage_issues([scene])))
        scene['narration'] = 'Mila hat kein Pferd und kein Auto.'
        self.assertEqual(visual_coverage_issues([scene]), [])

    def test_negated_actions_and_abstract_taking_do_not_need_a_fake_pickup(self):
        scene = {'narration': 'Mila nimmt sich Zeit. Sie liest das Buch nicht.', 'stickman': {
            'characters': [{'id': 'lead'}], 'props': [{'kind': 'book'}]}}
        self.assertEqual(visual_coverage_issues([scene]), [])

    def test_object_interactions_require_valid_targets_and_unique_ownership(self):
        invalid = [
            {'characters': [{'cues': [{'on': 'nimmt', 'pose': 'pick'}]}], 'props': [{'kind': 'book'}]},
            {'characters': [{'cues': [{'on': 'nimmt', 'pose': 'pick', 'target_prop': 0}]}], 'props': [{'kind': 'desk'}]},
            {'characters': [{'cues': [{'on': 'streichelt', 'pose': 'pet', 'target_character': 'friend'}]}, {'id': 'friend'}]},
        ]
        for board in invalid:
            with self.subTest(board=board), self.assertRaises(ValidationError):
                StickmanBoard.model_validate(board)
        board = StickmanBoard.model_validate({'characters': [
            {'id': 'a', 'cues': [{'on': 'nimmt', 'pose': 'pick', 'target_prop': 0}]},
            {'id': 'b', 'cues': [{'on': 'trägt', 'pose': 'carry', 'target_prop': 0}]}], 'props': [{'kind': 'book'}]})
        with self.assertRaises(ValueError):
            board.validate_narration('Mila nimmt das Buch und Jonas trägt es.')

    def test_action_cannot_target_an_object_that_has_already_disappeared(self):
        board = StickmanBoard.model_validate({'characters': [{'cues': [{'on': 'liest', 'pose': 'read', 'target_prop': 0}]}],
                                              'props': [{'kind': 'book', 'exit_on': 'verschwindet'}]})
        with self.assertRaises(ValueError):
            board.validate_narration('Das Buch verschwindet und Mila liest darin.')

    def test_placement_coordinates_are_bounded_and_only_valid_together_on_placement(self):
        from backend.stickman import MotionCue
        for values in [{'place_x': 60}, {'place_x': 60, 'place_y': 900}, {'place_x': 60, 'place_y': 65, 'pose': 'pick'}]:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                MotionCue.model_validate({'on': 'legt', 'pose': 'place', 'target_prop': 0, **values})
        board = StickmanBoard.model_validate({'characters': [{'cues': [
            {'on': 'nimmt', 'pose': 'pick', 'target_prop': 0},
            {'on': 'legt', 'pose': 'place', 'target_prop': 0, 'place_x': 60, 'place_y': 65}]}], 'props': [{'kind': 'book'}]})
        board.validate_narration('Mila nimmt das Buch und legt es auf den Tisch.')

    def test_pronouns_keep_requiring_the_previous_object_across_sentences_and_shots(self):
        scenes = [
            {'narration': 'Mila nimmt das Buch.', 'stickman': {'characters': [{'cues': [{'on': 'nimmt', 'pose': 'pick', 'target_prop': 0}]}], 'props': [{'kind': 'book'}]}},
            {'narration': 'Dann liest sie darin. Schließlich legt sie es ab.', 'stickman': {'characters': [{'cues': []}], 'props': [{'kind': 'book'}]}},
        ]
        issues = visual_coverage_issues(scenes)
        self.assertTrue(any('read' in issue for issue in issues))
        self.assertTrue(any('place' in issue for issue in issues))
        scenes[1]['stickman']['characters'][0]['cues'] = [
            {'on': 'liest', 'pose': 'read', 'target_prop': 0}, {'on': 'legt', 'pose': 'place', 'target_prop': 0}]
        self.assertEqual(visual_coverage_issues(scenes), [])

    def test_english_phone_actions_and_topic_only_object_are_checked(self):
        scene = {'narration': 'Sam takes the phone and carries it. Then Sam puts it down.', 'stickman': {
            'characters': [{'cues': [{'on': 'takes', 'pose': 'pick', 'target_prop': 0},
                                     {'on': 'carries', 'pose': 'carry', 'target_prop': 0},
                                     {'on': 'puts', 'pose': 'place', 'target_prop': 0}]}], 'props': [{'kind': 'phone'}]}}
        self.assertEqual(visual_coverage_issues([scene], 'A phone'), [])
        scene['stickman']['characters'][0]['cues'] = []
        self.assertTrue(visual_coverage_issues([scene]))
        self.assertTrue(visual_coverage_issues([{'narration': 'Ein neuer Anfang.', 'stickman': {'characters': [{'id': 'lead'}]}}], 'Ein Buch lesen'))

    def test_placement_surface_must_be_a_valid_visible_desk(self):
        for kind, index in [('desk', 7), ('heart', 1)]:
            with self.subTest(kind=kind), self.assertRaises(ValidationError):
                StickmanBoard.model_validate({'characters': [{'cues': [{'on': 'legt', 'pose': 'place', 'target_prop': 0, 'place_surface': index}]}],
                                              'props': [{'kind': 'book'}, {'kind': kind}]})
        board = StickmanBoard.model_validate({'characters': [{'cues': [{'on': 'legt', 'pose': 'place', 'target_prop': 0, 'place_surface': 1}]}],
                                              'props': [{'kind': 'book'}, {'kind': 'desk', 'enter_on': 'erscheint'}]})
        with self.assertRaises(ValueError):
            board.validate_narration('Mila legt das Buch ab. Danach erscheint der Tisch.')
