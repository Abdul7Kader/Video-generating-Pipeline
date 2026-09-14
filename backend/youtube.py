from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import settings


def upload_video(job: dict[str, Any], video_path: Path) -> str:
    """Upload exactly one approved render. Caller persists the returned video id."""
    if not settings.youtube_enabled:
        raise RuntimeError("YouTube-Upload ist deaktiviert")
    if not settings.youtube_client_secrets.exists() or not settings.youtube_token.exists():
        raise RuntimeError("YouTube-OAuth-Dateien fehlen")

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    credentials = Credentials.from_authorized_user_file(str(settings.youtube_token), ["https://www.googleapis.com/auth/youtube.upload"])
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        settings.youtube_token.write_text(credentials.to_json(), encoding="utf-8")
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": job["script"]["title"], "description": job["script"]["description"], "categoryId": "27"},
            "status": {"privacyStatus": settings.youtube_privacy, "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    return str(response["id"])
