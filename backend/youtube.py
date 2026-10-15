from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import settings


def upload_video(job: dict[str, Any], video_path: Path) -> str:
    """Upload exactly one approved render. Caller persists the returned video id."""
    from .integrations import load,path as integration_path
    from .credentials import credentials as vault
    preferences = load()
    native = preferences.youtube_enabled
    if not native and integration_path().exists():
        raise RuntimeError('YouTube ist unter Einstellungen deaktiviert.')
    if not native and not settings.youtube_enabled:
        raise RuntimeError("YouTube-Upload ist deaktiviert")
    if not native and (not settings.youtube_client_secrets.exists() or not settings.youtube_token.exists()):
        raise RuntimeError("YouTube-OAuth-Dateien fehlen")

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    if native:
        refresh, secret = vault.get('youtube_refresh_token'), vault.get('youtube_client_secret')
        if not refresh or not secret or not preferences.youtube_client_id:
            raise RuntimeError('YouTube-Zugang fehlt. Unter Einstellungen mit YouTube verbinden.')
        credentials = Credentials(token=None, refresh_token=refresh, client_id=preferences.youtube_client_id,
            client_secret=secret, token_uri='https://oauth2.googleapis.com/token',
            scopes=['https://www.googleapis.com/auth/youtube.upload'])
        try:
            credentials.refresh(Request())
        except Exception:
            raise RuntimeError('Die YouTube-Anmeldung muss erneuert werden; es wurde kein Upload gestartet.') from None
    else:
        credentials = Credentials.from_authorized_user_file(str(settings.youtube_token), ["https://www.googleapis.com/auth/youtube.upload"])
    if not native and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        settings.youtube_token.write_text(credentials.to_json(), encoding="utf-8")
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": job["script"]["title"], "description": job["script"]["description"], "categoryId": "27"},
            "status": {"privacyStatus": preferences.youtube_privacy if native else settings.youtube_privacy, "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    return str(response["id"])
