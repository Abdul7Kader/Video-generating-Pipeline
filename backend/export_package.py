"""Offline handoff for channels without an available API grant; no login scripts."""
import json
from pathlib import Path

from .config import settings
from .integrations import load
from .plan import file_sha256
from .video_storage import copy_verified,output_file


def prepare_package(job):
    if not job.get('output_sha256') or not job.get('render_outputs'):
        raise RuntimeError('Zuerst ein fertiges Video erzeugen.')
    preference = load()
    base = Path(preference.archive_directory).resolve() if preference.archive_directory else settings.data_dir / 'exports'
    target = base / 'Uploadpakete' / f"{job['id']}-v{job['render_version']}-{job['output_sha256'][:16]}"
    target.mkdir(parents=True,exist_ok=True)
    files = {}
    for ratio,item in job['render_outputs'].items():
        source = output_file(item,settings)
        if not source.is_file() or file_sha256(source) != item['sha256']:
            raise RuntimeError('Die fertige Videodatei fehlt oder wurde verändert.')
        destination = target / ('video-' + ratio.replace(':','x') + '.mp4')
        copy_verified(source,destination,item['sha256'])
        files[ratio] = {'file':destination.name,'sha256':item['sha256']}
    contents = {'Beschriftung.txt':job['script']['title'] + '\n\n' + job['script']['description'],
        'Hinweise.txt':'Dieses Paket veröffentlicht nichts automatisch. Vor einem manuellen Upload den bisherigen Plattformstatus prüfen, damit kein doppelter Post entsteht. Nur das passende Videoformat wählen. Die Monetarisierung wird im jeweiligen Plattformkonto eingerichtet.',
        'Dateien.json':json.dumps({'job_id':job['id'],'version':job['render_version'],'files':files},ensure_ascii=False,indent=2)}
    for name,content in contents.items():
        path = target / name
        if path.is_symlink() or (path.exists() and path.read_text(encoding='utf-8') != content):
            raise RuntimeError('Geänderte Texte im Uploadpaket bleiben erhalten; vorhandenes Paket manuell prüfen.')
        if not path.exists():
            with path.open('x',encoding='utf-8') as output:
                output.write(content)
    return str(target)
