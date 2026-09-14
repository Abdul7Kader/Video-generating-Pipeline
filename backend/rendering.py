from __future__ import annotations

import json
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

from .config import settings


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


def synthesize(text: str, output: Path, fallback_duration: float) -> tuple[str, float]:
    model = ensure_voice()
    if model:
        try:
            from piper import PiperVoice

            voice = PiperVoice.load(str(model), use_cuda=False)
            with wave.open(str(output), "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)
            with wave.open(str(output), "rb") as wav_file:
                duration = wav_file.getnframes() / wav_file.getframerate()
            return "piper", max(1.0, duration)
        except Exception:
            pass
    duration = max(5.0, fallback_duration)
    sample_rate = 24000
    frames_left = int(duration * sample_rate)
    silence = b"\x00\x00" * min(sample_rate, frames_left)
    with wave.open(str(output), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        while frames_left:
            count = min(sample_rate, frames_left)
            wav_file.writeframes(silence[: count * 2])
            frames_left -= count
    return "silent_fallback", duration


def render_job(job: dict[str, Any]) -> tuple[str, str]:
    version = int(job["render_version"])
    job_dir = settings.jobs_dir / job["id"] / f"v{version}"
    job_dir.mkdir(parents=True, exist_ok=True)
    narration = " ".join(scene["narration"] for scene in job["script"]["scenes"])
    audio_path = job_dir / "narration.wav"
    tts_mode, audio_duration = synthesize(narration, audio_path, float(job["duration_seconds"]))

    total = max(float(job["duration_seconds"]), audio_duration + 0.6)
    weights = [max(1, len(scene["narration"].split())) for scene in job["script"]["scenes"]]
    weight_sum = sum(weights)
    scenes = []
    cursor = 0.0
    for index, (scene, weight) in enumerate(zip(job["script"]["scenes"], weights)):
        duration = total - cursor if index == len(weights) - 1 else total * weight / weight_sum
        scenes.append({**scene, "start": cursor, "duration": duration})
        cursor += duration

    props = {
        "title": job["script"]["title"],
        "scenes": scenes,
        "durationSeconds": total,
        "aspectRatio": job["aspect_ratio"],
        "language": job["language"],
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
    return str(output_path), tts_mode


def dependency_status() -> dict[str, Any]:
    return {
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "node": bool(shutil.which("node")),
        "piper_voice": _voice_model().exists(),
        "renderer": (settings.renderer_dir / "render.mjs").exists(),
    }
