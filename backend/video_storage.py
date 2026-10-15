"""Copy finished, hash-verified videos to a chosen folder; never move originals."""
from pathlib import Path
import os
import shutil
import tempfile

from .config import settings
from .integrations import load
from .plan import file_sha256


def archive_video(job):
    preference = load()
    if not preference.archive_directory:
        return []
    root = Path(preference.archive_directory).expanduser().resolve()
    if root == Path(root.anchor):
        raise RuntimeError('Bitte einen eigenen Videoordner statt des Laufwerksstamms wählen.')
    root.mkdir(parents=True, exist_ok=True)
    saved = []
    for ratio, item in job['render_outputs'].items():
        source = (settings.jobs_dir / item['path']).resolve()
        if settings.jobs_dir not in source.parents or not source.is_file() or file_sha256(source) != item['sha256']:
            raise RuntimeError('Nur unveränderte fertige Videos können in den gewählten Videoordner kopiert werden.')
        name = f"{job['id']}-v{job['render_version']}-{ratio.replace(':', 'x')}.mp4"
        target = root / name
        if target.is_symlink() or target.exists():
            if target.is_symlink() or not target.is_file() or file_sha256(target) != item['sha256']:
                raise RuntimeError('Im Videoordner existiert bereits eine andere Datei dieses Namens; sie wird nicht überschrieben.')
            saved.append(str(target))
            continue
        with tempfile.NamedTemporaryFile(prefix='.video-', suffix='.pending', dir=root, delete=False) as handle:
            temporary = Path(handle.name)
        try:
            shutil.copyfile(source, temporary)
            if file_sha256(temporary) != item['sha256']:
                raise RuntimeError('Die Videokopie wurde nicht vollständig geschrieben.')
            # Exclusive creation prevents a race with a newly created destination.
            with target.open('xb') as destination, temporary.open('rb') as content:
                shutil.copyfileobj(content, destination)
                destination.flush()
                os.fsync(destination.fileno())
            saved.append(str(target))
        finally:
            temporary.unlink(missing_ok=True)
    return saved
