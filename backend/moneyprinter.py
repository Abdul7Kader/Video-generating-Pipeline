from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from .plan import file_sha256, object_sha256
from .quality import probe_media


_SAFE_ENVIRONMENT_KEYS = {
    "APPDATA",
    "COMSPEC",
    "HOME",
    "LOCALAPPDATA",
    "NUMBER_OF_PROCESSORS",
    "PATH",
    "PATHEXT",
    "PROGRAMDATA",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "WINDIR",
}
_MAX_STDOUT_BYTES = 2 * 1024 * 1024


class MoneyPrinterError(RuntimeError):
    pass


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def moneyprinter_status(adapter_settings: Any) -> dict[str, Any]:
    if not adapter_settings.moneyprinter_enabled:
        return {
            "ready": False,
            "mode": "local_batch_cli",
            "reason": "MoneyPrinterTurbo ist nicht aktiviert.",
        }
    root = Path(adapter_settings.moneyprinter_root).resolve()
    python = Path(adapter_settings.moneyprinter_python).resolve()
    cli = root / "cli.py"
    application_root = Path(__file__).resolve().parent.parent
    if _is_within(root, application_root):
        reason = "MoneyPrinterTurbo muss außerhalb dieses Repositories installiert sein."
    elif not root.is_dir():
        reason = "Das konfigurierte MoneyPrinterTurbo-Verzeichnis fehlt."
    elif not cli.is_file():
        reason = "Im MoneyPrinterTurbo-Verzeichnis fehlt cli.py."
    elif not python.is_file() or not _is_within(python, root):
        reason = "Die isolierte MoneyPrinterTurbo-Python-Umgebung fehlt oder liegt außerhalb des MoneyPrinterTurbo-Verzeichnisses."
    else:
        reason = ""
    return {
        "ready": not reason,
        "mode": "local_batch_cli",
        "reason": reason,
    }


def build_batch_manifest(job: dict[str, Any], audio_path: Path, material_paths: list[Path]) -> list[dict[str, Any]]:
    if not material_paths:
        raise MoneyPrinterError("MoneyPrinterTurbo benötigt mindestens ein vorbereitetes lokales Medium.")
    narration = "\n\n".join(
        str(scene.get("narration") or "").strip()
        for scene in job["script"]["scenes"]
        if str(scene.get("narration") or "").strip()
    )
    if not narration:
        raise MoneyPrinterError("Der freigegebene Szenenplan enthält keinen Sprechertext.")
    return [{
        "video_subject": str(job["topic"]),
        "video_script": narration,
        "video_language": str(job["language"]),
        "video_aspect": str(job["aspect_ratio"]),
        "video_source": "local",
        "video_materials": [
            {"provider": "local", "url": str(path.resolve()), "duration": 0}
            for path in material_paths
        ],
        "custom_audio_file": str(audio_path.resolve()),
        "video_count": 1,
        "video_concat_mode": "sequential",
        "match_materials_to_script": True,
        "bgm_type": "",
        "bgm_volume": 0,
        # MoneyPrinterTurbo cannot ingest our reviewed SRT through its public CLI.
        # Enabling its own transcription would add a different, unapproved input.
        "subtitle_enabled": False,
    }]


def _safe_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in _SAFE_ENVIRONMENT_KEYS
    }
    environment.update({
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "NO_PROXY": "127.0.0.1,localhost",
    })
    return environment


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)


def _run_process(command: list[str], root: Path, timeout_seconds: int) -> tuple[int, str]:
    process_options: dict[str, Any] = {}
    if os.name == "nt":
        process_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        process_options["start_new_session"] = True
    with tempfile.TemporaryFile() as stdout:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=_safe_environment(),
            stdout=stdout,
            stderr=subprocess.DEVNULL,
            **process_options,
        )
        deadline = time.monotonic() + timeout_seconds
        while process.poll() is None:
            if os.fstat(stdout.fileno()).st_size > _MAX_STDOUT_BYTES:
                _terminate_process_tree(process)
                raise MoneyPrinterError("MoneyPrinterTurbo lieferte eine unerwartet große Antwort.")
            if time.monotonic() >= deadline:
                _terminate_process_tree(process)
                raise MoneyPrinterError("MoneyPrinterTurbo hat das konfigurierte Zeitlimit überschritten.")
            time.sleep(0.1)
        return_code = process.wait(timeout=15)
        if os.fstat(stdout.fileno()).st_size > _MAX_STDOUT_BYTES:
            raise MoneyPrinterError("MoneyPrinterTurbo lieferte eine unerwartet große Antwort.")
        stdout.seek(0)
        return return_code, stdout.read().decode("utf-8", errors="replace")


