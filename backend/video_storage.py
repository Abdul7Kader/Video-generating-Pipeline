"""Separate verified end products and keep their durable locations in the database."""
from pathlib import Path
import os
import shutil

from .config import settings
from .integrations import load
from .plan import file_sha256


def output_file(item, config=None):
    """Only server-recorded final locations or legacy files inside the jobs root."""
    config = config or settings
    if item.get('final_path'):
        final = Path(item['final_path'])
        if not final.is_absolute() or str(final).startswith(('\\\\','//')) or final.is_symlink() or getattr(final,'is_junction',lambda:False)():
            raise RuntimeError('Ungültiger lokaler Videoort.')
        return final.resolve()
    original = (config.jobs_dir / item['path']).resolve()
    if config.jobs_dir not in original.parents:
        raise RuntimeError('Ungültiger Videoort.')
    return original


def primary_output(job, config=None):
    return output_file(job['render_outputs'][job['aspect_ratio']],config)


def copy_verified(source, target, digest):
    if target.is_symlink() or target.exists():
        if target.is_symlink() or not target.is_file() or file_sha256(target) != digest:
            raise RuntimeError('Eine andere vorhandene Datei wird nicht überschrieben.')
        return
    created = False
    try:
        with target.open('xb') as destination:
            created = True
            with source.open('rb') as content:
                shutil.copyfileobj(content, destination)
            destination.flush()
            os.fsync(destination.fileno())
        if file_sha256(target) != digest:
            raise RuntimeError('Die Videokopie wurde nicht vollständig geschrieben.')
    except Exception:
        if created:
            target.unlink(missing_ok=True)
        raise


def archive_video(job):
    preference = load()
    root = Path(preference.archive_directory).resolve() if preference.archive_directory else settings.data_dir / 'videos'
    if root == Path(root.anchor):
        raise RuntimeError('Bitte einen eigenen Videoordner statt des Laufwerksstamms wählen.')
    if root == settings.jobs_dir or settings.jobs_dir in root.parents:
        raise RuntimeError('Den Videoordner außerhalb der Arbeitsdateien wählen.')
    root.mkdir(parents=True, exist_ok=True)
    saved = []
    for ratio, item in job['render_outputs'].items():
        source = output_file(item)
        if not source.is_file() or file_sha256(source) != item['sha256']:
            raise RuntimeError('Nur unveränderte fertige Videos können in den gewählten Videoordner kopiert werden.')
        name = f"{job['id']}-v{job['render_version']}-{ratio.replace(':', 'x')}-{item['sha256'][:16]}.mp4"
        target = root / name
        copy_verified(source,target,item['sha256'])
        saved.append(str(target))
    return saved


def separate_finished_video(db, job):
    """Register verified end products before removing only their working duplicates."""
    from .operations import operations
    with operations.lock:
        if job['id'] in operations.active or job['status'] in {'render_queued','rendering','render_planning','cancelling','publish_queued','publishing','publish_pending'}:
            raise RuntimeError('Zuerst laufende Produktion oder Übertragung abschließen.')
        if not job.get('render_outputs'):
            return []
        paths = archive_video(job)
        outputs = {ratio:{**item,'final_path':path} for (ratio,item),path in zip(job['render_outputs'].items(),paths)}
        db.save_final_locations(job['id'],job['render_version'],outputs)
        for item in job['render_outputs'].values():
            original = (settings.jobs_dir / item['path']).resolve()
            if settings.jobs_dir in original.parents and original.is_file() and not original.is_symlink() and file_sha256(original) == item['sha256']:
                # The durable database pointer and the verified final file already exist.
                original.unlink()
        return paths
