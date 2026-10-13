import copy
import json
import unittest
from unittest.mock import patch

from backend import story
from backend.schemas import JobCreate, ProductionConfig


PASSAGES = {
    'Katze adoptieren': 'Mila besucht das Tierheim und setzt sich ruhig auf den Boden. Eine Katze schaut zuerst aus ihrem Versteck und nähert sich dann ihrer Hand. Mila wartet, bis das Tier selbst Kontakt sucht, und streichelt vorsichtig seinen Kopf. Zu Hause stellt sie Wasser, Futter und eine Rückzugsmöglichkeit bereit. In einer sicheren Transportbox begleitet sie die Katze in das vorbereitete Zimmer. Als die Tür offen ist, darf das Tier selbst entscheiden, wann es herauskommt. Mila bleibt in der Nähe und gibt ihm Zeit. So beginnt das Kennenlernen mit kleinen, ruhigen Schritten.',
    'Informatik lernen': 'Jonas öffnet sein erstes Programm und sieht zunächst nur eine Fehlermeldung. Statt alles neu zu schreiben, liest er die letzte Zeile und findet einen fehlenden Buchstaben. Er korrigiert ihn und startet das Programm erneut. Nun erscheint die gewünschte Nachricht auf dem Bildschirm. Danach verändert Jonas eine kleine Sache und beobachtet, was passiert. Er notiert seine Vermutung, probiert sie aus und vergleicht das Ergebnis. Wenn er nicht weiterkommt, zerlegt er die Aufgabe in kleinere Schritte. Aus einem unübersichtlichen Problem wird so ein Versuch, dessen Ergebnis er nachvollziehen und erklären kann.',
    'Learning to cook': 'Sam places the ingredients on the kitchen table before starting to cook. A carrot rolls toward the edge, so Sam moves it back and clears a little space. With the recipe nearby, Sam prepares each ingredient and keeps the work surface tidy. When the vegetables are ready, they go into the pan together. Sam watches them carefully and adjusts the heat rather than rushing ahead. At the end, Sam tastes the meal and writes down what could be improved next time. Cooking becomes easier when each small action has a clear purpose.',
}


def response(topic='Katze adoptieren', **changes):
    english = topic == 'Learning to cook'
    return {'title': topic, 'description': 'A concrete story.' if english else 'Eine konkrete Geschichte.', 'narration': PASSAGES[topic],
            'visual_summary': 'The main character handles visible objects to illustrate the described actions.' if english else 'Die Hauptfigur handelt mit sichtbaren Gegenständen und zeigt die beschriebenen Schritte.',
            'fact_check_notes': [], **changes}


def request(topic='Katze adoptieren', **changes):
    return JobCreate(topic=topic, duration_seconds=30, script_mode='story',
                     production_config=ProductionConfig(script_provider='antigravity'), **changes)


