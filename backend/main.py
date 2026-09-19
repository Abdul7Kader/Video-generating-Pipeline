from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .antigravity import antigravity_status
from .assets import asset_provider_status, render_plan_readiness
from .config import settings
from .db import Database
from .gemini_cli import GeminiCliPool, parse_profile_names
from .gemini_workflow import GeminiScriptWorkflow
from .imported_media import ImportedMediaError, inspect_imported_video, save_stream, write_provenance_manifest
from .moneyprinter import moneyprinter_status
from .plan import file_sha256, finalize_scene_plan, script_hash
from .planner import ScriptProviderUnavailable, generate_script, script_provider_status, unload_script_model
from .production import build_production_catalog, normalize_production_config, production_plan_readiness
from .publishing import configured_automatic_platforms, platform_catalog, publish_to_target
from .rendering import dependency_status, render_job
from .schemas import JobCreate, ProductionConfigUpdate, Scene, SceneUpdate, ScriptRevision, ScriptUpdate, VersionAction

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("video-pipeline")
db = Database(settings.database_path)
try:
    _gemini_profile_names = parse_profile_names(settings.gemini_cli_profiles)
except ValueError:
    logger.exception("Invalid GEMINI_CLI_PROFILES configuration")
    _gemini_profile_names = ()
gemini_cli_pool = GeminiCliPool(
    _gemini_profile_names,
    settings.gemini_cli_profile_root,
    command=settings.gemini_cli_command,
    timeout_seconds=settings.gemini_cli_timeout_seconds,
    default_cooldown_seconds=settings.gemini_cli_cooldown_seconds,
)
gemini_script_workflow = GeminiScriptWorkflow(settings.database_path, gemini_cli_pool)


def require_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Auftrag nicht gefunden")
    output_path = job.get("output_path")
    if output_path:
        report_path = (settings.jobs_dir / str(output_path)).parent / "render-comparison.json"
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if (
                isinstance(report, dict)
                and report.get("script_hash") == job.get("render_script_hash")
                and (report.get("candidate") or {}).get("sha256") == job.get("output_sha256")
            ):
                job["render_comparison"] = report
        except (OSError, json.JSONDecodeError):
            pass
    return job


async def render_worker(stop: asyncio.Event) -> None:
    while not stop.is_set():
        job = db.claim_render()
        if job:
            try:
                await asyncio.to_thread(unload_script_model)
                output, tts_mode = await asyncio.to_thread(render_job, job)
                relative = str(Path(output).relative_to(settings.jobs_dir))
                output_hash = await asyncio.to_thread(file_sha256, Path(output))
                db.finish_render(job["id"], int(job["render_version"]), relative, output_hash, tts_mode)
            except Exception as exc:
                logger.exception("Render failed for %s", job["id"])
                db.fail_render(job["id"], str(exc))
            continue
        publish_job = db.claim_publication()
        if publish_job:
            platform = publish_job["publication_target"]["platform"]
            try:
                output = (settings.jobs_dir / publish_job["output_path"]).resolve()
                if file_sha256(output) != publish_job["approved_output_sha256"]:
                    raise RuntimeError("Die freigegebene Videodatei wurde nach der Freigabe verändert; Upload gestoppt.")
                remote_id, remote_url = await asyncio.to_thread(publish_to_target, publish_job, output, platform)
                db.finish_publication(publish_job["id"], platform, remote_id, remote_url)
            except Exception as exc:
                logger.exception("Publish failed for %s on %s", publish_job["id"], platform)
                db.fail_publication(publish_job["id"], platform, str(exc))
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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # FastAPI's Swagger UI intentionally loads its own documented CDN assets.
    # Keep the production UI strict without silently breaking /api/docs.
    if request.url.path != "/api/docs":
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"
        )
    return response


