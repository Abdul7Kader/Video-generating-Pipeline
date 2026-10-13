"""Deterministic checks for supported, explicitly narrated subjects; no model verdicts."""
import re

from .speech import anchor_index


ANIMALS = {
    'cat': r'\b(?:katze[n]?|kater|kätzchen|cat[s]?|kitten[s]?)\b',
    'dog': r'\b(?:hund(?:e|en)?|hündin|welpe[n]?|dog[s]?|pupp(?:y|ies))\b',
}
OBJECTS = {
    'carrier': r'\b(?:transportbox|transportkorb|pet carrier)\b',
    'pet_bed': r'\b(?:katzenbett|kuschelbett|katzenkörbchen|pet bed)\b',
    'bowl': r'\b(?:napf|näpfe|näpfen|futternapf|wassernapf|bowl[s]?)\b',
    'litter_box': r'\b(?:katzenklo|katzentoilette|litter box)\b',
    'cat_tree': r'\b(?:kratzbaum|cat tree)\b',
    'book': r'\b(?:buch|bücher[n]?|book[s]?)\b',
    'phone': r'\b(?:telefon|handy|smartphone[s]?|phone[s]?)\b',
    'laptop': r'\b(?:laptop[s]?|computer[n]?|notebook[s]?)\b',
    'document': r'\b(?:dokument[e]?|formular[e]?|vertrag|document[s]?|form[s]?|contract[s]?)\b',
    'food': r'\b(?:futter|tierfutter|pet food)\b',
}
# ponytail: bounded German/English vocabulary, not a universal semantic verdict.
UNSUPPORTED = {
    'Pferd': r'\b(?:pferd[e]?|horse[s]?)\b',
    'Vogel': r'\b(?:vogel|vögel|bird[s]?)\b',
    'Fisch': r'\b(?:fisch[e]?|fish)\b',
    'Auto': r'\b(?:auto[s]?|car[s]?)\b',
    'Fahrrad': r'\b(?:fahrrad|fahrräder|bicycle[s]?|bike[s]?)\b',
    'Flugzeug': r'\b(?:flugzeug[e]?|airplane[s]?)\b',
    'Pfanne': r'\b(?:pfanne[n]?|frying pan)\b',
}
ACTIONS = {
    'read': r'\b(?:liest|lesen|lese|las|read[s]?|reading)\b',
    'work': r'\b(?:tippt|tippen|tippte|types?|typing)\b',
    'pick': r'\b(?:nimmt|nehmen|nahm|greift|greifen|picks?|takes?)\b',
    'carry': r'\b(?:trägt|tragen|trug|carries|carry|carrying)\b',
    'place': r'\b(?:legt|legen|legte|stellt|stellen|stellte|places?|puts?)\b',
    'pet': r'\b(?:streichelt|streicheln|streichelte|pets?|petting|strokes?)\b',
}


def _mentions(pattern, text):
    return [match for match in re.finditer(pattern, text, re.I)
            if not re.search(r'\b(?:kein\w*|ohne|no|without)\s+(?:\w+\s+){0,2}$', text[max(0, match.start()-45):match.start()], re.I)]


def unsupported_motif_issues(text):
    return [f'Das erzählte Motiv {name} ist im Zeichenkatalog noch nicht unterstützt; bitte das Skript überarbeiten oder den Zeichenkatalog erweitern.'
            for name, pattern in UNSUPPORTED.items() if _mentions(pattern, text)]


