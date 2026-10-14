"""Continuous speech and bounded direction derived from the approved narration."""
from array import array
import copy
import math
from pathlib import Path
import re
import sys
import wave

VOICE_POLICY = "continuous-v2"
TIMING_METHOD = "speech-energy-word-estimate"


def _read_pcm(path):
    with wave.open(str(path), 'rb') as audio:
        params = audio.getparams()
        if params.sampwidth != 2 or params.nchannels not in (1, 2) or not 8000 <= params.framerate <= 96000 or params.nframes > params.framerate * 300:
            raise ValueError("Sprachdatei braucht begrenztes 16-Bit-PCM-Audio.")
        samples = array('h', audio.readframes(params.nframes))
        if len(samples) != params.nframes*params.nchannels:
            raise ValueError('Die Sprachdatei ist unvollständig.')
    if sys.byteorder != 'little':
        samples.byteswap()
    return params, samples


def _regions(params, samples):
    """Ten millisecond windows; threshold below -54 dBFS protects quiet speech."""
    block = max(1, round(params.framerate * .01))
    regions = []
    for start in range(0, params.nframes, block):
        end = min(params.nframes, start + block)
        voiced = max((abs(v) for v in samples[start*params.nchannels:end*params.nchannels]), default=0) > 64
        if regions and regions[-1][2] == voiced:
            regions[-1] = (regions[-1][0], end, voiced)
        else:
            regions.append((start, end, voiced))
    return regions


def compact_speech(path: Path) -> dict:
    params, samples = _read_pcm(path)
    regions = _regions(params, samples)
    if not any(voiced for _, _, voiced in regions):
        raise ValueError("Die Audiodatei enthält keine hörbare Sprache.")
    result = array('h')
    for index, (start, end, voiced) in enumerate(regions):
        length = end - start
        if not voiced:
            limit = .02 if index == 0 else .04 if index == len(regions)-1 else .10
            if index in (0, len(regions)-1) or length / params.framerate > .24:
                length = min(length, round(limit * params.framerate))
        if not voiced and length < end-start and index not in (0,len(regions)-1):
            # Keep both original speech boundaries; remove only the middle of a long gap.
            head = length//2
            result.extend(samples[start*params.nchannels:(start+head)*params.nchannels])
            result.extend(samples[(end-(length-head))*params.nchannels:end*params.nchannels])
        else:
            result.extend(samples[start*params.nchannels:(start+length)*params.nchannels])
    if sys.byteorder != 'little':
        result.byteswap()
    processed = path.with_suffix('.compact.wav')
    try:
        with wave.open(str(processed), 'wb') as audio:
            audio.setparams(params)
            audio.writeframes(result.tobytes())
        processed.replace(path)
    finally:
        processed.unlink(missing_ok=True)
    duration = len(result) / params.nchannels / params.framerate
    return {'policy':VOICE_POLICY, 'duration':duration, 'removed_seconds':params.nframes/params.framerate-duration}


def speech_metrics(path: Path) -> dict:
    try:
        params, samples = _read_pcm(path)
    except (wave.Error, EOFError) as exc:
        raise ValueError('Ungültige Sprachdatei.') from exc
    regions = _regions(params,samples)
    if not any(voiced for _,_,voiced in regions):
        raise ValueError('Die Audiodatei enthält keine hörbare Sprache.')
    peak = max(abs(value) for value in samples)
    return {'duration_seconds':params.nframes/params.framerate,
            'peak_dbfs':round(20*math.log10(peak/32768),2),
            'clipped_ratio':sum(abs(value)>=32760 for value in samples)/len(samples),
            'longest_internal_pause_seconds':max(( (end-start)/params.framerate for start,end,voiced in regions[1:-1] if not voiced),default=0)}


def estimate_word_timings(text: str, path: Path) -> list[dict]:
    params, samples = _read_pcm(path)
    regions = [(start/params.framerate, end/params.framerate) for start,end,voiced in _regions(params, samples) if voiced]
    words = text.split()
    if not regions or not words:
        raise ValueError("Wortpositionen brauchen hörbare Sprache und Sprechertext.")
    weights = [max(1, len(re.sub(r'\W', '', word))) for word in words]
    total_weight = sum(weights)
    voiced_duration = sum(end-start for start,end in regions)

    def position(progress):
        remaining = progress * voiced_duration
        for start,end in regions:
            if remaining <= end-start:
                return start+remaining
            remaining -= end-start
        return regions[-1][1]

    cursor = 0
    result = []
    for word, weight in zip(words, weights):
        result.append({'text':word, 'start':position(cursor/total_weight), 'end':position((cursor+weight)/total_weight)})
        cursor += weight
    return result


