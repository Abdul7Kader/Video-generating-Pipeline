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
from .production import legacy_production_config, normalize_production_config
from .publishing import profile_for


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
                    production_config_json TEXT NOT NULL DEFAULT '{}',
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
                    production_config_json TEXT NOT NULL DEFAULT '{}',
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
                CREATE TABLE IF NOT EXISTS publication_targets (
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    platform TEXT NOT NULL,
                    position INTEGER NOT NULL DEFAULT 0,
                    delivery_mode TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'planned',
                    approved_output_sha256 TEXT,
                    idempotency_key TEXT UNIQUE,
                    remote_id TEXT,
                    remote_url TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(job_id, platform)
                );
                CREATE INDEX IF NOT EXISTS idx_publication_targets_status
                ON publication_targets(status, updated_at);
                """
            )
            script_columns = {row["name"] for row in conn.execute("PRAGMA table_info(script_versions)").fetchall()}
            if "metadata_json" not in script_columns:
                conn.execute("ALTER TABLE script_versions ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")
            if "content_hash" not in script_columns:
                conn.execute("ALTER TABLE script_versions ADD COLUMN content_hash TEXT")
            if "production_config_json" not in script_columns:
                conn.execute("ALTER TABLE script_versions ADD COLUMN production_config_json TEXT NOT NULL DEFAULT '{}'")
            job_columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
            for name in ("approved_script_hash", "render_script_hash", "output_sha256", "approved_output_sha256"):
                if name not in job_columns:
                    conn.execute(f"ALTER TABLE jobs ADD COLUMN {name} TEXT")
            if "production_config_json" not in job_columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN production_config_json TEXT NOT NULL DEFAULT '{}'")
            legacy_jobs = conn.execute(
                "SELECT id,video_type,production_config_json FROM jobs"
            ).fetchall()
            for row in legacy_jobs:
                if row["production_config_json"] not in {None, "", "{}"}:
                    continue
                config = legacy_production_config(row["video_type"])
                conn.execute(
                    "UPDATE jobs SET production_config_json=? WHERE id=?",
                    (json.dumps(config, ensure_ascii=False), row["id"]),
                )
            conn.execute(
                """UPDATE script_versions SET production_config_json=(
                    SELECT jobs.production_config_json FROM jobs WHERE jobs.id=script_versions.job_id
                ) WHERE production_config_json IS NULL OR production_config_json='' OR production_config_json='{}'"""
            )
            unhashed = conn.execute(
                "SELECT job_id,version,title,description,scenes_json FROM script_versions WHERE content_hash IS NULL OR content_hash=''"
            ).fetchall()
            for row in unhashed:
                digest = canonical_script_hash(row["title"], row["description"], json.loads(row["scenes_json"]))
                conn.execute(
                    "UPDATE script_versions SET content_hash=? WHERE job_id=? AND version=?",
                    (digest, row["job_id"], row["version"]),
                )
            legacy_targets = conn.execute("SELECT id,target_platform,created_at,updated_at FROM jobs").fetchall()
            for row in legacy_targets:
                try:
                    mode = profile_for(row["target_platform"])["delivery_mode"]
                except ValueError:
                    mode = "download"
                conn.execute(
                    """INSERT OR IGNORE INTO publication_targets
                    (job_id,platform,position,delivery_mode,status,created_at,updated_at)
                    VALUES(?,?,?,?, 'planned',?,?)""",
                    (row["id"], row["target_platform"], 0, mode, row["created_at"], row["updated_at"]),
                )
            conn.commit()

    def create_job(self, values: dict[str, Any], script: dict[str, Any], *, job_id: str | None = None) -> str:
        job_id = job_id or str(uuid.uuid4())
        now = utcnow()
        production_config = normalize_production_config(
            values.get("production_config"),
            legacy_video_type=values["video_type"],
            legacy_script_provider=values.get("script_generator", "qwen"),
        )
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone():
                conn.commit()
                return job_id
            conn.execute(
                """INSERT INTO jobs
                (id, created_at, updated_at, topic, language, duration_seconds, aspect_ratio,
                 video_type, production_config_json, target_platform, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'script_review')""",
                (job_id, now, now, values["topic"], values["language"], values["duration_seconds"],
                 values["aspect_ratio"], production_config["video_type"],
                 json.dumps(production_config, ensure_ascii=False), values["target_platform"]),
            )
            self._insert_script(conn, job_id, 1, script, now, production_config)
            targets = values.get("target_platforms") or [values["target_platform"]]
            for position, platform in enumerate(dict.fromkeys(targets)):
                mode = profile_for(platform)["delivery_mode"]
                conn.execute(
                    """INSERT INTO publication_targets
                    (job_id,platform,position,delivery_mode,status,created_at,updated_at)
                    VALUES(?,?,?,?, 'planned',?,?)""",
                    (job_id, platform, position, mode, now, now),
                )
            self._event(conn, job_id, "job_created", "Skriptentwurf wurde erstellt.")
            conn.commit()
        return job_id

    def _insert_script(
        self,
        conn: sqlite3.Connection,
        job_id: str,
        version: int,
        script: dict[str, Any],
        now: str,
        production_config: dict[str, Any] | None = None,
    ) -> str:
        metadata = script.get("metadata") or {"provider": "manual_or_legacy", "model": None}
        content_hash = canonical_script_hash(script["title"], script.get("description", ""), script["scenes"])
        if production_config is None:
            row = conn.execute("SELECT production_config_json FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            production_config = json.loads(row["production_config_json"])
        conn.execute(
            """INSERT INTO script_versions
            (job_id, version, title, description, scenes_json, metadata_json,
             production_config_json, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, version, script["title"], script.get("description", ""),
             json.dumps(script["scenes"], ensure_ascii=False),
             json.dumps(metadata, ensure_ascii=False),
             json.dumps(production_config, ensure_ascii=False), content_hash, now),
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
        jobs = [dict(row) for row in rows]
        for job in jobs:
            job["production_config"] = json.loads(job.pop("production_config_json"))
        return jobs

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
            publication_targets = conn.execute(
                """SELECT platform,position,delivery_mode,status,approved_output_sha256,
                remote_id,remote_url,error,updated_at FROM publication_targets
                WHERE job_id=? ORDER BY position,platform""",
                (job_id,),
            ).fetchall()
        job["script"] = dict(script)
        job["production_config"] = json.loads(job.pop("production_config_json"))
        job["script"]["scenes"] = json.loads(job["script"].pop("scenes_json"))
        job["script"]["metadata"] = json.loads(job["script"].pop("metadata_json"))
        job["script"]["production_config"] = json.loads(job["script"].pop("production_config_json"))
        job["script"]["integrity_verified"] = (
            canonical_script_hash(job["script"]["title"], job["script"]["description"], job["script"]["scenes"])
            == job["script"]["content_hash"]
        )
        job["events"] = [{**dict(e), "metadata": json.loads(e["metadata_json"])} for e in events]
        for event in job["events"]:
            event.pop("metadata_json", None)
        job["publication_targets"] = [dict(target) for target in publication_targets]
        job["target_platforms"] = [target["platform"] for target in job["publication_targets"]]
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
            conn.execute(
                """UPDATE publication_targets SET status='planned',approved_output_sha256=NULL,
                idempotency_key=NULL,remote_id=NULL,remote_url=NULL,error=NULL,updated_at=? WHERE job_id=?""",
                (now, job_id),
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
            conn.execute(
                """UPDATE publication_targets SET status='planned',approved_output_sha256=NULL,
                idempotency_key=NULL,remote_id=NULL,remote_url=NULL,error=NULL,updated_at=? WHERE job_id=?""",
                (now, job_id),
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

    def attach_imported_video(
        self,
        job_id: str,
        expected: int,
        expected_hash: str,
        output_path: str,
        output_sha256: str,
        source: str,
    ) -> dict[str, Any]:
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
            if row["status"] in {"render_queued", "rendering", "publish_queued", "publishing"}:
                raise ValueError("job_busy")
            conn.execute(
                """UPDATE jobs SET status='video_review',render_version=?,render_script_hash=?,
                output_path=?,output_sha256=?,tts_mode=?,approved_render_version=NULL,
                approved_output_sha256=NULL,publish_key=NULL,youtube_video_id=NULL,
                updated_at=?,error=NULL WHERE id=?""",
                (expected, actual_hash, output_path, output_sha256, f"import:{source}", now, job_id),
            )
            conn.execute(
                """UPDATE publication_targets SET status='planned',approved_output_sha256=NULL,
                idempotency_key=NULL,remote_id=NULL,remote_url=NULL,error=NULL,updated_at=? WHERE job_id=?""",
                (now, job_id),
            )
            self._event(
                conn,
                job_id,
                "external_video_imported",
                "Externes Video wurde geprüft und ist zur Freigabe bereit.",
                {"source": source, "script_hash": actual_hash, "output_sha256": output_sha256},
            )
            conn.commit()
        return self.get_job(job_id)  # type: ignore[return-value]

    def update_production_config(
        self,
        job_id: str,
        expected: int,
        production_config: dict[str, Any],
    ) -> dict[str, Any]:
        now = utcnow()
        normalized = normalize_production_config(
            production_config,
            legacy_video_type=production_config.get("video_type", "stickman"),
            legacy_script_provider=production_config.get("script_provider", "qwen"),
        )
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            job = conn.execute(
                "SELECT script_version,status,production_config_json FROM jobs WHERE id=?",
                (job_id,),
            ).fetchone()
            if not job:
                raise KeyError(job_id)
            if job["script_version"] != expected:
                raise ValueError("version_conflict")
            if job["status"] in {"render_queued", "rendering", "publish_queued", "publishing"}:
                raise ValueError("job_busy")
            if json.loads(job["production_config_json"]) == normalized:
                raise ValueError("configuration_unchanged")
            current = conn.execute(
                "SELECT title,description,scenes_json,metadata_json FROM script_versions WHERE job_id=? AND version=?",
                (job_id, expected),
            ).fetchone()
            if not current:
                raise KeyError(job_id)
            version = expected + 1
            script = {
                "title": current["title"],
                "description": current["description"],
                "scenes": json.loads(current["scenes_json"]),
                "metadata": json.loads(current["metadata_json"]),
            }
            self._insert_script(conn, job_id, version, script, now, normalized)
            conn.execute(
                """UPDATE jobs SET updated_at=?, status='script_review', script_version=?,
                video_type=?,production_config_json=?,approved_script_version=NULL,
                approved_script_hash=NULL,render_version=NULL,render_script_hash=NULL,
                approved_render_version=NULL,output_path=NULL,output_sha256=NULL,
                approved_output_sha256=NULL,tts_mode=NULL,error=NULL,youtube_video_id=NULL,
                publish_key=NULL WHERE id=?""",
                (now, version, normalized["video_type"], json.dumps(normalized, ensure_ascii=False), job_id),
            )
            conn.execute(
                """UPDATE publication_targets SET status='planned',approved_output_sha256=NULL,
                idempotency_key=NULL,remote_id=NULL,remote_url=NULL,error=NULL,updated_at=? WHERE job_id=?""",
                (now, job_id),
            )
            self._event(
                conn,
                job_id,
                "production_config_updated",
                f"Produktionskonfiguration als Version {version} gespeichert; frühere Freigaben sind ungültig.",
                {"production_config": normalized},
            )
            conn.commit()
        return self.get_job(job_id)  # type: ignore[return-value]

    def fail_render(self, job_id: str, message: str) -> None:
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE jobs SET status='render_failed',error=?,updated_at=? WHERE id=?", (message[:2000], utcnow(), job_id))
            self._event(conn, job_id, "render_failed", "Videoproduktion fehlgeschlagen.", {"error": message[:500]})
            conn.commit()

    def _refresh_publication_job_state(self, conn: sqlite3.Connection, job_id: str) -> str:
        statuses = [row["status"] for row in conn.execute(
            "SELECT status FROM publication_targets WHERE job_id=?", (job_id,)
        ).fetchall()]
        if "publishing" in statuses:
            status = "publishing"
        elif "queued" in statuses:
            status = "publish_queued"
        elif any(value in {"failed", "unknown"} for value in statuses):
            status = "publish_failed"
        elif "published" in statuses:
            status = "published" if all(value in {"published", "ready"} for value in statuses) else "published_partial"
        else:
            status = "ready_to_publish"
        conn.execute("UPDATE jobs SET status=?,updated_at=? WHERE id=?", (status, utcnow(), job_id))
        return status

    def approve_video(
        self,
        job_id: str,
        expected: int,
        expected_hash: str,
        enabled_platforms: set[str] | bool,
    ) -> dict[str, Any]:
        now = utcnow()
        enabled = {"youtube"} if enabled_platforms is True else set() if enabled_platforms is False else set(enabled_platforms)
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
            targets = conn.execute(
                "SELECT platform,delivery_mode FROM publication_targets WHERE job_id=? ORDER BY position",
                (job_id,),
            ).fetchall()
            if row["target_platform"] not in {target["platform"] for target in targets} and len(targets) == 1:
                conn.execute("DELETE FROM publication_targets WHERE job_id=?", (job_id,))
                mode = profile_for(row["target_platform"])["delivery_mode"]
                conn.execute(
                    """INSERT INTO publication_targets
                    (job_id,platform,position,delivery_mode,status,created_at,updated_at)
                    VALUES(?,?,?,?, 'planned',?,?)""",
                    (job_id, row["target_platform"], 0, mode, row["created_at"], now),
                )
                targets = conn.execute(
                    "SELECT platform,delivery_mode FROM publication_targets WHERE job_id=? ORDER BY position",
                    (job_id,),
                ).fetchall()
            for target in targets:
                platform = target["platform"]
                mode = target["delivery_mode"]
                if platform == "download":
                    target_status = "ready"
                elif mode == "automatic" and platform in enabled:
                    target_status = "queued"
                elif mode == "automatic":
                    target_status = "setup_required"
                else:
                    # RSS feeds and distributor release packages are planned artifacts,
                    # but do not exist merely because a video was approved.
                    target_status = "setup_required"
                key = f"publish:v1:{job_id}:{platform}:{expected_hash}"
                conn.execute(
                    """UPDATE publication_targets SET status=?,approved_output_sha256=?,
                    idempotency_key=?,remote_id=NULL,remote_url=NULL,error=NULL,updated_at=?
                    WHERE job_id=? AND platform=?""",
                    (target_status, expected_hash, key, now, job_id, platform),
                )
            publish_key = row["publish_key"] or f"{job_id}:{expected}:{expected_hash}"
            conn.execute(
                """UPDATE jobs SET approved_render_version=?,approved_output_sha256=?,publish_key=?,
                updated_at=?,error=NULL WHERE id=?""",
                (expected, expected_hash, publish_key, now, job_id),
            )
            self._refresh_publication_job_state(conn, job_id)
            self._event(
                conn, job_id, "video_approved", f"Videoversion {expected} zur Veröffentlichung freigegeben.",
                {"output_sha256": expected_hash, "script_hash": actual_script_hash, "targets": [target["platform"] for target in targets]},
            )
            conn.commit()
        return self.get_job(job_id)  # type: ignore[return-value]

    def claim_publication(self) -> dict[str, Any] | None:
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """SELECT target.job_id,target.platform FROM publication_targets target
                JOIN jobs ON jobs.id=target.job_id
                WHERE target.status='queued' AND target.approved_output_sha256=jobs.output_sha256
                AND jobs.approved_output_sha256=jobs.output_sha256
                ORDER BY target.updated_at,target.position LIMIT 1"""
            ).fetchone()
            if not row:
                conn.rollback()
                return None
            now = utcnow()
            updated = conn.execute(
                """UPDATE publication_targets SET status='publishing',updated_at=?
                WHERE job_id=? AND platform=? AND status='queued'""",
                (now, row["job_id"], row["platform"]),
            )
            if updated.rowcount != 1:
                conn.rollback()
                return None
            self._refresh_publication_job_state(conn, row["job_id"])
            self._event(
                conn,
                row["job_id"],
                "publish_started",
                f"Veröffentlichung auf {row['platform']} gestartet.",
                {"platform": row["platform"]},
            )
            conn.commit()
        job = self.get_job(row["job_id"])
        if job:
            job["publication_target"] = next(
                target for target in job["publication_targets"] if target["platform"] == row["platform"]
            )
        return job

    def finish_publication(self, job_id: str, platform: str, remote_id: str, remote_url: str | None) -> None:
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            now = utcnow()
            updated = conn.execute(
                """UPDATE publication_targets SET status='published',remote_id=?,remote_url=?,
                error=NULL,updated_at=? WHERE job_id=? AND platform=? AND status='publishing'""",
                (remote_id, remote_url, now, job_id, platform),
            )
            if updated.rowcount != 1:
                raise ValueError("publication_not_claimed")
            if platform == "youtube":
                conn.execute("UPDATE jobs SET youtube_video_id=? WHERE id=?", (remote_id, job_id))
            self._refresh_publication_job_state(conn, job_id)
            self._event(
                conn,
                job_id,
                "published",
                f"Freigegebener Inhalt wurde auf {platform} veröffentlicht.",
                {"platform": platform, "remote_id": remote_id, "remote_url": remote_url},
            )
            conn.commit()

    def fail_publication(self, job_id: str, platform: str, message: str) -> None:
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            now = utcnow()
            conn.execute(
                """UPDATE publication_targets SET status='failed',error=?,updated_at=?
                WHERE job_id=? AND platform=? AND status='publishing'""",
                (message[:2000], now, job_id, platform),
            )
            conn.execute("UPDATE jobs SET error=? WHERE id=?", (f"{platform}: {message}"[:2000], job_id))
            self._refresh_publication_job_state(conn, job_id)
            self._event(
                conn,
                job_id,
                "publish_failed",
                f"Veröffentlichung auf {platform} fehlgeschlagen und wird nicht automatisch wiederholt.",
                {"platform": platform, "error": message[:500]},
            )
            conn.commit()

    def claim_publish(self) -> dict[str, Any] | None:
        return self.claim_publication()

    def finish_publish(self, job_id: str, youtube_video_id: str) -> None:
        self.finish_publication(job_id, "youtube", youtube_video_id, f"https://www.youtube.com/watch?v={youtube_video_id}")

    def fail_publish(self, job_id: str, message: str) -> None:
        self.fail_publication(job_id, "youtube", message)

    def recover_interrupted(self) -> None:
        with self._write_lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute("SELECT id FROM jobs WHERE status='rendering'").fetchall()
            for row in rows:
                conn.execute("UPDATE jobs SET status='render_queued',updated_at=? WHERE id=?", (utcnow(), row["id"]))
                self._event(conn, row["id"], "render_recovered", "Unterbrochener Auftrag erneut eingereiht.")
            publishing = conn.execute(
                "SELECT job_id,platform FROM publication_targets WHERE status='publishing'"
            ).fetchall()
            affected: set[str] = set()
            for row in publishing:
                message = "Upload wurde durch einen Neustart unterbrochen; externer Status ist unbekannt und muss manuell geprüft werden."
                conn.execute(
                    """UPDATE publication_targets SET status='unknown',error=?,updated_at=?
                    WHERE job_id=? AND platform=?""",
                    (message, utcnow(), row["job_id"], row["platform"]),
                )
                affected.add(row["job_id"])
                self._event(
                    conn,
                    row["job_id"],
                    "publish_interrupted",
                    f"Unterbrochener Upload auf {row['platform']} wird nicht automatisch wiederholt.",
                    {"platform": row["platform"]},
                )
            for job_id in affected:
                self._refresh_publication_job_state(conn, job_id)
            conn.commit()
