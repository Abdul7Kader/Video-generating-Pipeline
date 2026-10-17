from __future__ import annotations

import asyncio
import copy
import json
import logging
import re
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

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
from .production import build_production_catalog, normalize_production_config, production_plan_readiness, require_active_production
from .publishing import configured_automatic_platforms, platform_catalog, publish_to_target, PublicationError, PendingPublication
from .rendering import dependency_status, render_job, synthesize, normalize_narration_audio
from .schemas import JobCreate, ProductionConfig, ProductionConfigUpdate, Scene, SceneUpdate, ScriptRevision, ScriptUpdate, VersionAction, VideoApproval, VoicePreview, ProjectRetention
from .voices import VOICE_CHOICES, voice_choice, validate_voice_language, estimated_words_per_minute
from .speech import compact_speech, speech_metrics, VOICE_POLICY
from .story import generate_story, generate_storyboard, spoken_story
from .visual_coverage import visual_coverage_issues
from . import qwen_tts
from .operations import operations, OperationCancelled
from .plan import object_sha256
from . import setup
from .device import load_preferences
from . import web_import
from .failures import PipelineFailure,describe,STAGES
from .modes import require_mode,MODES
from . import frame

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("video-pipeline")
db = Database(settings.database_path)


def remember_failure(error,stage,job_id=None,**context):
    failure = describe(error,stage,**context)
    logger.error('Pipeline failure id=%s stage=%s code=%s type=%s',failure.identifier,failure.stage,failure.code,failure.diagnostics.get('exception_type','PipelineFailure'))
    try:
        db.record_failure(failure,job_id)
    except Exception:
        logger.error('Diagnostic persistence failed for id=%s',failure.identifier)
    return failure


def failed_http(error,stage,job_id=None,status=502):
    failure = remember_failure(error,stage,job_id)
    response = HTTPException(status,str(failure))
    response.pipeline_failure = failure
    return response


def request_stage(request):
    path = request.url.path
    if '/settings/images' in path or '/settings/image-access' in path: return 'image'
    if 'voice' in path: return 'voice'
    if 'approve-and-render' in path or 'web-board' in path or 'approve-frame-plan' in path: return 'planning'
    if 'discord' in path: return 'discord'
    if any(value in path for value in ('archive','export-package','clean-work','/video')): return 'storage'
    if 'publication' in path or 'approve-video' in path: return 'publish'
    if 'render' in path: return 'render'
    if path == '/api/jobs' or any(value in path for value in ('script','revision','scene','web-import')): return 'script'
    return 'request'


def request_job(request):
    match = re.match(r'^/api/jobs/([0-9a-f-]{36})(?:/|$)',request.url.path)
    return match[1] if match else None
_voice_preview_slot = threading.BoundedSemaphore(1)
_story_plan_slot = threading.BoundedSemaphore(1)
_web_import_lock = threading.Lock()
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
    if job.get('generation_mode')=='frame':
        from .frame_media import production_status
        job['frame_production']=production_status(job)
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
    next_confirmation = time.monotonic() + 60
    next_cleanup = time.monotonic() + 30
    while not stop.is_set() and not app.state.shutdown_requested.is_set():
        with app.state.worker_claim_lock:
            if app.state.shutdown_requested.is_set():
                return
            with operations.lock:
                # A planning operation may atomically queue its result before its
                # own context exits. Do not race it or lose a simultaneous cancel.
                job = None if operations.active else db.claim_render()
        if job:
            try:
                with operations.start(job['id'], db) as operation:
                    await asyncio.to_thread(unload_script_model)
                    outputs, tts_mode = {}, ''
                    for ratio in job['aspect_ratios']:
                        variant_dir = None if ratio == job['aspect_ratio'] else settings.jobs_dir / job['id'] / f"v{job['render_version']}" / 'formats' / ratio.replace(':', 'x')
                        variant_job = {**job, 'aspect_ratio': ratio, 'script': copy.deepcopy(job['script'])}
                        output, tts_mode = await asyncio.to_thread(operation.run, 'render',
                            {'job': variant_job, 'directory': str(variant_dir) if variant_dir else None})
                        outputs[ratio] = {'path': str(Path(output).relative_to(settings.jobs_dir)),
                                          'sha256': await asyncio.to_thread(file_sha256, Path(output))}
                    with operations.lock:
                        operation.check()
                        db.finish_render_variants(job['id'], int(job['render_version']), outputs, tts_mode)
                try:
                    from .video_storage import separate_finished_video
                    paths = await asyncio.to_thread(separate_finished_video, db, db.get_job(job['id']))
                    if paths:
                        db.record_event(job['id'], 'video_archived', 'Endvideos getrennt von Arbeitsdateien gespeichert.', {'paths': paths})
                except Exception as error:
                    remember_failure(error,'storage',job['id'])
                    db.record_event(job['id'], 'archive_failed', 'Videokopie fehlgeschlagen. Original im Projekt bleibt verfügbar; Ordner und freien Speicher prüfen.')
                try:
                    from .integrations import load as integration_preferences
                    from .reviews import Reviews
                    preference = integration_preferences()
                    if preference.discord_enabled:
                        Reviews(db).enqueue(job['id'],preference)
                except Exception as error:
                    remember_failure(error,'discord',job['id'])
                    db.record_event(job['id'],'discord_failed','Discord-Abnahme nicht eingereiht. Einstellungen prüfen; Video bleibt lokal verfügbar.')
            except OperationCancelled:
                pass
            except Exception as exc:
                failure = remember_failure(exc,'render',job['id'])
                db.fail_render(job["id"],str(failure))
            continue
        with app.state.worker_claim_lock:
            if app.state.shutdown_requested.is_set():
                return
            publish_job = db.claim_publication()
        if publish_job:
            platform = publish_job["publication_target"]["platform"]
            try:
                selected_output = publish_job.get("publication_output") or {
                    "path": publish_job["output_path"], "sha256": publish_job["output_sha256"]
                }
                from .video_storage import output_file
                output = output_file(selected_output,settings)
                if file_sha256(output) != publish_job["publication_target"]["approved_output_sha256"]:
                    raise PublicationError("Die freigegebene Videodatei wurde nach der Freigabe verändert; Upload gestoppt.")
                receipt = await asyncio.to_thread(publish_to_target, publish_job, output, platform)
                if isinstance(receipt,PendingPublication):
                    db.finish_publication(publish_job['id'],platform,receipt.remote_id,receipt.remote_url,awaiting_user=True,notice=receipt.message)
                else:
                    remote_id,remote_url = receipt
                    db.finish_publication(publish_job['id'],platform,remote_id,remote_url)
            except Exception as exc:
                failure = remember_failure(exc,'publish',publish_job['id'],platform=platform)
                message = str(failure)
                db.fail_publication(publish_job['id'],platform,message,unknown=getattr(exc,'uncertain',True),remote_id=getattr(exc,'remote_id',None))
            service = getattr(app.state,'discord_service',None)
            if service:
                await asyncio.to_thread(service.publish_status,publish_job['id'])
            continue
        if not job:
            if time.monotonic() >= next_cleanup:
                next_cleanup = time.monotonic() + 3600
                try:
                    from .retention import clean_expired_work
                    await asyncio.to_thread(clean_expired_work,db)
                except Exception:
                    logger.warning('Arbeitsdatei-Bereinigung pausiert; Dateien bleiben erhalten.')
            if time.monotonic() >= next_confirmation:
                next_confirmation = time.monotonic() + 60
                try:
                    from .social import check_pending
                    confirmed = await asyncio.to_thread(check_pending,db)
                    service = getattr(app.state,'discord_service',None)
                    if confirmed and service:
                        await asyncio.to_thread(service.publish_status,confirmed['job_id'])
                except Exception:
                    pass  # Read-only confirmation failure never queues another upload.
            try:
                await asyncio.wait_for(stop.wait(), timeout=1.5)
            except asyncio.TimeoutError:
                pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not getattr(app.state, 'desktop_mode', False):
        app.state.shutdown_requested.clear()
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)
    settings.voices_dir.mkdir(parents=True, exist_ok=True)
    db.initialize()
    db.recover_interrupted(resume_rendering=not getattr(app.state, 'desktop_mode', False))
    from .discord_review import DiscordReviewService
    discord_service = DiscordReviewService(db,approve_video,approve_story_and_render,
        accepting=lambda: not app.state.shutdown_requested.is_set(),claim_lock=app.state.worker_claim_lock)
    discord_service.reviews.recover()
    app.state.discord_service = discord_service
    app.state.integration_changes_blocked = lambda: any(job['status'] in {'publish_queued','publishing'} for job in db.list_jobs())
    discord_service.start()
    setup.manager.blocked = lambda: any(job['status'] in {'render_queued','rendering','publish_queued','publishing'} for job in db.list_jobs())
    preferences = load_preferences()
    if preferences and preferences.script == 'local' and settings.ollama_model:
        try:
            await asyncio.to_thread(setup.manager.ensure_ollama)
        except (OSError, RuntimeError):
            logger.warning('Lokaler Skriptdienst noch nicht bereit; Einrichtung in den Einstellungen prüfen.')
    stop = asyncio.Event()
    worker = asyncio.create_task(render_worker(stop))
    yield
    stop.set()
    await asyncio.to_thread(discord_service.close)
    await worker
    from .image_settings import close as close_image_preview
    await asyncio.to_thread(close_image_preview)
    setup.manager.close()


