"""Bounded drawing instructions; model output never supplies SVG, code or URLs."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RENDERER_VERSION = "ink-story-v8"
PORTABLE_PROPS = {'phone', 'book', 'basket', 'rock', 'spear', 'food', 'water', 'bowl', 'carrier', 'document'}
Pose = Literal["stand", "walk", "run", "point", "think", "shrug", "sit", "sleep", "work", "gather", "carry", "celebrate", "talk", "pick", "place", "read", "pet", "feed", "sniff"]
Expression = Literal["neutral", "happy", "sad", "worried", "angry", "surprised", "tired", "determined"]


class DrawingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class MotionCue(DrawingModel):
    on: str = Field(min_length=2, max_length=100, description="Exact words from this scene's narration that trigger the action.")
    pose: Pose
    expression: Expression | None = None
    target_prop: int | None = Field(default=None, ge=0, le=7, strict=True, description="Zero-based prop index to point at, pick, carry, place or read.")
    target_character: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,32}$", description="Existing character id for petting or interacting with an animal.")
    move_to: float | None = Field(default=None, ge=8, le=92)
    place_x: float | None = Field(default=None, ge=5, le=95, description='New prop base x after placement; use only with place, paired with place_y.')
    place_y: float | None = Field(default=None, ge=15, le=84, description='New prop base y after placement; null to reuse its current surface.')
    place_surface: int | None = Field(default=None, ge=0, le=7, strict=True, description='Optional prop index of a desk to place onto; renderer aligns the object bottom to its tabletop.')
    duration: float = Field(default=0.55, ge=0.15, le=2.5, description="Seconds to finish the movement, not the length of the scene.")

    def model_post_init(self, context):
        if (self.place_x is None) != (self.place_y is None) or (self.place_x is not None and self.pose != 'place'):
            raise ValueError('Eine Ablageposition braucht x und y gemeinsam und eine place-Aktion.')
        if self.place_surface is not None and self.pose != 'place':
            raise ValueError('Eine Ablagefläche ist nur bei einer place-Aktion erlaubt.')
        if self.place_surface is not None and self.place_x is not None:
            raise ValueError('Entweder eine Tischfläche oder freie Ablagekoordinaten angeben.')


class Character(DrawingModel):
    id: str = Field(default="lead", pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    species: Literal["human", "cat", "dog"] = "human"
    x: float = Field(default=40, ge=8, le=92, description="Horizontal position, percent of drawing stage.")
    y: float = Field(default=78, ge=40, le=84, description="Feet position, percent of drawing stage.")
    scale: float = Field(default=1, ge=0.4, le=1.6)
    pose: Pose = "stand"
    expression: Expression = "neutral"
    outfit: Literal["plain", "prehistoric", "office", "scientist", "casual"] = "plain"
    facing: Literal["left", "right"] = "right"
    enter: float = Field(default=0, ge=0, le=0.9, description="Entry time as fraction of scene duration.")
    exit: float | None = Field(default=None, ge=0.05, le=1)
    enter_on: str | None = Field(default=None, min_length=2, max_length=100)
    exit_on: str | None = Field(default=None, min_length=2, max_length=100, description="Exact spoken phrase to disappear, e.g. after entering a carrier.")
    end_x: float | None = Field(default=None, ge=8, le=92, description="Movement destination; null to stay in place.")
    speed: float = Field(default=1.35, ge=0.6, le=2.5)
    initial_prop: int | None = Field(default=None, ge=0, le=7, strict=True, description='Prop already held at shot start; continuity resolves its local index across cuts.')
    cues: list[MotionCue] = Field(default_factory=list, max_length=8)

    def model_post_init(self, context):
        if self.exit is not None and self.exit <= self.enter:
            raise ValueError("Eine Figur muss nach ihrem Auftritt verschwinden.")
        if self.species != "human" and any(pose not in {"stand", "walk", "run", "sit", "sleep", "sniff"} for pose in [self.pose, *(cue.pose for cue in self.cues)]):
            raise ValueError("Tierfiguren brauchen eine unterstützte Tierbewegung.")


class Prop(DrawingModel):
    id: str | None = Field(default=None, pattern=r'^[a-zA-Z0-9_-]{1,32}$', description='Stable object identity across shots; required for multiple portable objects of the same kind.')
    kind: Literal["clock", "laptop", "desk", "chair", "bed", "phone", "book", "tree", "bush", "fire", "spear", "basket", "rock", "sun", "moon", "cloud", "house", "food", "water", "gear", "lightbulb", "arrow", "question", "check", "cross", "heart", "chart", "carrier", "pet_bed", "bowl", "litter_box", "cat_tree", "shelf", "document"]
    x: float = Field(default=65, ge=5, le=95)
    y: float = Field(default=76, ge=15, le=84)
    scale: float = Field(default=1, ge=0.3, le=2)
    enter: float = Field(default=0, ge=0, le=0.9)
    exit: float | None = Field(default=None, ge=0.05, le=1, description="Disappearance time as fraction of scene duration; null to remain.")
    enter_on: str | None = Field(default=None, min_length=2, max_length=100, description="Exact narration phrase for appearance; null to use enter fraction.")
    exit_on: str | None = Field(default=None, min_length=2, max_length=100, description="Exact narration phrase for disappearance; null to use exit fraction.")
    label: str = Field(default="", max_length=32, description="Only intentional short visible text, never visual directions.")

    def model_post_init(self, context):
        if self.exit is not None and self.exit <= self.enter:
            raise ValueError("Eine Requisite muss nach ihrem Auftritt verschwinden.")


class StickmanBoard(DrawingModel):
    setting: Literal["white", "room", "office", "nature", "camp", "city", "classroom"] = "white"
    framing: Literal["wide", "medium", "closeup", "split"] = "wide"
    camera_move: Literal["static", "push_in", "pan_left", "pan_right"] = "static"
    characters: list[Character] = Field(default_factory=list, max_length=4)
    props: list[Prop] = Field(default_factory=list, max_length=8)

    def model_post_init(self, context):
        if not self.characters and not self.props:
            raise ValueError("Ein Zeichenplan braucht mindestens eine Figur oder eine Requisite.")
        ids = [character.id for character in self.characters]
        if len(ids) != len(set(ids)):
            raise ValueError("Figuren brauchen eindeutige IDs.")
        prop_ids = [prop.id for prop in self.props if prop.id]
        if len(prop_ids) != len(set(prop_ids)):
            raise ValueError('Gegenstände brauchen eindeutige IDs.')
        initial = [actor.initial_prop for actor in self.characters if actor.initial_prop is not None]
        if len(initial) != len(set(initial)):
            raise ValueError('Ein Gegenstand kann anfangs nur einer Figur gehören.')
        for character in self.characters:
            if character.initial_prop is not None and (character.species != 'human' or character.initial_prop >= len(self.props) or self.props[character.initial_prop].kind not in PORTABLE_PROPS):
                raise ValueError('Ein anfangs gehaltener Gegenstand braucht ein tragbares Ziel und eine menschliche Figur.')
            for cue in character.cues:
                if cue.target_prop is not None and cue.target_prop >= len(self.props):
                    raise ValueError("Ein Handlungsschritt verweist auf einen fehlenden Gegenstand.")
                if cue.target_character is not None and (cue.target_character not in ids or cue.target_character == character.id):
                    raise ValueError("Ein Handlungsschritt verweist auf eine fehlende oder dieselbe Figur.")
                if cue.pose in {'pick', 'carry', 'place', 'read'}:
                    if cue.target_prop is None or self.props[cue.target_prop].kind not in PORTABLE_PROPS:
                        raise ValueError('Greifen, Tragen, Ablegen und Lesen brauchen einen tragbaren Zielgegenstand.')
                if cue.pose == 'read' and self.props[cue.target_prop].kind not in {'book', 'document', 'phone'}:
                    raise ValueError('Lesen braucht ein Buch, Dokument oder Telefon als Ziel.')
                if cue.pose == 'pet' and not any(target.id == cue.target_character and target.species != 'human' for target in self.characters):
                    raise ValueError('Streicheln braucht eine sichtbare Tierfigur als Ziel.')
                if cue.place_surface is not None and (cue.place_surface >= len(self.props) or self.props[cue.place_surface].kind != 'desk'):
                    raise ValueError('Die Ablagefläche muss auf einen vorhandenen Tisch verweisen.')

    def validate_narration(self, narration):
        from .speech import anchor_index
        ownership = []
        for character in self.characters:
            cursor = 0
            for cue in character.cues:
                start = anchor_index(narration, cue.on, cursor)
                cursor = start+len(cue.on.split())
                target = self.props[cue.target_prop] if cue.target_prop is not None else next((actor for actor in self.characters if actor.id == cue.target_character), None)
                if target:
                    if (target.enter_on and anchor_index(narration, target.enter_on) > start) or (target.exit_on and anchor_index(narration, target.exit_on) <= start):
                        raise ValueError('Das Interaktionsziel ist am gesprochenen Aktionsanker nicht sichtbar.')
                if cue.place_surface is not None:
                    desk = self.props[cue.place_surface]
                    if (desk.enter_on and anchor_index(narration, desk.enter_on) > start) or (desk.exit_on and anchor_index(narration, desk.exit_on) <= start):
                        raise ValueError('Die Ablagefläche ist am gesprochenen Aktionsanker nicht sichtbar.')
                if cue.pose in {'pick', 'carry', 'read', 'place'}:
                    ownership.append((start, character.id, cue))
        for prop in [*self.props, *self.characters]:
            enter = anchor_index(narration, prop.enter_on) if prop.enter_on else None
            exit = anchor_index(narration, prop.exit_on) if prop.exit_on else None
            if enter is not None and exit is not None and exit <= enter:
                raise ValueError("Der Abgangs-Textanker muss nach dem Auftritt liegen.")
        held = {actor.id:actor.initial_prop for actor in self.characters if actor.initial_prop is not None}
        owners = {prop:actor for actor, prop in held.items()}
        beats = set()
        for start, actor, cue in sorted(ownership, key=lambda event: event[0]):
            index = cue.target_prop
            if (start, index) in beats:
                raise ValueError('Besitzwechsel desselben Gegenstands brauchen getrennte Textanker.')
            beats.add((start, index))
            if owners.get(index, actor) != actor:
                raise ValueError('Ein Gegenstand kann nicht gleichzeitig von zwei Figuren gehalten werden.')
            if cue.pose == 'place':
                if actor in held and held[actor] != index:
                    raise ValueError('Die Figur muss den tatsächlich gehaltenen Gegenstand ablegen.')
                owners.pop(index, None)
                held.pop(actor, None)
            else:
                if actor in held and held[actor] != index:
                    raise ValueError('Vor einem neuen Gegenstand muss die Figur den bisherigen ablegen.')
                owners[index], held[actor] = actor, index


def drawing_response_schema() -> dict:
    """Inline Pydantic refs for providers requiring self-contained JSON schemas."""
    schema = StickmanBoard.model_json_schema()
    definitions = schema.pop("$defs", {})

    def inline(value):
        if isinstance(value, list):
            return [inline(item) for item in value]
        if not isinstance(value, dict):
            return value
        if "$ref" in value:
            return inline(definitions[value["$ref"].split("/")[-1]])
        result = {key: inline(item) for key, item in value.items() if key not in {"default", "title"}}
        if result.get("type") == "object":
            result["required"] = list(result.get("properties", {}))
        return result

    return inline(schema)
