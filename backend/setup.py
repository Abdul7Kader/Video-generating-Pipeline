"""Explicit UI setup actions: fixed commands, local services, no user shell code."""
from __future__ import annotations

import copy
import json
import os
import ipaddress
import platform
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, ConfigDict

from .config import settings
from .device import ROOT, ModelName, MachinePreferences, ManualHardware, device_info, recommendation, load_preferences, save_preferences
from .moneyprinter import _safe_environment, _terminate_process_tree
from .quality import find_ffmpeg, find_ffprobe
from .qwen_tts import voice_status

router = APIRouter(prefix='/api/settings')
TOKEN = secrets.token_urlsafe(32)


class SetupAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['start_ollama', 'script_model', 'render_tools', 'piper_voice', 'qwen_voice']
    model: ModelName | None = None
    hardware: ManualHardware | None = None


def ollama_executable():
    candidates = [shutil.which('ollama'), ROOT / '.runtime' / 'ollama' / 'bin' / ('ollama.exe' if os.name == 'nt' else 'ollama')]
    if os.name == 'nt' and os.getenv('LOCALAPPDATA'):
        candidates.append(Path(os.environ['LOCALAPPDATA']) / 'Programs' / 'Ollama' / 'ollama.exe')
    return next((str(candidate) for candidate in candidates if candidate and Path(candidate).is_file()), None)


def local_request(path, payload=None, timeout=3):
    # Never accept a client URL, operator proxy, remote address or redirect.
    request = urllib.request.Request('http://127.0.0.1:11434' + path,
                                     data=json.dumps(payload).encode() if payload is not None else None,
                                     headers={'Content-Type': 'application/json'})
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise ValueError('Der lokale Dienst darf nicht auf einen anderen Host umleiten.')
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(request, timeout=timeout)