app = FastAPI(title="Video Pipeline", version="1.0.0", lifespan=lifespan, docs_url="/api/docs", redoc_url=None)
app.state.shutdown_requested = threading.Event()
app.state.worker_claim_lock = threading.Lock()
app.include_router(setup.router)
from .integrations import router as integrations_router
app.include_router(integrations_router)
from .image_settings import router as image_settings_router
app.include_router(image_settings_router)


@app.exception_handler(PipelineFailure)
async def pipeline_failure_response(request, error):
    failure = remember_failure(error,error.stage,request_job(request))
    return JSONResponse({'detail':str(failure),'failure':failure.public(request_job(request))},status_code=409 if failure.code == 'not_ready' else 502)


@app.exception_handler(StarletteHTTPException)
async def http_failure_response(request,error):
    failure = getattr(error,'pipeline_failure',None)
    if failure is None and error.status_code >= 500:
        failure = remember_failure(error.__cause__ or error,request_stage(request),request_job(request))
    payload = {'detail':str(failure) if failure else error.detail}
    if failure:
        payload['failure'] = failure.public(request_job(request))
    return JSONResponse(payload,status_code=error.status_code,headers=error.headers)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    loopback = {'localhost', '127.0.0.1', '::1'}
    if request.url.hostname not in loopback or not request.client or request.client.host not in {'127.0.0.1', '::1'}:
        return JSONResponse({'detail': 'Die Pipeline ist nur direkt auf diesem Rechner erreichbar.'}, status_code=403)
    origin = request.headers.get('origin')
    if request.headers.get('sec-fetch-site') == 'cross-site' or origin and origin != str(request.base_url).rstrip('/'):
        return JSONResponse({'detail': 'Ein fremder Webauftritt darf die lokale Pipeline nicht aufrufen.'}, status_code=403)
    production = request.method in {'POST','PUT','PATCH','DELETE'} and (request.url.path.startswith('/api/jobs') or request.url.path == '/api/voice-previews')
    if request.method == 'POST' and request.url.path == '/api/jobs':
        length=request.headers.get('content-length','')
        if not length.isdecimal() or int(length)>1500000:
            return JSONResponse({'detail':'Die Textanfrage benötigt eine gültige Länge bis 1,5 MB.'},status_code=413)
    if request.method == 'POST' and request.url.path.startswith('/api/jobs') and '/web-' in request.url.path:
        length = request.headers.get('content-length', '')
        if not length.isdecimal() or int(length) > 1500000:
            return JSONResponse({'detail': 'Die Webimport-Anfrage braucht eine gültige Länge von höchstens 1,5 MB.'}, status_code=413)
    if request.url.path.startswith('/api/settings') and request.method != 'GET':
        length = request.headers.get('content-length', '')
        if not length.isdecimal() or int(length) > 8192:
            return JSONResponse({'detail':'Die Einstellungsanfrage benötigt eine gültige Länge von höchstens 8192 Bytes.'}, status_code=413)
    with setup.manager.lock:
        if request.method not in {'GET', 'HEAD', 'OPTIONS'} and app.state.shutdown_requested.is_set():
            return JSONResponse({'detail': 'Die Anwendung wird beendet. Neue Arbeit wird nicht mehr gestartet.'}, status_code=503)
        blocked = production and setup.manager.busy
        if production and not blocked:
            setup.manager.production_requests += 1
    try:
        try:
            response = JSONResponse({'detail':'Die Rechnereinrichtung läuft. Warte auf ihren Abschluss.'}, status_code=409) if blocked else await call_next(request)
        except Exception as error:
            failure = remember_failure(error,request_stage(request),request_job(request))
            response = JSONResponse({'detail':str(failure),'failure':failure.public(request_job(request))},status_code=500)
    finally:
        if production and not blocked:
            with setup.manager.lock:
                setup.manager.production_requests -= 1
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith('/api/settings'):
        response.headers['Cache-Control'] = 'no-store'
    elif not request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-cache'
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
    cloud_selected = settings.script_provider == 'antigravity'
    preferred_cloud = antigravity_status() if cloud_selected else {'ready':False,'message':'Optionales Cloudprofil; anderer Skriptzugang ist gewählt.'}
    return {
        "status": "ok",
        'generation_modes':MODES,
        "dependencies": dependency_status(),
        "script_generation": preferred_cloud if cloud_selected else script_provider_status(),
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
    preferences = load_preferences()
    cloud_status = antigravity_status() if not preferences or preferences.script == 'antigravity' else {'ready':False,'message':'Optional: Cloudprofil in den Einstellungen aktivieren.'}
    qwen_ready = bool(
        (script_status.get("provider") == "ollama" and script_status.get("ready"))
        or script_status.get("fallback_ready")
    )
    if preferences and preferences.script == 'local' and qwen_ready:
        qwen_ready = setup.local_service_safe()
    catalog = build_production_catalog(
        qwen_ready=qwen_ready,
        gemini_cli_ready=bool(settings.gemini_cli_enabled and any(profile.get('status') == 'available' for profile in profiles)),
        antigravity_ready=bool(cloud_status.get("ready")),
        pexels_ready=bool(settings.pexels_api_key),
        piper_ready=bool(dependencies.get("piper_voice") or settings.piper_auto_download),
        gemini_tts_ready=bool(settings.allow_cloud_tts and settings.gemini_api_key),
        remotion_ready=all(
            bool(dependencies.get(name))
            for name in ("ffmpeg", "ffprobe", "node", "renderer")
        ),
        moneyprinter_ready=bool(dependencies.get("moneyprinter")),
        antigravity_reason=str(cloud_status.get("message", "Antigravity ist nicht verfügbar.")),
        qwen_tts_ready=qwen_tts.voice_status()["ready"],
    )
    preferences = load_preferences()
    defaults = {'antigravity': 'cloud_stickman', 'web_import': 'web_stickman'}
    catalog['default_profile_id'] = defaults.get(settings.script_provider, 'local_stickman')
    if preferences:
        catalog['default_profile_id'] = defaults.get(preferences.script, 'local_stickman')
        catalog['default_voice_id'] = 'qwen_narrator' if settings.tts_provider == 'qwen_tts' else 'thorsten'
    return catalog


@app.get("/api/gemini-profiles")
def gemini_profiles():
    return {
        "enabled": settings.gemini_cli_enabled,
        "profiles": gemini_cli_pool.statuses(),
        "remaining_tokens": None,
        "message": "Resttokens werden nicht geschätzt; angezeigt werden nur von der CLI belegte Zustände.",
    }


@app.get("/api/voices")
def voice_catalog():
    catalog = []
    for item in VOICE_CHOICES:
        if item.get("provider") == "qwen_tts":
            status = qwen_tts.voice_status()
            installed, available, reason = status["ready"], status["ready"], status["message"]
            if installed:
                from .device import device_info, recommendation
                if not recommendation(device_info())['qwen_suitable']:
                    available, reason = False, 'Für Qwen fehlt aktuell freier Arbeitsspeicher. Große Programme schließen oder ausdrücklich Piper wählen.'
        else:
            model = settings.voices_dir / f"{item['model']}.onnx"
            installed = model.is_file() and model.with_suffix(".onnx.json").is_file() and not (item['id']=='thorsten' and (settings.voices_dir / '.piper-setup-pending').exists())
            available, reason = settings.piper_auto_download or installed, ""
        catalog.append({**item, "provider": item.get("provider", "piper"),
                        "estimated_words_per_minute": estimated_words_per_minute(item["id"]),
                        "installed": installed, "available": available, "reason": reason})
    return catalog


@app.post("/api/voice-previews")
def create_voice_preview(payload: VoicePreview):
    if not _voice_preview_slot.acquire(blocking=False):
        raise HTTPException(429, "Eine Hörprobe wird gerade erstellt. Bitte danach erneut versuchen.")
    try:
        choice = voice_choice(payload.voice_id)
        cache_config = {**payload.model_dump(), "voice": choice, "policy": VOICE_POLICY}
        if choice.get("provider") == "qwen_tts":
            cache_config["qwen_voice"] = qwen_tts.voice_fingerprint()
        key = object_sha256(cache_config)
        root = settings.data_dir / "voice-previews"
        root.mkdir(parents=True, exist_ok=True)
        destination = root / f"{key}.wav"
        cached = destination.is_file()
        if cached:
            try:
                report = speech_metrics(destination)
            except (ValueError, OSError):
                destination.unlink(missing_ok=True)
                cached = False
        if not cached:
            if sum(path.stat().st_size for path in root.glob("*.wav")) > 128 * 1024 * 1024:
                raise HTTPException(429, "Der Hörproben-Cache ist voll. Vor weiteren Proben lokal bereinigen.")
            temporary = root / f"{key}.tmp.wav"
            try:
                if choice.get("provider") == "qwen_tts":
                    unload_script_model()
                mode, _ = synthesize(payload.text, temporary, choice["language"], provider=choice.get("provider", "piper"), voice_id=payload.voice_id, speed=payload.speed)
                if mode != choice.get('provider','piper'):
                    raise ValueError('Die erzeugte Stimme entspricht nicht der Auswahl.')
                compact_speech(temporary)
                normalize_narration_audio(temporary)
                report = speech_metrics(temporary)
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
        return {"voice_id": payload.voice_id, "voice_provider":choice.get('provider','piper'),
                "url": f"/api/voice-previews/{key}", "speed": payload.speed, 'cached':cached,
                'speech':report, 'policy':VOICE_POLICY}
    except (RuntimeError, ValueError, OSError) as exc:
        raise failed_http(exc,'voice',status=503) from None
    finally:
        _voice_preview_slot.release()


@app.get("/api/voice-previews/{preview_id}")
def get_voice_preview(preview_id: str):
    if not re.fullmatch(r"[0-9a-f]{64}", preview_id):
        raise HTTPException(404, "Hörprobe nicht gefunden.")
    path = settings.data_dir / "voice-previews" / f"{preview_id}.wav"
    if not path.is_file():
        raise HTTPException(404, "Hörprobe nicht gefunden.")
    return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/jobs")
def list_jobs():
    return db.list_jobs()


@app.post('/api/jobs/{job_id}/cancel')
def cancel_job(job_id: str):
    require_job(job_id)
    try:
        return operations.cancel(job_id, db)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


@app.post('/api/jobs/{job_id}/archive')
def archive_job(job_id: str):
    from .video_storage import separate_finished_video
    job = require_job(job_id)
    try:
        paths = separate_finished_video(db,job)
        if not paths:
            raise RuntimeError('Zuerst ein fertiges Video erzeugen.')
        db.record_event(job_id, 'video_archived', 'Fertige Videos im gewählten Videoordner gespeichert.', {'paths': paths})
        return {'paths': paths}
    except (RuntimeError, OSError, KeyError, ValueError) as error:
        raise failed_http(error,'storage',job_id,status=409) from None


@app.put('/api/jobs/{job_id}/retention')
def retain_work_files(job_id: str, payload: ProjectRetention):
    require_job(job_id)
    db.retain_project(job_id,payload.keep_work_files)
    return db.get_job(job_id)


@app.post('/api/jobs/{job_id}/clean-work')
def clean_job_work(job_id: str, payload: VersionAction):
    from .retention import clean_expired_work
    job = require_job(job_id)
    if payload.expected_version != job['render_version'] or payload.expected_hash != job['output_sha256']:
        raise HTTPException(409,'Videoversion geändert. Aktuelle Version neu laden.')
    try:
        return {'files':clean_expired_work(db,job_id=job_id,expected=(payload.expected_version,payload.expected_hash)),'job':db.get_job(job_id)}
    except (OSError,RuntimeError,ValueError) as error:
        raise failed_http(error,'storage',job_id,status=409) from None


@app.get('/api/jobs/{job_id}/discord-review')
def review_status(job_id: str):
    from .reviews import Reviews
    from .video_storage import primary_output
    job = require_job(job_id)
    service = getattr(app.state,'discord_service',None)
    return {'review':Reviews(db).latest(job_id),'connection':service.status if service else 'Discord-Abnahme startet mit der Anwendung.',
            'local_path':str(primary_output(job,settings)) if job['output_path'] else None,'job_status':job['status']}


@app.post('/api/jobs/{job_id}/discord-review')
def send_review(job_id: str, payload: VersionAction):
    from .integrations import load as integration_preferences
    from .reviews import Reviews
    current = require_job(job_id)
    if current['render_version'] != payload.expected_version or current['output_sha256'] != payload.expected_hash:
        raise HTTPException(409,'Die Videoversion hat sich geändert. Aktuelles Video neu laden.')
    preference = integration_preferences()
    if not preference.discord_enabled:
        raise HTTPException(409,'Zuerst Discord unter Einstellungen einrichten und aktivieren.')
    try:
        return Reviews(db).enqueue(job_id,preference,force=True)
    except ValueError as error:
        raise HTTPException(409,str(error)) from None


@app.post('/api/jobs/{job_id}/check-publication')
def check_publication(job_id: str):
    require_job(job_id)
    from .social import check_pending
    try:
        result = check_pending(db,job_id)
        service = getattr(app.state,'discord_service',None)
        if result and service:
            service.publish_status(job_id)
        return result or {'status':'Keine offene eingerichtete TikTok-Bestätigung.'}
    except PublicationError as error:
        raise HTTPException(409,str(error)) from None


@app.post('/api/jobs/{job_id}/export-package')
def export_package(job_id: str, payload: VersionAction):
    from .export_package import prepare_package
    job = require_job(job_id)
    if job['render_version'] != payload.expected_version or job['output_sha256'] != payload.expected_hash:
        raise HTTPException(409,'Die Videoversion wurde geändert. Aktuelle Version neu laden.')
    try:
        return {'directory':prepare_package(job)}
    except (RuntimeError,OSError) as error:
        raise failed_http(error,'storage',job_id,status=409) from None


def web_request(payload):
    if payload.generation_mode == 'frame':
        raise ValueError('Frame verwendet eigenen Sprechertext oder den eingerichteten automatischen Skriptzugang; dieser Webimport ist für Animationen.')
    values = payload.model_dump()
    config = normalize_production_config(values.get('production_config'), legacy_video_type=payload.video_type, legacy_script_provider=payload.script_generator)
    require_active_production(config)
    if config['script_provider'] != 'web_import':
        raise ValueError('Wähle das Profil Web-KI · manuell kopieren und einfügen.')
    validate_voice_language(config, payload.language)
    return payload.model_copy(update={'production_config': ProductionConfig.model_validate(config), 'script_mode': 'story', 'video_type': 'stickman'})


def current_web_story(job_id, payload):
    current = require_job(job_id)
    if current['production_config']['script_provider'] != 'web_import':
        raise HTTPException(422, 'Dieser Auftrag nutzt keinen manuellen Webimport.')
    if (current['script_version'] != payload.expected_version or current['script']['content_hash'] != payload.expected_hash
            or not current['script']['integrity_verified']):
        raise HTTPException(409, 'Die Textversion hat sich geändert. Neu laden und den aktuellen Prompt verwenden.')
    if current['status'] in {'render_queued', 'rendering', 'publish_queued', 'publishing'}:
        raise HTTPException(409, 'Der Auftrag wird bereits bearbeitet.')
    request = JobCreate.model_validate({key: current[key] for key in ('topic', 'language', 'duration_seconds', 'aspect_ratio', 'production_config')})
    return current, request


@app.post('/api/jobs/web-prompt')
def web_story_prompt(payload: web_import.WebStoryRequest):
    try:
        request = web_request(payload.request)
        prompt, _ = web_import.story.story_prompt(request)
        return {'prompt': web_import.prompt_text(prompt, web_import.story.StoryDraft.model_json_schema()), 'manual': True}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.post('/api/jobs/web-import', status_code=201)
def import_web_story(payload: web_import.WebStoryRequest):
    try:
        request = web_request(payload.request)
        if not request.generation_id:
            raise ValueError('Für einen wiederholbaren Import fehlt die generation_id.')
        identity = object_sha256({'request': request.model_dump(), 'response': payload.response})
        job_id = str(uuid.uuid5(uuid.NAMESPACE_URL, 'video-pipeline:web-import:'+request.generation_id))
        with _web_import_lock:
            existing = db.get_job(job_id)
            if existing:
                if existing['script'].get('metadata', {}).get('web_input_hash') != identity:
                    raise HTTPException(409, 'Diese Importkennung gehört zu einem anderen Entwurf. Lege einen neuen Auftrag an.')
                return existing
            script = web_import.validate_story(request, payload.response)
            script['metadata'].update(manual_import=True, web_input_hash=identity)
            return require_job(db.create_job(request.model_dump(), script, job_id=job_id))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.post('/api/jobs/{job_id}/web-revision-prompt')
def web_revision_prompt(job_id: str, payload: web_import.WebRevision):
    current, request = current_web_story(job_id, payload)
    prompt, _ = web_import.story.story_prompt(request, previous=current['script'], instructions=payload.instructions)
    return {'prompt': web_import.prompt_text(prompt, web_import.story.StoryDraft.model_json_schema()), 'manual': True}


@app.post('/api/jobs/{job_id}/web-revision-import')
def import_web_revision(job_id: str, payload: web_import.WebRevision):
    current, request = current_web_story(job_id, payload)
    try:
        revised = web_import.validate_story(request, payload.response, previous=current['script'], instructions=payload.instructions)
        if script_hash(revised) == current['script']['content_hash'] and all(revised['metadata'].get(key) == current['script'].get('metadata', {}).get(key) for key in ('visual_summary', 'fact_check_notes')):
            raise ValueError('Die Antwort enthält keine Änderung am Text oder an der Bildidee.')
        revised['metadata'].update(manual_import=True, web_input_hash=current['script'].get('metadata', {}).get('web_input_hash'))
        return db.update_script(job_id, payload.expected_version, revised)
    except ValueError as exc:
        raise HTTPException(409 if str(exc) in {'version_conflict', 'job_busy'} else 422, str(exc)) from None


@app.post('/api/jobs/{job_id}/web-board-prompt')
def web_board_prompt(job_id: str, payload: web_import.WebBoard):
    current, request = current_web_story(job_id, payload)
    try:
        instruction = web_import.story.storyboard_instruction(request, current['script'])
        prompt = web_import.planner._prompt(request, current['script'], instruction)
        db.approve_script(job_id, payload.expected_version, payload.expected_hash)
        return {'prompt': web_import.prompt_text(prompt, web_import.planner._response_schema()), 'manual': True,
                'expected_version': payload.expected_version, 'expected_hash': payload.expected_hash}
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


@app.post('/api/jobs/{job_id}/web-board-import')
def import_web_board(job_id: str, payload: web_import.WebBoard):
    existing = require_job(job_id)
    metadata = existing['script'].get('metadata', {})
    response_hash = object_sha256(payload.response)
    if (existing['production_config']['script_provider'] == 'web_import' and existing['script']['integrity_verified']
            and metadata.get('approved_story_version') == payload.expected_version
            and metadata.get('approved_story_hash') == payload.expected_hash
            and metadata.get('manual_board_hash') == response_hash
            and existing['approved_script_hash'] == existing['render_script_hash'] == existing['script']['content_hash']):
        return existing
    current, request = current_web_story(job_id, payload)
    if current['approved_script_version'] != payload.expected_version or current['approved_script_hash'] != payload.expected_hash:
        raise HTTPException(409, 'Gib zuerst den aktuellen Text frei und kopiere seinen Zeichenprompt.')
    try:
        plan = web_import.validate_board(request, current['script'], payload.response)
        plan['metadata']['manual_board_hash'] = response_hash
        return db.queue_story_render(job_id, payload.expected_version, payload.expected_hash, plan)
    except ValueError as exc:
        raise HTTPException(409 if str(exc) in {'version_conflict', 'hash_conflict', 'script_integrity_error', 'job_busy'} else 422, str(exc)) from None


def frame_request(job):
    return JobCreate.model_validate({**{key:job[key] for key in ('topic','language','duration_seconds','aspect_ratio','production_config')},
                                     'generation_mode':'frame','script_mode':'story'})


def create_frame_job(payload):
    if not _story_plan_slot.acquire(blocking=False):
        raise HTTPException(429,'Eine Text-/Bildplanung läuft bereits. Bitte danach erneut versuchen.')
    try:
        config=normalize_production_config(payload.production_config.model_dump() if payload.production_config else None,
                                           legacy_video_type='stickman',legacy_script_provider=payload.script_generator)
        require_active_production(config)
        validate_voice_language(config,payload.language)
        request=payload.model_copy(update={'production_config':ProductionConfig.model_validate(config),'video_type':'stickman'})
        values=request.model_dump();fingerprint=object_sha256(values)
        job_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'video-pipeline:frame:'+payload.generation_id)) if payload.generation_id else None
        if job_id and (existing:=db.get_job(job_id)):
            if existing['generation_mode']!='frame' or existing['script']['metadata'].get('request_fingerprint')!=fingerprint:
                raise HTTPException(409,'Diese Anfrage-ID gehört zu einem anderen Auftrag. Neu anlegen.')
            return existing
        if request.input_kind=='narration':
            script=frame.draft(request)
        else:
            from .operations import Operation
            script=Operation().run('frame_draft',{'request':values},timeout=frame.operation_timeout(request))
        script['metadata']['request_fingerprint']=fingerprint
        return require_job(db.create_job(values,script,job_id=job_id))
    except HTTPException:
        raise
    except Exception as error:
        raise failed_http(error,'script',status=503 if isinstance(error,ScriptProviderUnavailable) else 422 if isinstance(error,ValueError) else 502) from None
    finally:
        _story_plan_slot.release()


