from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any

from .config import settings


_ERROR_MESSAGES = {
    "disabled": "Antigravity ist in der lokalen Konfiguration nicht aktiviert.",
    "missing": "Die Antigravity-CLI 'agy' ist nicht installiert oder nicht im PATH.",
    "auth_required": "Antigravity ist nicht angemeldet. Starte 'agy' einmal interaktiv und melde dich regulär an.",
    "timeout": "Antigravity hat das konfigurierte Zeitlimit überschritten.",
    "invalid_response": "Antigravity lieferte keine vollständige, schema-konforme Antwort.",
    "policy_violation": "Antigravity wollte ein Werkzeug verwenden; der Lauf wurde aus Sicherheitsgründen verworfen.",
    "quota_or_capacity": "Antigravity ist wegen Kontingent- oder Kapazitätsgrenzen vorübergehend nicht verfügbar.",
    "unavailable": "Antigravity konnte den Skriptauftrag nicht abschließen.",
}


class AntigravityError(RuntimeError):
    """Sanitized Antigravity failure that never carries prompts, output, or credentials."""

    def __init__(self, code: str):
        self.code = code if code in _ERROR_MESSAGES else "unavailable"
        super().__init__(_ERROR_MESSAGES[self.code])


_INFLIGHT_LOCK = threading.Lock()
_INFLIGHT: dict[str, Future[tuple[dict[str, Any], dict[str, Any]]]] = {}


def _executable() -> str:
    if not settings.antigravity_enabled:
        raise AntigravityError("disabled")
    executable = shutil.which(settings.antigravity_command)
    if not executable:
        raise AntigravityError("missing")
    return executable


def _classify_failure(diagnostic: str) -> str:
    text = diagnostic.casefold()
    if any(marker in text for marker in ("not logged", "sign in", "authentication required", "unauthenticated")):
        return "auth_required"
    if any(marker in text for marker in ("quota", "rate limit", "resource exhausted", "capacity")):
        return "quota_or_capacity"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    return "unavailable"


def _metrics(result: dict[str, Any]) -> dict[str, Any]:
    usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
    metrics: dict[str, Any] = {
        "model": settings.antigravity_model,
        "effort": settings.antigravity_effort,
    }
    duration = result.get("duration_seconds")
    if isinstance(duration, (int, float)) and not isinstance(duration, bool):
        metrics["duration_seconds"] = duration
    for key in ("input_tokens", "output_tokens", "thinking_tokens", "cache_read_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            metrics[key] = value
    return metrics


def _invoke_cli(prompt: str, schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    executable = _executable()
    with tempfile.TemporaryDirectory(prefix="video-pipeline-antigravity-") as temp_name:
        workspace = Path(temp_name)
        schema_path = workspace / "response-schema.json"
        schema_path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
        command = [
            executable,
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--json-schema", str(schema_path),
            "--model", settings.antigravity_model,
            "--effort", settings.antigravity_effort,
            "--mode", "plan",
            "--disable-slash-commands",
            "--sandbox",
            "--print-timeout", f"{settings.antigravity_timeout_seconds}s",
            "--log-file", os.devnull,
        ]
        try:
            process = subprocess.Popen(
                command,
                cwd=str(workspace),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            raise AntigravityError("unavailable") from exc
        message = json.dumps({"event": "user", "message": {"content": prompt}}, ensure_ascii=False) + "\n"
        try:
            stdout, stderr = process.communicate(message, timeout=settings.antigravity_timeout_seconds + 15)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            try:
                process.communicate("", timeout=5)
            except subprocess.TimeoutExpired:
                pass
            raise AntigravityError("timeout") from exc

    if len(stdout.encode("utf-8", errors="replace")) > 2 * 1024 * 1024:
        raise AntigravityError("invalid_response")

    result: dict[str, Any] | None = None
    tool_attempted = False
    try:
        for line in stdout.splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") == "step_update" and event.get("step_update", {}).get("step_type") == "tool":
                tool_attempted = True
            if event.get("event") == "result":
                result = event.get("result")
    except (json.JSONDecodeError, AttributeError, TypeError) as exc:
        raise AntigravityError("invalid_response") from exc

    if tool_attempted:
        raise AntigravityError("policy_violation")
    if not isinstance(result, dict):
        diagnostic = stderr[-2000:] if isinstance(stderr, str) else ""
        code = _classify_failure(diagnostic) if process.returncode else "invalid_response"
        raise AntigravityError(code)
    if process.returncode != 0 or result.get("status") != "SUCCESS":
        diagnostic = f"{result.get('error', '')}\n{stderr[-2000:]}"
        raise AntigravityError(_classify_failure(diagnostic))
    structured = result.get("structured_output")
    if not isinstance(structured, dict):
        raise AntigravityError("invalid_response")
    return structured, _metrics(result)


def generate_structured(prompt: str, schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    request_key = hashlib.sha256(
        json.dumps(
            {
                "prompt": prompt,
                "schema": schema,
                "model": settings.antigravity_model,
                "effort": settings.antigravity_effort,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    with _INFLIGHT_LOCK:
        in_flight = _INFLIGHT.get(request_key)
        leader = in_flight is None
        if leader:
            in_flight = Future()
            _INFLIGHT[request_key] = in_flight

    if not leader:
        try:
            return copy.deepcopy(in_flight.result(timeout=settings.antigravity_timeout_seconds + 30))
        except FutureTimeoutError as exc:
            raise AntigravityError("timeout") from exc

    try:
        result = _invoke_cli(prompt, schema)
        in_flight.set_result(copy.deepcopy(result))
        return result
    except BaseException as exc:
        in_flight.set_exception(exc)
        raise
    finally:
        with _INFLIGHT_LOCK:
            if _INFLIGHT.get(request_key) is in_flight:
                _INFLIGHT.pop(request_key, None)


def antigravity_status() -> dict[str, Any]:
    if not settings.antigravity_enabled:
        return {"ready": False, "provider": "antigravity", "model": settings.antigravity_model, "message": str(AntigravityError("disabled"))}
    if not shutil.which(settings.antigravity_command):
        return {"ready": False, "provider": "antigravity", "model": settings.antigravity_model, "message": str(AntigravityError("missing"))}
    return {
        "ready": True,
        "provider": "antigravity",
        "model": settings.antigravity_model,
        "message": "CLI installiert; Anmeldung wird beim ersten echten Auftrag geprüft.",
    }
