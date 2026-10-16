"""Local, token-protected settings for review destinations and native credentials."""
import json
import os
from pathlib import Path
import threading
import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationError

from .config import settings
from .credentials import credentials, CredentialError, SECRET_NAMES
from .setup import require_local

router = APIRouter(prefix='/api/settings/integrations')
lock = threading.RLock()
Target = Literal['youtube', 'facebook_reels', 'instagram_reels', 'tiktok', 'mastodon']


class Preferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    connection_revision: int = Field(default=0, ge=0)
    archive_directory: str = Field(default='', max_length=600)
    work_retention_days: int = Field(default=0, ge=0, le=3650)
    discord_enabled: bool = False
    discord_guild_id: str = Field(default='', pattern=r'^([0-9]{15,22})?$')
    discord_channel_id: str = Field(default='', pattern=r'^([0-9]{15,22})?$')
    discord_approver_ids: list[str] = Field(default_factory=list, max_length=20)
    discord_upload_mb: int = Field(default=10, ge=1, le=500)
    publish_targets: list[Target] = Field(default_factory=list, max_length=5)
    youtube_enabled: bool = False
    youtube_client_id: str = Field(default='', max_length=250)
    youtube_privacy: Literal['private', 'unlisted', 'public'] = 'private'
    facebook_enabled: bool = False
    facebook_page_id: str = Field(default='', pattern=r'^([0-9]{5,30})?$')
    instagram_enabled: bool = False
    instagram_account_id: str = Field(default='', pattern=r'^([0-9]{5,30})?$')
    instagram_login: Literal['instagram','facebook'] = 'instagram'
    tiktok_enabled: bool = False
    tiktok_client_id: str = Field(default='', max_length=150)
    mastodon_enabled: bool = False
    mastodon_base_url: str = Field(default='', max_length=250)
    mastodon_visibility: Literal['public', 'unlisted', 'private'] = 'private'

    @field_validator('discord_approver_ids')
    @classmethod
    def approvers(cls, values):
        if any(not value.isdecimal() or not 15 <= len(value) <= 22 for value in values):
            raise ValueError('Nutzer-IDs aus dem Discord-Entwicklermodus verwenden.')
        return list(dict.fromkeys(values))

    @field_validator('archive_directory')
    @classmethod
    def local_folder(cls, value):
        if value and (not Path(value).is_absolute() or value.startswith(('\\\\', '//')) or '\0' in value):
            raise ValueError('Einen absoluten lokalen Ordner auswählen; keine Netzwerkfreigabe.')
        if value:
            resolved = Path(value).resolve()
            if resolved == Path(resolved.anchor) or resolved == settings.jobs_dir or settings.jobs_dir in resolved.parents:
                raise ValueError('Einen eigenen Endvideoordner außerhalb der Arbeitsdateien wählen.')
        return value


def path():
    return settings.data_dir / 'integrations.json'


def load():
    source = path()
    if not source.exists():
        return Preferences()
    if source.stat().st_size > 16384:
        raise RuntimeError('Die lokale Kontokonfiguration ist beschädigt.')
    return Preferences.model_validate_json(source.read_text(encoding='utf-8'))


def save(preferences):
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.pending')
    temporary.write_text(preferences.model_dump_json(indent=2), encoding='utf-8')
    temporary.chmod(0o600)
    os.replace(temporary, target)


def snapshot():
    present, available, message = {}, True, 'Geschützter Betriebssystem-Tresor bereit.'
    try:
        present = {name: bool(credentials.get(name)) for name in SECRET_NAMES}
    except CredentialError as error:
        available, message = False, str(error)
    return {'preferences': load().model_dump(), 'secrets_present': present,
            'vault_ready': available, 'vault_message': message,
            'working_directory': str(settings.jobs_dir), 'final_directory':load().archive_directory or str(settings.data_dir / 'videos'), 'restart_required': False}