def ollama_models():
    try:
        with local_request('/api/tags') as response:
            values = [item['name'] for item in json.loads(response.read(1024 * 1024))['models']]
        return values if local_service_safe() else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def local_service_safe():
    """A pre-existing service must also be loopback-only before we use it."""
    try:
        if os.name == 'nt':
            command = ['powershell.exe','-NoProfile','-NonInteractive','-Command', '(Get-NetTCPConnection -State Listen -LocalPort 11434 -ErrorAction SilentlyContinue).LocalAddress | ConvertTo-Json -Compress']
            output = subprocess.check_output(command, timeout=8, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            values = json.loads(output) if output.strip() else []
            addresses = [values] if isinstance(values,str) else values
        elif platform.system() == 'Linux':
            addresses = []
            for name in ('tcp','tcp6'):
                for line in Path('/proc/net',name).read_text().splitlines()[1:]:
                    columns=line.split()
                    raw,port=columns[1].split(':')
                    if int(port,16)!=11434 or columns[3]!='0A':
                        continue
                    raw_bytes=bytes.fromhex(raw)
                    address=raw_bytes[::-1] if name=='tcp' else b''.join(raw_bytes[i:i+4][::-1] for i in range(0,16,4))
                    addresses.append(str(ipaddress.ip_address(address)))
        else:
            output=subprocess.check_output(['lsof','-nP','-iTCP:11434','-sTCP:LISTEN','-Fn'],timeout=5,text=True)
            addresses=[line[1:].rsplit(':',1)[0].strip('[]') for line in output.splitlines() if line.startswith('n')]
        return bool(addresses) and all(ipaddress.ip_address(address).is_loopback for address in addresses)
    except (OSError,ValueError,TypeError,subprocess.SubprocessError):
        return False


def browser_available():
    configured = os.getenv('REMOTION_BROWSER_EXECUTABLE')
    if configured:
        return Path(configured).is_file()
    if os.name == 'nt':
        roots = [os.getenv('PROGRAMFILES', 'C:/Program Files'), os.getenv('PROGRAMFILES(X86)', 'C:/Program Files (x86)'), os.getenv('LOCALAPPDATA', '')]
        return any((Path(root) / suffix).is_file() for root in roots if root for suffix in ('Google/Chrome/Application/chrome.exe','Microsoft/Edge/Application/msedge.exe'))
    return bool(shutil.which('google-chrome') or shutil.which('google-chrome-stable') or shutil.which('chromium') or shutil.which('chromium-browser') or
                Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome').is_file() or Path('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge').is_file())


class SetupManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.task = {'status': 'idle', 'message': 'Noch kein Einrichtungsschritt gestartet.', 'percent': None}
        self.production_requests = 0
        self.service = None
        self.process = None
        self.cancel = threading.Event()
        self.blocked = lambda: False

    @property
    def busy(self):
        with self.lock:
            return self.task['status'] == 'running'

    def status(self):
        with self.lock:
            return copy.deepcopy(self.task)

    def update(self, **values):
        with self.lock:
            self.task.update(values)

    def require_idle(self):
        if self.busy or self.production_requests or self.blocked():
            raise HTTPException(409, 'Einrichtung und Videoproduktion können nicht gleichzeitig laufen. Warte auf den laufenden Vorgang.')

    def run(self, command, *, cwd=ROOT, timeout=1800, environment=None):
        env = _safe_environment()
        env.update(environment or {})
        env.update(PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_CONFIG_FILE=os.devnull, PIP_NO_INPUT='1',
                   NPM_CONFIG_STRICT_SSL='true',
                   HF_HUB_DISABLE_TELEMETRY='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1')
        cache = ROOT / 'data' / 'setup-cache'
        for key, name in [('PIP_CACHE_DIR','pip'),('NPM_CONFIG_CACHE','npm'),('HF_HOME','huggingface'),('TMPDIR','tmp'),('TEMP','tmp'),('TMP','tmp')]:
            destination=cache / name
            destination.mkdir(parents=True,exist_ok=True)
            env[key]=str(destination)
        options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
        (ROOT / '.runtime').mkdir(exist_ok=True)
        # npm refuses loading the same empty file twice; keep user/global
        # configs separate, without inheriting tokens or weakened TLS settings.
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime', prefix='setup-config-', ignore_cleanup_errors=True) as folder:
            for name, key in [('user.conf','NPM_CONFIG_USERCONFIG'),('global.conf','NPM_CONFIG_GLOBALCONFIG')]:
                path=Path(folder,name)
                path.write_text('',encoding='utf-8')
                env[key]=str(path)
            with subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options) as process:
                self.process = process
                try:
                    process.wait(timeout=timeout)
                    if process.returncode:
                        raise RuntimeError('Der Installationsschritt ist fehlgeschlagen. Prüfe Internetverbindung, freien Speicher und die angegebenen Voraussetzungen; du kannst ihn erneut starten.')
                except subprocess.TimeoutExpired:
                    _terminate_process_tree(process)
                    raise RuntimeError('Die Einrichtung hat ihr Zeitlimit erreicht. Ein erneuter Start setzt vorhandene Downloads nach Möglichkeit fort.')
                finally:
                    self.process = None

    def ensure_ollama(self):
        if ollama_models() is not None:
            return
        executable = ollama_executable()
        if not executable:
            raise RuntimeError('Installiere Ollama über den offiziellen Download und prüfe den Rechner erneut.')
        try:
            with socket.create_connection(('127.0.0.1', 11434), timeout=1):
                raise RuntimeError('Der lokale Ollama-Port ist bereits durch einen unbekannten Dienst belegt. Es wird kein weiterer Port geöffnet.')
        except (ConnectionRefusedError, socket.timeout):
            pass
        env = _safe_environment()
        env.update(OLLAMA_HOST='127.0.0.1:11434', OLLAMA_NO_CLOUD='1', OLLAMA_NOHISTORY='1',
                   OLLAMA_MODELS=str(ROOT / 'data' / 'ollama' / 'models'),
                   OLLAMA_NUM_PARALLEL='1', OLLAMA_MAX_LOADED_MODELS='1', OLLAMA_MAX_QUEUE='4')
        options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
        self.service = subprocess.Popen([executable, 'serve'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
        for _ in range(40):
            if ollama_models() is not None:
                return
            if self.service.poll() is not None:
                break
            time.sleep(.25)
        raise RuntimeError('Ollama konnte lokal nicht gestartet werden. Prüfe den offiziellen Installer und den lokalen Port 11434.')

    def start(self, payload):
        if not all((ROOT / name).resolve().is_relative_to(ROOT) for name in ('.runtime','data')):
            raise HTTPException(422, 'Die Einrichtungsverzeichnisse dürfen den Projektordner nicht über Verknüpfungen verlassen.')
        if payload.action == 'piper_voice' and not settings.voices_dir.resolve().is_relative_to(ROOT):
            raise HTTPException(422, 'Die UI lädt Stimmen nur in den Projektordner. Prüfe DATA_DIR in deiner externen Konfiguration.')
        info = device_info(payload.hardware)
        choice = recommendation(info)
        if payload.action == 'script_model' and payload.model not in choice['allowed_models']:
            raise HTTPException(422, 'Dieses Modell liegt außerhalb des erkannten Rechnerbudgets. Ergänze bei Bedarf die Geräteangaben.')
        if payload.action == 'qwen_voice':
            expected = ROOT / '.runtime' / 'qwen-python' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            if not expected.resolve().is_relative_to(ROOT) or settings.qwen_tts_python.resolve() != expected.resolve():
                raise HTTPException(422, 'Die UI installiert Qwen ausschließlich in der projektlokalen Laufzeit. Prüfe die extern gesetzte QWEN_TTS_PYTHON-Konfiguration.')
            if not settings.qwen_tts_model_dir.resolve().is_relative_to(ROOT) or settings.qwen_tts_model_dir.resolve() != (ROOT / 'data' / 'voices' / 'qwen-model').resolve():
                raise HTTPException(422, 'Die UI lädt Stimmendaten nur in den Projektordner. Prüfe die extern gesetzte QWEN_TTS_MODEL_DIR-Konfiguration.')
            if not choice['qwen_suitable'] or info['disk_free_gb'] < 20:
                raise HTTPException(422, 'Für die Qwen-Einrichtung sind mindestens 24 GB RAM, genügend freier Arbeitsspeicher und 20 GB freier Plattenplatz vorgesehen. Nutze sonst Piper.')
            supported = info['os'] in {'Windows','Linux'} and info['architecture'].lower() in {'amd64','x86_64'} or info['os'] == 'Darwin' and info['architecture'].lower() in {'arm64','x86_64'}
            if not supported:
                raise HTTPException(422, 'Für diese Plattform liegt keine passende automatische Qwen-Laufzeit vor. Auf diesem Gerät bleibt Piper verfügbar.')
        if payload.action == 'render_tools' and (not shutil.which('npm') or info['disk_free_gb'] < 3):
            raise HTTPException(422, 'Installiere Node.js LTS über den offiziellen Download; mindestens 3 GB Plattenplatz müssen frei sein.')
        if payload.action == 'render_tools' and (not settings.renderer_dir.resolve().is_relative_to(ROOT) or settings.renderer_dir.resolve() != (ROOT / 'renderer').resolve()):
            raise HTTPException(422, 'Die UI installiert die Schnittwerkzeuge nur im Projektordner. Prüfe RENDERER_DIR in der externen Konfiguration.')
        with self.lock:
            self.require_idle()
            self.cancel.clear()
            self.task = {'status': 'running', 'action': payload.action, 'message': 'Einrichtung wird gestartet.',
                         'started_at': time.time(), 'percent': None, 'remaining_seconds': None}
            threading.Thread(target=self.perform, args=(payload,), daemon=True).start()
        return self.status()

    def perform(self, payload):
        try:
            if payload.action in {'script_model', 'start_ollama'}:
                self.update(message='Lokalen Skriptdienst starten …')
                self.ensure_ollama()
            if payload.action == 'script_model':
                if payload.model in (ollama_models() or []):
                    self.update(status='completed',message='Dieses Modell ist bereits vollständig heruntergeladen.',percent=100,remaining_seconds=0)
                    return
                if not self.service or self.service.poll() is not None:
                    raise RuntimeError('Ein anderer Ollama-Dienst läuft bereits. Für neue Downloads beende ihn regulär und starte den lokalen Dienst in der Pipeline; so bleiben große Modelldaten im Projektordner und belegen kein unbekanntes Systemlaufwerk.')
                self.update(message='Skriptmodell herunterladen · nur Modelldaten, kein Nutzertext.')
                part, baseline, started = None, 0, time.monotonic()
                with local_request('/api/pull', {'model': payload.model, 'stream': True}, timeout=60) as response:
                    while not self.cancel.is_set():
                        line = response.readline(16384)
                        if not line:
                            break
                        value = json.loads(line)
                        if value.get('error'):
                            raise RuntimeError('Ollama konnte das feste Modell nicht herunterladen. Prüfe Netzwerk und Speicher.')
                        total, completed = value.get('total', 0), value.get('completed', 0)
                        if value.get('digest') != part:
                            part, baseline, started = value.get('digest'), completed, time.monotonic()
                        seconds = time.monotonic() - started
                        self.update(message='Skriptmodell: ' + str(value.get('status', 'Download läuft'))[:120],
                                    percent=min(99, round(completed / total * 100)) if total else None,
                                    remaining_seconds=round((total-completed) / (completed-baseline) * seconds) if total and completed > baseline and seconds > 2 else None)
                if self.cancel.is_set() or payload.model not in (ollama_models() or []):
                    raise RuntimeError('Der Download ist noch nicht vollständig. Starte denselben Schritt erneut.')
            elif payload.action == 'render_tools':
                self.update(message='Videoschnitt und gebündelte Medienwerkzeuge lokal installieren …')
                self.run([shutil.which('npm'), 'ci', '--ignore-scripts', '--no-audit', '--no-fund', '--registry', 'https://registry.npmjs.org'], cwd=settings.renderer_dir)
                if not find_ffmpeg() or not find_ffprobe():
                    raise RuntimeError('Die Schnittpakete sind installiert; FFmpeg/FFprobe fehlen auf dieser Plattform noch. Nutze den offiziellen Download in den Einstellungen.')
            elif payload.action == 'piper_voice':
                self.update(message='Deutsche Piper-Stimme herunterladen …')
                settings.voices_dir.mkdir(parents=True,exist_ok=True)
                pending=settings.voices_dir / '.piper-setup-pending'
                pending.touch()
                self.run([sys.executable, '-m', 'piper.download_voices', '--force-redownload', '--data-dir', str(settings.voices_dir), 'de_DE-thorsten-high'])
                pending.unlink()
            elif payload.action == 'qwen_voice':
                self.install_qwen()
            self.update(status='completed', message='Schritt abgeschlossen. Prüfe den Einrichtungsstatus und übernimm dann deine Auswahl.', percent=100, remaining_seconds=0)
        except Exception as exc:
            message = str(exc) if isinstance(exc, RuntimeError) else 'Die Einrichtung konnte nicht abgeschlossen werden. Prüfe die Voraussetzungen und versuche den Schritt erneut.'
            self.update(status='failed', message=message, remaining_seconds=None)

    def install_qwen(self):
        python = settings.qwen_tts_python
        if not python.is_file() or not (python.parent.parent / 'pyvenv.cfg').is_file():
            command = ['py', '-3.12'] if os.name == 'nt' and shutil.which('py') else [shutil.which('python3.12') or 'python3.12']
            self.update(message='Isolierte Python-3.12-Laufzeit für die Stimme erstellen …')
            self.run([*command, '-m', 'venv', str(python.parent.parent)])
        pending=python.parent.parent / '.pipeline-setup-pending'
        repair=['--force-reinstall'] if pending.exists() else []
        pending.touch()
        self.update(message='Qwen-Sprachsoftware installieren · separate Laufzeit, keine Systempakete …')
        mac = platform.system() == 'Darwin'
        torch = '2.9.1' if mac else '2.9.1+cpu'
        self.run([str(python), '-m', 'pip', 'install', *repair, f'torch=={torch}', f'torchaudio=={torch}', '--index-url', 'https://pypi.org/simple' if mac else 'https://download.pytorch.org/whl/cpu'])
        if mac:
            # macOS wheels use the same pinned release without the +cpu suffix.
            with tempfile.TemporaryDirectory(dir=ROOT / '.runtime', prefix='qwen-lock-') as folder:
                lock=Path(folder,'requirements.txt')
                lock.write_text((ROOT / 'requirements-qwen-lock.txt').read_text(encoding='utf-8').replace('torch==2.9.1+cpu','torch==2.9.1').replace('torchaudio==2.9.1+cpu','torchaudio==2.9.1'),encoding='utf-8')
                self.run([str(python), '-m', 'pip', 'install', *repair, '-r', str(lock), '--index-url', 'https://pypi.org/simple'])
        else:
            self.run([str(python), '-m', 'pip', 'install', *repair, '-r', str(ROOT / 'requirements-qwen-lock.txt'), '--index-url', 'https://pypi.org/simple'])
        self.run([str(python), '-m', 'pip', 'check'])
        self.update(message='Qwen-Stimmendaten herunterladen · etwa 4,5 GB …')
        self.run([str(python), str(ROOT / 'scripts' / 'setup_qwen_voice.py')], environment={'QWEN_TTS_MODEL_DIR': str(settings.qwen_tts_model_dir)}, timeout=3600)
        pending.unlink()
        if not voice_status()['ready']:
            pending.touch()
            raise RuntimeError('Die Qwen-Stimme ist noch nicht vollständig eingerichtet. Prüfe Python 3.12 und starte den Schritt erneut.')

    def close(self):
        self.cancel.set()
        if self.process and self.process.poll() is None:
            _terminate_process_tree(self.process)
        if self.service and self.service.poll() is None:
            _terminate_process_tree(self.service)


manager = SetupManager()


def require_local(request):
    if request.url.hostname not in {'localhost', '127.0.0.1', '::1'} or not request.client or request.client.host not in {'127.0.0.1', '::1'}:
        raise HTTPException(403, 'Rechnereinrichtung ist nur direkt auf diesem Rechner möglich.')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'Ein fremder Webauftritt darf die Rechnerkonfiguration nicht aufrufen.')
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Die Einstellungen dürfen nur über diese lokale Oberfläche geändert werden.')
    if request.method != 'GET' and not secrets.compare_digest(request.headers.get('x-setup-token', '').encode('utf-8'), TOKEN.encode('utf-8')):
        raise HTTPException(403, 'Öffne die Einstellungen erneut, bevor du einen Schritt startest.')


@router.get('')
def setup_status(request: Request):
    require_local(request)
    preferences = load_preferences()
    info = device_info(preferences.hardware if preferences else None)
    installed = ollama_models()
    return {'token': TOKEN, 'device': info, 'recommendation': recommendation(info), 'task': manager.status(),
            'production_busy': bool(manager.production_requests or manager.blocked()),
            'preferences': preferences.model_dump() if preferences else None,
            'effective': {'model': settings.ollama_model, 'voice': settings.tts_provider, 'script': settings.script_provider,
                          'antigravity_model': settings.antigravity_model},
            'installed_models': installed or [],
            'tools': {'ollama': bool(ollama_executable()), 'ollama_running': installed is not None,
                      'node': bool(shutil.which('node')), 'renderer': (settings.renderer_dir / 'node_modules' / '@remotion' / 'renderer').is_dir(),
                      'ffmpeg': bool(find_ffmpeg() and find_ffprobe()), 'piper': (settings.voices_dir / 'de_DE-thorsten-high.onnx').is_file() and (settings.voices_dir / 'de_DE-thorsten-high.onnx.json').is_file() and not (settings.voices_dir / '.piper-setup-pending').exists(),
                      'qwen': voice_status()['ready'], 'browser': browser_available()}}


@router.get('/task')
def task_status(request: Request):
    require_local(request)
    return manager.status()


@router.get('/accounts')
def accounts(request: Request, provider: Literal['local', 'antigravity', 'web_import', 'all'] = 'all',
             model: Annotated[str | None, Query(max_length=87, pattern=r'^gemini-[a-z0-9][a-z0-9.-]{0,79}$')] = None):
    require_local(request)
    from .antigravity import antigravity_status
    if provider == 'web_import':
        return {'web_import': {'ready': True, 'code': 'ready', 'message': 'Manuell: Prompt in deiner Web-KI verwenden und JSON-Antwort hier einfügen.',
                              'next_step': 'Sprechertext und anschließend Zeichenplan importieren. Anmeldung und Limits gelten auf der gewählten Webseite.'}}
    if provider == 'antigravity':
        return {'antigravity': antigravity_status(model=model, refresh=True)}
    installed = ollama_models()
    ready = installed is not None and settings.ollama_model in installed
    code = 'ready' if ready else 'missing' if not ollama_executable() else 'service_unavailable' if installed is None else 'model_missing'
    next_steps = {'ready': 'Du kannst einen Sprechertext erstellen.', 'missing': 'Installiere Ollama über den offiziellen Download.',
                  'service_unavailable': 'Starte den lokalen Dienst in den Einstellungen. Bei einem blockierten Port wird kein weiterer geöffnet.',
                  'model_missing': 'Lade das ausgewählte Skriptmodell herunter.'}
    result = {'local': {'ready': ready, 'provider': 'ollama', 'model': settings.ollama_model, 'code': code,
                      'message': 'Kein Konto nötig. Lokales Modell erreichbar.' if ready else 'Kein Konto nötig. Der lokale Skriptzugang ist noch nicht bereit.',
                      'next_step': next_steps[code]}}
    if provider == 'all':
        result['antigravity'] = antigravity_status(refresh=True)
    return result


@router.post('/recommend')
def manual_recommendation(request: Request, payload: ManualHardware):
    require_local(request)
    info = device_info(payload)
    return {'device': info, 'recommendation': recommendation(info)}


@router.post('/actions')
def setup_action(request: Request, payload: SetupAction):
    require_local(request)
    return manager.start(payload)


@router.put('/preferences')
def preferences_update(request: Request, payload: MachinePreferences):
    require_local(request)
    choice = recommendation(device_info(payload.hardware))
    if payload.script == 'local' and payload.model not in choice['allowed_models'] or payload.voice == 'qwen_tts' and not choice['qwen_suitable']:
        raise HTTPException(422, 'Die Auswahl liegt außerhalb des Gerätebudgets. Nutze die Empfehlung oder prüfe die Geräteangaben.')
    if payload.script == 'local' and payload.model not in (ollama_models() or []):
        raise HTTPException(422, 'Lade zuerst das ausgewählte Skriptmodell herunter.')
    if payload.voice == 'qwen_tts' and not voice_status()['ready']:
        raise HTTPException(422, 'Richte zuerst die Qwen-Stimme vollständig ein.')
    if payload.script == 'antigravity':
        from .antigravity import antigravity_status
        access = antigravity_status(model=payload.antigravity_model or settings.antigravity_model, refresh=True)
        if not access['ready']:
            raise HTTPException(422, access['message'] + ' ' + access['next_step'])
    with manager.lock:
        manager.require_idle()
        try:
            save_preferences(payload, settings)
        except (OSError, ValueError) as exc:
            raise HTTPException(422, 'Die Geräteeinstellungen konnten im Projektordner nicht gespeichert werden. Nutze einen Ordner mit Schreibrechten für deinen normalen Benutzer; Systemrechte werden nicht erweitert.') from exc
    return {'saved': True, 'message': 'Einstellungen gespeichert und aktiv. Sie gelten für neue Aufträge; vorhandene Aufträge behalten ihre gespeicherte Herstellung.'}