def anchor_index(narration: str, anchor: str, after=0) -> int:
    normalize = lambda text: re.sub(r'^\W+|\W+$', '', text).casefold()
    words = [normalize(word) for word in narration.split()]
    phrase = [normalize(word) for word in anchor.split()]
    if phrase and all(phrase):
        for index in range(after, len(words)-len(phrase)+1):
            if words[index:index+len(phrase)] == phrase:
                return index
    raise ValueError(f'Textanker „{anchor}“ fehlt oder steht nicht in der richtigen Reihenfolge im Sprechertext.')


def speech_scene_durations(scenes, segments):
    if len(scenes) != len(segments):
        raise ValueError("Audiosegmente und Szenen stimmen nicht überein.")
    return [float(segment['duration']) for segment in segments]


def anchor_movement(character, narration):
    cues = character.get('cues', [])
    if any(cue['pose'] in {'walk','run'} for cue in cues):
        character['end_x'] = None
        if character.get('pose') in {'walk','run'}:
            character['pose'] = 'stand'
    elif character.get('pose') in {'walk','run'} and character.get('end_x') is not None:
        match = re.search(r'\b(?:geht|gehen|läuft|laufen|rennt|rennen|walks?|walked|goes|runs?|went)\b', narration, re.I)
        if not match:
            raise ValueError('Ein Laufweg braucht einen gesprochenen Bewegungsanker.')
        cues = [*cues, {'on':match.group(), 'pose':character['pose'], 'move_to':character['end_x'], 'duration':.7}]
        character['cues'] = sorted(cues,key=lambda cue:anchor_index(narration,cue['on']))
        character['pose'], character['end_x'] = 'stand', None


def direct_scene(scene: dict, words: list[dict], duration: float) -> dict:
    result = copy.deepcopy(scene)
    board = result.get('stickman')
    if not board:
        return result
    if not math.isfinite(duration) or duration <= 0 or len(words) != len(scene['narration'].split()):
        raise ValueError('Sprachzeiten und Sprechertext stimmen nicht überein.')
    previous_end = 0
    for word in words:
        start, end = word['start'], word['end']
        if not all(math.isfinite(value) for value in (start, end)) or not 0 <= start < end <= duration+.001 or start+.001 < previous_end:
            raise ValueError('Ungültige oder überlappende Sprachzeiten.')
        previous_end = end
    for character in board.get('characters', []):
        anchor_movement(character, scene['narration'])
        cursor = 0
        motions = []
        for cue in character.get('cues', []):
            index = anchor_index(scene['narration'], cue['on'], cursor)
            cursor = index+len(cue['on'].split())
            motions.append({**cue, 'at':words[index]['start'], 'active_until':words[cursor-1]['end']})
        for index, motion in enumerate(motions):
            limit = motions[index+1]['at'] if index+1 < len(motions) else duration
            available = limit-motion['at']
            if available < 1/30:
                raise ValueError('Die Aktionsanker liegen zu eng für eine sichtbare Bewegung. Bitte die Bildplanung überarbeiten.')
            ceiling = 1.2 if motion['pose'] in {'walk', 'run'} else .9
            motion['duration'] = min(motion['duration'], ceiling, available)
            motion['active_until'] = min(limit, max(motion['active_until'], motion['at']+motion['duration']))
        character['motion_cues'] = motions
    # Complete release before the next owner acquires the same object.
    interactions = {}
    for character in board.get('characters', []):
        for cue in character.get('motion_cues', []):
            if cue.get('target_prop') is not None and cue['pose'] in {'pick', 'read', 'carry', 'place'}:
                interactions.setdefault(cue['target_prop'], []).append(cue)
    for cues in interactions.values():
        cues.sort(key=lambda cue: cue['at'])
        for cue, following in zip(cues, cues[1:]):
            if cue['pose'] == 'place':
                cue['duration'] = min(cue['duration'], max(.001, following['at']-cue['at']))
    for prop in [*board.get('props', []), *board.get('characters', [])]:
        for field, anchor in (('enter','enter_on'), ('exit','exit_on')):
            if prop.get(anchor):
                prop[field] = words[anchor_index(scene['narration'], prop[anchor])]['start']/duration
    for character in board.get('characters', []):
        for cue in character.get('motion_cues', []):
            targets = [character]
            if cue.get('target_prop') is not None:
                targets.append(board['props'][cue['target_prop']])
            if cue.get('place_surface') is not None:
                targets.append(board['props'][cue['place_surface']])
            if cue.get('target_character'):
                targets.extend(actor for actor in board['characters'] if actor['id'] == cue['target_character'])
            # Fractions round-trip through duration; ignore only sub-nanosecond numeric noise.
            if any((target.get('enter') or 0)*duration > cue['at']+1e-9 or
                   target.get('exit') is not None and target['exit']*duration+1e-9 < cue['at']+cue['duration'] for target in targets):
                raise ValueError('Ein Interaktionsziel ist während der gesprochenen Aktion nicht sichtbar. Bitte Auftritt und Abgang korrigieren.')
    result['words'] = words
    result['timing_method'] = TIMING_METHOD
    result['motion_policy'] = 'speech-beats-v2'
    return result
