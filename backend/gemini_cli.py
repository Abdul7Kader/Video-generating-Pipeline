from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


_PROFILE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_AUTH_ENVIRONMENT = {
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_PROJECT_ID",
    "GOOGLE_CLOUD_LOCATION",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_profile_names(raw: str) -> tuple[str, ...]:
    names = tuple(dict.fromkeys(part.strip().lower() for part in raw.split(",") if part.strip()))
    if any(not _PROFILE_NAME.fullmatch(name) for name in names):
        raise ValueError("Ungültiger Gemini-Profilname; erlaubt sind Kleinbuchstaben, Zahlen, _ und -.")
    return names


def provision_profile(root: Path, name: str) -> Path:
    if not _PROFILE_NAME.fullmatch(name):
        raise ValueError("Ungültiger Gemini-Profilname")
    profile = (root / name).resolve()
    if root.resolve() not in profile.parents:
        raise ValueError("Gemini-Profil muss unterhalb des Profilwurzelverzeichnisses liegen")
    config = profile / ".gemini"
    policies = config / "policies"
    workspace = profile / "workspace"
    policies.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    settings_path = config / "settings.json"
    policy_path = policies / "pipeline-deny-all.toml"
    if not settings_path.exists():
        settings_path.write_text(
            json.dumps(
                {
                    "security": {"disableYoloMode": True},
                    "tools": {"core": []},
                    "general": {"defaultApprovalMode": "default"},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if not policy_path.exists():
        policy_path.write_text(
            '[[rule]]\ntoolName = "*"\ndecision = "deny"\npriority = 999\n'
            'denyMessage = "Pipeline generation profiles cannot use tools."\n',
            encoding="utf-8",
        )
    for directory in (profile, config, policies, workspace):
        try:
            directory.chmod(0o700)
        except OSError:
            pass
    for file_path in (settings_path, policy_path):
        try:
            file_path.chmod(0o600)
        except OSError:
            pass
    return profile


@dataclass(frozen=True)
class GeminiCliResult:
    response: str
    profile: str
    model: str | None
    stats: dict[str, Any]


class GeminiCliPool:
    def __init__(
        self,
        profiles: tuple[str, ...],
        root: Path,
        *,
        command: str = "gemini",
        timeout_seconds: int = 300,
        default_cooldown_seconds: int = 300,
        run_process: Callable[..., Any] = subprocess.run,
    ):
        self.profiles = profiles
        self.root = root.resolve()
        self.command = shutil.which(command) or command
        self.timeout_seconds = max(30, min(1800, timeout_seconds))
        self.default_cooldown_seconds = max(30, min(3600, default_cooldown_seconds))
        self.run_process = run_process
        self._lock = threading.Lock()
        self._states = {name: self._load_state(name) for name in profiles}

    def _profile_dir(self, name: str) -> Path:
        profile = (self.root / name).resolve()
        if self.root not in profile.parents:
            raise ValueError("Ungültiger Gemini-Profilpfad")
        return profile

    def _state_path(self, name: str) -> Path:
        return self._profile_dir(name) / "pipeline-state.json"

    def _load_state(self, name: str) -> dict[str, Any]:
        path = self._state_path(name)
        base = {
            "name": name,
            "status": "unknown",
            "last_success": None,
            "last_error": None,
            "cooldown_until": None,
        }
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            return {**base, **{key: loaded.get(key) for key in base if key != "name"}}
        except (OSError, ValueError, TypeError):
            return base

    def _save_state(self, name: str) -> None:
        profile = self._profile_dir(name)
        profile.mkdir(parents=True, exist_ok=True)
        path = self._state_path(name)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self._states[name], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            temporary.chmod(0o600)
        except OSError:
            pass
        os.replace(temporary, path)

    def statuses(self) -> list[dict[str, Any]]:
        now = _utcnow()
        with self._lock:
            result = []
            for name in self.profiles:
                state = dict(self._states[name])
                cooldown = state.get("cooldown_until")
                if state["status"] == "cooldown" and cooldown:
                    try:
                        if datetime.fromisoformat(cooldown) <= now:
                            state["status"] = "available"
                    except ValueError:
                        state["status"] = "unknown"
                result.append(state)
            return result

    @staticmethod
    def _classify_failure(output: str) -> tuple[str, int | None]:
        lowered = output.lower()
        retry_match = re.search(r"retry-after\s*[:=]\s*(\d+)", lowered)
        retry_after = min(3600, int(retry_match.group(1))) if retry_match else None
        if any(marker in lowered for marker in ("429", "resource_exhausted", "rate limit", "quota")):
            return "quota_or_rate_limit", retry_after
        if any(marker in lowered for marker in (
            "401", "unauthenticated", "login required", "sign in", "auth method", '"code": 41', "code 41",
        )):
            return "authentication", None
        if any(marker in lowered for marker in (
            "403", "permission_denied", "permission denied", "client is no longer supported",
        )):
            return "access_denied", None
        if any(marker in lowered for marker in ("timeout", "timed out", "503", "unavailable", "temporar")):
            return "temporary_unavailable", retry_after
        return "cli_error", None

    def _available(self, name: str, now: datetime) -> bool:
        state = self._states[name]
        if state["status"] in {"needs_login", "access_denied"}:
            return False
        cooldown = state.get("cooldown_until")
        if cooldown:
            try:
                if datetime.fromisoformat(cooldown) > now:
                    return False
            except ValueError:
                pass
        return True

    def _invoke(self, name: str, prompt: str) -> GeminiCliResult:
        profile = self._profile_dir(name)
        if not (profile / ".gemini" / "policies" / "pipeline-deny-all.toml").is_file():
            raise RuntimeError(f"Gemini-Profil {name} ist nicht sicher eingerichtet.")
        environment = dict(os.environ)
        for variable in _AUTH_ENVIRONMENT:
            environment.pop(variable, None)
        environment.update({
            "GEMINI_CLI_HOME": str(profile),
            "NO_COLOR": "1",
        })
        completed = self.run_process(
            [self.command, "--output-format", "json"],
            input=prompt,
            cwd=str(profile / "workspace"),
            env=environment,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            category, retry_after = self._classify_failure(f"{completed.stdout}\n{completed.stderr}"[:20000])
            raise _GeminiCliFailure(category, retry_after)
        try:
            payload = json.loads(completed.stdout)
            response = payload["response"]
            if not isinstance(response, str) or not response.strip():
                raise ValueError("empty response")
            stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
            models = stats.get("models") if isinstance(stats.get("models"), dict) else {}
            model = next(iter(models), None)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise _GeminiCliFailure("invalid_output", None) from exc
        return GeminiCliResult(response=response, profile=name, model=model, stats=stats)

    def generate(self, prompt: str) -> GeminiCliResult:
        if not prompt.strip():
            raise ValueError("Gemini-Eingabe darf nicht leer sein")
        with self._lock:
            now = _utcnow()
            attempted = False
            for name in self.profiles:
                if not self._available(name, now):
                    continue
                attempted = True
                self._states[name]["status"] = "busy"
                self._save_state(name)
                try:
                    result = self._invoke(name, prompt)
                except subprocess.TimeoutExpired:
                    failure = _GeminiCliFailure("temporary_unavailable", None)
                except _GeminiCliFailure as exc:
                    failure = exc
                else:
                    self._states[name].update({
                        "status": "available",
                        "last_success": _utcnow().isoformat(),
                        "last_error": None,
                        "cooldown_until": None,
                    })
                    self._save_state(name)
                    return result
                cooldown = failure.retry_after or self.default_cooldown_seconds
                if failure.category in {"authentication", "access_denied"}:
                    new_status = "needs_login" if failure.category == "authentication" else "access_denied"
                    cooldown_until = None
                else:
                    new_status = "cooldown"
                    cooldown_until = (_utcnow() + timedelta(seconds=cooldown)).isoformat()
                self._states[name].update({
                    "status": new_status,
                    "last_error": failure.category,
                    "cooldown_until": cooldown_until,
                })
                self._save_state(name)
            suffix = " verfügbar" if attempted else " eingerichtet oder abgekühlt"
            raise RuntimeError(f"Kein Gemini-Profil ist{suffix}.")


class _GeminiCliFailure(RuntimeError):
    def __init__(self, category: str, retry_after: int | None):
        super().__init__(category)
        self.category = category
        self.retry_after = retry_after
