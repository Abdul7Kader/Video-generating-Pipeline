import copy
import unittest

from backend.continuity import normalize_continuity


def scene(text, *, actors=None, props=None, setting='room'):
    return {'narration': text, 'stickman': {'setting': setting,
            'characters': actors if actors is not None else [{'id': 'mila', 'outfit': 'casual'}],
            'props': props if props is not None else [{'id': 'reading', 'kind': 'book', 'x': 45, 'y': 65}]}}


class ContinuityTests(unittest.TestCase):
    def test_carried_object_survives_cut_and_local_prop_reordering(self):
        scenes = [scene('Mila nimmt das Buch.', actors=[{'id':'mila','outfit':'casual','cues':[{'on':'nimmt','pose':'pick','target_prop':0}]}]),
                  scene('Sie trägt es weiter.', actors=[{'id':'mila','outfit':'casual','x':60,'cues':[{'on':'trägt','pose':'carry','target_prop':1}]}],
                        props=[{'kind':'desk'},{'id':'reading','kind':'book','x':30,'y':65}])]
        before=copy.deepcopy(scenes)
        result=normalize_continuity(scenes)
        self.assertEqual(result[1]['stickman']['characters'][0]['initial_prop'],1)
        self.assertEqual(scenes,before)
        self.assertEqual(normalize_continuity(result),result)

    def test_placement_stays_on_same_surface_after_cut(self):
        actors=[{'id':'mila','outfit':'casual','cues':[{'on':'nimmt','pose':'pick','target_prop':0},
                 {'on':'legt','pose':'place','target_prop':0,'place_x':70,'place_y':68}]}]
        result=normalize_continuity([scene('Mila nimmt das Buch und legt es ab.',actors=actors),scene('Mila betrachtet das Buch.')])
        self.assertEqual((result[1]['stickman']['props'][0]['x'],result[1]['stickman']['props'][0]['y']),(70,68))
        self.assertIsNone(result[1]['stickman']['characters'][0]['initial_prop'])

    def test_identity_changes_disappearing_held_objects_and_owner_swaps_are_rejected(self):
        first=scene('Mila nimmt das Buch.',actors=[{'id':'mila','outfit':'casual','cues':[{'on':'nimmt','pose':'pick','target_prop':0}]}])
        for second in [scene('Mila wartet.',props=[]),scene('Mila wartet.',actors=[{'id':'mila','outfit':'office'}]),
                       scene('Mila wartet.',props=[{'id':'reading','kind':'phone'}]),
                       scene('Ben trägt das Buch.',actors=[{'id':'ben','enter_on':'Ben','initial_prop':0}])]:
            with self.subTest(second=second),self.assertRaises(ValueError):
                normalize_continuity([first,second])

    def test_same_animal_cannot_change_species_or_be_renamed_without_entry(self):
        first=scene('Die Katze sitzt.',actors=[{'id':'luna','species':'cat','pose':'sit'}],props=[])
        for actor in [{'id':'luna','species':'dog'},{'id':'newcat','species':'cat'}]:
            with self.subTest(actor=actor),self.assertRaises(ValueError):
                normalize_continuity([first,scene('Die Katze wartet.',actors=[actor],props=[])])

    def test_multiple_portable_props_need_stable_unique_ids(self):
        with self.assertRaises(ValueError):
            normalize_continuity([scene('Zwei Bücher.',props=[{'kind':'book'},{'kind':'book'}])])
        result=normalize_continuity([scene('Zwei Bücher.',props=[{'id':'a','kind':'book'},{'id':'b','kind':'book'}])])
        self.assertEqual(len(result[0]['stickman']['props']),2)
        for props in [[{'id':'../outside','kind':'book'}], [{'id':'same','kind':'book'},{'id':'same','kind':'phone'}]]:
            with self.subTest(props=props),self.assertRaises(ValueError):
                normalize_continuity([scene('Bücher.',props=props)])
        for actor in [{'id':'mila','initial_prop':7},{'id':'luna','species':'cat','initial_prop':0}]:
            with self.subTest(actor=actor),self.assertRaises(ValueError):
                normalize_continuity([scene('Ein Buch.',actors=[actor])])
        from backend.continuity import continuity_issues
        errors=continuity_issues([scene('Ein Buch.',actors=[{'id':'mila','svg':'private-output'}])])
        self.assertTrue(errors)
        self.assertNotIn('private-output',' '.join(errors))

    def test_explicit_release_allows_next_person_to_pick_up_after_cut(self):
        first=scene('Mila nimmt das Buch und legt es ab.',actors=[{'id':'mila','outfit':'casual','cues':[
            {'on':'nimmt','pose':'pick','target_prop':0},{'on':'legt','pose':'place','target_prop':0,'place_x':65,'place_y':68}]}])
        second=scene('Ben nimmt das Buch.',actors=[{'id':'ben','enter_on':'Ben','cues':[{'on':'nimmt','pose':'pick','target_prop':0}]}])
        result=normalize_continuity([first,second])
        self.assertIsNone(result[1]['stickman']['characters'][0]['initial_prop'])
        self.assertEqual(result[1]['stickman']['props'][0]['x'],65)

    def test_resting_animal_state_and_spoken_movement_survive_a_cut(self):
        scenes=[scene('Die Katze schläft.',actors=[{'id':'luna','species':'cat','pose':'sleep'}],props=[]),
                scene('Die Katze wartet und geht nach Hause.',actors=[{'id':'luna','species':'cat','pose':'walk','end_x':65}],props=[])]
        result=normalize_continuity(scenes)
        actor=result[1]['stickman']['characters'][0]
        self.assertEqual(actor['pose'],'sleep')
        self.assertIsNone(actor['end_x'])
        self.assertEqual(actor['cues'][0]['on'],'geht')
        self.assertEqual(actor['cues'][0]['move_to'],65)


if __name__=='__main__':
    unittest.main()
