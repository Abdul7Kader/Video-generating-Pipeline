from __future__ import annotations

import json
import shutil
import subprocess
import wave
from array import array
from pathlib import Path
from typing import Any

from .plan import file_sha256


class QualityGateError(RuntimeError):
    pass


def _check(name: str, passed: bool, details: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def find_ffprobe() -> str | None:
    system = shutil.which("ffprobe")
    if system:
        return system
    project_root = Path(__file__).resolve().parent.parent
    for platform in ("compositor-linux-x64-gnu", "compositor-linux-x64-musl"):
        candidate = project_root / "renderer" / "node_modules" / "@remotion" / platform / "ffprobe"
        if candidate.is_file() and candidate.stat().st_mode & 0o111:
            return str(candidate)
    return None


def _probe(path: Path) -> dict[str, Any]:
    executable = find_ffprobe()
    if not executable:
        raise QualityGateError("ffprobe fehlt; Audio-/Videoströme können nicht verlässlich geprüft werden.")
    result = subprocess.run(
        [executable, "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name", "-of", "json", str(path)],
        text=True,
        capture_output=True,
        timeout=60,
        check=True,
    )
    return json.loads(result.stdout)


def run_quality_gate(
    *,
    output_path: Path,
    audio_path: Path,
    subtitles_path: Path,
    asset_manifest_path: Path,
    expected_duration: float,
    expected_script_hash: str,
    report_path: Path,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())
            audio_duration = wav_file.getnframes() / wav_file.getframerate()
            samples = array("h", frames[: min(len(frames), wav_file.getframerate() * wav_file.getsampwidth() * 30)])
            peak = max((abs(sample) for sample in samples), default=0)
        checks.append(_check("voice_audio", audio_duration > 0.5 and peak > 32, f"duration={audio_duration:.3f}s peak={peak}"))
    except Exception as exc:
        checks.append(_check("voice_audio", False, str(exc)))

    subtitle_text = subtitles_path.read_text(encoding="utf-8") if subtitles_path.exists() else ""
    cue_count = subtitle_text.count(" --> ")
    checks.append(_check("subtitles", cue_count > 0, f"cues={cue_count}"))

    manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8")) if asset_manifest_path.exists() else {"assets": []}
    asset_failures = []
    for asset in manifest.get("assets") or []:
        if asset.get("status") == "procedural":
            continue
        local_file = asset_manifest_path.parent / str(asset.get("local_file") or "")
        if not local_file.exists() or file_sha256(local_file) != asset.get("sha256"):
            asset_failures.append(str(asset.get("scene_id")))
    checks.append(_check("scene_assets", not asset_failures and bool(manifest.get("assets")), f"invalid={asset_failures}"))

    checks.append(_check("script_binding", bool(expected_script_hash), f"script_hash={expected_script_hash}"))
    checks.append(_check("output_file", output_path.exists() and output_path.stat().st_size >= 10_000, f"bytes={output_path.stat().st_size if output_path.exists() else 0}"))

    try:
        probe = _probe(output_path)
        streams = probe.get("streams") or []
        has_video = any(stream.get("codec_type") == "video" for stream in streams)
        has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
        duration = float((probe.get("format") or {}).get("duration") or 0)
        tolerance = max(1.0, expected_duration * 0.05)
        checks.append(_check("video_stream", has_video, json.dumps(streams, ensure_ascii=False)))
        checks.append(_check("audio_stream", has_audio, json.dumps(streams, ensure_ascii=False)))
        checks.append(_check("duration", abs(duration - expected_duration) <= tolerance, f"actual={duration:.3f}s expected={expected_duration:.3f}s tolerance={tolerance:.3f}s"))
    except Exception as exc:
        checks.append(_check("media_probe", False, str(exc)))

    report = {"passed": all(check["passed"] for check in checks), "checks": checks}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not report["passed"]:
        failures = "; ".join(f"{check['name']}: {check['details']}" for check in checks if not check["passed"])
        raise QualityGateError(f"Qualitätsprüfung fehlgeschlagen: {failures}")
    return report
