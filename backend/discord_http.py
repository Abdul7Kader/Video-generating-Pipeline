"""Discord REST over fixed HTTPS, bounded responses and streamed attachments."""
import http.client
import hashlib
import json
from pathlib import Path
import uuid
import re

from .credentials import credentials


class DiscordError(RuntimeError):
    def __init__(self, message, *, uncertain=False):
        super().__init__(message)
        self.uncertain = uncertain


def request(method, path, payload=None, *, file=None, filename='video.mp4', limit=10 * 1024 * 1024, expected_sha256=None):
    if not path.startswith('/') or '\r' in path or '\n' in path:
        raise DiscordError('Ungültiger Discord-Aufruf.')
    token = credentials.get('discord_bot_token')
    if not token:
        raise DiscordError('Discord Bot-Token fehlt. Unter Einstellungen speichern.')
    headers = {'Authorization':'Bot ' + token,
               'User-Agent':'DiscordBot (https://github.com/Abdul7Kader/Video-generating-Pipeline, 0.2)'}
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else b''
    suffix = b''
    headers['Content-Type'] = 'application/json'
    if file:
        if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,120}', filename):
            raise DiscordError('Ungültiger Anhangsname.')
        file = Path(file)
        size = file.stat().st_size
        if size > limit:
            raise DiscordError('Das fertige Video überschreitet die eingestellte Discord-Dateigrenze. Original bleibt lokal; Servergrenze in Einstellungen prüfen.')
        boundary = 'video-pipeline-' + uuid.uuid4().hex
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n'.encode()
            + body + f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="files[0]"; filename="{filename}"\r\nContent-Type: {"video/mp4" if filename.endswith(".mp4") else "text/plain; charset=utf-8"}\r\n\r\n'.encode())
        suffix = f'\r\n--{boundary}--\r\n'.encode()
        headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
    headers['Content-Length'] = str(len(body) + len(suffix) + (file.stat().st_size if file else 0))
    connection = http.client.HTTPSConnection('discord.com', timeout=60)
    sent = False
    try:
        connection.putrequest(method, '/api/v10' + path)
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.endheaders()
        sent = True
        connection.send(body)
        if file:
            digest = hashlib.sha256()
            with file.open('rb') as stream:
                while chunk := stream.read(64 * 1024):
                    digest.update(chunk)
                    connection.send(chunk)
            connection.send(suffix)
            if expected_sha256 and digest.hexdigest() != expected_sha256:
                raise DiscordError('Die Datei wurde während der Discord-Übertragung verändert. Keine Freigabe möglich.', uncertain=True)
        response = connection.getresponse()
        content = response.read(1024 * 1024 + 1)
        if not 200 <= response.status < 300:
            raise DiscordError(f'Discord antwortet mit HTTP {response.status}. Rechte, Dateigrenze und Anbieterlimits prüfen.', uncertain=response.status >= 500)
        if len(content) > 1024 * 1024:
            raise DiscordError('Die Discord-Antwort ist zu groß.', uncertain=method != 'GET')
        return json.loads(content) if content else {}
    except DiscordError:
        raise
    except Exception:
        # Never expose request URLs: interaction paths contain short-lived secrets.
        raise DiscordError('Discord-Verbindung unterbrochen. Externen Zustand vor einer Wiederholung prüfen.', uncertain=sent and method != 'GET') from None
    finally:
        connection.close()


def check(preferences):
    bot = request('GET', '/users/@me')
    if not bot.get('bot') or not str(bot.get('id', '')).isdecimal():
        raise DiscordError('Nur ein regulärer Discord-Bot wird unterstützt, kein persönlicher Nutzertoken.')
    result = {'bot_name': str(bot.get('username', 'Bot')), 'channel_ready':False,
              'invite_url':f"https://discord.com/oauth2/authorize?client_id={bot['id']}&permissions=101376&scope=bot%20applications.commands"}
    try:
        channel = request('GET', '/channels/' + preferences.discord_channel_id)
        result['channel_ready'] = str(channel.get('guild_id')) == preferences.discord_guild_id
    except DiscordError:
        pass
    return result