@app.get("/api/health")
def health():
    preferred_cloud = antigravity_status()
    return {
        "status": "ok",
        "dependencies": dependency_status(),
        "script_generation": preferred_cloud if preferred_cloud.get("ready") else script_provider_status(),
        "antigravity": preferred_cloud,
        "asset_generation": asset_provider_status(),
        "publication_platforms": platform_catalog(),
        "gemini_cli": {
            "enabled": settings.gemini_cli_enabled,
            "installed_profiles": len(_gemini_profile_names),
            "profiles": gemini_cli_pool.statuses(),
        },
        "youtube_enabled": settings.youtube_enabled,
    }


@app.get("/api/publication-platforms")
def publication_platforms():
    return platform_catalog()


@app.get("/api/production-options")
def production_options():
    dependencies = dependency_status()
    script_status = script_provider_status()
    profiles = gemini_cli_pool.statuses()
    qwen_ready = bool(
        (script_status.get("provider") == "ollama" and script_status.get("ready"))
        or script_status.get("fallback_ready")
    )
    return build_production_catalog(
        qwen_ready=qwen_ready,
        gemini_cli_ready=bool(
            settings.gemini_cli_enabled
            and any(profile.get("status") == "available" for profile in profiles)
        ),
        antigravity_ready=bool(antigravity_status().get("ready")),
        pexels_ready=bool(settings.pexels_api_key),
        piper_ready=bool(dependencies.get("piper_voice") or settings.piper_auto_download),
        gemini_tts_ready=bool(settings.allow_cloud_tts and settings.gemini_api_key),
        remotion_ready=all(
            bool(dependencies.get(name))
            for name in ("ffmpeg", "ffprobe", "node", "renderer")
        ),
        moneyprinter_ready=bool(dependencies.get("moneyprinter")),
    )


@app.get("/api/gemini-profiles")
def gemini_profiles():
    return {
        "enabled": settings.gemini_cli_enabled,
        "profiles": gemini_cli_pool.statuses(),
        "remaining_tokens": None,
        "message": "Resttokens werden nicht geschätzt; angezeigt werden nur von der CLI belegte Zustände.",
    }


@app.get("/api/jobs")
def list_jobs():
    return db.list_jobs()


@app.post("/api/jobs", status_code=201)
def create_job(payload: JobCreate):
    try:
        values = payload.model_dump()
        production_config = normalize_production_config(
            values.get("production_config"),
            legacy_video_type=payload.video_type,
            legacy_script_provider=payload.script_generator,
        )
        values["production_config"] = production_config
        values["video_type"] = production_config["video_type"]
        script_provider = production_config["script_provider"]
        job_id = None
        if payload.generation_id:
            provider_key = "gemini-cli" if script_provider == "gemini_cli" else script_provider
            job_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"video-pipeline:{provider_key}:{payload.generation_id}",
                )
            )
            existing = db.get_job(job_id)
            if existing:
                return existing
        if script_provider == "gemini_cli":
            if not settings.gemini_cli_enabled or not _gemini_profile_names:
                raise ScriptProviderUnavailable(
                    "Gemini CLI ist noch nicht aktiviert oder es ist kein angemeldetes Profil eingerichtet."
                )
            if not payload.generation_id:
                raise HTTPException(422, "Für Gemini CLI fehlt die generation_id zur sicheren Wiederaufnahme.")
            script = gemini_script_workflow.run(payload.generation_id, values)
            db.create_job(values, script, job_id=job_id)
            gemini_script_workflow.attach_job(payload.generation_id, job_id)
            return require_job(job_id)
        script = generate_script(payload.model_copy(update={"video_type": production_config["video_type"]}))
    except ScriptProviderUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Skripterstellung fehlgeschlagen: {exc}") from exc
    return require_job(db.create_job(values, script, job_id=job_id))


@app.get("/api/script-generations/{generation_id}")
def script_generation_status(generation_id: str):
    try:
        return gemini_script_workflow.status(generation_id)
    except KeyError as exc:
        raise HTTPException(404, "Skripterstellung nicht gefunden") from exc


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