@app.post('/api/jobs/{job_id}/approve-frame-plan')
def approve_frame_plan(job_id: str, payload: VersionAction):
    current=require_job(job_id)
    if current['generation_mode']!='frame':
        raise HTTPException(422,'Bildsequenzplanung gehört zum Frame-Modus.')
    if current['script_version']!=payload.expected_version or current['script']['content_hash']!=payload.expected_hash or not current['script']['integrity_verified']:
        raise HTTPException(409,'Der Sprechertext wurde geändert. Aktuelle Fassung lesen und erneut freigeben.')
    if current.get('frame_plan') and current['approved_script_hash']==payload.expected_hash:
        frame.validate_plan(current['frame_plan'],current['script'])
        return queue_render(job_id,payload)
    if not _story_plan_slot.acquire(blocking=False):
        raise HTTPException(429,'Eine Text-/Bildplanung läuft bereits.')
    try:
        from .frame_media import production_readiness
        production_readiness(current)
        with operations.lock:
            if current['status']=='cancelling' or job_id in operations.active:
                raise ValueError('job_busy')
            db.approve_script(job_id,payload.expected_version,payload.expected_hash,allow_frame=True)
        with operations.start(job_id,db,allow_frame=True) as operation:
            db.begin_planning(job_id,payload.expected_version)
            request=frame_request(current)
            plan=operation.run('frame_plan',{'request':request.model_dump(),'script':current['script']},
                               timeout=frame.operation_timeout(request,frame.narration(current['script'])))
            with operations.lock:
                operation.check()
                db.save_frame_plan(job_id,payload.expected_version,payload.expected_hash,plan)
                return db.queue_render(job_id,payload.expected_version,payload.expected_hash)
    except OperationCancelled as error:
        raise HTTPException(409,str(error)) from None
    except Exception as error:
        failure=remember_failure(error,'planning',job_id)
        db.planning_failed(job_id,str(failure))
        response=HTTPException(409 if str(error) in {'version_conflict','hash_conflict','job_busy'} else 502,str(failure))
        response.pipeline_failure=failure
        raise response from None
    finally:
        _story_plan_slot.release()


