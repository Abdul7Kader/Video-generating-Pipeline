"""Bounded identity and object-state continuity; no semantic model verdicts."""
import copy
from collections import Counter

from .speech import anchor_index, anchor_movement
from .stickman import PORTABLE_PROPS, StickmanBoard


def _keys(board):
    counts = Counter(prop['kind'] for prop in board['props'])
    keys = []
    for prop in board['props']:
        kind = prop['kind']
        if counts[kind] > 1 and kind in PORTABLE_PROPS and not prop.get('id'):
            raise ValueError('Mehrere tragbare Gegenstände desselben Typs brauchen stabile IDs.')
        if prop.get('id'):
            keys.append(prop['id'])
        elif counts[kind] == 1:
            keys.append(f'portable:{kind}' if kind in PORTABLE_PROPS else f"{board['setting']}:{kind}")
        else:
            keys.append(None)
    return keys


def normalize_continuity(scenes):
    result = copy.deepcopy(scenes)
    cast, objects, resting, held, poses = {}, {}, {}, {}, {}
    previous_cast = {}
    seen_board = False
    for scene in result:
        if not scene.get('stickman'):
            continue
        board = StickmanBoard.model_validate(scene['stickman']).model_dump()
        keys = _keys(board)
        local = {key:index for index, key in enumerate(keys) if key is not None}
        actors = {actor['id']:actor for actor in board['characters']}
        for actor in board['characters']:
            anchor_movement(actor, scene['narration'])
            identity = (actor['species'], actor['outfit'], actor['scale'])
            if actor['id'] in cast and cast[actor['id']] != identity:
                raise ValueError('Eine wiederkehrende Figur darf Tierart, Kleidung oder Größe nicht zwischen Bildabschnitten wechseln.')
            peers = [other for other in previous_cast.values() if other['species']==actor['species']]
            current_peers = [other for other in actors.values() if other['species']==actor['species']]
            if len(peers)==len(current_peers)==1 and actor['id'] not in cast and not actor.get('enter_on'):
                raise ValueError('Eine wiederkehrende Figur braucht dieselbe ID; neue Figuren einen gesprochenen Auftrittsanker.')
            incoming = held.get(actor['id'])
            if actor['id'] in poses and not actor.get('enter_on'):
                actor['pose'], actor['expression'] = poses[actor['id']]
            if incoming is not None:
                if incoming not in local:
                    raise ValueError('Ein gehaltener Gegenstand fehlt nach dem Bildwechsel.')
                if actor['initial_prop'] is not None and keys[actor['initial_prop']] != incoming:
                    raise ValueError('Der gehaltene Gegenstand darf beim Bildwechsel nicht wechseln.')
                actor['initial_prop'] = local[incoming]
            elif actor['initial_prop'] is not None:
                if seen_board and (actor['id'] in cast or not actor.get('enter_on')):
                    raise ValueError('Anfangsbesitz braucht vorheriges Greifen oder einen ausdrücklich eingeführten neuen Träger.')
                key = keys[actor['initial_prop']]
                if key in held.values():
                    raise ValueError('Besitzwechsel brauchen vorheriges Ablegen.')
                held[actor['id']] = key
            cast[actor['id']] = identity
        for index, prop in enumerate(board['props']):
            key = keys[index]
            if key is None:
                continue
            identity = (prop['kind'], prop['scale'], prop['label'])
            if key in objects and objects[key] != identity:
                raise ValueError('Ein wiederkehrender Gegenstand darf Typ, Größe oder Beschriftung nicht wechseln.')
            objects[key] = identity
            owners = [owner for owner, item in held.items() if item==key]
            if owners and owners[0] not in actors:
                raise ValueError('Ein sichtbarer gehaltener Gegenstand braucht auch seinen Träger im Bild.')
            if not owners and key in resting and resting[key][0]==board['setting'] and not prop.get('enter_on'):
                prop['x'], prop['y'] = resting[key][1:]
        events = []
        for actor in board['characters']:
            cursor = 0
            for cue in actor['cues']:
                start = anchor_index(scene['narration'], cue['on'], cursor)
                cursor = start+len(cue['on'].split())
                if cue['pose'] in {'pick','carry','read','place'}:
                    events.append((start, actor['id'], cue))
        for _, owner, cue in sorted(events, key=lambda event:event[0]):
            index = cue['target_prop']
            key = keys[index]
            other = next((actor for actor, item in held.items() if item==key and actor!=owner), None)
            if other is not None:
                raise ValueError('Besitzwechsel brauchen vorheriges Ablegen.')
            if owner in held and held[owner] != key:
                raise ValueError('Vor einem neuen Gegenstand muss der bisherige abgelegt werden.')
            if cue['pose']=='pick' and held.get(owner)==key:
                raise ValueError('Ein bereits gehaltener Gegenstand kann erst nach dem Ablegen erneut aufgenommen werden.')
            if cue['pose']=='place':
                if owner not in held and seen_board:
                    raise ValueError('Ablegen braucht einen zuvor gehaltenen Gegenstand.')
                held.pop(owner, None)
                prop = board['props'][index]
                if cue['place_surface'] is not None:
                    desk = board['props'][cue['place_surface']]
                    bottom = {'book':10,'phone':1,'document':3}.get(prop['kind'],0)
                    position = (desk['x'], desk['y']-67*desk['scale']/6+bottom*prop['scale']/6)
                else:
                    position = (cue['place_x'] if cue['place_x'] is not None else prop['x'], cue['place_y'] if cue['place_y'] is not None else prop['y'])
                resting[key] = (board['setting'], *position)
            else:
                held[owner] = key
        for index, prop in enumerate(board['props']):
            key = keys[index]
            if key is not None and key not in held.values() and not any(cue['pose']=='place' and keys[cue['target_prop']]==key for _, _, cue in events):
                resting[key] = (board['setting'], prop['x'], prop['y'])
        validated = StickmanBoard.model_validate(board)
        validated.validate_narration(scene['narration'])
        scene['stickman'] = validated.model_dump()
        scene['continuity_policy'] = 'identity-and-props-v1'
        for actor in scene['stickman']['characters']:
            pose, expression = actor['pose'], actor['expression']
            for cue in actor['cues']:
                pose, expression = cue['pose'], cue['expression'] or expression
            if pose not in {'sit','sleep','read','work','sniff'}:
                pose = 'stand'
            poses[actor['id']] = (pose, expression)
        previous_cast = actors
        seen_board = True
    return result


def continuity_issues(scenes):
    try:
        normalize_continuity(scenes)
    except ValueError as exc:
        # Pydantic errors may include raw model data; expose only bounded contract errors.
        from pydantic import ValidationError
        return ['Die Figuren- oder Gegenstandskontinuität ist ungültig.'] if isinstance(exc, ValidationError) or str(exc).startswith('Textanker') else [str(exc)]
    return []
