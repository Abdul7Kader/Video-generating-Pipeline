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
    script_provider: str = os.getenv("SCRIPT_PROVIDER", "template").lower()
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "z-ai/glm-5.2:free")
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
