from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Scene(BaseModel):
    scene_id: str = Field(default="", max_length=64)
    narration: str = Field(min_length=2, max_length=1200)
    visual: str = Field(
        min_length=2,
        max_length=1200,
        description="Konkrete sichtbare Einstellung; kein Platzhalter und keine Regieanweisung zum Einblenden.",
    )
    visual_type: Literal[
        "stickman",
        "generated_image",
        "generated_video",
        "stock_image",
        "stock_video",
        "motion_graphics",
        "talking_head",
        "waveform",
    ] = "motion_graphics"
    source_strategy: Literal["generate", "stock", "provided", "procedural", "recorded"] | None = None
    source_ref: str = Field(default="", max_length=2000)
    asset_query: str = Field(default="", max_length=200)
    asset_prompt: str = Field(default="", max_length=2000)
    on_screen_text: str = Field(default="", max_length=240)
    camera: str = Field(default="", max_length=500)
    transition: Literal["cut", "dissolve", "wipe", "zoom", "match_cut", "none"] = "cut"
    duration_seconds: float = Field(default=5, gt=0, le=180)
    action: Literal["intro", "stand", "walk", "point", "think", "explain", "celebrate", "outro"] = "explain"
    accent: str = Field(default="#ff6b4a", pattern=r"^#[0-9a-fA-F]{6}$")


class JobCreate(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    language: Literal["de", "en"] = "de"
    duration_seconds: int = Field(default=60, ge=15, le=600)
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    video_type: Literal["stickman", "explainer", "social", "podcast", "generated"] = "stickman"
    target_platform: Literal["download", "youtube"] = "download"

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, value: str) -> str:
        return " ".join(value.split())


class ScriptUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    title: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=5000)
    scenes: list[Scene] = Field(min_length=1, max_length=30)


class ScriptDraft(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=5000)
    audience: str = Field(min_length=2, max_length=300)
    tone: str = Field(min_length=2, max_length=300)
    fact_check_notes: list[str] = Field(default_factory=list, max_length=20)
    scenes: list[Scene] = Field(min_length=1, max_length=30)


class ScriptRevision(BaseModel):
    expected_version: int = Field(ge=1)
    instructions: str = Field(min_length=3, max_length=4000)

    @field_validator("instructions")
    @classmethod
    def normalize_instructions(cls, value: str) -> str:
        return " ".join(value.split())


class VersionAction(BaseModel):
    expected_version: int = Field(ge=1)
    expected_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