@router.get('')
def read_preferences(request: Request):
    require_local(request)
    with lock:
        value = snapshot()
        value['native_picker'] = bool(getattr(request.app.state, 'desktop_control', None))
        return value


@router.post('/folder')
async def choose_folder(request: Request):
    require_local(request)
    control = getattr(request.app.state, 'desktop_control', None)
    if not control:
        raise HTTPException(409, 'Ordnerauswahl steht in der Desktop-App bereit. Alternativ den lokalen Ordnerpfad eintragen.')
    try:
        return {'directory': await asyncio.to_thread(control.choose_folder)}
    except RuntimeError as error:
        raise HTTPException(409, str(error)) from None


@router.get('/youtube-connect')
def youtube_status(request: Request):
    require_local(request)
    from .oauth import status
    return status()


@router.post('/discord-check')
def discord_check(request: Request):
    require_local(request)
    from .discord_http import check, DiscordError
    try:
        return check(load())
    except (DiscordError,CredentialError) as error:
        raise HTTPException(409,str(error)) from None


@router.post('/youtube-connect')
def youtube_connect(request: Request):
    require_local(request)
    from .oauth import connect_youtube
    try:
        return connect_youtube(blocked=getattr(request.app.state,'integration_changes_blocked',lambda: False))
    except RuntimeError as error:
        raise HTTPException(409, str(error)) from None


@router.put('')
async def update_preferences(request: Request):
    require_local(request)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 8192:
            raise HTTPException(413, 'Die Kontoeinstellung ist zu groß.')
    try:
        value = json.loads(body)
        if not isinstance(value, dict) or set(value) - {'preferences', 'secrets', 'clear_secrets'}:
            raise ValueError()
        preferences = Preferences.model_validate(value['preferences'])
        changes, clear = value.get('secrets', {}), value.get('clear_secrets', [])
        if not isinstance(changes, dict) or not isinstance(clear, list) or not all(isinstance(item, str) for item in clear):
            raise ValueError()
        if (set(changes) | set(clear)) - SECRET_NAMES:
            raise ValueError()
        if any(not isinstance(item, str) or len(item.encode('utf-16-le')) > 2400 or any(c in item for c in '\r\n\0') for item in changes.values()):
            raise ValueError()
        changes = {name: item.strip() for name, item in changes.items() if item.strip()}
        changes.update({name: '' for name in clear})
        if preferences.discord_enabled and not (preferences.discord_guild_id and preferences.discord_channel_id and preferences.discord_approver_ids):
            raise ValueError()
    except (KeyError, TypeError, ValueError, ValidationError, UnicodeError):
        # Never echo credential input in validation errors.
        raise HTTPException(422, 'Prüfe Ordner, IDs und Zugangsdaten. Discord benötigt Server, Kanal und mindestens eine erlaubte Nutzer-ID.') from None
    with lock:
        try:
            if getattr(request.app.state, 'integration_changes_blocked', lambda: False)():
                raise HTTPException(409, 'Eine Freigabe wartet auf Veröffentlichung oder wird übertragen. Kanäle und Schlüssel danach ändern.')
            current = load()
            connection_fields = set(Preferences.model_fields) - {'archive_directory', 'work_retention_days', 'discord_upload_mb', 'connection_revision'}
            preferences.connection_revision = current.connection_revision + int(bool(changes) or any(getattr(current,name) != getattr(preferences,name) for name in connection_fields))
            previous = {name: credentials.get(name) for name in changes}
            applied = []
            try:
                for name, item in changes.items():
                    credentials.set(name, item)
                    applied.append(name)
                save(preferences)
            except Exception:
                for name in applied:
                    credentials.set(name, previous[name])
                raise
            return snapshot()
        except CredentialError as error:
            raise HTTPException(409, str(error)) from None
        except OSError:
            raise HTTPException(409, 'Einstellungen konnten nicht gespeichert werden. Ordnerrechte prüfen.') from None
