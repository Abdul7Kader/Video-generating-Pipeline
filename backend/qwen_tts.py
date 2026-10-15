"""One fixed synthetic narrator, generated offline in a separate Python runtime."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import wave
from pathlib import Path

from .config import settings
from .quality import find_ffmpeg
from .moneyprinter import _safe_environment, _terminate_process_tree

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
MODEL_REVISION = "fd4b254389122332181a7c3db7f27e918eec64e3"
REFERENCE = ROOT / "examples" / "qwen-narrator-reference.wav"
REFERENCE_SHA256 = "866676d828cc7df2cdaf4723f167b6a530298ac72b2f49e7085358075e400ab4"
REFERENCE_TEXT = "Ganz ehrlich: Der Anfang ist oft das Schwerste. Mila legt ihr Handy weg, schlägt ein Buch auf und entdeckt eine Idee, die plötzlich alles verändert."
POLICY = "qwen-fixed-reference-cpu-fp32-v1"
_LOCK = threading.Lock()


def voice_fingerprint() -> dict:
    try:
        reference_hash = hashlib.sha256(REFERENCE.read_bytes()).hexdigest()
    except OSError:
        reference_hash = "missing"
    return {"model": MODEL_ID, "revision": MODEL_REVISION, "reference": reference_hash, "policy": POLICY}


def voice_status() -> dict:
    reason = "Qwen-Stimme einmalig einrichten: siehe docs/qwen-voice.md."
    if (settings.qwen_tts_python.parent.parent / '.pipeline-setup-pending').exists():
        return {'ready':False, 'message':'Die Qwen-Einrichtung ist unvollständig. Öffne die Einstellungen und starte „Qwen-Stimme einrichten“ erneut.'}
    try:
        model = settings.qwen_tts_model_dir
        manifest = json.loads((model / "pipeline-install.json").read_text(encoding="utf-8"))
        ready = (
            settings.qwen_tts_python.is_file()
            and manifest == {"model": MODEL_ID, "revision": MODEL_REVISION, "runtime": "qwen-tts==0.1.1"}
            and (model / "config.json").is_file()
            and any(model.glob("*.safetensors"))
            and (model / "speech_tokenizer" / "config.json").is_file()
            and any((model / "speech_tokenizer").glob("*.safetensors"))
            and voice_fingerprint()["reference"] == REFERENCE_SHA256
        )
    except (OSError, ValueError):
        ready = False
    return {"ready": bool(ready), "message": "" if ready else reason}


def _run_worker(request: dict) -> None:
    command = [str(settings.qwen_tts_python), "-I", str(ROOT / "scripts" / "qwen_voice_worker.py")]
    # Reuse the existing limited environment and owned process-tree cleanup.
    # Windows venv launchers spawn another Python process; killing only the
    # launcher would leave inference running after a timeout.
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    from .process_control import owned_command
    with subprocess.Popen(owned_command(command), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding="utf-8", env=_safe_environment(), **options) as process:
        try:
            _, errors = process.communicate(json.dumps(request), timeout=settings.qwen_tts_timeout_seconds)
        except BaseException:
            _terminate_process_tree(process)
            raise
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command, stderr=errors)


def synthesize(text: str, output: Path, language: str, speed: float) -> tuple[str, float]:
    if language != "de" or not isinstance(text, str) or not 3 <= len(text.strip()) <= 1200:
        raise ValueError("Qwen-Erzähler benötigt einen deutschen Sprechertext mit 3–1200 Zeichen.")
    if not 0.85 <= speed <= 1.25:
        raise ValueError("Unzulässiges Sprechtempo.")
    status = voice_status()
    if not status["ready"]:
        raise RuntimeError(status["message"])
    from .device import device_info, recommendation
    if not recommendation(device_info())["qwen_suitable"]:
        raise RuntimeError('Für Qwen ist aktuell nicht genügend freier Arbeitsspeicher verfügbar. Schließe große Programme oder wähle Piper in den Einstellungen.')
    raw = output.with_name(output.stem + ".qwen-raw.wav")
    request = {
        "text": text, "model": str(settings.qwen_tts_model_dir),
        "output": str(raw.resolve()), "threads": settings.qwen_tts_threads,
    }
    with _LOCK:
        try:
            _run_worker(request)
            if speed == 1:
                raw.replace(output)
            else:
                ffmpeg = find_ffmpeg()
                if not ffmpeg:
                    raise RuntimeError("FFmpeg fehlt für das Qwen-Sprechtempo.")
                subprocess.run(
                    [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
                     "-af", f"atempo={speed}", "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(output)],
                    check=True, capture_output=True, timeout=60,
                )
            with wave.open(str(output), "rb") as audio:
                duration = audio.getnframes() / audio.getframerate()
                if audio.getnchannels() != 1 or audio.getframerate() != 24000 or not 0.1 < duration <= 180:
                    raise ValueError("Ungültige Qwen-Audiodatei.")
            return "qwen_tts", duration
        except (OSError, ValueError, subprocess.SubprocessError, wave.Error) as exc:
            output.unlink(missing_ok=True)
            raise RuntimeError("Lokale Qwen-Spracherzeugung fehlgeschlagen. Laufzeit prüfen; es wird keine Ersatzstimme verwendet.") from exc
        finally:
            raw.unlink(missing_ok=True)
