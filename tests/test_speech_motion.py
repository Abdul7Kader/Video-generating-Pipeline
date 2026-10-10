from array import array
import math
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch

from backend.speech import compact_speech, speech_scene_durations, estimate_word_timings, direct_scene


def tone(seconds, rate=16000):
    return array('h', (int(12000 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(round(seconds * rate))))


def write_audio(path, samples, rate=16000):
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(samples.tobytes())


class SpeechMotionTests(unittest.TestCase):
    def test_compacted_voice_invalidates_old_cache_then_reuses_word_timings(self):
        from backend.rendering import prepare_scene_audio
        scenes = [{'scene_id':'scene-one', 'narration':'Eine kurze Geschichte.'}]
        def generate(text, path, language):
            samples = tone(.3) + array('h', [0] * 8000) + tone(.3)
            write_audio(path, samples)
            return 'piper', 1.1
        with tempfile.TemporaryDirectory() as root, patch('backend.rendering.synthesize', side_effect=generate) as synth:
            prepare_scene_audio(Path(root)/'v1', scenes, 'de')
            current, _ = prepare_scene_audio(Path(root)/'v2', scenes, 'de', continuous=True)
            self.assertEqual(synth.call_count, 2)
            cached, _ = prepare_scene_audio(Path(root)/'v3', scenes, 'de', continuous=True)
            self.assertEqual(synth.call_count, 2)
            self.assertEqual(cached[0]['words'], current[0]['words'])
            self.assertAlmostEqual(cached[0]['duration'], .7)
            self.assertIn('reused_from', cached[0])

    def test_long_gaps_are_shortened_without_changing_spoken_samples(self):
        spoken = tone(.5)
        samples = array('h', [0] * 8000) + spoken + array('h', [0] * 16000) + spoken + array('h', [0] * 8000)
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'voice.wav'
            write_audio(path, samples)
            report = compact_speech(path)
            with wave.open(str(path), 'rb') as wav:
                result = array('h', wav.readframes(wav.getnframes()))
        self.assertLess(report['duration'], 1.3)
        self.assertEqual([v for v in result if v], [v for v in samples if v])

    def test_short_word_gaps_are_preserved_and_empty_speech_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'voice.wav'
            samples = tone(.3) + array('h', [0] * 1600) + tone(.3)
            write_audio(path, samples)
            compact_speech(path)
            with wave.open(str(path), 'rb') as wav:
                self.assertEqual(array('h', wav.readframes(wav.getnframes())), samples)
            write_audio(path, array('h', [0] * 16000))
            with self.assertRaisesRegex(ValueError, 'Sprache'):
                compact_speech(path)

    def test_scene_length_follows_audio_instead_of_padding_to_brief(self):
        self.assertEqual(speech_scene_durations([{'duration_seconds':10}, {'duration_seconds':10}],
                                              [{'duration':2.5}, {'duration':3.1}]), [2.5, 3.1])

    def test_text_anchor_drives_action_and_prop_reveal_from_speech_timing(self):
        scene = {'narration':'Er geht zum Baum und sammelt Beeren.', 'stickman': {
            'characters':[{'id':'lead', 'x':20, 'y':80, 'pose':'stand', 'cues':[
                {'on':'geht', 'pose':'walk', 'move_to':50, 'duration':.7},
                {'on':'sammelt Beeren', 'pose':'gather', 'target_prop':0, 'duration':.4}]}],
            'props':[{'kind':'bush', 'x':55, 'y':80, 'enter_on':'Baum'}]}}
        words = [{'text':w, 'start':i*.4, 'end':(i+1)*.4} for i,w in enumerate(scene['narration'].split())]
        result = direct_scene(scene, words, 3)
        cues = result['stickman']['characters'][0]['motion_cues']
        self.assertEqual([cue['at'] for cue in cues], [.4, 2.0])
        self.assertAlmostEqual(result['stickman']['props'][0]['enter'], 1.2/3)
        self.assertNotIn('motion_cues', scene['stickman']['characters'][0])

    def test_word_estimates_stay_inside_actual_voice(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'voice.wav'
            write_audio(path, tone(1) + array('h', [0]*1600) + tone(1))
            words = estimate_word_timings('Eine Figur sammelt Beeren.', path)
        self.assertEqual([w['text'] for w in words], ['Eine','Figur','sammelt','Beeren.'])
        self.assertTrue(all(0 <= w['start'] < w['end'] <= 2.1 for w in words))
        self.assertTrue(all(left['end'] <= right['start'] for left,right in zip(words, words[1:])))
