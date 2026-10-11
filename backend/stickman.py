"""Bounded drawing instructions; model output never supplies SVG, code or URLs."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RENDERER_VERSION = "ink-story-v3"
Pose = Literal["stand", "walk", "run", "point", "think", "shrug", "sit", "sleep", "work", "gather", "carry", "celebrate", "talk", "pick", "place", "read"]
Expression = Literal["neutral", "happy", "sad", "worried", "angry", "surprised", "tired", "determined"]


class DrawingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class MotionCue(DrawingModel):
    on: str = Field(min_length=2, max_length=100, description="Exact words from this scene's narration that trigger the action.")
    pose: Pose
    expression: Expression | None = None
    target_prop: int | None = Field(default=None, ge=0, le=7, description="Zero-based prop index to point at, pick, carry, place or read.")
    move_to: float | None = Field(default=None, ge=8, le=92)
    duration: float = Field(default=0.55, ge=0.15, le=2.5, description="Seconds to finish the movement, not the length of the scene.")


class Character(DrawingModel):
    id: str = Field(default="lead", pattern=r"^[a-zA-Z0-9_-]{1,32}$")
    x: float = Field(default=40, ge=8, le=92, description="Horizontal position, percent of drawing stage.")
    y: float = Field(default=78, ge=40, le=84, description="Feet position, percent of drawing stage.")
    scale: float = Field(default=1, ge=0.4, le=1.6)
    pose: Pose = "stand"
    expression: Expression = "neutral"
    outfit: Literal["plain", "prehistoric", "office", "scientist", "casual"] = "plain"
    facing: Literal["left", "right"] = "right"
    enter: float = Field(default=0, ge=0, le=0.9, description="Entry time as fraction of scene duration.")
    end_x: float | None = Field(default=None, ge=8, le=92, description="Movement destination; null to stay in place.")
    speed: float = Field(default=1.35, ge=0.6, le=2.5)
    cues: list[MotionCue] = Field(default_factory=list, max_length=8)


class Prop(DrawingModel):
    kind: Literal["clock", "laptop", "desk", "chair", "bed", "phone", "book", "tree", "bush", "fire", "spear", "basket", "rock", "sun", "moon", "cloud", "house", "food", "water", "gear", "lightbulb", "arrow", "question", "check", "cross", "heart", "chart"]
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
        for character in self.characters:
            for cue in character.cues:
                if cue.target_prop is not None and cue.target_prop >= len(self.props):
                    raise ValueError("Ein Handlungsschritt verweist auf einen fehlenden Gegenstand.")

    def validate_narration(self, narration):
        from .speech import anchor_index
        for character in self.characters:
            cursor = 0
            for cue in character.cues:
                cursor = anchor_index(narration, cue.on, cursor)+len(cue.on.split())
        for prop in self.props:
            enter = anchor_index(narration, prop.enter_on) if prop.enter_on else None
            exit = anchor_index(narration, prop.exit_on) if prop.exit_on else None
            if enter is not None and exit is not None and exit <= enter:
                raise ValueError("Der Abgangs-Textanker muss nach dem Auftritt liegen.")


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
