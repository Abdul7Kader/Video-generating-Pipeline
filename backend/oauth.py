"""Explicit manufacturer OAuth; temporary callback bound only to IPv4 loopback."""
import logging
import sys
import threading

from .credentials import credentials
from .integrations import load,save,lock as configuration_lock

lock = threading.Lock()
state = {'status': 'idle', 'message': 'YouTube noch nicht über diese Einstellungen verbunden.'}


class PrivateOAuthLog(logging.Filter):
    def filter(self, record):
        # The manufacturer's WSGI handler otherwise logs callback codes/state.
        return False


def status():
    with lock:
        return dict(state)


def connect_youtube(*, blocked=lambda: False):
    if blocked():
        raise RuntimeError('Anmeldung nach Abschluss der laufenden Veröffentlichungen ändern.')
    preference = load()
    secret = credentials.get('youtube_client_secret')
    if not preference.youtube_client_id.endswith('.apps.googleusercontent.com') or not secret:
        raise RuntimeError('Zuerst die OAuth-Desktop-Client-ID und das Client-Secret speichern. Danach erneut verbinden.')
    with lock:
        if state['status'] == 'running':
            return dict(state)
        state.update(status='running', message='Google-Anmeldung im regulären Browser abschließen. Der Rückkanal ist nur auf diesem Rechner für höchstens drei Minuten geöffnet.')

    def work():
        logger = logging.getLogger('google_auth_oauthlib.flow')
        privacy = PrivateOAuthLog()
        logger.addFilter(privacy)
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_config({'installed': {
                'client_id': preference.youtube_client_id, 'client_secret': secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': ['http://localhost']}}, scopes=['https://www.googleapis.com/auth/youtube.upload'])
            result = flow.run_local_server(host='127.0.0.1', bind_addr='127.0.0.1', port=0,
                timeout_seconds=180, open_browser=True, browser='windows-default' if sys.platform == 'win32' else None,
                authorization_prompt_message=None, success_message='YouTube ist verbunden. Du kannst dieses Fenster schließen und zur Video Pipeline zurückkehren.',
                access_type='offline', prompt='consent')
            if not result.refresh_token:
                raise RuntimeError('Kein dauerhafter Zugang erhalten')
            with configuration_lock:
                current = load()
                if blocked() or current.youtube_client_id != preference.youtube_client_id or credentials.get('youtube_client_secret') != secret:
                    raise RuntimeError('Kontokonfiguration wurde während der Anmeldung geändert.')
                previous = credentials.get('youtube_refresh_token')
                credentials.set('youtube_refresh_token',result.refresh_token)
                try:
                    current.connection_revision += 1
                    save(current)
                except Exception:
                    credentials.set('youtube_refresh_token',previous)
                    raise
            with lock:
                state.update(status='connected', message='YouTube-Anmeldung gespeichert. Es wurde kein Video hochgeladen.')
        except Exception:
            with lock:
                state.update(status='failed', message='YouTube-Anmeldung nicht abgeschlossen. Prüfe Desktop-Client, Testnutzer/App-Freigabe und Zustimmung; es wurde kein Video hochgeladen.')
        finally:
            logger.removeFilter(privacy)
    threading.Thread(target=work, name='youtube-oauth', daemon=True).start()
    return status()