def _parse_output(stdout: str, root: Path) -> tuple[str, Path]:
    try:
        payload = json.loads(stdout)
        tasks = payload["tasks"]
        task = tasks[0]
        task_id = str(task["task_id"])
        videos = task["result"]["videos"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise MoneyPrinterError("MoneyPrinterTurbo lieferte keine gültige Batch-Antwort.") from exc
    if payload.get("total") != 1 or payload.get("succeeded") != 1 or payload.get("failed") != 0:
        raise MoneyPrinterError("MoneyPrinterTurbo meldete keinen vollständig erfolgreichen Einzelauftrag.")
    try:
        UUID(task_id)
    except ValueError as exc:
        raise MoneyPrinterError("MoneyPrinterTurbo meldete eine ungültige Aufgabenkennung.") from exc
    if task.get("status") != "succeeded":
        raise MoneyPrinterError("MoneyPrinterTurbo meldete einen ungültigen Aufgabenstatus.")
    if not isinstance(videos, list) or len(videos) != 1:
        raise MoneyPrinterError("MoneyPrinterTurbo lieferte nicht genau eine Videodatei.")
    candidate = Path(str(videos[0]))
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    task_directory = (root / "storage" / "tasks" / task_id).resolve()
    if not _is_within(task_directory, root / "storage" / "tasks") or not _is_within(candidate, task_directory):
        raise MoneyPrinterError("MoneyPrinterTurbo meldete eine Videodatei außerhalb seines Aufgabenverzeichnisses.")
    if not candidate.is_file() or candidate.stat().st_size < 10_000:
        raise MoneyPrinterError("MoneyPrinterTurbo erzeugte keine gültige Videodatei.")
    return task_id, candidate


def render_with_moneyprinter(
    job: dict[str, Any],
    job_dir: Path,
    audio_path: Path,
    material_paths: list[Path],
    adapter_settings: Any,
) -> Path:
    status = moneyprinter_status(adapter_settings)
    if not status["ready"]:
        raise MoneyPrinterError(status["reason"])
    root = Path(adapter_settings.moneyprinter_root).resolve()
    python = Path(adapter_settings.moneyprinter_python).resolve()
    cli = (root / "cli.py").resolve()
    manifest = build_batch_manifest(job, audio_path, material_paths)
    manifest_path = job_dir / "moneyprinter-input.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_hash = file_sha256(manifest_path)
    command = [
        str(python),
        str(cli),
        "--batch-file",
        str(manifest_path.resolve()),
        "--stop-at",
        "video",
    ]
    try:
        try:
            return_code, stdout = _run_process(
                command,
                root,
                int(adapter_settings.moneyprinter_timeout_seconds),
            )
        except OSError as exc:
            raise MoneyPrinterError("MoneyPrinterTurbo konnte nicht gestartet werden.") from exc
        if return_code != 0:
            category = "Eingabe abgelehnt" if return_code == 2 else "Produktion fehlgeschlagen"
            raise MoneyPrinterError(f"MoneyPrinterTurbo: {category} (Exitcode {return_code}).")
        task_id, source = _parse_output(stdout, root)
        destination = job_dir / "video.mp4"
        destination.unlink(missing_ok=True)
        shutil.copy2(source, destination)
        provenance = {
            "adapter": "MoneyPrinterTurbo",
            "interface": "official_batch_cli",
            "task_id": task_id,
            "script_hash": str(job["render_script_hash"]),
            "input_manifest_sha256": manifest_hash,
            "output_sha256": file_sha256(destination),
            "output_bytes": destination.stat().st_size,
            "cli_sha256": file_sha256(cli),
            "subtitles_embedded": False,
            "external_publish_requested": False,
        }
        provenance["provenance_sha256"] = object_sha256(provenance)
        (job_dir / "moneyprinter-provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return destination
    finally:
        manifest_path.unlink(missing_ok=True)


def _artifact_metrics(path: Path, editor: str, relative_path: str) -> dict[str, Any]:
    probe = probe_media(path)
    streams = probe.get("streams") or []
    return {
        "editor": editor,
        "relative_path": relative_path.replace("\\", "/"),
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
        "duration_seconds": float((probe.get("format") or {}).get("duration") or 0),
        "video_codecs": [
            str(stream.get("codec_name") or "unknown")
            for stream in streams
            if stream.get("codec_type") == "video"
        ],
        "audio_codecs": [
            str(stream.get("codec_name") or "unknown")
            for stream in streams
            if stream.get("codec_type") == "audio"
        ],
        "subtitles_embedded": editor != "moneyprinter",
    }


def write_render_comparison(
    job_dir: Path,
    output_path: Path,
    editor: str,
    script_hash: str,
) -> dict[str, Any]:
    version_root = job_dir.parent
    report: dict[str, Any] = {
        "status": "baseline_missing",
        "same_script_hash": False,
        "script_hash": script_hash,
        "candidate": _artifact_metrics(output_path, editor, str(output_path.relative_to(version_root))),
        "limits": "Technische Messwerte ersetzen keine redaktionelle Sichtprüfung.",
    }
    for props_path in sorted(
        version_root.glob("v*/render-props.json"),
        key=lambda path: path.parent.stat().st_mtime,
        reverse=True,
    ):
        if props_path.parent.resolve() == job_dir.resolve():
            continue
        try:
            props = json.loads(props_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        video = props_path.parent / "video.mp4"
        if props.get("scriptHash") != script_hash or not video.is_file():
            continue
        baseline_editor = "moneyprinter" if (props_path.parent / "moneyprinter-provenance.json").is_file() else "remotion"
        if baseline_editor == editor:
            continue
        report.update({
            "status": "ready",
            "same_script_hash": True,
            "baseline": _artifact_metrics(video, baseline_editor, str(video.relative_to(version_root))),
        })
        break
    (job_dir / "render-comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report
