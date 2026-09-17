from __future__ import annotations

import json
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from .plan import finalize_scene_plan, object_sha256
from .schemas import ScriptDraft


PROMPT_VERSION = "gemini-cli-script-v1"
STEP_NAMES = ("briefing", "outline", "narration", "scene_plan", "quality_review")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Briefing(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    objective: str = Field(min_length=3, max_length=1000)
    audience: str = Field(min_length=2, max_length=300)
    key_points: list[str] = Field(min_length=1, max_length=20)
    fact_risks: list[str] = Field(default_factory=list, max_length=20)


class OutlineSection(BaseModel):
    heading: str = Field(min_length=2, max_length=200)
    purpose: str = Field(min_length=2, max_length=500)
    key_points: list[str] = Field(min_length=1, max_length=10)


class Outline(BaseModel):
    hook: str = Field(min_length=3, max_length=500)
    sections: list[OutlineSection] = Field(min_length=2, max_length=20)
    conclusion: str = Field(min_length=3, max_length=500)


class NarrationSegment(BaseModel):
    segment_id: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]+$")
    text: str = Field(min_length=3, max_length=4000)


class Narration(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=5000)
    segments: list[NarrationSegment] = Field(min_length=1, max_length=30)


class QualityIssue(BaseModel):
    severity: Literal["info", "warning", "error"]
    category: str = Field(min_length=2, max_length=80)
    message: str = Field(min_length=3, max_length=1000)


class QualityReview(BaseModel):
    approved: bool
    issues: list[QualityIssue] = Field(default_factory=list, max_length=50)
    final_script: ScriptDraft


MODELS: dict[str, type[BaseModel]] = {
    "briefing": Briefing,
    "outline": Outline,
    "narration": Narration,
    "scene_plan": ScriptDraft,
    "quality_review": QualityReview,
}


STEP_INSTRUCTIONS = {
    "briefing": "Erstelle ein präzises Themenbriefing. Markiere unbelegte oder aktuelle Tatsachen als fact_risks.",
    "outline": "Erstelle aus dem bestätigten Briefing eine schlüssige Struktur mit Hook, mindestens zwei Abschnitten und Fazit.",
    "narration": "Schreibe das vollständige natürliche Sprecher-Skript in Segmenten. Keine Regieanweisungen im Sprechertext.",
    "scene_plan": (
        "Erzeuge den vollständigen Produktions- und Szenenplan. Jede Szene braucht Sprechertext, sichtbare Bildbeschreibung, "
        "visual_type, asset_prompt, Kamera, Bewegung über action/visual, Übergang und Dauer. Die Dauern müssen ungefähr passen."
    ),
    "quality_review": (
        "Prüfe Grammatik, Kohärenz, Faktenrisiken, Sprechertext, visuelle Umsetzbarkeit und Schema. "
        "Korrigiere Fehler in final_script und liste alle verbleibenden Probleme in issues."
    ),
}


