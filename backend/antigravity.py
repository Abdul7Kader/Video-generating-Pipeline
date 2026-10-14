from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
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
    "model_unavailable": "Du bist angemeldet, aber das gewählte Modell wird für dieses Konto nicht angeboten.",
    "credits_enabled": "Antigravity erlaubt derzeit Zusatzcredits. Schalte in 'agy' unter /config 'Use G1 Credits' aus. Die Pipeline ändert keine Kontoeinstellungen und startet bis dahin keine Skripterzeugung.",
    "billing_unknown": "Die Antigravity-Credit-Einstellung konnte nicht sicher geprüft werden. Prüfe die Herstellerkonfiguration oder nutze den manuellen Webimport.",
}


class AntigravityError(RuntimeError):
    """Sanitized Antigravity failure that never carries prompts, output, or credentials."""

    def __init__(self, code: str):
        self.code = code if code in _ERROR_MESSAGES else "unavailable"
        super().__init__(_ERROR_MESSAGES[self.code])


_INFLIGHT_LOCK = threading.Lock()
_INFLIGHT: dict[str, Future[tuple[dict[str, Any], dict[str, Any]]]] = {}
_STATUS_LOCK = threading.Lock()
_STATUS_CACHE: tuple[str, str, float, dict[str, Any]] | None = None


def _executable() -> str:
    if not settings.antigravity_enabled:
        raise AntigravityError("disabled")
    executable = shutil.which(settings.antigravity_command)
    if not executable:
        raise AntigravityError("missing")
    return executable


def credit_guard() -> dict[str, str | bool]:
    """Check the documented CLI setting without modifying global account state."""
    path = Path.home() / '.gemini' / 'antigravity-cli' / 'settings.json'
    try:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return {'extra_credits_allowed': False, 'credit_setting_source': 'manufacturer_default'}
        if size > 65536:
            raise ValueError()
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        credits = value.get('useG1Credits', False)
        if not isinstance(credits, bool):
            raise ValueError()
        if credits:
            raise AntigravityError('credits_enabled')
        return {'extra_credits_allowed': False, 'credit_setting_source': 'manufacturer_settings'}
    except (OSError, ValueError, AttributeError, RecursionError):
        raise AntigravityError('billing_unknown') from None


def _safe_environment():
    # Keep the manufacturer's own login, excluding API/billing keys and unrelated secrets.
    allowed = {'PATH','PATHEXT','SYSTEMROOT','WINDIR','COMSPEC','APPDATA','LOCALAPPDATA','USERPROFILE',
               'HOME','TEMP','TMP','TMPDIR','LANG','LC_ALL','TZ','HOMEDRIVE','HOMEPATH','SYSTEMDRIVE'}
    return {key: value for key, value in os.environ.items() if key.upper() in allowed}


def _classify_failure(diagnostic: str) -> str:
    text = diagnostic.casefold().replace('_', ' ')
    if any(marker in text for marker in ("not logged", "sign in", "authentication required", "auth required", "authentication failed", "unauthenticated", "unauthorized", "login required")):
        return "auth_required"
    if any(marker in text for marker in ("quota", "rate limit", "resource exhausted", "capacity", "too many requests")) or re.search(r'\b429\b', text):
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
    billing = credit_guard()
    # The CLI can leave a child holding its working directory briefly on Windows.
    # Cleanup must not replace a valid response or the sanitized provider error.
    # Only the bounded JSON schema is written here; prompts stay on stdin.
    with tempfile.TemporaryDirectory(prefix="video-pipeline-antigravity-", ignore_cleanup_errors=True) as temp_name:
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
                env=_safe_environment(),
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
            if event.get("event") == "step_update":
                step = event.get("step_update", {})
                if step.get("step_type") == "tool":
                    # `finish` is Antigravity's structured-output completion,
                    # not a filesystem, shell, network or delegation action.
                    info = step.get("tool_info", {})
                    if step.get("tool_name") != "finish" or (info and info.get("name") != "finish"):
                        tool_attempted = True
                elif step.get("step_type") == "subagent":
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
    return structured, {**_metrics(result), **billing, 'billing_policy': 'baseline-only'}


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
            return copy.deepcopy(in_flight.result(timeout=2 * (settings.antigravity_timeout_seconds + 15) + 30))
        except FutureTimeoutError as exc:
            raise AntigravityError("timeout") from exc

    try:
        try:
            result = _invoke_cli(prompt, schema)
        except AntigravityError as exc:
            if exc.code != 'unavailable':
                raise
            # One retry for a general provider failure; never retry quota, auth or policy errors.
            output, metrics = _invoke_cli(prompt, schema)
            result = (output, {**metrics, 'provider_attempts': 2, 'provider_retry_reason': exc.code})
        in_flight.set_result(copy.deepcopy(result))
        return result
    except BaseException as exc:
        in_flight.set_exception(exc)
        raise
    finally:
        with _INFLIGHT_LOCK:
            if _INFLIGHT.get(request_key) is in_flight:
                _INFLIGHT.pop(request_key, None)