class StoryQualityTests(unittest.TestCase):
    def test_topics_are_checked_against_voice_budget_without_rendering(self):
        for topic in PASSAGES:
            with self.subTest(topic=topic), patch('backend.story.generate_structured', return_value=(response(topic), {})) as generate:
                script = story.generate_story(request(topic, language='en' if topic == 'Learning to cook' else 'de'))
            quality = script['metadata']['story_quality']
            self.assertEqual(quality['word_count'], len(PASSAGES[topic].split()))
            self.assertFalse(quality['facts_verified'])
            self.assertEqual(quality['attempts'], 1)
            self.assertEqual(generate.call_count, 1)
            self.assertEqual(len(script['scenes']), 1)
            self.assertNotIn('stickman', script['scenes'][0])

    def test_one_repair_pass_corrects_short_or_formatted_narration(self):
        for bad in ['Hallo, hier ist die Katze.', 'Szene 1: Tierheim\n'+PASSAGES['Katze adoptieren'],
                    '- '+PASSAGES['Katze adoptieren'], '[Pause] '+PASSAGES['Katze adoptieren'],
                    ' '.join([PASSAGES['Katze adoptieren']]*3)]:
            with self.subTest(bad=bad[:20]), patch('backend.story.generate_structured', side_effect=[(response(narration=bad), {}), (response(), {})]) as generate:
                script = story.generate_story(request())
            self.assertEqual(generate.call_count, 2)
            self.assertEqual(script['metadata']['story_quality']['attempts'], 2)
            self.assertEqual(story.spoken_story(script), PASSAGES['Katze adoptieren'])

    def test_a_second_failure_stops_without_accepting_or_exposing_bad_output(self):
        bad = response(visual_summary='TODO private-generated-text')
        with patch('backend.story.generate_structured', return_value=(bad, {})) as generate, self.assertRaises(ValueError) as failure:
            story.generate_story(request())
        self.assertEqual(generate.call_count, 2)
        self.assertNotIn('private-generated-text', str(failure.exception))

    def test_repeated_sentences_are_repaired_even_when_length_fits(self):
        sentence = 'Mila wartet ruhig neben der Katze und beobachtet ihre Bewegungen.'
        with patch('backend.story.generate_structured', side_effect=[(response(narration=' '.join([sentence]*8)), {}), (response(), {})]) as generate:
            script = story.generate_story(request())
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(script['metadata']['story_quality']['attempts'], 2)

    def test_revision_receives_previous_visual_intent_notes_and_latest_request(self):
        with patch('backend.story.generate_structured', return_value=(response(), {})):
            previous = story.generate_story(request())
        previous['metadata']['visual_summary'] = 'Dieselbe Katze mit Transportbox und blauem Halsband.'
        previous['metadata']['fact_check_notes'] = ['Der Ablauf hängt vom Tierheim ab.']
        snapshot = copy.deepcopy(previous)
        with patch('backend.story.generate_structured', return_value=(response(), {})) as generate:
            story.generate_story(request(), previous=previous, instructions='Die Bildidee deutlicher zeigen, den Text behalten.')
        prompt = generate.call_args.args[0]
        context = json.loads(prompt.split('INPUT_JSON:\n', 1)[1].splitlines()[0])
        self.assertEqual(context['previous']['visual_summary'], previous['metadata']['visual_summary'])
        self.assertEqual(context['previous']['fact_check_notes'], previous['metadata']['fact_check_notes'])
        self.assertEqual(context['previous']['narration'], story.spoken_story(previous))
        self.assertEqual(context['change_request'], 'Die Bildidee deutlicher zeigen, den Text behalten.')
        self.assertEqual(previous, snapshot)

    def test_word_budget_uses_chosen_voice_and_speed(self):
        config = ProductionConfig(script_provider='antigravity', voice_provider='qwen_tts', voice_id='qwen_narrator', voice_speed=1.2)
        chosen = request().model_copy(update={'production_config': config})
        with patch('backend.story.generate_structured', return_value=(response(), {})):
            script = story.generate_story(chosen)
        self.assertEqual(script['metadata']['story_quality']['target_words'], 94)

    def test_different_lengths_accept_suitable_text_without_extra_model_calls(self):
        middle = 'Am nächsten Tag setzt Mila sich wieder in das Zimmer und liest dort leise. Die Katze schaut aus ihrem Versteck, bleibt aber zunächst auf Abstand. Mila stellt das Buch zur Seite und hält ihre Hand ruhig. Als das Tier näherkommt, wartet sie weiter und beobachtet seine Haltung. Dann steht sie langsam auf und lässt den Weg zur Tür frei. Die Katze folgt ihr ein Stück und bleibt am Teppich stehen. Mila schaut zurück, ohne sie zu rufen. Sie lässt das Tier selbst entscheiden, ob es weitergehen oder in das vertraute Zimmer zurückkehren möchte.'
        end = 'Später legt Mila eine Decke neben ihren Stuhl und setzt sich wieder hin. Die Katze kommt näher und schnuppert am Stoff. Sie prüft die neue Stelle, dreht sich kurz um und legt sich schließlich darauf. Mila lässt ihre Hand auf dem eigenen Knie liegen. Sie wartet, bis das Tier sich entspannt, und spricht ruhig mit ihm. Die Katze hebt den Kopf, schaut zu ihr und bleibt liegen. Mila freut sich über diesen kleinen Schritt. Sie muss nichts erzwingen, um Zeit mit ihrer neuen Mitbewohnerin zu verbringen und sie besser kennenzulernen.'
        for duration, text in [(30, PASSAGES['Katze adoptieren']), (60, PASSAGES['Katze adoptieren']+' '+middle), (90, PASSAGES['Katze adoptieren']+' '+middle+' '+end)]:
            chosen = request().model_copy(update={'duration_seconds': duration})
            with self.subTest(duration=duration), patch('backend.story.generate_structured', return_value=(response(narration=text), {})) as generate:
                script = story.generate_story(chosen)
            self.assertEqual(generate.call_count, 1)
            self.assertEqual(story.spoken_story(script), text)

    def test_local_and_cloud_api_use_the_same_text_checks(self):
        for provider, method in [('ollama', '_generate_with_ollama'), ('gemini', '_generate_with_gemini')]:
            with self.subTest(provider=provider), patch('backend.story.planner._provider_for_request', return_value=(provider, 'chosen-model')), patch('backend.story.planner.'+method, side_effect=[(response(narration='Ein zu kurzer Text.'), {}), (response(), {})]) as generate:
                script = story.generate_story(request())
            self.assertEqual(generate.call_count, 2)
            self.assertEqual(script['metadata']['provider'], provider)
            self.assertEqual(script['metadata']['story_quality']['attempts'], 2)

    def test_schema_failure_is_bounded_and_does_not_echo_model_output(self):
        bad = response(fact_check_notes=['private-output-'*100])
        with patch('backend.story.generate_structured', return_value=(bad, {})) as generate, self.assertRaises(ValueError) as failure:
            story.generate_story(request())
        self.assertEqual(generate.call_count, 2)
        self.assertNotIn('private-output', str(failure.exception))


if __name__ == '__main__':
    unittest.main()
