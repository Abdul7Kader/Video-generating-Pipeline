"""Fixed image providers; account secrets never enter worker request/result files."""
import base64
import binascii
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import settings
from .credentials import credentials
from .quality import find_ffmpeg, find_ffprobe

MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_RESPONSE_BYTES = 17 * 1024 * 1024
MODEL = '@cf/black-forest-labs/flux-1-schnell'

MESSAGES = {
    'not_configured': 'Bildzugang unvollständig. Cloudflare-Free-Konto, Account-ID und Token in den Einstellungen prüfen.',
    'credentials': 'Der Bildanbieter hat den Zugang abgelehnt. Anmeldung, Token und Kontorechte prüfen.',
    'rate_limit': 'Das Bildkontingent oder die Anbieterkapazität ist erschöpft. Später ausdrücklich erneut versuchen; keine Zusatzcredits aktiviert.',
    'timeout': 'Die Bilderzeugung hat ihr Zeitlimit überschritten. Es wurde kein weiterer Aufruf gestartet.',
    'invalid_response': 'Der Bildanbieter lieferte kein gültiges, begrenztes PNG-/JPEG-Bild.',
    'unavailable': 'Der Bildanbieter ist momentan nicht erreichbar. Es wurde kein Ersatzanbieter aufgerufen.',
    'policy': 'Der Google-Bildlauf konnte nicht auf die erlaubte Bildfunktion begrenzt werden und wurde verworfen.',
    'tools_missing': 'Die vorhandenen FFmpeg-/FFprobe-Werkzeuge für die sichere Bildprüfung fehlen. Schnittwerkzeuge in den Einstellungen einrichten.',
}


class ImageError(RuntimeError):
    def __init__(self, code):
        self.code = code if code in MESSAGES else 'unavailable'
        super().__init__(MESSAGES[self.code])