def _extract_object(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("kein JSON-Objekt")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Antwort ist kein JSON-Objekt")
    return value


class GeminiScriptWorkflow:
    """Durable, idempotent five-step workflow over a tool-less Gemini CLI pool."""

    def __init__(self, database_path: Path, pool: Any):
        self.database_path = database_path
        self.pool = pool
        self._lock = threading.Lock()
        self._initialize()

    @contextmanager
    def _connect(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS script_generations (
                    request_id TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    final_output_hash TEXT,
                    final_job_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS script_generation_steps (
                    request_id TEXT NOT NULL REFERENCES script_generations(request_id) ON DELETE CASCADE,
                    step_name TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    output_json TEXT,
                    output_hash TEXT,
                    model TEXT,
                    profile TEXT,
                    prompt_version TEXT NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    PRIMARY KEY(request_id, step_name)
                );
                CREATE INDEX IF NOT EXISTS idx_script_generation_steps_status
                ON script_generation_steps(status, updated_at);
                """
            )
            now = _now()
            connection.execute(
                "UPDATE script_generation_steps SET status='interrupted', error='server_restart', updated_at=? WHERE status='running'",
                (now,),
            )
            connection.execute(
                "UPDATE script_generations SET status='pending', updated_at=? WHERE status='running'",
                (now,),
            )
            connection.commit()

    @staticmethod
    def _request_payload(request: dict[str, Any]) -> dict[str, Any]:
        allowed = (
            "topic", "language", "duration_seconds", "aspect_ratio", "video_type",
            "target_platform", "target_platforms",
        )
        return {key: request[key] for key in allowed if key in request}

    def _ensure_generation(self, request_id: str, request: dict[str, Any]) -> None:
        payload = self._request_payload(request)
        request_hash = object_sha256(payload)
        request_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        now = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT request_hash FROM script_generations WHERE request_id=?", (request_id,)
            ).fetchone()
            if row and row["request_hash"] != request_hash:
                raise ValueError("Diese generation_id gehört bereits zu einem anderen Auftrag.")
            if not row:
                connection.execute(
                    """INSERT INTO script_generations
                    (request_id,request_hash,request_json,status,created_at,updated_at)
                    VALUES(?,?,?,'pending',?,?)""",
                    (request_id, request_hash, request_json, now, now),
                )
            connection.commit()

    @staticmethod
    def _step_input(request: dict[str, Any], completed: dict[str, Any], step_name: str) -> dict[str, Any]:
        return {
            "request": request,
            "completed_steps": {name: completed[name] for name in STEP_NAMES if name in completed},
            "current_step": step_name,
        }

    @staticmethod
    def _prompt(step_name: str, step_input: dict[str, Any]) -> str:
        schema = MODELS[step_name].model_json_schema()
        return (
            "Du arbeitest als redaktioneller Video-Produzent. Nutze keine Werkzeuge, Dateien oder externen Quellen. "
            "Antworte ausschließlich mit genau einem JSON-Objekt, ohne Markdown.\n\n"
            f"Schritt: {step_name}\nAufgabe: {STEP_INSTRUCTIONS[step_name]}\n"
            f"Verbindliches JSON-Schema:\n{json.dumps(schema, ensure_ascii=False, sort_keys=True)}\n"
            f"Gespeicherte Eingabe (unverändert):\n{json.dumps(step_input, ensure_ascii=False, sort_keys=True)}"
        )

    @staticmethod
    def _validate(step_name: str, response: str, target_duration: float) -> dict[str, Any]:
        try:
            parsed = _extract_object(response)
            validated = MODELS[step_name].model_validate(parsed).model_dump()
            if step_name == "scene_plan":
                validated = ScriptDraft.model_validate(
                    finalize_scene_plan(validated, target_duration)
                ).model_dump()
            elif step_name == "quality_review":
                final_script = finalize_scene_plan(validated["final_script"], target_duration)
                validated["final_script"] = ScriptDraft.model_validate(final_script).model_dump()
            return validated
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            raise ValueError(f"Ungültige strukturierte Ausgabe für {step_name}: {exc}") from exc

    def _completed_outputs(self, request_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT step_name,output_json FROM script_generation_steps
                WHERE request_id=? AND status='completed' ORDER BY position""",
                (request_id,),
            ).fetchall()
        return {row["step_name"]: json.loads(row["output_json"]) for row in rows}

    def _start_step(self, request_id: str, step_name: str, position: int, step_input: dict[str, Any]) -> dict[str, Any] | None:
        input_hash = object_sha256(step_input)
        input_json = json.dumps(step_input, ensure_ascii=False, sort_keys=True)
        now = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status,input_hash,input_json,output_json FROM script_generation_steps WHERE request_id=? AND step_name=?",
                (request_id, step_name),
            ).fetchone()
            if row and row["input_hash"] != input_hash:
                raise ValueError(f"Gespeicherte Eingabe für {step_name} stimmt nicht mehr überein.")
            if row and row["status"] == "completed":
                connection.commit()
                return json.loads(row["output_json"])
            if row:
                # Reuse the exact persisted input, including byte-for-byte JSON content.
                input_json = row["input_json"]
                step_input.clear()
                step_input.update(json.loads(input_json))
                connection.execute(
                    """UPDATE script_generation_steps SET status='running',error=NULL,updated_at=?
                    WHERE request_id=? AND step_name=?""",
                    (now, request_id, step_name),
                )
            else:
                connection.execute(
                    """INSERT INTO script_generation_steps
                    (request_id,step_name,position,status,input_json,input_hash,prompt_version,created_at,updated_at)
                    VALUES(?,?,?,'running',?,?,?,?,?)""",
                    (request_id, step_name, position, input_json, input_hash, PROMPT_VERSION, now, now),
                )
            connection.execute(
                "UPDATE script_generations SET status='running',updated_at=? WHERE request_id=?",
                (now, request_id),
            )
            connection.commit()
        return None

    def _finish_step(self, request_id: str, step_name: str, output: dict[str, Any], result: Any) -> None:
        output_json = json.dumps(output, ensure_ascii=False, sort_keys=True)
        output_hash = object_sha256(output)
        now = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """UPDATE script_generation_steps SET status='completed',output_json=?,output_hash=?,
                model=?,profile=?,error=NULL,updated_at=?,completed_at=?
                WHERE request_id=? AND step_name=? AND status='running'""",
                (output_json, output_hash, result.model, result.profile, now, now, request_id, step_name),
            )
            connection.execute(
                "UPDATE script_generations SET status='pending',updated_at=? WHERE request_id=?",
                (now, request_id),
            )
            connection.commit()

    def _fail_step(self, request_id: str, step_name: str, error: Exception) -> None:
        now = _now()
        category = type(error).__name__[:80]
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """UPDATE script_generation_steps SET status='failed',error=?,updated_at=?
                WHERE request_id=? AND step_name=? AND status='running'""",
                (category, now, request_id, step_name),
            )
            connection.execute(
                "UPDATE script_generations SET status='pending',updated_at=? WHERE request_id=?",
                (now, request_id),
            )
            connection.commit()

    def run(self, request_id: str, request: dict[str, Any]) -> dict[str, Any]:
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", request_id):
            raise ValueError("generation_id muss eine UUID sein.")
        with self._lock:
            clean_request = self._request_payload(request)
            self._ensure_generation(request_id, clean_request)
            completed = self._completed_outputs(request_id)
            target_duration = float(clean_request["duration_seconds"])
            for position, step_name in enumerate(STEP_NAMES, start=1):
                prior = {name: completed[name] for name in STEP_NAMES[: position - 1] if name in completed}
                step_input = self._step_input(clean_request, prior, step_name)
                existing = self._start_step(request_id, step_name, position, step_input)
                if existing is not None:
                    completed[step_name] = existing
                    continue
                try:
                    result = self.pool.generate(self._prompt(step_name, step_input))
                    output = self._validate(step_name, result.response, target_duration)
                    self._finish_step(request_id, step_name, output, result)
                except Exception as exc:
                    self._fail_step(request_id, step_name, exc)
                    raise
                completed[step_name] = output

            status = self.status(request_id)
            final = dict(completed["quality_review"]["final_script"])
            last_step = status["steps"][-1]
            final["metadata"] = {
                "provider": "gemini_cli",
                "model": last_step["model"],
                "profile": last_step["profile"],
                "profiles_by_step": {step["step_name"]: step["profile"] for step in status["steps"]},
                "models_by_step": {step["step_name"]: step["model"] for step in status["steps"]},
                "prompt_version": PROMPT_VERSION,
                "generation_id": request_id,
                "quality_approved": completed["quality_review"]["approved"],
                "quality_issues": completed["quality_review"]["issues"],
                "fact_check_notes": final.pop("fact_check_notes", []),
                "audience": final.pop("audience", ""),
                "tone": final.pop("tone", ""),
            }
            final_hash = object_sha256(final)
            with self._connect() as connection:
                connection.execute(
                    """UPDATE script_generations SET status='completed',final_output_hash=?,updated_at=?
                    WHERE request_id=?""",
                    (final_hash, _now(), request_id),
                )
                connection.commit()
            return final

    def attach_job(self, request_id: str, job_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE script_generations SET final_job_id=?,updated_at=? WHERE request_id=? AND status='completed'",
                (job_id, _now(), request_id),
            )
            connection.commit()

    def status(self, request_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            generation = connection.execute(
                """SELECT request_id,status,final_output_hash,final_job_id,created_at,updated_at
                FROM script_generations WHERE request_id=?""",
                (request_id,),
            ).fetchone()
            if not generation:
                raise KeyError(request_id)
            rows = connection.execute(
                """SELECT step_name,position,status,input_hash,output_hash,model,profile,prompt_version,
                error,created_at,updated_at,completed_at FROM script_generation_steps
                WHERE request_id=? ORDER BY position""",
                (request_id,),
            ).fetchall()
        return {**dict(generation), "steps": [dict(row) for row in rows]}