@app.patch("/api/jobs/{job_id}/scenes/{scene_id}")
def update_scene(job_id: str, scene_id: str, payload: SceneUpdate):
    current = require_job(job_id)
    if current["script_version"] != payload.expected_version:
        raise HTTPException(409, "Das Skript wurde zwischenzeitlich geändert. Bitte neu laden.")
    scenes = [dict(scene) for scene in current["script"]["scenes"]]
    index = next((index for index, scene in enumerate(scenes) if scene.get("scene_id") == scene_id), None)
    if index is None:
        raise HTTPException(404, "Szene nicht gefunden")
    changes = payload.model_dump(exclude={"expected_version"}, exclude_none=True)
    candidate = Scene.model_validate({**scenes[index], **changes, "scene_id": scene_id}).model_dump()
    if candidate == Scene.model_validate(scenes[index]).model_dump():
        raise HTTPException(409, "Die Szene enthält keine tatsächliche Änderung.")
    scenes[index] = candidate
    script = finalize_scene_plan({
        "title": current["script"]["title"],
        "description": current["script"].get("description", ""),
        "scenes": scenes,
        "metadata": {
            "provider": "scene_edit",
            "model": None,
            "changed_scene_id": scene_id,
            "parent": current["script"].get("metadata", {}),
        },
    }, current["duration_seconds"], current["script"])
    try:
        return db.update_script(job_id, payload.expected_version, script)
    except ValueError as exc:
        if str(exc) == "version_conflict":
            raise HTTPException(409, "Das Skript wurde zwischenzeitlich geändert. Bitte neu laden.") from exc
        raise


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
        "production_config": current["production_config"],
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


@app.put("/api/jobs/{job_id}/production-config")
def update_production_config(job_id: str, payload: ProductionConfigUpdate):
    try:
        return db.update_production_config(
            job_id,
            payload.expected_version,
            payload.production_config.model_dump(),
        )
    except KeyError as exc:
        raise HTTPException(404, "Auftrag nicht gefunden") from exc
    except ValueError as exc:
        if str(exc) == "version_conflict":
            raise HTTPException(409, "Der Auftrag wurde zwischenzeitlich geändert. Bitte neu laden.") from exc
        if str(exc) == "job_busy":
            raise HTTPException(409, "Während Produktion oder Veröffentlichung kann das Produktionsprofil nicht geändert werden.") from exc
        if str(exc) == "configuration_unchanged":
            raise HTTPException(409, "Die Produktionskonfiguration wurde nicht verändert.") from exc
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/jobs/{job_id}/render")
def queue_render(job_id: str, payload: VersionAction):
    job = require_job(job_id)
    adapter_issues = []
    if job["production_config"].get("editor") == "moneyprinter":
        adapter_status = moneyprinter_status(settings)
        if not adapter_status["ready"]:
            adapter_issues.append(str(adapter_status["reason"]))
    readiness_issues = [
        *adapter_issues,
        *production_plan_readiness(job["production_config"], job["script"]["scenes"]),
        *render_plan_readiness(job["script"]["scenes"]),
    ]
    if readiness_issues:
        raise HTTPException(
            409,
            "Dieser Szenenplan ist noch nicht produzierbar: " + " ".join(readiness_issues),
        )
    try:
        return db.queue_render(job_id, payload.expected_version, payload.expected_hash)
    except KeyError:
        raise HTTPException(404, "Auftrag nicht gefunden")
    except ValueError as exc:
        if str(exc) in {"hash_conflict", "script_integrity_error"}:
            raise HTTPException(409, "Der freigegebene Szenenplan stimmt nicht mit der aktuellen Fassung überein.") from exc
        raise HTTPException(409, "Die aktuelle Skriptversion ist nicht freigegeben.") from exc