@app.post("/api/jobs", status_code=201)
def create_job(payload: JobCreate):
    if payload.generation_mode == 'frame':
        return create_frame_job(payload)
    require_mode(payload.generation_mode)
    try:
        values = payload.model_dump()
        production_config = normalize_production_config(
            values.get("production_config"),
            legacy_video_type=payload.video_type,
            legacy_script_provider=payload.script_generator,
        )
        values["production_config"] = production_config
        require_active_production(production_config)
        validate_voice_language(production_config, payload.language)
        values["video_type"] = production_config["video_type"]
        script_provider = production_config["script_provider"]
        story_mode = payload.script_mode == 'story' and production_config['video_type'] == 'stickman'
        job_id = None
        if payload.generation_id:
            provider_key = "gemini-cli" if script_provider == "gemini_cli" else script_provider
            if story_mode:
                provider_key += ':story'
            job_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"video-pipeline:{provider_key}:{payload.generation_id}",
                )
            )
            existing = db.get_job(job_id)
            if existing:
                return existing
        if story_mode:
            script = generate_story(payload.model_copy(update={'production_config': ProductionConfig.model_validate(production_config)}))
        elif script_provider == "gemini_cli":
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
        else:
            script = generate_script(payload.model_copy(update={"video_type": production_config["video_type"]}))
    except ScriptProviderUnavailable as exc:
        raise failed_http(exc,'script',locals().get('job_id'),status=503) from None
    except HTTPException:
        raise
    except ValueError as exc:
        raise failed_http(exc,'script',locals().get('job_id'),status=422) from None
    except Exception as exc:
        raise failed_http(exc,'script',locals().get('job_id')) from None
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
    if require_job(job_id)['generation_mode']=='frame':
        raise HTTPException(422,'Frame verwendet einen Fließtext. Änderungen über „KI verbessert das Skript“ anfordern.')
    try:
        current = require_job(job_id)
        script = payload.model_dump(exclude={"expected_version"})
        script["metadata"] = {
            **{key: current["script"].get("metadata", {}).get(key) for key in ("audience", "tone", "fact_check_notes")},
            "provider": "manual_edit",
            "model": None,
            "parent": current["script"].get("metadata", {}),
        }
        script = finalize_scene_plan(script, current["duration_seconds"], current["script"])
        return db.update_script(job_id, payload.expected_version, script)
    except KeyError:
        raise HTTPException(404, "Auftrag nicht gefunden")
    except ValueError as exc:
        raise HTTPException(409, "Während der Produktion kann das Skript nicht geändert werden." if str(exc) == 'job_busy' else "Das Skript wurde zwischenzeitlich geändert. Bitte neu laden.") from exc


