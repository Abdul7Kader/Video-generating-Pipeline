"""Deterministic checks for supported, explicitly narrated subjects; no model verdicts."""
import re


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
}


def visual_coverage_issues(scenes, topic=''):
    story = topic + ' ' + ' '.join(str(scene.get('narration', '')) for scene in scenes)
    central = {species for species, pattern in ANIMALS.items() if re.search(pattern, story, re.I)}
    issues = []
    for scene in scenes:
        narration = str(scene.get('narration', ''))
        board = scene.get('stickman') or {}
        species = {actor.get('species', 'human') for actor in board.get('characters', [])}
        props = {prop.get('kind') for prop in board.get('props', [])}
        required = {animal for animal, pattern in ANIMALS.items() if re.search(pattern, narration, re.I)}
        if len(central) == 1 and re.search(r'\b(?:tier|tierheimtier|haustier|vierbeiner|animal|pet)\b', narration, re.I):
            required |= central
        for animal in required - species:
            issues.append(f"{scene.get('scene_id', '?')}: Das erzählte Tier {animal} fehlt als sichtbare Tierfigur.")
        for kind, pattern in OBJECTS.items():
            if re.search(pattern, narration, re.I) and kind not in props:
                issues.append(f"{scene.get('scene_id', '?')}: Der erzählte Gegenstand {kind} fehlt; ein Symbol oder ähnliches Möbel ersetzt ihn nicht.")
    visible = {actor.get('species') for scene in scenes for actor in (scene.get('stickman') or {}).get('characters', [])}
    for animal in central - visible:
        issues.append(f"Das zentrale Motiv {animal} kommt im gesamten Zeichenplan nicht vor.")
    return issues