@app.get("/api/jobs/{job_id}/comparison-video/baseline")
def comparison_baseline_video(job_id: str):
    job = require_job(job_id)
    report = job.get("render_comparison") or {}
    baseline = report.get("baseline") or {}
    relative_path = baseline.get("relative_path")
    if report.get("status") != "ready" or not isinstance(relative_path, str):
        raise HTTPException(404, "Für diesen Auftrag liegt noch kein vergleichbarer Basis-Render vor.")
    job_root = (settings.jobs_dir / job_id).resolve()
    candidate = (job_root / relative_path).resolve()
    try:
        candidate.relative_to(job_root)
    except ValueError as exc:
        raise HTTPException(409, "Der gespeicherte Vergleichspfad ist ungültig.") from exc
    if not candidate.is_file() or file_sha256(candidate) != baseline.get("sha256"):
        raise HTTPException(409, "Das Vergleichsvideo fehlt oder wurde nachträglich verändert.")
    return FileResponse(candidate, media_type="video/mp4", filename="comparison-baseline.mp4")


@app.post("/api/jobs/{job_id}/import-video")
async def import_external_video(
    job_id: str,
    request: Request,
    source: str,
    expected_version: int,
    expected_hash: str,
    filename: str = "video.mp4",
):
    job = require_job(job_id)
    if (
        not job["script"]["integrity_verified"]
        or job["script_version"] != expected_version
        or job["approved_script_version"] != expected_version
        or job["approved_script_hash"] != expected_hash
        or job["script"]["content_hash"] != expected_hash
    ):
        raise HTTPException(409, "Nur die aktuelle freigegebene Skriptversion kann ein externes Video übernehmen.")
    if source not in {"gemini_app", "notebooklm"}:
        raise HTTPException(400, "Unbekannte externe Quelle.")
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in {"video/mp4", "application/mp4", "application/octet-stream"}:
        raise HTTPException(415, "Bitte eine MP4-Videodatei auswählen.")
    max_bytes = settings.external_import_max_mb * 1024 * 1024
    try:
        declared_size = int(request.headers.get("content-length", "0"))
    except ValueError:
        declared_size = 0
    if declared_size > max_bytes:
        raise HTTPException(413, f"Die Datei ist größer als das Limit von {settings.external_import_max_mb} MB.")

    version_dir = settings.jobs_dir / job_id / f"v{expected_version}"
    token = uuid.uuid4().hex
    temporary = version_dir / f"external-{token}.uploading"
    output = version_dir / f"external-{token}.mp4"
    manifest_path = version_dir / f"external-{token}.manifest.json"
    try:
        await save_stream(request.stream(), temporary, max_bytes=max_bytes)
        inspection = await asyncio.to_thread(inspect_imported_video, temporary)
        temporary.replace(output)
        manifest = await asyncio.to_thread(
            write_provenance_manifest,
            manifest_path,
            media_path=output,
            source=source,
            original_filename=filename,
            script_version=expected_version,
            script_hash=expected_hash,
            inspection=inspection,
        )
        relative = str(output.relative_to(settings.jobs_dir))
        return await asyncio.to_thread(
            db.attach_imported_video,
            job_id,
            expected_version,
            expected_hash,
            relative,
            manifest["sha256"],
            source,
        )
    except ImportedMediaError as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "Auftrag nicht gefunden") from exc
    except ValueError as exc:
        if str(exc) in {"hash_conflict", "script_integrity_error", "script_not_approved", "job_busy"}:
            raise HTTPException(409, "Der Auftrag hat sich während des Imports verändert. Bitte neu laden.") from exc
        raise
    finally:
        temporary.unlink(missing_ok=True)
        if not (db.get_job(job_id) or {}).get("output_path") == str(output.relative_to(settings.jobs_dir)):
            output.unlink(missing_ok=True)
            manifest_path.unlink(missing_ok=True)


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
        return db.approve_video(
            job_id,
            payload.expected_version,
            payload.expected_hash,
            configured_automatic_platforms(),
        )
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