@app.patch("/api/jobs/{job_id}/scenes/{scene_id}")
def update_scene(job_id: str, scene_id: str, payload: SceneUpdate):
    current = require_job(job_id)
    if current['generation_mode']=='frame':
        raise HTTPException(422,'Frame hat keine animierten Einzelszenen. Den vollständigen Sprechertext überarbeiten lassen.')
    if current["script_version"] != payload.expected_version:
        raise HTTPException(409, "Das Skript wurde zwischenzeitlich geändert. Bitte neu laden.")
    scenes = [dict(scene) for scene in current["script"]["scenes"]]
    index = next((index for index, scene in enumerate(scenes) if scene.get("scene_id") == scene_id), None)
    if index is None:
        raise HTTPException(404, "Szene nicht gefunden")
    changes = payload.model_dump(exclude={"expected_version"}, exclude_none=True)
    try:
        candidate = Scene.model_validate({**scenes[index], **changes, "scene_id": scene_id}).model_dump()
    except ValueError as exc:
        raise HTTPException(422, "Zeichenregie passt nicht zum Sprechertext oder Gegenständen. Textanker und Regieschritte prüfen.") from exc
    if candidate == Scene.model_validate(scenes[index]).model_dump():
        raise HTTPException(409, "Die Szene enthält keine tatsächliche Änderung.")
    scenes[index] = candidate
    script = finalize_scene_plan({
        "title": current["script"]["title"],
        "description": current["script"].get("description", ""),
        "scenes": scenes,
        "metadata": {
            **{key: current["script"].get("metadata", {}).get(key) for key in ("audience", "tone", "fact_check_notes")},
            "provider": "scene_edit",
            "model": None,
            "changed_scene_id": scene_id,
            "parent": current["script"].get("metadata", {}),
        },
    }, current["duration_seconds"], current["script"])
    try:
        return db.update_script(job_id, payload.expected_version, script)
    except ValueError as exc:
        if str(exc) in {"version_conflict", "job_busy"}:
            raise HTTPException(409, "Das Skript wurde zwischenzeitlich geändert. Bitte neu laden.") from exc
        raise


