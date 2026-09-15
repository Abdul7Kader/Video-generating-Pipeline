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
from .plan import file_sha256, finalize_scene_plan, script_hash
from .planner import ScriptProviderUnavailable, generate_script, script_provider_status
from .rendering import dependency_status, render_job
from .schemas import JobCreate, ScriptRevision, ScriptUpdate, VersionAction
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
                output_hash = await asyncio.to_thread(file_sha256, Path(output))
                db.finish_render(job["id"], int(job["render_version"]), relative, output_hash, tts_mode)
            except Exception as exc:
                logger.exception("Render failed for %s", job["id"])
                db.fail_render(job["id"], str(exc))
            continue
        publish_job = db.claim_publish() if settings.youtube_enabled else None
        if publish_job:
            try:
                output = (settings.jobs_dir / publish_job["output_path"]).resolve()
                if file_sha256(output) != publish_job["approved_output_sha256"]:
                    raise RuntimeError("Die freigegebene Videodatei wurde nach der Freigabe verändert; Upload gestoppt.")
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
    return {
        "status": "ok",
        "dependencies": dependency_status(),
        "script_generation": script_provider_status(),
        "youtube_enabled": settings.youtube_enabled,
    }


@app.get("/api/jobs")
def list_jobs():
    return db.list_jobs()


@app.post("/api/jobs", status_code=201)
def create_job(payload: JobCreate):
    try:
        script = generate_script(payload)
    except ScriptProviderUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Skripterstellung fehlgeschlagen: {exc}") from exc
    return require_job(db.create_job(payload.model_dump(), script))


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    return require_job(job_id)


@app.put("/api/jobs/{job_id}/script")
def update_script(job_id: str, payload: ScriptUpdate):
    try:
        current = require_job(job_id)
        script = payload.model_dump(exclude={"expected_version"})
        script["metadata"] = {
            "provider": "manual_edit",
            "model": None,
            "parent": current["script"].get("metadata", {}),
        }
        script = finalize_scene_plan(script, current["duration_seconds"], current["script"])
        return db.update_script(job_id, payload.expected_version, script)
    except KeyError:
        raise HTTPException(404, "Auftrag nicht gefunden")
    except ValueError:
        raise HTTPException(409, "Das Skript wurde zwischenzeitlich geändert. Bitte neu laden.")


@app.post("/api/jobs/{job_id}/revise-script")
def revise_script(job_id: str, payload: ScriptRevision):
    current = require_job(job_id)
    if current["script_version"] != payload.expected_version:
        raise HTTPException(409, "Das Skript wurde zwischenzeitlich geändert. Bitte neu laden.")
    request = JobCreate.model_validate({
        "topic": current["topic"],
        "language": current["language"],
        "duration_seconds": current["duration_seconds"],
        "aspect_ratio": current["aspect_ratio"],
        "video_type": current["video_type"],
        "target_platform": current["target_platform"],
    })
    try:
        revised = generate_script(request, previous=current["script"], instructions=payload.instructions)
        if script_hash(revised) == current["script"]["content_hash"]:
            raise RuntimeError("Das Modell hat den Szenenplan trotz Änderungswunsch nicht verändert.")
        return db.update_script(job_id, payload.expected_version, revised)
    except ScriptProviderUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        if str(exc) == "version_conflict":
            raise HTTPException(409, "Das Skript wurde zwischenzeitlich geändert. Bitte neu laden.") from exc
        raise HTTPException(502, f"Skriptüberarbeitung fehlgeschlagen: {exc}") from exc
    except Exception as exc:
        raise HTTPException(502, f"Skriptüberarbeitung fehlgeschlagen: {exc}") from exc


@app.post("/api/jobs/{job_id}/approve-script")
def approve_script(job_id: str, payload: VersionAction):
    try:
        return db.approve_script(job_id, payload.expected_version, payload.expected_hash)
    except KeyError:
        raise HTTPException(404, "Auftrag nicht gefunden")
    except ValueError as exc:
        if str(exc) in {"hash_conflict", "script_integrity_error"}:
            raise HTTPException(409, "Der Szenenplan hat sich verändert oder seine Integritätsprüfung ist fehlgeschlagen. Bitte neu laden.") from exc
        raise HTTPException(409, "Nur die aktuelle Skriptversion kann freigegeben werden.") from exc


@app.post("/api/jobs/{job_id}/render")
def queue_render(job_id: str, payload: VersionAction):
    job = require_job(job_id)
    unsupported_visuals = [
        scene.get("visual_type")
        for scene in job["script"]["scenes"]
        if scene.get("visual_type", "stickman") != "stickman"
    ]
    if job["video_type"] != "stickman" or unsupported_visuals:
        raise HTTPException(
            409,
            "Diese Videoart wird erst freigeschaltet, wenn ihre visuellen Assets tatsächlich erzeugt und geprüft werden. "
            "Der alte Strichmännchen-Renderer wird nicht als Ersatz verwendet.",
        )
    try:
        return db.queue_render(job_id, payload.expected_version, payload.expected_hash)
    except KeyError:
        raise HTTPException(404, "Auftrag nicht gefunden")
    except ValueError as exc:
        if str(exc) in {"hash_conflict", "script_integrity_error"}:
            raise HTTPException(409, "Der freigegebene Szenenplan stimmt nicht mit der aktuellen Fassung überein.") from exc
        raise HTTPException(409, "Die aktuelle Skriptversion ist nicht freigegeben.") from exc


@app.post("/api/jobs/{job_id}/approve-video")
def approve_video(job_id: str, payload: VersionAction):
    job = require_job(job_id)
    if not job["output_path"]:
        raise HTTPException(409, "Video noch nicht erzeugt.")
    candidate = (settings.jobs_dir / job["output_path"]).resolve()
    if settings.jobs_dir not in candidate.parents or not candidate.exists():
        raise HTTPException(409, "Die zu prüfende Videodatei fehlt.")
    if file_sha256(candidate) != payload.expected_hash:
        raise HTTPException(409, "Die Videodatei hat sich seit dem Laden verändert. Bitte neu laden und erneut prüfen.")
    try:
        return db.approve_video(job_id, payload.expected_version, payload.expected_hash, settings.youtube_enabled)
    except KeyError:
        raise HTTPException(404, "Auftrag nicht gefunden")
    except ValueError as exc:
        raise HTTPException(409, "Nur die unveränderte aktuell gerenderte Videoversion kann freigegeben werden.") from exc


@app.get("/api/jobs/{job_id}/video")
def get_video(job_id: str):
    job = require_job(job_id)
    if not job["output_path"]:
        raise HTTPException(404, "Video noch nicht vorhanden")
    candidate = (settings.jobs_dir / job["output_path"]).resolve()
    if settings.jobs_dir not in candidate.parents or not candidate.exists():
        raise HTTPException(404, "Videodatei fehlt")
    if not job["output_sha256"] or file_sha256(candidate) != job["output_sha256"]:
        raise HTTPException(409, "Die Videodatei stimmt nicht mehr mit der erzeugten Version überein.")
    return FileResponse(candidate, media_type="video/mp4", filename=f"{job['script']['title']}.mp4")


web_dir = Path(__file__).resolve().parent.parent / "web"
app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
