from __future__ import annotations

import http.client
import json
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlparse

from .config import settings


def validate_base_url(value: str) -> tuple[str, int | None]:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise RuntimeError("MASTODON_BASE_URL muss eine feste HTTPS-Instanz ohne Pfad oder Zugangsdaten sein.")
    return parsed.hostname, parsed.port


def build_status_payload(job: dict[str, Any], media_id: str) -> bytes:
    visibility = settings.mastodon_visibility
    if visibility not in {"public", "unlisted", "private"}:
        raise RuntimeError("MASTODON_VISIBILITY muss public, unlisted oder private sein.")
    title = str(job["script"]["title"]).strip()
    description = str(job["script"].get("description") or "").strip()
    text = title if not description else f"{title}\n\n{description}"
    return urlencode({
        "status": text[:480],
        "media_ids[]": media_id,
        "visibility": visibility,
        "language": job.get("language", "de"),
    }).encode()


def _connection() -> http.client.HTTPSConnection:
    host, port = validate_base_url(settings.mastodon_base_url)
    return http.client.HTTPSConnection(host, port=port, timeout=300)


def _read_json(response: http.client.HTTPResponse, operation: str) -> dict[str, Any]:
    body = response.read(2_000_000)
    if response.status < 200 or response.status >= 300:
        raise RuntimeError(f"Mastodon {operation} antwortete mit HTTP {response.status}.")
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"Mastodon {operation} lieferte keine gültige JSON-Antwort.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Mastodon {operation} lieferte ein unerwartetes Ergebnis.")
    return payload


def _upload_media(video_path: Path) -> dict[str, Any]:
    boundary = f"----VideoPipeline{uuid.uuid4().hex}"
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="video.mp4"\r\n'
        "Content-Type: video/mp4\r\n\r\n"
    ).encode()
    suffix = f"\r\n--{boundary}--\r\n".encode()
    connection = _connection()
    try:
        connection.putrequest("POST", "/api/v2/media")
        connection.putheader("Authorization", f"Bearer {settings.mastodon_access_token}")
        connection.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
        connection.putheader("Content-Length", str(len(prefix) + video_path.stat().st_size + len(suffix)))
        connection.endheaders()
        connection.send(prefix)
        with video_path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                connection.send(chunk)
        connection.send(suffix)
        return _read_json(connection.getresponse(), "Medienupload")
    finally:
        connection.close()


def _request_json(method: str, path: str, *, body: bytes | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    connection = _connection()
    request_headers = {"Authorization": f"Bearer {settings.mastodon_access_token}", **(headers or {})}
    try:
        connection.request(method, path, body=body, headers=request_headers)
        return _read_json(connection.getresponse(), path)
    finally:
        connection.close()


def publish_video(job: dict[str, Any], video_path: Path) -> tuple[str, str | None]:
    if not settings.mastodon_enabled or not settings.mastodon_access_token:
        raise RuntimeError("Mastodon-Veröffentlichung ist nicht vollständig konfiguriert.")
    validate_base_url(settings.mastodon_base_url)
    media = _upload_media(video_path)
    media_id = str(media.get("id") or "")
    if not media_id:
        raise RuntimeError("Mastodon lieferte keine Medien-ID.")
    for _ in range(15):
        if media.get("url"):
            break
        time.sleep(2)
        media = _request_json("GET", f"/api/v1/media/{quote(media_id, safe='')}")
    if not media.get("url"):
        raise RuntimeError("Mastodon hat das Video nicht rechtzeitig verarbeitet; Status muss manuell geprüft werden.")
    output_hash = str(job.get("approved_output_sha256") or job.get("output_sha256") or "")
    idempotency_key = f"publish:v1:{job['id']}:mastodon:{output_hash}"
    status = _request_json(
        "POST",
        "/api/v1/statuses",
        body=build_status_payload(job, media_id),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Idempotency-Key": idempotency_key,
        },
    )
    remote_id = str(status.get("id") or "")
    remote_url = status.get("url")
    if not remote_id or (remote_url is not None and not str(remote_url).startswith("https://")):
        raise RuntimeError("Mastodon lieferte keine gültige Veröffentlichungsreferenz.")
    return remote_id, str(remote_url) if remote_url else None