class Preferences(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    provider: Literal['cloudflare', 'antigravity'] = 'cloudflare'
    cloudflare_account_id: str = Field(default='', pattern=r'^([a-f0-9]{32})?$')
    cloudflare_free_confirmed: bool = False


def config_path():
    return settings.data_dir / 'image-provider.json'


def load():
    source = config_path()
    if not source.exists():
        return Preferences()
    if source.is_symlink() or source.stat().st_size > 4096:
        raise ImageError('not_configured')
    return Preferences.model_validate_json(source.read_text(encoding='utf-8'))


def save(preferences, token=None):
    target = config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ImageError('not_configured')
    previous = credentials.get('cloudflare_api_token') if token is not None else None
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(preferences.model_dump_json(indent=2))
    try:
        temporary.chmod(0o600)
        if token is not None:
            credentials.set('cloudflare_api_token', token)
        try:
            os.replace(temporary, target)
        except OSError:
            if token is not None:
                credentials.set('cloudflare_api_token', previous)
            raise
    finally:
        temporary.unlink(missing_ok=True)


def status(*, inspect_account=False):
    from .antigravity import antigravity_status
    from .credentials import CredentialError
    preferences = load()
    try:
        present = bool(credentials.get('cloudflare_api_token'))
        vault = True
    except CredentialError:
        present, vault = False, False
    account = antigravity_status(refresh=True) if inspect_account and preferences.provider == 'antigravity' else {}
    configured = bool(preferences.cloudflare_account_id and preferences.cloudflare_free_confirmed and present) if preferences.provider == 'cloudflare' else bool(account.get('ready')) if inspect_account else True
    return {'preferences':preferences.model_dump(), 'token_present':present, 'vault_ready':vault,
        'configured':configured, 'ready':False, 'image_generation':'not_verified', 'vision':'not_verified',
        'account':{key:account.get(key) for key in ('ready','installed','authenticated','code','extra_credits_allowed')},
        'message':'Cloudflare-Konfiguration vorhanden.' if configured and preferences.provider == 'cloudflare' else
                  'Google-Skriptzugang bereit; Bildfunktion separat testen.' if account.get('ready') else
                  'Google-Abobildweg ausgewählt. Anmeldung und Bildfunktion getrennt prüfen.' if preferences.provider=='antigravity' and not inspect_account else 'Bildzugang in den Einstellungen einrichten.',
        'pipeline_available':True,
        'next_step':'Die Frame-Produktion prüft jedes echte Bild über die bestehende Google-/Antigravity-Anmeldung. Ein Testbild hier prüft nur den Bildaufruf. Öffnen oder Speichern erzeugt keine Bilder und ändert keinen Tarif.'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ImageError('unavailable')


def http_json(url, payload, headers):
    # Only this exact outbound endpoint is allowed, without operator proxies or redirects.
    if not re.fullmatch(r'https://api\.cloudflare\.com/client/v4/accounts/[a-f0-9]{32}/ai/run/@cf/black-forest-labs/flux-1-schnell', url):
        raise ImageError('policy')
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json', **headers}, method='POST')
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(request, timeout=180) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise ImageError('invalid_response')
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ImageError('invalid_response')
        return value
    except urllib.error.HTTPError as error:
        code = 'rate_limit' if error.code == 429 else 'credentials' if error.code in {401,403} else 'timeout' if error.code in {408,504} else 'unavailable'
        error.close()
        raise ImageError(code) from None
    except (TimeoutError, subprocess.TimeoutExpired):
        raise ImageError('timeout') from None
    except (urllib.error.URLError, OSError):
        raise ImageError('unavailable') from None
    except (ValueError, TypeError):
        raise ImageError('invalid_response') from None


def normalize_image(data, destination):
    """Decode bounded raster data with the existing native tools; remove metadata."""
    if not isinstance(data, bytes) or len(data) > MAX_IMAGE_BYTES or not data.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff')):
        raise ImageError('invalid_response')
    ffmpeg, ffprobe = find_ffmpeg(), find_ffprobe()
    if not ffmpeg or not ffprobe:
        raise ImageError('tools_missing')
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ImageError('policy')
    from .process_control import owned_command
    options = {'input':data,'stdout':subprocess.PIPE,'stderr':subprocess.DEVNULL,'timeout':25,
               'creationflags':getattr(subprocess,'CREATE_NO_WINDOW',0)}
    try:
        probe = subprocess.run(owned_command([ffprobe,'-v','error','-max_alloc','67108864','-protocol_whitelist','pipe',
            '-f','image2pipe','-i','pipe:0','-show_entries','stream=width,height,codec_name','-of','json']), **options)
        streams = json.loads(probe.stdout)['streams']
        stream = streams[0]
        width, height = stream['width'], stream['height']
        if probe.returncode or len(streams) != 1 or stream['codec_name'] not in {'png','mjpeg'} or not (128 <= width <= 4096 and 128 <= height <= 4096) or width*height > 8_500_000:
            raise ImageError('invalid_response')
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(owned_command([ffmpeg,'-v','error','-nostdin','-max_alloc','67108864','-threads','1',
            '-protocol_whitelist','pipe','-f','image2pipe','-i','pipe:0','-map_metadata','-1','-frames:v','1',
            '-threads','1','-f','image2pipe','-c:v','png','pipe:1']), **options)
        if result.returncode or not result.stdout.startswith(b'\x89PNG\r\n\x1a\n') or len(result.stdout) > MAX_IMAGE_BYTES:
            raise ImageError('invalid_response')
        with destination.open('xb') as output:
            output.write(result.stdout)
        destination.chmod(0o600)
        return {'width':width, 'height':height}
    except (ValueError, KeyError, IndexError, TypeError):
        raise ImageError('invalid_response') from None
    except subprocess.TimeoutExpired:
        raise ImageError('timeout') from None


def generate(prompt, destination, preferences=None):
    preferences = preferences or load()
    if not isinstance(prompt,str) or not 1 <= len(prompt) <= 2048 or '\0' in prompt:
        raise ImageError('invalid_response')
    if not find_ffmpeg() or not find_ffprobe():
        raise ImageError('tools_missing')
    if preferences.provider == 'antigravity':
        from .antigravity_images import generate as google_generate
        return google_generate(prompt, destination)
    if not preferences.cloudflare_account_id or not preferences.cloudflare_free_confirmed:
        raise ImageError('not_configured')
    token = credentials.get('cloudflare_api_token')
    if not token:
        raise ImageError('not_configured')
    value = http_json('https://api.cloudflare.com/client/v4/accounts/' + preferences.cloudflare_account_id + '/ai/run/' + MODEL,
                      {'prompt':prompt,'steps':4}, {'Authorization':'Bearer '+token})
    if value.get('success') is not True:
        codes = {item.get('code') for item in value.get('errors',[]) if isinstance(item,dict)}
        raise ImageError('rate_limit' if codes & {3036,3040} else 'credentials' if codes & {3023,3041,5018} else 'unavailable')
    try:
        encoded = value['result']['image']
        if not isinstance(encoded,str) or len(encoded) > MAX_RESPONSE_BYTES:
            raise ValueError()
        data = base64.b64decode(encoded,validate=True)
    except (KeyError, TypeError, ValueError, binascii.Error):
        raise ImageError('invalid_response') from None
    return {'provider':'cloudflare','model':MODEL,**normalize_image(data,destination)}
