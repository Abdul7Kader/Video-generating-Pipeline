from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any

from .assets import prepare_scene_assets
from .captions import add_scene_captions, write_srt
from .config import settings
from .moneyprinter import moneyprinter_status, render_with_moneyprinter, write_render_comparison
from .plan import file_sha256, object_sha256
from .quality import find_ffmpeg, find_ffprobe, run_quality_gate
from .speech import VOICE_POLICY, TIMING_METHOD, compact_speech, estimate_word_timings, speech_scene_durations, direct_scene
from .continuity import normalize_continuity
from .voices import voice_choice, validate_voice_language
from . import qwen_tts
from .failures import at_stage,failure_stage
from .modes import require_mode

prepare_scene_assets = at_stage('image')(prepare_scene_assets)
run_quality_gate = at_stage('quality')(run_quality_gate)


_PIPER_VOICE_CACHE: dict[str, Any] = {}
_PIPER_LOCK = threading.Lock()


def _run(command: list[str], *, input_text: str | None = None, timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, input=input_text, text=True, capture_output=True, check=True, timeout=timeout)
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(f"Prozess fehlgeschlagen ({command[0]}): {details[-4000:]}") from exc


def _voice_model() -> Path:
    return settings.voices_dir / f"{settings.piper_voice}.onnx"


def ensure_voice(voice_id: str | None = None) -> Path | None:
    model = settings.voices_dir / f"{voice_choice(voice_id)['model']}.onnx" if voice_id else _voice_model()
    if model.stem == 'de_DE-thorsten-high' and (settings.voices_dir / '.piper-setup-pending').exists():
        raise RuntimeError('Die Piper-Einrichtung wurde unterbrochen. Öffne die Einstellungen und lade die Piper-Stimme erneut herunter.')
    if model.exists() and model.with_suffix(".onnx.json").exists():
        return model
    if not settings.piper_auto_download:
        return None
    settings.voices_dir.mkdir(parents=True, exist_ok=True)
    try:
        _run([sys.executable, "-m", "piper.download_voices", "--data-dir", str(settings.voices_dir), model.stem], timeout=900)
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


@at_stage('voice')
def synthesize(text: str, output: Path, language: str, *, provider: str | None = None, voice_id: str | None = None, speed: float = 1.0) -> tuple[str, float]:
    selected_provider = provider or settings.tts_provider
    if selected_provider == "qwen_tts":
        validate_voice_language({"voice_id": voice_id, "voice_provider": selected_provider}, language)
        return qwen_tts.synthesize(text, output, language, speed)
    if selected_provider in {"gemini", "gemini_tts"}:
        return _synthesize_gemini(text, output, language)
    if selected_provider != "piper":
        raise RuntimeError(f"Unbekannter Stimmenanbieter: {selected_provider}")
    voice_id = voice_id or ('thorsten' if language=='de' else 'ljspeech')
    validate_voice_language({"voice_id": voice_id, "voice_provider": selected_provider}, language)
    if not 0.85 <= speed <= 1.25:
        raise ValueError("Unzulässiges Sprechtempo.")
    try:
        from piper import PiperVoice, SynthesisConfig

        # Piper/espeak and downloads share process-global state; serialize them.
        with _PIPER_LOCK:
            model = ensure_voice(voice_id) if voice_id else ensure_voice()
            if not model:
                raise RuntimeError("Keine funktionsfähige Sprecherstimme verfügbar; stumme Ersatzvideos sind deaktiviert.")
            voice = _PIPER_VOICE_CACHE.get(str(model))
            if voice is None:
                voice = PiperVoice.load(str(model), use_cuda=False)
                _PIPER_VOICE_CACHE[str(model)] = voice
            with wave.open(str(output), "wb") as wav_file:
                config = SynthesisConfig(speaker_id=voice_choice(voice_id)["speaker_id"] if voice_id else None, length_scale=voice.config.length_scale / speed)
                voice.synthesize_wav(text, wav_file, syn_config=config)
        with wave.open(str(output), "rb") as wav_file:
            duration = wav_file.getnframes() / wav_file.getframerate()
        return "piper", max(1.0, duration)
    except Exception as exc:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"Spracherzeugung fehlgeschlagen: {exc}") from exc


