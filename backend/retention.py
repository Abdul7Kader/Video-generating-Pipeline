"""App-owned work files expire; end products, scripts and pinned projects do not."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re

from .config import settings
from .db import utcnow
from .integrations import load
from .operations import operations
from .plan import file_sha256
from .video_storage import output_file, separate_finished_video

BUSY = {'render_queued','rendering','render_planning','cancelling','publish_queued','publishing','publish_pending','script_approved','script_review'}
GENERATED = {'narration.wav','captions.srt','subtitles.srt','render-props.json','voice-manifest.json','asset-manifest.json','frame-timeline.json','frame-concat.txt'}


def linked(path):
    return path.is_symlink() or getattr(path,'is_junction',lambda:False)()


def work_files(root):
    """Never follow links/reparse directories; unknown files and every MP4 survive."""
    for directory,folders,files in os.walk(root,followlinks=False):
        current = Path(directory)
        folders[:] = [name for name in folders if not linked(current / name)]
        for name in files:
            file = current / name
            if linked(file) or root not in file.resolve().parents or file.suffix.lower() == '.mp4':
                continue
            relative = file.relative_to(root)
            if not re.fullmatch(r'v[0-9]+',relative.parts[0]):
                continue
            frame_sidecar=('audio' in relative.parts or 'assets' in relative.parts) and bool(re.fullmatch(r'[a-f0-9]{64}(\.rejected|\.pending)?\.json',name))
            if name in GENERATED or frame_sidecar or ('audio' in relative.parts and file.suffix.lower() == '.wav') or ('assets' in relative.parts and file.suffix.lower() in {'.svg','.png','.jpg','.jpeg','.webp'}):
                yield file


def clean_expired_work(db, *, now=None, job_id=None, expected=None):
    days = load().work_retention_days
    if not days and not job_id:
        return 0
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    removed = 0
    for candidate in ([db.get_job(job_id)] if job_id else db.list_jobs()):
        if not candidate:
            continue
        if expected and (candidate['render_version'],candidate['output_sha256']) != expected:
            continue
        if candidate.get('keep_work_files') or candidate['status'] in BUSY or (not job_id and datetime.fromisoformat(candidate['updated_at']) > cutoff):
            continue
        if not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',candidate['id']):
            continue
        root = settings.jobs_dir / candidate['id']
        if linked(settings.jobs_dir) or linked(root) or not root.is_dir() or root.resolve().parent != settings.jobs_dir.resolve():
            continue
        if candidate.get('render_outputs') and any(not item.get('final_path') for item in candidate['render_outputs'].values()):
            try:
                separate_finished_video(db,db.get_job(candidate['id']))
            except (OSError,RuntimeError,ValueError):
                continue
        # Serialize with work starts and all database mutations until deletion ends.
        with operations.lock,db._write_lock,db.connect() as conn:
            if candidate['id'] in operations.active:
                continue
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM jobs WHERE id=?',(candidate['id'],)).fetchone()
            if expected and row and (row['render_version'],row['output_sha256']) != expected:
                continue
            if not row or row['keep_work_files'] or row['status'] in BUSY or (not job_id and datetime.fromisoformat(row['updated_at']) > cutoff):
                continue
            pending = conn.execute("SELECT 1 FROM publication_targets WHERE job_id=? AND status IN ('queued','publishing','unknown','awaiting_user')",(candidate['id'],)).fetchone()
            review = conn.execute("SELECT 1 FROM discord_reviews WHERE job_id=? AND state IN ('queued','sending','deciding','revision_requested','revising','render_requested','planning')",(candidate['id'],)).fetchone()
            if pending or review:
                continue
            outputs = json.loads(row['output_variants_json'])
            if outputs and any(not item.get('final_path') or not output_file(item,settings).is_file() or file_sha256(output_file(item,settings)) != item['sha256'] for item in outputs.values()):
                continue  # A missing/disconnected end-product drive never permits cleanup.
            files = list(work_files(root))
            if not job_id and any(file.stat().st_mtime > cutoff.timestamp() for file in files):
                continue
            count = 0
            for file in files:
                if linked(file) or root.resolve() not in file.resolve().parents:
                    continue
                file.unlink()
                count += 1
            if count:
                conn.execute('UPDATE jobs SET work_cleaned_at=? WHERE id=?',(utcnow(),candidate['id']))
                db._event(conn,candidate['id'],'work_cleaned','Ton-/Bild-Arbeitsdateien bereinigt; Endvideos und Skriptversionen erhalten.',{'files':count,'manual':bool(job_id)})
                conn.commit()
                removed += count
    return removed
