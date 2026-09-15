from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .plan import canonical_script_hash


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._write_lock = threading.Lock()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    language TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    aspect_ratio TEXT NOT NULL,
                    video_type TEXT NOT NULL,
                    target_platform TEXT NOT NULL,
                    status TEXT NOT NULL,
                    script_version INTEGER NOT NULL DEFAULT 1,
                    approved_script_version INTEGER,
                    approved_script_hash TEXT,
                    render_version INTEGER,
                    render_script_hash TEXT,
                    approved_render_version INTEGER,
                    output_path TEXT,
                    output_sha256 TEXT,
                    approved_output_sha256 TEXT,
                    tts_mode TEXT,
                    error TEXT,
                    youtube_video_id TEXT,
                    publish_key TEXT UNIQUE
                );
                CREATE TABLE IF NOT EXISTS script_versions (
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    scenes_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(job_id, version)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id, id);
                """
            )
            script_columns = {row["name"] for row in conn.execute("PRAGMA table_info(script_versions)").fetchall()}
            if "metadata_json" not in script_columns:
                conn.execute("ALTER TABLE script_versions ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")
            if "content_hash" not in script_columns:
                conn.execute("ALTER TABLE script_versions ADD COLUMN content_hash TEXT")
            job_columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
            for name in ("approved_script_hash", "render_script_hash", "output_sha256", "approved_output_sha256"):
                if name not in job_columns:
                    conn.execute(f"ALTER TABLE jobs ADD COLUMN {name} TEXT")
            unhashed = conn.execute(
                "SELECT job_id,version,title,description,scenes_json FROM script_versions WHERE content_hash IS NULL OR content_hash=''"
            ).fetchall()
            for row in unhashed:
                digest = canonical_script_hash(row["title"], row["description"], json.loads(row["scenes_json"]))
                conn.execute(
                    "UPDATE script_versions SET content_hash=? WHERE job_id=? AND version=?",
                    (digest, row["job_id"], row["version"]),
                )
            conn.commit()

    def create_job(self, values: dict[str, Any], script: dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        now = utcnow()
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO jobs
                (id, created_at, updated_at, topic, language, duration_seconds, aspect_ratio,
                 video_type, target_platform, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'script_review')""",
                (job_id, now, now, values["topic"], values["language"], values["duration_seconds"],
                 values["aspect_ratio"], values["video_type"], values["target_platform"]),
            )
            self._insert_script(conn, job_id, 1, script, now)
            self._event(conn, job_id, "job_created", "Skriptentwurf wurde erstellt.")
            conn.commit()
        return job_id

    def _insert_script(self, conn: sqlite3.Connection, job_id: str, version: int, script: dict[str, Any], now: str) -> str:
        metadata = script.get("metadata") or {"provider": "manual_or_legacy", "model": None}
        content_hash = canonical_script_hash(script["title"], script.get("description", ""), script["scenes"])
        conn.execute(
            """INSERT INTO script_versions
            (job_id, version, title, description, scenes_json, metadata_json, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, version, script["title"], script.get("description", ""),
             json.dumps(script["scenes"], ensure_ascii=False),
             json.dumps(metadata, ensure_ascii=False), content_hash, now),
        )
        return content_hash

    def _event(self, conn: sqlite3.Connection, job_id: str, event_type: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        conn.execute(
            "INSERT INTO events(job_id,event_type,message,metadata_json,created_at) VALUES(?,?,?,?,?)",
            (job_id, event_type, message, json.dumps(metadata or {}, ensure_ascii=False), utcnow()),
        )

    def _verified_script_hash(self, conn: sqlite3.Connection, job_id: str, version: int) -> str:
        row = conn.execute(
            "SELECT title,description,scenes_json,content_hash FROM script_versions WHERE job_id=? AND version=?",
            (job_id, version),
        ).fetchone()
        if not row:
            raise KeyError(job_id)
        actual = canonical_script_hash(row["title"], row["description"], json.loads(row["scenes_json"]))
        if actual != row["content_hash"]:
            raise ValueError("script_integrity_error")
        return actual

    def list_jobs(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                return None
            job = dict(row)
            script = conn.execute(
                "SELECT * FROM script_versions WHERE job_id=? AND version=?",
                (job_id, job["script_version"]),
            ).fetchone()
            events = conn.execute(
                "SELECT event_type,message,metadata_json,created_at FROM events WHERE job_id=? ORDER BY id DESC LIMIT 30",
                (job_id,),
            ).fetchall()
        job["script"] = dict(script)
        job["script"]["scenes"] = json.loads(job["script"].pop("scenes_json"))
        job["script"]["metadata"] = json.loads(job["script"].pop("metadata_json"))
        job["script"]["integrity_verified"] = (
            canonical_script_hash(job["script"]["title"], job["script"]["description"], job["script"]["scenes"])
            == job["script"]["content_hash"]
        )
        job["events"] = [{**dict(e), "metadata": json.loads(e["metadata_json"])} for e in events]
        for event in job["events"]:
            event.pop("metadata_json", None)
        return job

    def update_script(self, job_id: str, expected: int, script: dict[str, Any]) -> dict[str, Any]:
        now = utcnow()
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT script_version FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            if row["script_version"] != expected:
                raise ValueError("version_conflict")
            version = expected + 1
            self._insert_script(conn, job_id, version, script, now)
            conn.execute(
                """UPDATE jobs SET updated_at=?, status='script_review', script_version=?,
                approved_script_version=NULL, approved_script_hash=NULL,
                render_version=NULL, render_script_hash=NULL, approved_render_version=NULL,
                output_path=NULL, output_sha256=NULL, approved_output_sha256=NULL,
                error=NULL, youtube_video_id=NULL, publish_key=NULL WHERE id=?""",
                (now, version, job_id),
            )
            self._event(conn, job_id, "script_updated", f"Skriptversion {version} gespeichert; frühere Freigaben sind ungültig.")
            conn.commit()
        return self.get_job(job_id)  # type: ignore[return-value]

    def approve_script(self, job_id: str, expected: int, expected_hash: str) -> dict[str, Any]:
        now = utcnow()
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT script_version,status FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            if row["script_version"] != expected:
                raise ValueError("version_conflict")
            actual_hash = self._verified_script_hash(conn, job_id, expected)
            if actual_hash != expected_hash:
                raise ValueError("hash_conflict")
            conn.execute(
                """UPDATE jobs SET approved_script_version=?,approved_script_hash=?,status='script_approved',
                updated_at=?,error=NULL WHERE id=?""",
                (expected, actual_hash, now, job_id),
            )
            self._event(
                conn, job_id, "script_approved", f"Skriptversion {expected} freigegeben.",
                {"script_hash": actual_hash},
            )
            conn.commit()
        return self.get_job(job_id)  # type: ignore[return-value]

    def queue_render(self, job_id: str, expected: int, expected_hash: str) -> dict[str, Any]:
        now = utcnow()
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            actual_hash = self._verified_script_hash(conn, job_id, expected)
            if actual_hash != expected_hash:
                raise ValueError("hash_conflict")
            if (
                row["script_version"] != expected
                or row["approved_script_version"] != expected
                or row["approved_script_hash"] != actual_hash
            ):
                raise ValueError("script_not_approved")
            if (
                row["status"] in {"render_queued", "rendering", "video_review"}
                and row["render_version"] == expected
                and row["render_script_hash"] == actual_hash
            ):
                conn.rollback()
                return self.get_job(job_id)  # type: ignore[return-value]
            conn.execute(
                """UPDATE jobs SET status='render_queued',render_version=?,render_script_hash=?,
                output_path=NULL,output_sha256=NULL,approved_render_version=NULL,approved_output_sha256=NULL,
                updated_at=?,error=NULL WHERE id=?""",
                (expected, actual_hash, now, job_id),
            )
            self._event(
                conn, job_id, "render_queued", f"Video für Skriptversion {expected} eingereiht.",
                {"script_hash": actual_hash},
            )
            conn.commit()
        return self.get_job(job_id)  # type: ignore[return-value]

    def claim_render(self) -> dict[str, Any] | None:
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT id FROM jobs WHERE status='render_queued' ORDER BY updated_at LIMIT 1"
            ).fetchone()
            if not row:
                conn.rollback()
                return None
            now = utcnow()
            conn.execute("UPDATE jobs SET status='rendering',updated_at=? WHERE id=?", (now, row["id"]))
            self._event(conn, row["id"], "render_started", "Videoproduktion gestartet.")
            conn.commit()
        return self.get_job(row["id"])

    def finish_render(self, job_id: str, version: int, output_path: str, output_sha256: str, tts_mode: str) -> None:
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT script_version,render_version,render_script_hash FROM jobs WHERE id=?", (job_id,)
            ).fetchone()
            if not row or row["script_version"] != version or row["render_version"] != version:
                conn.rollback()
                return
            actual_hash = self._verified_script_hash(conn, job_id, version)
            if row["render_script_hash"] != actual_hash:
                raise ValueError("render_script_hash_mismatch")
            conn.execute(
                """UPDATE jobs SET status='video_review',output_path=?,output_sha256=?,tts_mode=?,
                updated_at=?,error=NULL WHERE id=?""",
                (output_path, output_sha256, tts_mode, utcnow(), job_id),
            )
            self._event(
                conn, job_id, "render_finished", "Video ist zur Prüfung bereit.",
                {"tts_mode": tts_mode, "script_hash": actual_hash, "output_sha256": output_sha256},
            )
            conn.commit()

    def fail_render(self, job_id: str, message: str) -> None:
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE jobs SET status='render_failed',error=?,updated_at=? WHERE id=?", (message[:2000], utcnow(), job_id))
            self._event(conn, job_id, "render_failed", "Videoproduktion fehlgeschlagen.", {"error": message[:500]})
            conn.commit()

    def approve_video(self, job_id: str, expected: int, expected_hash: str, youtube_enabled: bool) -> dict[str, Any]:
        now = utcnow()
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            if (
                row["status"] not in {"video_review", "ready_to_publish", "publish_failed"}
                or row["render_version"] != expected
                or not row["output_sha256"]
                or row["output_sha256"] != expected_hash
            ):
                raise ValueError("video_not_ready")
            actual_script_hash = self._verified_script_hash(conn, job_id, expected)
            if row["render_script_hash"] != actual_script_hash:
                raise ValueError("render_script_hash_mismatch")
            publish_key = row["publish_key"] or f"{job_id}:{expected}:{expected_hash}:{row['target_platform']}"
            should_publish = row["target_platform"] == "youtube" and youtube_enabled
            status = "publish_queued" if should_publish else "ready_to_publish"
            conn.execute(
                """UPDATE jobs SET approved_render_version=?,approved_output_sha256=?,status=?,publish_key=?,
                updated_at=?,error=NULL WHERE id=?""",
                (expected, expected_hash, status, publish_key, now, job_id),
            )
            self._event(
                conn, job_id, "video_approved", f"Videoversion {expected} zur Veröffentlichung freigegeben.",
                {"output_sha256": expected_hash, "script_hash": actual_script_hash},
            )
            conn.commit()
        return self.get_job(job_id)  # type: ignore[return-value]

    def claim_publish(self) -> dict[str, Any] | None:
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """SELECT id FROM jobs WHERE status='publish_queued' AND youtube_video_id IS NULL
                AND output_sha256 IS NOT NULL AND approved_output_sha256=output_sha256
                ORDER BY updated_at LIMIT 1"""
            ).fetchone()
            if not row:
                conn.rollback()
                return None
            conn.execute("UPDATE jobs SET status='publishing',updated_at=? WHERE id=?", (utcnow(), row["id"]))
            self._event(conn, row["id"], "publish_started", "YouTube-Upload gestartet.")
            conn.commit()
        return self.get_job(row["id"])

    def finish_publish(self, job_id: str, youtube_video_id: str) -> None:
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE jobs SET status='published',youtube_video_id=?,updated_at=?,error=NULL WHERE id=? AND youtube_video_id IS NULL",
                (youtube_video_id, utcnow(), job_id),
            )
            self._event(conn, job_id, "published", "Freigegebenes Video wurde auf YouTube hochgeladen.", {"youtube_video_id": youtube_video_id})
            conn.commit()

    def fail_publish(self, job_id: str, message: str) -> None:
        """A failed upload is never retried automatically to avoid duplicate publication."""
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE jobs SET status='publish_failed',error=?,updated_at=? WHERE id=?", (message[:2000], utcnow(), job_id))
            self._event(conn, job_id, "publish_failed", "YouTube-Upload fehlgeschlagen und wird nicht automatisch wiederholt.", {"error": message[:500]})
            conn.commit()

    def recover_interrupted(self) -> None:
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute("SELECT id FROM jobs WHERE status='rendering'").fetchall()
            for row in rows:
                conn.execute("UPDATE jobs SET status='render_queued',updated_at=? WHERE id=?", (utcnow(), row["id"]))
                self._event(conn, row["id"], "render_recovered", "Unterbrochener Auftrag erneut eingereiht.")
            publishing = conn.execute("SELECT id FROM jobs WHERE status='publishing'").fetchall()
            for row in publishing:
                conn.execute("UPDATE jobs SET status='publish_failed',error=?,updated_at=? WHERE id=?", ("Upload wurde durch einen Neustart unterbrochen; Status muss vor einem neuen Versuch manuell geprüft werden.", utcnow(), row["id"]))
                self._event(conn, row["id"], "publish_interrupted", "Unterbrochener Upload wurde aus Sicherheitsgründen nicht automatisch wiederholt.")
            conn.commit()
