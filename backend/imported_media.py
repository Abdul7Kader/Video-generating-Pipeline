from __future__ import annotations

import json
from collections.abc import AsyncIterable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .plan import file_sha256
from .quality import probe_media


ALLOWED_SOURCES = {"gemini_app", "notebooklm"}


class ImportedMediaError(ValueError):
    pass


async def save_stream(chunks: AsyncIterable[bytes], destination: Path, *, max_bytes: int) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        with destination.open("xb") as output:
            async for chunk in chunks:
                if not chunk:
                    continue
                written += len(chunk)
                if written > max_bytes:
                    raise ImportedMediaError(f"Die Datei ist größer als das erlaubte Limit von {max_bytes // (1024 * 1024)} MB.")
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return written


def inspect_imported_video(
    path: Path,
    *,
    probe: Callable[[Path], dict[str, Any]] = probe_media,
) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size < 10_000:
        raise ImportedMediaError("Die Videodatei ist leer oder unvollständig.")
    try:
        result = probe(path)
    except Exception as exc:
        raise ImportedMediaError(f"Die Videodatei konnte nicht geprüft werden: {exc}") from exc
    streams = result.get("streams") or []
    if not any(stream.get("codec_type") == "video" for stream in streams):
        raise ImportedMediaError("Die Datei enthält keine Videospur.")
    if not any(stream.get("codec_type") == "audio" for stream in streams):
        raise ImportedMediaError("Die Datei enthält keine Audiospur.")
    try:
        duration = float((result.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError) as exc:
        raise ImportedMediaError("Die Videolaufzeit ist ungültig.") from exc
    if duration <= 0:
        raise ImportedMediaError("Die Videolaufzeit ist ungültig.")
    return {
        "duration_seconds": round(duration, 3),
        "size_bytes": path.stat().st_size,
        "streams": [
            {"codec_type": stream.get("codec_type"), "codec_name": stream.get("codec_name")}
            for stream in streams
        ],
    }


def _safe_filename(value: str) -> str:
    name = Path(value.replace("\\", "/")).name.strip()
    return "video.mp4" if not name or name in {".", ".."} else name[:255]


def write_provenance_manifest(
    manifest_path: Path,
    *,
    media_path: Path,
    source: str,
    original_filename: str,
    script_version: int,
    script_hash: str,
    inspection: dict[str, Any],
) -> dict[str, Any]:
    if source not in ALLOWED_SOURCES:
        raise ImportedMediaError("Unbekannte externe Quelle.")
    manifest = {
        "schema_version": 1,
        "source": source,
        "import_method": "official_download_then_local_upload",
        "original_filename": _safe_filename(original_filename),
        "local_file": media_path.name,
        "sha256": file_sha256(media_path),
        "size_bytes": media_path.stat().st_size,
        "duration_seconds": inspection["duration_seconds"],
        "streams": inspection["streams"],
        "script_version": script_version,
        "script_hash": script_hash,
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