@app.post("/api/jobs/{job_id}/revise-script")
def revise_script(job_id: str, payload: ScriptRevision):
    current = require_job(job_id)
    if current["script_version"] != payload.expected_version:
        raise HTTPException(409, "Das Skript wurde zwischenzeitlich geändert. Bitte neu laden.")
    if current['generation_mode']=='frame':
        if payload.scene_id or not current['script']['integrity_verified']:
            raise HTTPException(409,'Frame überarbeitet den vollständigen unveränderten Sprechertext.')
        if not _story_plan_slot.acquire(blocking=False):
            raise HTTPException(429,'Eine Text-/Bildplanung läuft bereits.')
        try:
            with operations.start(job_id,db,allow_frame=True) as operation:
                request=frame_request(current)
                revised=operation.run('frame_revise',{'request':request.model_dump(),'script':current['script'],'instructions':payload.instructions},
                                      timeout=frame.operation_timeout(request,frame.narration(current['script'])))
                if current['script']['metadata'].get('request_fingerprint'):
                    revised['metadata']['request_fingerprint']=current['script']['metadata']['request_fingerprint']
                with operations.lock:
                    operation.check()
                    if script_hash(revised)==current['script']['content_hash'] and all(revised.get('metadata',{}).get(key)==current['script'].get('metadata',{}).get(key) for key in ('visual_summary','fact_check_notes','visual_requests')):
                        raise ValueError('Die Überarbeitung hat den Text nicht verändert.')
                    return db.update_script(job_id,payload.expected_version,revised)
        except OperationCancelled as error:
            raise HTTPException(409,str(error)) from None
        except Exception as error:
            raise failed_http(error,'script',job_id,status=409 if str(error) in {'version_conflict','job_busy'} else 502) from None
        finally:
            _story_plan_slot.release()
    if payload.story_mode or current['script'].get('metadata', {}).get('workflow') in {'story_draft', 'storyboard'}:
        if current['video_type'] != 'stickman':
            raise HTTPException(422, 'Dieser Ablauf ist für Strichmännchen-Videos vorgesehen.')
        if payload.scene_id:
            raise HTTPException(422, 'Im Text-zuerst-Ablauf wird das ganze Skript überarbeitet.')
        if current['status'] in {'render_queued', 'rendering', 'publishing', 'publish_queued'}:
            raise HTTPException(409, 'Während der Produktion kann das Skript nicht überarbeitet werden.')
        request = JobCreate.model_validate({**{key: current[key] for key in ('topic', 'language', 'duration_seconds', 'aspect_ratio', 'production_config')}, 'script_mode': 'story'})
        try:
            revised = generate_story(request, previous=current['script'], instructions=payload.instructions)
            if script_hash(revised) == current['script']['content_hash'] and all(revised.get('metadata', {}).get(key) == current['script'].get('metadata', {}).get(key) for key in ('visual_summary', 'fact_check_notes')):
                raise ValueError('Die KI hat weder Text noch Bildidee oder sachliche Hinweise verändert.')
            return db.update_script(job_id, payload.expected_version, revised)
        except ScriptProviderUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409 if str(exc) in {'version_conflict', 'job_busy'} else 502, 'Während der Produktion kann das Skript nicht geändert werden.' if str(exc) == 'job_busy' else str(exc)) from exc
    selected_scene = next((scene for scene in current["script"]["scenes"] if scene["scene_id"] == payload.scene_id), None)
    if payload.scene_id and selected_scene is None:
        raise HTTPException(404, "Szene nicht gefunden.")
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
        instructions = payload.instructions
        if selected_scene:
            instructions = (f"Revise ONLY scene_id={payload.scene_id}; preserve this id and its duration. "
                            "Keep every other scene, title and description unchanged. Rewrite narration AND its drawing cues together. "
                            f"Requested scene change: {instructions}")
        revised = generate_script(request, previous=current["script"], instructions=instructions)
        if selected_scene:
            replacement = next((scene for scene in revised["scenes"] if scene["scene_id"] == payload.scene_id), None)
            if replacement is None:
                raise ValueError("Die KI hat die ausgewählte Szene nicht mit ihrer ID zurückgegeben.")
            replacement = Scene.model_validate({**replacement, "duration_seconds": selected_scene["duration_seconds"]}).model_dump()
            merged = copy.deepcopy(current["script"])
            merged["scenes"] = [replacement if scene["scene_id"] == payload.scene_id else scene for scene in merged["scenes"]]
            merged["metadata"] = {**revised.get("metadata", {}), "changed_scene_id": payload.scene_id, "revision_scope": "scene"}
            revised = merged
        if script_hash(revised) == current["script"]["content_hash"]:
            raise RuntimeError("Das Modell hat den Szenenplan trotz Änderungswunsch nicht verändert.")
        return db.update_script(job_id, payload.expected_version, revised)
    except ScriptProviderUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        if str(exc) in {"version_conflict", "job_busy"}:
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
        require_active_production(payload.production_config.model_dump())
        validate_voice_language(payload.production_config.model_dump(), require_job(job_id)["language"])
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
    require_mode(job.get('generation_mode','animated'))
    if job.get('generation_mode')=='frame':
        try:
            from .frame_media import production_readiness
            production_readiness(job)
            return db.queue_render(job_id,payload.expected_version,payload.expected_hash)
        except ValueError:
            raise HTTPException(409,'Aktuellen Frame-Text und Bildplan erneut freigeben; laufende Vorgänge zuerst beenden.') from None
    try:
        require_active_production(job["production_config"])
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    adapter_issues = []
    if job["production_config"].get("editor") == "moneyprinter":
        adapter_status = moneyprinter_status(settings)
        if not adapter_status["ready"]:
            adapter_issues.append(str(adapter_status["reason"]))
    readiness_issues = [
        *adapter_issues,
        *production_plan_readiness(job["production_config"], job["script"]["scenes"]),
        *render_plan_readiness(job["script"]["scenes"]),
        *(visual_coverage_issues(job['script']['scenes'], job['topic']) if job['video_type'] == 'stickman' else []),
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


@app.post('/api/jobs/{job_id}/approve-and-render')
def approve_story_and_render(job_id: str, payload: VersionAction):
    current = require_job(job_id)
    if current.get('generation_mode')=='frame':
        return approve_frame_plan(job_id,payload)
    require_mode(current.get('generation_mode','animated'))
    script = current['script']
    if not script['integrity_verified']:
        raise HTTPException(409, 'Die Integritätsprüfung des Skripts ist fehlgeschlagen.')
    metadata = script.get('metadata', {})
    if current['video_type'] != 'stickman':
        raise HTTPException(422, 'Dieser Ablauf ist für Strichmännchen-Videos vorgesehen.')
    original_approval = metadata.get('approved_story_hash') == payload.expected_hash and metadata.get('approved_story_version') == payload.expected_version
    current_approval = current['script_version'] == payload.expected_version and script['content_hash'] == payload.expected_hash
    approved_story = metadata.get('workflow') == 'storyboard' and (original_approval or current_approval) and current['render_script_hash'] == script['content_hash'] and current['approved_script_hash'] == script['content_hash']
    if approved_story:
        if current['status'] in {'render_failed', 'cancelled'}:
            return queue_render(job_id, VersionAction(expected_version=current['script_version'], expected_hash=script['content_hash']))
        if current['status'] in {'render_queued', 'rendering', 'video_review', 'ready_to_publish', 'publish_queued', 'publishing', 'published', 'published_partial', 'publish_failed'}:
            return current
    if current['script_version'] != payload.expected_version or script['content_hash'] != payload.expected_hash:
        raise HTTPException(409, 'Das Skript wurde zwischenzeitlich geändert. Bitte neu laden.')
    if current['status'] in {'render_queued', 'rendering', 'publish_queued', 'publishing'}:
        raise HTTPException(409, 'Der Auftrag wird bereits bearbeitet.')
    if not _story_plan_slot.acquire(blocking=False):
        raise HTTPException(429, 'Eine Geschichte wird bereits für die Produktion geplant. Bitte danach erneut versuchen.')
    try:
        require_active_production(current['production_config'])
        request = JobCreate.model_validate({key: current[key] for key in ('topic', 'language', 'duration_seconds', 'aspect_ratio', 'production_config')})
        with operations.start(job_id, db) as operation:
            db.begin_planning(job_id, payload.expected_version)
            plan = operation.run('plan', {'request': request.model_dump(), 'script': script})
            if spoken_story(plan) != spoken_story(script):
                raise ValueError('Die Bildplanung darf den freigegebenen Sprechertext nicht verändern.')
            issues = production_plan_readiness(current['production_config'], plan['scenes']) + render_plan_readiness(plan['scenes']) + visual_coverage_issues(plan['scenes'], current['topic'])
            if issues:
                raise ValueError(' '.join(issues))
            with operations.lock:
                operation.check()
                return db.queue_story_render(job_id, payload.expected_version, payload.expected_hash, plan)
    except OperationCancelled as exc:
        raise HTTPException(409, str(exc)) from exc
    except ScriptProviderUnavailable as exc:
        failure = remember_failure(exc,'planning',job_id)
        db.planning_failed(job_id,str(failure))
        response = HTTPException(503,str(failure))
        response.pipeline_failure=failure
        raise response from None
    except (ValueError, RuntimeError) as exc:
        status = 409 if str(exc) in {'version_conflict', 'hash_conflict', 'script_integrity_error', 'job_busy'} else 502
        failure = remember_failure(exc,'planning',job_id)
        db.planning_failed(job_id,str(failure))
        response = HTTPException(status,str(failure))
        response.pipeline_failure=failure
        raise response from None
    finally:
        _story_plan_slot.release()


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
        if str(exc) == "import_requires_single_format":
            raise HTTPException(409, "Der Videoimport unterstützt nur Aufträge mit genau einem Format.") from exc
        if str(exc) in {"hash_conflict", "script_integrity_error", "script_not_approved", "job_busy"}:
            raise HTTPException(409, "Der Auftrag hat sich während des Imports verändert. Bitte neu laden.") from exc
        raise
    finally:
        temporary.unlink(missing_ok=True)
        if not (db.get_job(job_id) or {}).get("output_path") == str(output.relative_to(settings.jobs_dir)):
            output.unlink(missing_ok=True)
            manifest_path.unlink(missing_ok=True)


@app.post("/api/jobs/{job_id}/approve-video")
def approve_video(job_id: str, payload: VideoApproval):
    from .integrations import lock as configuration_lock
    with configuration_lock:
        return _approve_video_locked(job_id,payload)


def _approve_video_locked(job_id: str, payload: VideoApproval):
    job = require_job(job_id)
    if not job["output_path"]:
        raise HTTPException(409, "Video noch nicht erzeugt.")
    from .video_storage import primary_output,output_file
    candidate = primary_output(job,settings)
    if not candidate.exists():
        raise HTTPException(409, "Die zu prüfende Videodatei fehlt.")
    if file_sha256(candidate) != payload.expected_hash:
        raise HTTPException(409, "Die Videodatei hat sich seit dem Laden verändert. Bitte neu laden und erneut prüfen.")
    for ratio, item in job["render_outputs"].items():
        variant = output_file(item,settings)
        if not variant.is_file() or file_sha256(variant) != item["sha256"]:
            raise HTTPException(409, f"Das gerenderte Format {ratio} fehlt oder wurde verändert. Bitte erneut erzeugen.")
    try:
        return db.approve_video(
            job_id,
            payload.expected_version,
            payload.expected_hash,
            configured_automatic_platforms(),
            payload.target_platforms,
        )
    except KeyError:
        raise HTTPException(404, "Auftrag nicht gefunden")
    except ValueError as exc:
        if str(exc) == "format_unavailable":
            raise HTTPException(409, "Für mindestens eine gewählte Plattform fehlt ein passendes Videoformat.") from exc
        if str(exc) == "media_unavailable":
            raise HTTPException(409, "Für Audio- oder Musikplattformen fehlt noch ein geeignetes Ausgabeformat.") from exc
        if str(exc) == "publication_already_approved":
            raise HTTPException(409, "Diese Videoversion ist bereits freigegeben. Für andere Ziele ist eine neue Videoversion nötig.") from exc
        raise HTTPException(409, "Nur die unveränderte aktuell gerenderte Videoversion kann freigegeben werden.") from exc


@app.get("/api/jobs/{job_id}/video")
def get_video(job_id: str, aspect_ratio: str | None = Query(default=None)):
    job = require_job(job_id)
    ratio = aspect_ratio or job["aspect_ratio"]
    variant = job["render_outputs"].get(ratio)
    if not variant:
        raise HTTPException(404, "Video noch nicht vorhanden")
    from .video_storage import output_file
    candidate = output_file(variant,settings)
    if not candidate.exists():
        raise HTTPException(404, "Videodatei fehlt")
    if not variant["sha256"] or file_sha256(candidate) != variant["sha256"]:
        raise HTTPException(409, "Die Videodatei stimmt nicht mehr mit der erzeugten Version überein.")
    safe_title = "".join(char if char.isalnum() or char in "-_ " else "_" for char in job["script"]["title"])
    return FileResponse(candidate, media_type="video/mp4", filename=f"{safe_title}-{ratio.replace(':', 'x')}.mp4")


web_dir = Path(__file__).resolve().parent.parent / "web"
app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