def _action_issues(scene, central, previous_text=''):
    text = str(scene.get('narration', ''))
    board = scene.get('stickman') or {}
    cues = []
    for actor in board.get('characters', []):
        cursor = 0
        for cue in actor.get('cues', []):
            try:
                start = anchor_index(text, cue['on'], cursor)
            except (ValueError, KeyError):
                continue
            cursor = start + len(cue['on'].split())
            cues.append((actor, cue, start, cursor))
    issues = []
    for sentence in re.finditer(r'[^.!?]+', text):
        fragment = sentence.group()
        for pose, pattern in ACTIONS.items():
            for action in re.finditer(pattern, fragment, re.I):
                tail = fragment[action.end():]
                following = re.split(r'[,;]|\b(?:und|and|then|dann)\b', tail, maxsplit=1, flags=re.I)[0]
                prefix = fragment[max(0, action.start()-25):action.start()]
                if re.search(r'\b(?:nicht|not|never|kein\w*)\b', following, re.I) or re.search(r"\b(?:nicht|not|never|don't|doesn't)\s*$", prefix, re.I):
                    continue
                vocabulary = ANIMALS if pose == 'pet' else OBJECTS
                required = {kind for kind, names in vocabulary.items() if _mentions(names, following)}
                if not required and re.search(r'\b(?:es|ihn|sie|it|them|darin)\b', following, re.I):
                    preceding = previous_text+' '+text[:sentence.start()+action.start()]
                    references = [(match.end(), kind) for kind, names in vocabulary.items() for match in _mentions(names, preceding)]
                    required = {max(references)[1]} if references else set()
                if pose == 'pet' and not required and re.search(r'\b(?:tier|animal|pet)\b', following, re.I):
                    required = central if len(central) == 1 else set()
                if not required:
                    continue
                word = len(text[:sentence.start()+action.start()].split())
                for kind in required:
                    def matches(actor, cue, start, end):
                        if cue.get('pose') != pose or actor.get('species', 'human') != 'human' or not (start <= word < end or word <= start <= word+2):
                            return False
                        if pose == 'pet':
                            return any(target.get('id') == cue.get('target_character') and target.get('species') == kind for target in board.get('characters', []))
                        index = cue.get('target_prop')
                        return isinstance(index, int) and 0 <= index < len(board.get('props', [])) and board['props'][index].get('kind') == kind
                    if not any(matches(*cue) for cue in cues):
                        issues.append(f"{scene.get('scene_id', '?')}: Die erzählte Aktion „{action.group()}“ braucht {pose} mit passendem Textanker und sichtbarem Ziel {kind}.")
    return issues


def visual_coverage_issues(scenes, topic=''):
    story = topic + ' ' + ' '.join(str(scene.get('narration', '')) for scene in scenes)
    central = {species for species, pattern in ANIMALS.items() if _mentions(pattern, story)}
    issues = []
    issues.extend(unsupported_motif_issues(story))
    preceding = ''
    for scene in scenes:
        narration = str(scene.get('narration', ''))
        board = scene.get('stickman') or {}
        species = {actor.get('species', 'human') for actor in board.get('characters', [])}
        props = {prop.get('kind') for prop in board.get('props', [])}
        required = {animal for animal, pattern in ANIMALS.items() if _mentions(pattern, narration)}
        if len(central) == 1 and re.search(r'\b(?:tier|tierheimtier|haustier|vierbeiner|animal|pet)\b', narration, re.I):
            required |= central
        for animal in required - species:
            issues.append(f"{scene.get('scene_id', '?')}: Das erzählte Tier {animal} fehlt als sichtbare Tierfigur.")
        for kind, pattern in OBJECTS.items():
            if _mentions(pattern, narration) and kind not in props:
                issues.append(f"{scene.get('scene_id', '?')}: Der erzählte Gegenstand {kind} fehlt; ein Symbol oder ähnliches Möbel ersetzt ihn nicht.")
        issues.extend(_action_issues(scene, central, preceding))
        preceding += ' '+narration
    visible = {actor.get('species') for scene in scenes for actor in (scene.get('stickman') or {}).get('characters', [])}
    for animal in central - visible:
        issues.append(f"Das zentrale Motiv {animal} kommt im gesamten Zeichenplan nicht vor.")
    visible_props = {prop.get('kind') for scene in scenes for prop in (scene.get('stickman') or {}).get('props', [])}
    for kind, pattern in OBJECTS.items():
        if _mentions(pattern, topic) and kind not in visible_props:
            issues.append(f'Das zentrale Motiv {kind} kommt im gesamten Zeichenplan nicht vor.')
    return issues
