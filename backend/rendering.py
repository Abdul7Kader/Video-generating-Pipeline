from __future__ import annotations

import base64
import json
import shutil
import subprocess
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any

from .assets import prepare_scene_assets
from .captions import add_scene_captions, write_srt
from .config import settings
from .quality import find_ffprobe, run_quality_gate


def _run(command: list[str], *, input_text: str | None = None, timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, input=input_text, text=True, capture_output=True, check=True, timeout=timeout)
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(f"Prozess fehlgeschlagen ({command[0]}): {details[-4000:]}") from exc


def _voice_model() -> Path:
    return settings.voices_dir / f"{settings.piper_voice}.onnx"


def ensure_voice() -> Path | None:
    model = _voice_model()
    if model.exists() and model.with_suffix(".onnx.json").exists():
        return model
    if not settings.piper_auto_download:
        return None
    settings.voices_dir.mkdir(parents=True, exist_ok=True)
    try:
        _run(["python3", "-m", "piper.download_voices", "--data-dir", str(settings.voices_dir), settings.piper_voice], timeout=900)
    except (subprocess.SubprocessError, OSError):
        return None
    return model if model.exists() else None


def _synthesize_gemini(text: str, output: Path, language: str) -> tuple[str, float]:
    if not settings.allow_cloud_tts:
        raise RuntimeError("Cloud-TTS ist nicht freigegeben. Setze ALLOW_CLOUD_TTS=1 erst nach Kosten-/Datenschutzentscheidung.")
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY fehlt für Gemini TTS.")
    language_name = "German" if language == "de" else "English"
    prompt = (
        f"{settings.gemini_tts_style} Speak in {language_name}. Read the transcript verbatim; do not add, remove or paraphrase words.\n\n"
        f"Transcript:\n{text}"
    )
    payload = {
        "model": settings.gemini_tts_model,
        "input": prompt,
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": settings.gemini_tts_voice}]},
    }
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": settings.gemini_api_key},
        method="POST",
    )
    data: dict[str, Any] | None = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.loads(response.read())
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 500 and attempt == 0:
                continue
            raise RuntimeError(f"Gemini TTS antwortete mit HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Gemini TTS ist nicht erreichbar: {exc.reason}") from exc
    try:
        pcm = base64.b64decode(data["output_audio"]["data"], validate=True)  # type: ignore[index]
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Gemini TTS lieferte keine gültigen Audiodaten.") from exc
    if len(pcm) < 2048:
        raise RuntimeError("Gemini TTS lieferte eine leere oder zu kurze Audiodatei.")
    with wave.open(str(output), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(pcm)
    duration = len(pcm) / (24000 * 2)
    return f"gemini:{settings.gemini_tts_model}:{settings.gemini_tts_voice}", duration


def synthesize(text: str, output: Path, language: str) -> tuple[str, float]:
    if settings.tts_provider == "gemini":
        return _synthesize_gemini(text, output, language)
    if settings.tts_provider != "piper":
        raise RuntimeError(f"Unbekannter TTS_PROVIDER: {settings.tts_provider}")
    model = ensure_voice()
    if not model:
        raise RuntimeError("Keine funktionsfähige Sprecherstimme verfügbar; stumme Ersatzvideos sind deaktiviert.")
    try:
        from piper import PiperVoice

        voice = PiperVoice.load(str(model), use_cuda=False)
        with wave.open(str(output), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        with wave.open(str(output), "rb") as wav_file:
            duration = wav_file.getnframes() / wav_file.getframerate()
        return "piper", max(1.0, duration)
    except Exception as exc:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"Spracherzeugung fehlgeschlagen: {exc}") from exc


def render_job(job: dict[str, Any]) -> tuple[str, str]:
    version = int(job["render_version"])
    job_dir = settings.jobs_dir / job["id"] / f"v{version}"
    job_dir.mkdir(parents=True, exist_ok=True)
    prepare_scene_assets(job_dir, job["script"]["scenes"], job["aspect_ratio"])
    narration = " ".join(scene["narration"] for scene in job["script"]["scenes"])
    audio_path = job_dir / "narration.wav"
    tts_mode, audio_duration = synthesize(narration, audio_path, job["language"])

    total = max(float(job["duration_seconds"]), audio_duration + 0.6)
    weights = [
        max(0.1, float(scene.get("duration_seconds") or len(scene["narration"].split()) or 1))
        for scene in job["script"]["scenes"]
    ]
    weight_sum = sum(weights)
    scenes = []
    cursor = 0.0
    for index, (scene, weight) in enumerate(zip(job["script"]["scenes"], weights)):
        duration = total - cursor if index == len(weights) - 1 else total * weight / weight_sum
        scenes.append({**scene, "start": cursor, "duration": duration})
        cursor += duration
    add_scene_captions(scenes)
    subtitles_path = job_dir / "subtitles.srt"
    write_srt(scenes, subtitles_path)

    props = {
        "title": job["script"]["title"],
        "scenes": scenes,
        "durationSeconds": total,
        "aspectRatio": job["aspect_ratio"],
        "language": job["language"],
        "scriptHash": job["render_script_hash"],
    }
    props_path = job_dir / "render-props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    output_path = job_dir / "video.mp4"
    output_path.unlink(missing_ok=True)
    _run([
        "node", str(settings.renderer_dir / "render.mjs"),
        str(props_path), str(output_path), str(settings.render_concurrency), str(audio_path),
    ], timeout=3600)
    if not output_path.exists() or output_path.stat().st_size < 10_000:
        raise RuntimeError("Renderer hat keine gültige Videodatei erzeugt")
    run_quality_gate(
        output_path=output_path,
        audio_path=audio_path,
        subtitles_path=subtitles_path,
        asset_manifest_path=job_dir / "asset-manifest.json",
        expected_duration=total,
        expected_script_hash=str(job["render_script_hash"]),
        report_path=job_dir / "quality-report.json",
    )
    return str(output_path), tts_mode


def dependency_status() -> dict[str, Any]:
    return {
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "ffprobe": bool(find_ffprobe()),
        "node": bool(shutil.which("node")),
        "piper_voice": _voice_model().exists(),
        "tts_provider": settings.tts_provider,
        "cloud_tts_allowed": settings.allow_cloud_tts,
        "renderer": (settings.renderer_dir / "render.mjs").exists(),
    }
