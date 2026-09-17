from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import settings


_PROFILES: tuple[dict[str, Any], ...] = (
    {"id": "download", "label": "Lokaler Download", "category": "local", "delivery_mode": "download", "preferred_aspect_ratio": "any", "media": "video"},
    {"id": "youtube", "label": "YouTube / Shorts", "category": "social_video", "delivery_mode": "automatic", "preferred_aspect_ratio": "16:9 oder 9:16", "media": "video"},
    {"id": "mastodon", "label": "Mastodon", "category": "social_video", "delivery_mode": "automatic", "preferred_aspect_ratio": "16:9 oder 1:1", "media": "video"},
    {"id": "tiktok", "label": "TikTok", "category": "social_video", "delivery_mode": "automatic", "preferred_aspect_ratio": "9:16", "media": "video"},
    {"id": "instagram_reels", "label": "Instagram Reels", "category": "social_video", "delivery_mode": "automatic", "preferred_aspect_ratio": "9:16", "media": "video"},
    {"id": "facebook_reels", "label": "Facebook Reels", "category": "social_video", "delivery_mode": "automatic", "preferred_aspect_ratio": "9:16", "media": "video"},
    {"id": "linkedin", "label": "LinkedIn", "category": "social_video", "delivery_mode": "automatic", "preferred_aspect_ratio": "16:9 oder 1:1", "media": "video"},
    {"id": "x", "label": "X", "category": "social_video", "delivery_mode": "automatic", "preferred_aspect_ratio": "16:9 oder 1:1", "media": "video"},
    {"id": "bluesky", "label": "Bluesky", "category": "social_video", "delivery_mode": "automatic", "preferred_aspect_ratio": "16:9 oder 1:1", "media": "video"},
    {"id": "spotify_podcast", "label": "Spotify Podcasts", "category": "podcast", "delivery_mode": "rss", "preferred_aspect_ratio": "Audio / RSS", "media": "podcast"},
    {"id": "apple_podcasts", "label": "Apple Podcasts", "category": "podcast", "delivery_mode": "rss", "preferred_aspect_ratio": "Audio / RSS", "media": "podcast"},
    {"id": "amazon_music_podcast", "label": "Amazon Music Podcasts", "category": "podcast", "delivery_mode": "rss", "preferred_aspect_ratio": "Audio / RSS", "media": "podcast"},
    {"id": "soundcloud", "label": "SoundCloud", "category": "audio", "delivery_mode": "automatic", "preferred_aspect_ratio": "Audio", "media": "audio"},
    {"id": "spotify_music", "label": "Spotify Music", "category": "music", "delivery_mode": "distributor", "preferred_aspect_ratio": "Musik-Master + Cover", "media": "song"},
    {"id": "apple_music", "label": "Apple Music", "category": "music", "delivery_mode": "distributor", "preferred_aspect_ratio": "Musik-Master + Cover", "media": "song"},
)

PLATFORM_IDS = tuple(profile["id"] for profile in _PROFILES)


def profile_for(platform: str) -> dict[str, Any]:
    profile = next((item for item in _PROFILES if item["id"] == platform), None)
    if not profile:
        raise ValueError("unknown_platform")
    return dict(profile)


def _mastodon_configured(config: Any) -> bool:
    if not getattr(config, "mastodon_enabled", False) or not getattr(config, "mastodon_access_token", ""):
        return False
    parsed = urlparse(getattr(config, "mastodon_base_url", ""))
    visibility = getattr(config, "mastodon_visibility", "private")
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and not parsed.username
        and not parsed.password
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
        and visibility in {"public", "unlisted", "private"}
    )


def _youtube_configured(config: Any) -> bool:
    if not getattr(config, "youtube_enabled", False):
        return False
    secrets = getattr(config, "youtube_client_secrets", None)
    token = getattr(config, "youtube_token", None)
    return isinstance(secrets, Path) and secrets.is_file() and isinstance(token, Path) and token.is_file()


def configured_automatic_platforms(config: Any = settings) -> set[str]:
    enabled: set[str] = set()
    if _youtube_configured(config):
        enabled.add("youtube")
    if _mastodon_configured(config):
        enabled.add("mastodon")
    return enabled


def platform_catalog(config: Any = settings) -> list[dict[str, Any]]:
    enabled = configured_automatic_platforms(config)
    result = []
    for profile in _PROFILES:
        item = dict(profile)
        item["configured"] = profile["id"] == "download" or profile["id"] in enabled
        if profile["delivery_mode"] == "rss":
            item["setup_hint"] = "Öffentliches Podcast-Hosting mit RSS-Feed erforderlich"
        elif profile["delivery_mode"] == "distributor":
            item["setup_hint"] = "Musikdistributor erforderlich"
        elif profile["delivery_mode"] == "automatic" and profile["id"] not in {"youtube", "mastodon"}:
            item["setup_hint"] = "Offizielle Entwickler-App und OAuth-Adapter noch einzurichten"
        elif profile["id"] in {"youtube", "mastodon"} and profile["id"] not in enabled:
            item["setup_hint"] = "Zugangsdaten fehlen oder Adapter ist deaktiviert"
        else:
            item["setup_hint"] = "Bereit"
        result.append(item)
    return result


def publish_to_target(job: dict[str, Any], video_path, platform: str) -> tuple[str, str | None]:
    if platform == "youtube":
        from .youtube import upload_video

        remote_id = upload_video(job, video_path)
        return remote_id, f"https://www.youtube.com/watch?v={remote_id}"
    if platform == "mastodon":
        from .mastodon import publish_video

        return publish_video(job, video_path)
    raise RuntimeError(f"Für {platform} ist kein automatischer Veröffentlichungsadapter aktiv.")
