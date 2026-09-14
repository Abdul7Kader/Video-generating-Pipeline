from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import Database
from .planner import generate_script
from .rendering import dependency_status, render_job
from .schemas import JobCreate, ScriptUpdate, VersionAction
from .youtube import upload_video

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("video-pipeline")
db = Database(settings.database_path)


def require_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Auftrag nicht gefunden")
    return job


async def render_worker(stop: asyncio.Event) -> None:
    while not stop.is_set():
        job = db.claim_render()
        if job:
            try:
                output, tts_mode = await asyncio.to_thread(render_job, job)
                relative = str(Path(output).relative_to(settings.jobs_dir))
                db.finish_render(job["id"], int(job["render_version"]), relative, tts_mode)
            except Exception as exc:
                logger.exception("Render failed for %s", job["id"])
                db.fail_render(job["id"], str(exc))
            continue
        publish_job = db.claim_publish() if settings.youtube_enabled else None
        if publish_job:
            try:
                output = (settings.jobs_dir / publish_job["output_path"]).resolve()
                video_id = await asyncio.to_thread(upload_video, publish_job, output)
                db.finish_publish(publish_job["id"], video_id)
            except Exception as exc:
                logger.exception("Publish failed for %s", publish_job["id"])
                db.fail_publish(publish_job["id"], str(exc))
            continue
        if not job:
            try:
                await asyncio.wait_for(stop.wait(), timeout=1.5)
            except asyncio.TimeoutError:
                pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)
    settings.voices_dir.mkdir(parents=True, exist_ok=True)
    db.initialize()
    db.recover_interrupted()
    stop = asyncio.Event()
    worker = asyncio.create_task(render_worker(stop))
    yield
    stop.set()
    await worker


app = FastAPI(title="Video Pipeline", version="1.0.0", lifespan=lifespan, docs_url="/api/docs", redoc_url=None)


@app.get("/api/health")
def health():
    return {"status": "ok", "dependencies": dependency_status(), "script_provider": settings.script_provider, "youtube_enabled": settings.youtube_enabled}


@app.get("/api/jobs")
def list_jobs():
    return db.list_jobs()


@app.post("/api/jobs", status_code=201)
def create_job(payload: JobCreate):
    try:
        script = generate_script(payload)
    except Exception as exc:
        raise HTTPException(502, f"Skripterstellung fehlgeschlagen: {exc}") from exc
    return require_job(db.create_job(payload.model_dump(), script))


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    return require_job(job_id)


@app.put("/api/jobs/{job_id}/script")
def update_script(job_id: str, payload: ScriptUpdate):
    try:
        return db.update_script(job_id, payload.expected_version, payload.model_dump(exclude={"expected_version"}))
    except KeyError:
        raise HTTPException(404, "Auftrag nicht gefunden")
    except ValueError:
        raise HTTPException(409, "Das Skript wurde zwischenzeitlich geändert. Bitte neu laden.")


@app.post("/api/jobs/{job_id}/approve-script")
def approve_script(job_id: str, payload: VersionAction):
    try:
        return db.approve_script(job_id, payload.expected_version)
    except KeyError:
        raise HTTPException(404, "Auftrag nicht gefunden")
    except ValueError:
        raise HTTPException(409, "Nur die aktuelle Skriptversion kann freigegeben werden.")


@app.post("/api/jobs/{job_id}/render")
def queue_render(job_id: str, payload: VersionAction):
    try:
        return db.queue_render(job_id, payload.expected_version)
    except KeyError:
        raise HTTPException(404, "Auftrag nicht gefunden")
    except ValueError:
        raise HTTPException(409, "Die aktuelle Skriptversion ist nicht freigegeben.")


@app.post("/api/jobs/{job_id}/approve-video")
def approve_video(job_id: str, payload: VersionAction):
    try:
        return db.approve_video(job_id, payload.expected_version, settings.youtube_enabled)
    except KeyError:
        raise HTTPException(404, "Auftrag nicht gefunden")
    except ValueError:
        raise HTTPException(409, "Nur die aktuell gerenderte Videoversion kann freigegeben werden.")


@app.get("/api/jobs/{job_id}/video")
def get_video(job_id: str):
    job = require_job(job_id)
    if not job["output_path"]:
        raise HTTPException(404, "Video noch nicht vorhanden")
    candidate = (settings.jobs_dir / job["output_path"]).resolve()
    if settings.jobs_dir not in candidate.parents or not candidate.exists():
        raise HTTPException(404, "Videodatei fehlt")
    return FileResponse(candidate, media_type="video/mp4", filename=f"{job['script']['title']}.mp4")


web_dir = Path(__file__).resolve().parent.parent / "web"
app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
