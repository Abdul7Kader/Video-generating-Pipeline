from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .stickman import StickmanBoard


PlatformId = Literal[
    "download", "youtube", "mastodon", "tiktok", "instagram_reels", "facebook_reels",
    "linkedin", "x", "bluesky", "spotify_podcast", "apple_podcasts",
    "amazon_music_podcast", "soundcloud", "spotify_music", "apple_music",
]

VideoType = Literal["stickman", "explainer", "social", "podcast", "generated"]
ScriptProviderId = Literal["qwen", "gemini_cli", "antigravity"]
MediaProviderId = Literal["procedural_stickman", "pexels_stock", "generated_media", "moneyprinter_media", "podcast_layout"]
VoiceProviderId = Literal["piper", "qwen_tts", "gemini_tts", "moneyprinter_voice"]
EditorId = Literal["remotion", "moneyprinter", "podcast_editor"]


class ProductionConfig(BaseModel):
    profile_id: str = Field(default="local_stickman", min_length=2, max_length=64, pattern=r"^[a-z0-9_]+$")
    video_type: VideoType = "stickman"
    script_provider: ScriptProviderId = "qwen"
    media_provider: MediaProviderId = "procedural_stickman"
    voice_provider: VoiceProviderId = "piper"
    editor: EditorId = "remotion"
    voice_id: Literal["thorsten", "thorsten_amused", "kerstin", "ljspeech", "qwen_narrator"] | None = None
    voice_speed: float = Field(default=1.0, ge=0.85, le=1.25, allow_inf_nan=False)


class Scene(BaseModel):
    stickman: StickmanBoard | None = None
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

    @model_validator(mode="after")
    def validate_motion_narration(self):
        if self.stickman:
            self.stickman.validate_narration(self.narration)
        return self


class JobCreate(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    language: Literal["de", "en"] = "de"
    duration_seconds: int = Field(default=60, ge=15, le=600)
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "16:9"
    aspect_ratios: list[Literal["9:16", "16:9", "1:1"]] | None = Field(default=None, min_length=1, max_length=3)
    video_type: VideoType = "stickman"
    target_platform: PlatformId = "download"
    target_platforms: list[PlatformId] = Field(default_factory=list, max_length=15)
    script_generator: Literal["qwen", "gemini_cli"] = "qwen"
    script_mode: Literal["scenes", "story"] = "scenes"
    production_config: ProductionConfig | None = None
    generation_id: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    )

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def normalize_targets(self):
        self.aspect_ratios = list(dict.fromkeys(self.aspect_ratios or [self.aspect_ratio]))
        self.aspect_ratio = self.aspect_ratios[0]
        selected = self.target_platforms if "target_platforms" in self.model_fields_set else [self.target_platform]
        self.target_platforms = list(dict.fromkeys(selected))
        if self.target_platforms:
            self.target_platform = self.target_platforms[0]
        if self.production_config is not None:
            self.video_type = self.production_config.video_type
            if self.production_config.script_provider in {"qwen", "gemini_cli"}:
                self.script_generator = self.production_config.script_provider
        return self


class ProductionConfigUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    production_config: ProductionConfig


class ScriptUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    title: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=5000)
    scenes: list[Scene] = Field(min_length=1, max_length=30)


class SceneUpdate(BaseModel):
    stickman: StickmanBoard | None = None
    expected_version: int = Field(ge=1)
    narration: str | None = Field(default=None, min_length=2, max_length=1200)
    visual: str | None = Field(default=None, min_length=2, max_length=1200)
    visual_type: Literal[
        "stickman", "generated_image", "generated_video", "stock_image", "stock_video",
        "motion_graphics", "talking_head", "waveform",
    ] | None = None
    source_strategy: Literal["generate", "stock", "provided", "procedural", "recorded"] | None = None
    source_ref: str | None = Field(default=None, max_length=2000)
    asset_query: str | None = Field(default=None, max_length=200)
    asset_prompt: str | None = Field(default=None, max_length=2000)
    on_screen_text: str | None = Field(default=None, max_length=240)
    camera: str | None = Field(default=None, max_length=500)
    transition: Literal["cut", "dissolve", "wipe", "zoom", "match_cut", "none"] | None = None
    duration_seconds: float | None = Field(default=None, gt=0, le=180)
    action: Literal["intro", "stand", "walk", "point", "think", "explain", "celebrate", "outro"] | None = None
    accent: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_dump(exclude={"expected_version"}, exclude_none=True):
            raise ValueError("Mindestens ein Szenenfeld muss geändert werden")
        return self


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
    scene_id: str | None = Field(default=None, min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]+$")
    story_mode: bool = False

    @field_validator("instructions")
    @classmethod
    def normalize_instructions(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 3:
            raise ValueError("Bitte einen konkreten Änderungswunsch eingeben.")
        return value


class VoicePreview(BaseModel):
    voice_id: Literal["thorsten", "thorsten_amused", "kerstin", "ljspeech", "qwen_narrator"]
    text: str = Field(min_length=3, max_length=600)
    speed: float = Field(default=1.0, ge=0.85, le=1.25, allow_inf_nan=False)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 3:
            raise ValueError("Bitte einen hörbaren Sprechertext eingeben.")
        return value

class VersionAction(BaseModel):
    expected_version: int = Field(ge=1)
    expected_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class VideoApproval(VersionAction):
    target_platforms: list[PlatformId] | None = Field(default=None, min_length=1, max_length=15)