def antigravity_status(*, model: str | None = None, refresh: bool = False) -> dict[str, Any]:
    global _STATUS_CACHE
    model = model or settings.antigravity_model
    status = {"ready": False, "provider": "antigravity", "model": model,
              "installed": None, "authenticated": None, "available_models": [],
              "account_required": True, "subscription_required": False,
              "quota": "not_checked", "billing": "not_checked"}
    def failed(code, next_step):
        return {**status, "code": code, "message": str(AntigravityError(code)), "next_step": next_step}
    if not settings.antigravity_enabled:
        return failed("disabled", "Aktiviere den vorhandenen Cloudzugang in der Konfiguration oder wähle den lokalen Betrieb.")
    executable = shutil.which(settings.antigravity_command)
    if not executable:
        status['installed'] = False
        return failed("missing", "Installiere die offizielle Antigravity-CLI und starte die Pipeline danach neu.")
    status['installed'] = True
    try:
        status.update(credit_guard(), credit_policy_checked=True)
    except AntigravityError as exc:
        return failed(exc.code, 'Schalte Use G1 Credits in der Hersteller-CLI aus. Die Pipeline überschreibt die Einstellung nicht; Webimport ist eine Alternative.')
    with _STATUS_LOCK:
        cached = _STATUS_CACHE
        if not refresh and cached and cached[:2] == (executable, model) and time.monotonic() - cached[2] < 30:
            return copy.deepcopy(cached[3])
        result = None
        failure = "unavailable"
        try:
            with tempfile.TemporaryDirectory(prefix="video-pipeline-antigravity-status-", ignore_cleanup_errors=True) as workspace:
                result = subprocess.run(
                    [executable, "--log-file", os.devnull, "models"],
                    cwd=workspace,
                    env=_safe_environment(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=20,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    check=False,
                )
        except subprocess.TimeoutExpired:
            failure = "timeout"
        except OSError:
            pass
        if result is not None and result.returncode != 0:
            failure = _classify_failure(f"{result.stdout[-2000:]}\n{getattr(result, 'stderr', '')[-2000:]}")
        models = set()
        if result is not None and result.returncode == 0:
            for line in result.stdout[:65536].splitlines():
                identifier = line.split()[0] if line.split() else ''
                if re.fullmatch(r"(?:gemini|claude|gpt)-[a-z0-9][a-z0-9.-]{0,79}", identifier):
                    models.add(identifier)
        if models:
            status.update(authenticated=True, available_models=sorted(m for m in models if m.startswith('gemini-')))
            if model in models:
                status.update(ready=True, code="ready", message="Anmeldung und Modellangebot bestätigt.",
                              next_step="Du kannst einen Sprechertext erstellen. Das verfügbare Kontingent wird erst bei der Anfrage geprüft.")
            else:
                status = failed("model_unavailable", "Wähle eines der angebotenen Gemini-Modelle und speichere die Auswahl; es wird nicht automatisch gewechselt.")
        else:
            if failure == "auth_required":
                status['authenticated'] = False
            steps = {"auth_required": "Öffne Antigravity regulär mit 'agy' und melde dich im Herstellerdialog an.",
                     "quota_or_capacity": "Warte auf die Kontingentfreigabe oder prüfe die Kapazität im Anbieter. Es wird kein Tarif aktiviert.",
                     "timeout": "Prüfe die Verbindung und klicke danach erneut auf Zugang prüfen."}
            status = failed(failure, steps.get(failure, "Die Verbindung oder Modellliste konnte nicht bestätigt werden. Prüfe Netzwerk und Anbieterstatus; eine neue Anmeldung ist nicht automatisch nötig."))
        _STATUS_CACHE = (executable, model, time.monotonic(), copy.deepcopy(status))
        return status