def _voice_fingerprint(scene: dict[str, Any], language: str, provider: str | None = None, *, continuous: bool = False, voice_id: str | None = None, speed: float = 1.0) -> str:
    provider = provider or settings.tts_provider
    normalized_provider = "gemini" if provider == "gemini_tts" else provider
    configuration = {
        "provider": normalized_provider,
        "language": language,
        "narration": scene["narration"],
        "piper_voice": settings.piper_voice if normalized_provider == "piper" else None,
        "gemini_model": settings.gemini_tts_model if normalized_provider == "gemini" else None,
        "gemini_voice": settings.gemini_tts_voice if normalized_provider == "gemini" else None,
        "gemini_style": settings.gemini_tts_style if normalized_provider == "gemini" else None,
    }
    if continuous:
        configuration["speech_policy"] = VOICE_POLICY
    if voice_id:
        configuration["local_voice"] = voice_choice(voice_id)
        if normalized_provider == "piper":
            configuration["piper_voice"] = voice_choice(voice_id)["model"]
    if normalized_provider == "qwen_tts":
        configuration["qwen_voice"] = qwen_tts.voice_fingerprint()
    if speed != 1.0:
        configuration["speed"] = speed
    return object_sha256(configuration)


def _cached_voice(job_dir: Path, scene_id: str, fingerprint: str) -> tuple[Path, dict[str, Any]] | None:
    manifests = sorted(job_dir.parent.glob("v*/voice-manifest.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for manifest_path in manifests:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for segment in manifest.get("segments") or []:
            if segment.get("scene_id") != scene_id or segment.get("fingerprint") != fingerprint:
                continue
            source = manifest_path.parent / str(segment.get("file") or "")
            if source.is_file() and file_sha256(source) == segment.get("sha256"):
                return source, segment
    return None


@at_stage('voice')
def prepare_scene_audio(
    job_dir: Path,
    scenes: list[dict[str, Any]],
    language: str,
    *,
    provider: str | None = None,
    continuous: bool = False,
    voice_id: str | None = None,
    speed: float = 1.0,
) -> tuple[list[dict[str, Any]], str]:
    audio_dir = job_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    segments: list[dict[str, Any]] = []
    modes: set[str] = set()
    for scene in scenes:
        scene_id = str(scene["scene_id"])
        fingerprint = _voice_fingerprint(scene, language, provider, continuous=continuous, voice_id=voice_id, speed=speed)
        destination = audio_dir / f"{scene_id}.wav"
        cached = _cached_voice(job_dir, scene_id, fingerprint)
        if cached:
            source, previous = cached
            if source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
            mode = str(previous["tts_mode"])
            duration = float(previous["duration"])
            reused_from = str(source)
        else:
            options = {"provider": provider} if provider else {}
            if voice_id or speed != 1.0:
                options.update(voice_id=voice_id, speed=speed)
            with failure_stage('voice',scene_id=scene_id):
                mode, duration = synthesize(str(scene["narration"]), destination, language, **options)
            reused_from = None
        expected_mode = 'gemini' if (provider or settings.tts_provider) in {'gemini','gemini_tts'} else (provider or settings.tts_provider)
        if mode != expected_mode and not (expected_mode=='gemini' and mode.startswith('gemini:')):
            raise RuntimeError('Die erzeugte Stimme entspricht nicht dem ausgewählten Anbieter. Es wird keine Ersatzstimme übernommen.')
        speech = {}
        if continuous:
            if not cached:
                speech = compact_speech(destination)
                duration = speech['duration']
            else:
                speech = previous.get('speech', {})
        modes.add(mode)
        entry = {
            "scene_id": scene_id,
            "fingerprint": fingerprint,
            "file": str(destination.relative_to(job_dir)),
            "sha256": file_sha256(destination),
            "duration": duration,
            "tts_mode": mode,
        }
        if reused_from:
            entry["reused_from"] = reused_from
        if continuous:
            entry['speech'] = speech
            entry['words'] = previous['words'] if cached else estimate_word_timings(str(scene['narration']), destination)
            entry['timing_method'] = TIMING_METHOD
        segments.append(entry)
    if len(modes) != 1:
        raise RuntimeError("Szenen verwenden inkonsistente Sprecherprofile.")
    manifest = {"tts_mode": next(iter(modes)), "segments": segments}
    (job_dir / "voice-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return segments, next(iter(modes))


@at_stage('voice')
def compose_scene_audio(job_dir: Path, segments: list[dict[str, Any]], scene_durations: list[float], output: Path) -> float:
    if len(segments) != len(scene_durations):
        raise ValueError("Audiosegmente und Szenen stimmen nicht überein")
    output_params: tuple[int, int, int] | None = None
    total_frames = 0
    with wave.open(str(output), "wb") as combined:
        for segment, scene_duration in zip(segments, scene_durations):
            source_path = job_dir / segment["file"]
            with wave.open(str(source_path), "rb") as source:
                params = (source.getnchannels(), source.getsampwidth(), source.getframerate())
                if output_params is None:
                    output_params = params
                    combined.setnchannels(params[0])
                    combined.setsampwidth(params[1])
                    combined.setframerate(params[2])
                elif params != output_params:
                    raise RuntimeError("Audiosegmente besitzen unterschiedliche Formate.")
                frames = source.readframes(source.getnframes())
                frame_count = source.getnframes()
                combined.writeframes(frames)
                target_frames = round(scene_duration * params[2])
                padding = max(0, target_frames - frame_count)
                if padding:
                    combined.writeframes(b"\x00" * padding * params[0] * params[1])
                total_frames += max(frame_count, target_frames)
    if output_params is None:
        raise RuntimeError("Keine Audiosegmente vorhanden.")
    return total_frames / output_params[2]


@at_stage('voice')
def normalize_narration_audio(audio_path: Path) -> float:
    """Normalize speech to a platform-friendly -16 LUFS with true-peak headroom."""
    executable = find_ffmpeg()
    if not executable:
        raise RuntimeError("ffmpeg fehlt; die Sprachlautheit kann nicht normalisiert werden.")
    normalized = audio_path.with_name(f"{audio_path.stem}.normalized.wav")
    normalized.unlink(missing_ok=True)
    try:
        _run([
            executable,
            "-y",
            "-i",
            str(audio_path),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(normalized),
        ], timeout=600)
        if not normalized.is_file() or normalized.stat().st_size < 1000:
            raise RuntimeError("ffmpeg hat keine normalisierte Sprachdatei erzeugt.")
        with wave.open(str(normalized), "rb") as wav_file:
            duration = wav_file.getnframes() / wav_file.getframerate()
        normalized.replace(audio_path)
        return duration
    finally:
        normalized.unlink(missing_ok=True)


@at_stage('render')
def render_job(job: dict[str, Any], *, job_dir_override: Path | None = None) -> tuple[str, str]:
    require_mode(job.get('generation_mode','animated'))
    version = int(job["render_version"])
    job_dir = job_dir_override or settings.jobs_dir / job["id"] / f"v{version}"
    job_dir.mkdir(parents=True, exist_ok=True)
    production_config = job.get("production_config") or job["script"].get("production_config") or {}
    editor = production_config.get("editor", "remotion")
    if editor not in {"remotion", "moneyprinter"}:
        raise RuntimeError(f"Der gewählte Schnittanbieter {editor} ist noch nicht integriert.")
    if editor == 'remotion' and all(scene.get('visual_type') == 'stickman' for scene in job['script']['scenes']):
        job = {**job, 'script': {**job['script'], 'scenes': normalize_continuity(job['script']['scenes'])}}
    prepare_scene_assets(job_dir, job["script"]["scenes"], job["aspect_ratio"])
    continuous = editor == 'remotion' and all(scene.get('visual_type') == 'stickman' for scene in job['script']['scenes'])
    audio_segments, tts_mode = prepare_scene_audio(
        job_dir,
        job["script"]["scenes"],
        job["language"],
        provider=production_config.get("voice_provider"),
        continuous=continuous,
        voice_id=production_config.get("voice_id"),
        speed=production_config.get("voice_speed", 1.0),
    )
    scene_durations = speech_scene_durations(job['script']['scenes'], audio_segments) if continuous else [
        max(float(scene.get("duration_seconds") or 0.1), float(segment["duration"]) + 0.2)
        for scene, segment in zip(job["script"]["scenes"], audio_segments)
    ]
    audio_path = job_dir / "narration.wav"
    compose_scene_audio(job_dir, audio_segments, scene_durations, audio_path)
    audio_duration = normalize_narration_audio(audio_path)

    total = audio_duration
    scenes = []
    cursor = 0.0
    for scene, duration, segment in zip(job["script"]["scenes"], scene_durations, audio_segments):
        directed = direct_scene(scene, segment['words'], duration) if continuous else scene
        scenes.append({**directed, "start": cursor, "duration": duration})
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
    if editor == "moneyprinter":
        material_paths = [
            Path(str(scene["asset_path"]))
            for scene in job["script"]["scenes"]
            if scene.get("asset_path")
        ]
        output_path = render_with_moneyprinter(
            job,
            job_dir,
            audio_path,
            material_paths,
            settings,
        )
    else:
        with failure_stage('render'):
            _run([
                "node", str(settings.renderer_dir / "render.mjs"),
                str(props_path), str(output_path), str(settings.render_concurrency), str(audio_path),
            ], timeout=3600)
    if not output_path.exists() or output_path.stat().st_size < 10_000:
        raise RuntimeError("Renderer hat keine gültige Videodatei erzeugt")
    quality_report = run_quality_gate(
        output_path=output_path,
        audio_path=audio_path,
        subtitles_path=subtitles_path,
        asset_manifest_path=job_dir / "asset-manifest.json",
        voice_manifest_path=job_dir / "voice-manifest.json",
        expected_duration=total,
        expected_script_hash=str(job["render_script_hash"]),
        report_path=job_dir / "quality-report.json",
    )
    if editor == "moneyprinter":
        quality_report["warnings"] = [
            "MoneyPrinterTurbo übernimmt die geprüfte SRT-Datei nicht über seine öffentliche CLI; der Pilot enthält keine eingebrannten Untertitel."
        ]
        (job_dir / "quality-report.json").write_text(
            json.dumps(quality_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        write_render_comparison(
            job_dir,
            output_path,
            str(editor),
            str(job["render_script_hash"]),
        )
    return str(output_path), tts_mode


def dependency_status() -> dict[str, Any]:
    from .setup import browser_available
    moneyprinter = moneyprinter_status(settings)
    return {
        "ffmpeg": bool(find_ffmpeg()),
        "ffprobe": bool(find_ffprobe()),
        "node": bool(shutil.which("node")),
        "browser": browser_available(),
        "piper_voice": _voice_model().exists(),
        "tts_provider": settings.tts_provider,
        "cloud_tts_allowed": settings.allow_cloud_tts,
        "renderer": (settings.renderer_dir / "render.mjs").exists() and (settings.renderer_dir / 'node_modules' / '@remotion' / 'renderer').is_dir(),
        "moneyprinter": moneyprinter["ready"],
        "moneyprinter_reason": moneyprinter["reason"],
    }
