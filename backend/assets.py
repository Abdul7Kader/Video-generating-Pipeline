from __future__ import annotations

import json
import mimetypes
import shutil
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .config import settings
from .plan import file_sha256, object_sha256


PEXELS_LICENSE_URL = "https://www.pexels.com/license/"
PEXELS_API_URL = "https://api.pexels.com/v1"
ALLOWED_MEDIA_HOSTS = {"images.pexels.com", "videos.pexels.com"}


class AssetResolutionError(RuntimeError):
    pass


def asset_provider_status() -> dict[str, Any]:
    return {
        "stock": {
            "ready": bool(settings.pexels_api_key),
            "provider": "pexels" if settings.pexels_api_key else None,
            "cost": "free_api_key",
            "attribution_required_in_app": True,
        },
        "generated_image": {
            "ready": False,
            "reason": "Kein kostenfreier, lokal sinnvoller Qualitätsadapter konfiguriert.",
            "paid_media_allowed": settings.allow_paid_media,
        },
        "generated_video": {
            "ready": False,
            "reason": "Generatives Video benötigt einen ausdrücklich genehmigten kostenpflichtigen Adapter.",
            "paid_media_allowed": settings.allow_paid_media,
        },
    }


def render_plan_readiness(scenes: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    for scene in scenes:
        scene_id = scene.get("scene_id") or "unbekannte Szene"
        visual_type = scene.get("visual_type", "stickman")
        if visual_type == "stickman":
            continue
        if visual_type in {"stock_image", "stock_video"}:
            if not settings.pexels_api_key:
                issues.append(f"{scene_id}: PEXELS_API_KEY fehlt für {visual_type}.")
            if not (scene.get("asset_query") or "").strip():
                issues.append(f"{scene_id}: asset_query fehlt für die Stocksuche.")
            continue
        if visual_type in {"generated_image", "generated_video"}:
            issues.append(f"{scene_id}: {visual_type} ist ohne genehmigten kostenpflichtigen Medienadapter nicht verfügbar.")
            continue
        issues.append(f"{scene_id}: Der visuelle Typ {visual_type} besitzt noch keinen verifizierten Renderer.")
    return issues


def _get_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise AssetResolutionError(f"Pexels antwortete mit HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise AssetResolutionError(f"Pexels ist nicht erreichbar: {exc.reason}") from exc


def _search_pexels(kind: str, query: str, aspect_ratio: str, duration: float) -> dict[str, Any]:
    orientation = "portrait" if aspect_ratio == "9:16" else "landscape" if aspect_ratio == "16:9" else "square"
    params = urllib.parse.urlencode({"query": query, "orientation": orientation, "per_page": 15, "size": "large"})
    endpoint = "videos/search" if kind == "stock_video" else "search"
    data = _get_json(
        f"{PEXELS_API_URL}/{endpoint}?{params}",
        {"Authorization": settings.pexels_api_key, "User-Agent": "local-video-pipeline/2"},
    )
    if kind == "stock_image":
        photos = data.get("photos") or []
        if not photos:
            raise AssetResolutionError(f"Keine Pexels-Fotos für Suchbegriff „{query}“ gefunden.")
        photo = photos[0]
        source_url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large") or photo.get("src", {}).get("original")
        if not source_url:
            raise AssetResolutionError("Pexels-Foto enthält keine nutzbare Datei.")
        return {
            "download_url": source_url,
            "page_url": photo.get("url", ""),
            "creator": photo.get("photographer", "Unbekannt"),
            "creator_url": photo.get("photographer_url", ""),
            "media_id": str(photo.get("id", "")),
            "kind": "image",
        }

    videos = data.get("videos") or []
    if not videos:
        raise AssetResolutionError(f"Keine Pexels-Videos für Suchbegriff „{query}“ gefunden.")
    target_aspect = 9 / 16 if aspect_ratio == "9:16" else 16 / 9 if aspect_ratio == "16:9" else 1
    candidates: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    for video in videos:
        for file in video.get("video_files") or []:
            width, height = int(file.get("width") or 0), int(file.get("height") or 0)
            if file.get("file_type") != "video/mp4" or not file.get("link") or width < 640 or height < 640:
                continue
            aspect_penalty = abs((width / height) - target_aspect) if height else 10
            duration_penalty = 0 if float(video.get("duration") or 0) >= min(duration, 8) else 1
            resolution_penalty = abs(max(width, height) - 1920) / 1920
            candidates.append((aspect_penalty * 10 + duration_penalty + resolution_penalty, video, file))
    if not candidates:
        raise AssetResolutionError("Pexels-Suchergebnis enthält kein geeignetes MP4 in ausreichender Auflösung.")
    _, video, file = min(candidates, key=lambda item: item[0])
    user = video.get("user") or {}
    return {
        "download_url": file["link"],
        "page_url": video.get("url", ""),
        "creator": user.get("name", "Unbekannt"),
        "creator_url": user.get("url", ""),
        "media_id": str(video.get("id", "")),
        "kind": "video",
    }


def _download_media(url: str, destination: Path) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_MEDIA_HOSTS:
        raise AssetResolutionError("Nicht erlaubte Medienquelle; Download gestoppt.")
    request = urllib.request.Request(url, headers={"User-Agent": "local-video-pipeline/2"})
    limit = settings.media_download_max_mb * 1024 * 1024
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            content_type = response.headers.get_content_type()
            declared = int(response.headers.get("Content-Length") or 0)
            if declared > limit:
                raise AssetResolutionError(f"Asset ist größer als das konfigurierte Limit von {settings.media_download_max_mb} MB.")
            size = 0
            with destination.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > limit:
                        raise AssetResolutionError(f"Asset überschreitet das konfigurierte Limit von {settings.media_download_max_mb} MB.")
                    output.write(chunk)
    except AssetResolutionError:
        destination.unlink(missing_ok=True)
        raise
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
        destination.unlink(missing_ok=True)
        raise AssetResolutionError(f"Mediendownload fehlgeschlagen: {exc}") from exc
    if destination.stat().st_size < 1024:
        destination.unlink(missing_ok=True)
        raise AssetResolutionError("Heruntergeladenes Asset ist leer oder beschädigt.")
    return content_type


def _cached_asset(job_dir: Path, scene_id: str, fingerprint: str) -> tuple[Path, dict[str, Any]] | None:
    manifests = sorted(job_dir.parent.glob("v*/asset-manifest.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for manifest_path in manifests:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for asset in manifest.get("assets") or []:
            if asset.get("scene_id") != scene_id or asset.get("fingerprint") != fingerprint or asset.get("status") != "ready":
                continue
            source = manifest_path.parent / str(asset.get("local_file") or "")
            if source.is_file() and file_sha256(source) == asset.get("sha256"):
                return source, asset
    return None


def prepare_scene_assets(job_dir: Path, scenes: list[dict[str, Any]], aspect_ratio: str) -> dict[str, Any]:
    issues = render_plan_readiness(scenes)
    if issues:
        raise AssetResolutionError("Szenenplan nicht produzierbar: " + " ".join(issues))
    assets_dir = job_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"provider": "pexels" if settings.pexels_api_key else None, "license_url": PEXELS_LICENSE_URL, "assets": []}
    for scene in scenes:
        visual_type = scene.get("visual_type", "stickman")
        fingerprint = object_sha256({
            "visual_type": visual_type,
            "source_strategy": scene.get("source_strategy"),
            "source_ref": scene.get("source_ref"),
            "asset_query": scene.get("asset_query"),
            "asset_prompt": scene.get("asset_prompt"),
            "aspect_ratio": aspect_ratio,
        })
        if visual_type == "stickman":
            manifest["assets"].append({
                "scene_id": scene.get("scene_id"), "status": "procedural", "visual_type": visual_type, "fingerprint": fingerprint,
            })
            continue
        query = str(scene.get("asset_query") or "").strip()
        cached = _cached_asset(job_dir, str(scene["scene_id"]), fingerprint)
        if cached:
            source, previous = cached
            extension = source.suffix
            destination = assets_dir / f"{scene['scene_id']}{extension}"
            if source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
            scene["asset_path"] = str(destination.resolve())
            scene["asset_kind"] = previous["kind"]
            scene["source_ref"] = previous.get("page_url", "")
            manifest["assets"].append({
                **previous,
                "local_file": str(destination.relative_to(job_dir)),
                "reused_from": str(source),
                "fingerprint": fingerprint,
            })
            continue
        selection = _search_pexels(visual_type, query, aspect_ratio, float(scene.get("duration_seconds") or 5))
        extension = ".mp4" if selection["kind"] == "video" else ".jpg"
        destination = assets_dir / f"{scene['scene_id']}{extension}"
        content_type = _download_media(selection.pop("download_url"), destination)
        if selection["kind"] == "video" and content_type not in {"video/mp4", "application/octet-stream"}:
            destination.unlink(missing_ok=True)
            raise AssetResolutionError(f"Unerwarteter Medientyp für {scene['scene_id']}: {content_type}")
        if selection["kind"] == "image" and not content_type.startswith("image/"):
            destination.unlink(missing_ok=True)
            raise AssetResolutionError(f"Unerwarteter Medientyp für {scene['scene_id']}: {content_type}")
        scene["asset_path"] = str(destination.resolve())
        scene["asset_kind"] = selection["kind"]
        scene["source_ref"] = selection["page_url"]
        manifest["assets"].append({
            "scene_id": scene["scene_id"],
            "status": "ready",
            "visual_type": visual_type,
            "query": query,
            "fingerprint": fingerprint,
            "local_file": str(destination.relative_to(job_dir)),
            "sha256": file_sha256(destination),
            "content_type": content_type or mimetypes.guess_type(destination.name)[0],
            "provider": "pexels",
            "license_url": PEXELS_LICENSE_URL,
            **selection,
        })
    manifest_path = job_dir / "asset-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
