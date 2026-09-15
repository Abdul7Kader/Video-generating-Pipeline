from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0").lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("DATA_DIR", "./data")).resolve()
    renderer_dir: Path = Path(os.getenv("RENDERER_DIR", "./renderer")).resolve()
    # "auto" uses only an explicitly configured API key. It never falls back to
    # a generic template, because that would make a failed AI request look like a
    # successful, topic-specific script.
    script_provider: str = os.getenv("SCRIPT_PROVIDER", "ollama").lower()
    allow_template_script: bool = _bool("ALLOW_TEMPLATE_SCRIPT", False)
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3.5:9b-q4_K_M")
    ollama_num_ctx: int = max(4096, min(16384, int(os.getenv("OLLAMA_NUM_CTX", "8192"))))
    ollama_num_predict: int = max(1024, min(4096, int(os.getenv("OLLAMA_NUM_PREDICT", "3072"))))
    ollama_timeout_seconds: int = max(60, min(1200, int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))))
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "5m")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "")
    asset_provider: str = os.getenv("ASSET_PROVIDER", "auto").lower()
    pexels_api_key: str = os.getenv("PEXELS_API_KEY", "")
    media_download_max_mb: int = max(10, min(500, int(os.getenv("MEDIA_DOWNLOAD_MAX_MB", "150"))))
    allow_paid_media: bool = _bool("ALLOW_PAID_MEDIA", False)
    tts_provider: str = os.getenv("TTS_PROVIDER", "piper").lower()
    allow_cloud_tts: bool = _bool("ALLOW_CLOUD_TTS", False)
    gemini_tts_model: str = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
    gemini_tts_voice: str = os.getenv("GEMINI_TTS_VOICE", "Iapetus")
    gemini_tts_style: str = os.getenv(
        "GEMINI_TTS_STYLE",
        "Natural documentary narration, warm and confident, clear articulation, moderate pace, no exaggerated advertising tone.",
    )
    piper_voice: str = os.getenv("PIPER_VOICE", "de_DE-thorsten-high")
    piper_auto_download: bool = _bool("PIPER_AUTO_DOWNLOAD", True)
    render_concurrency: int = max(1, min(3, int(os.getenv("RENDER_CONCURRENCY", "2"))))
    youtube_enabled: bool = _bool("YOUTUBE_ENABLED")
    youtube_client_secrets: Path = Path(os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "/data/secrets/youtube-client.json"))
    youtube_token: Path = Path(os.getenv("YOUTUBE_TOKEN_FILE", "/data/secrets/youtube-token.json"))
    youtube_privacy: str = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")

    @property
    def database_path(self) -> Path:
        return self.data_dir / "pipeline.sqlite3"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def voices_dir(self) -> Path:
        return self.data_dir / "voices"


settings = Settings()
