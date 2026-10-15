"""Only native OS credential stores; no plaintext or third-party backend fallback."""
import hashlib
from pathlib import Path
import sys

SERVICE = 'VideoPipeline.' + hashlib.sha256(str(Path(__file__).resolve().parents[1]).encode()).hexdigest()[:24]
SECRET_NAMES = frozenset({'discord_bot_token', 'youtube_client_secret', 'youtube_refresh_token',
    'facebook_token', 'instagram_token', 'tiktok_access_token', 'tiktok_refresh_token',
    'tiktok_client_secret', 'mastodon_token'})


class CredentialError(RuntimeError):
    pass


class CredentialStore:
    def backend(self):
        try:
            if sys.platform == 'win32':
                from keyring.backends.Windows import WinVaultKeyring
                backend = WinVaultKeyring()
                backend.persist = 'local machine'
            elif sys.platform == 'darwin':
                from keyring.backends.macOS import Keyring
                backend = Keyring()
            elif sys.platform.startswith('linux'):
                from keyring.backends.SecretService import Keyring
                backend = Keyring()
            else:
                raise CredentialError('Für dieses System ist kein geschützter Kontotresor eingerichtet.')
            if backend.priority <= 0:
                raise CredentialError('Der Betriebssystem-Tresor ist nicht bereit.')
            return backend
        except Exception:
            raise CredentialError('Der geschützte Betriebssystem-Tresor fehlt oder ist gesperrt. Einrichtung prüfen; Schlüssel werden nicht als Klartext gespeichert.') from None

    def get(self, name):
        if name not in SECRET_NAMES:
            raise CredentialError('Unbekannter Zugang.')
        try:
            return self.backend().get_password(SERVICE + '.' + name, 'credential') or ''
        except CredentialError:
            raise
        except Exception:
            raise CredentialError('Der gespeicherte Zugang konnte nicht aus dem Betriebssystem-Tresor gelesen werden.') from None

    def set(self, name, value):
        if name not in SECRET_NAMES or not isinstance(value, str) or len(value.encode('utf-16-le')) > 2400 or any(c in value for c in '\r\n\0'):
            raise CredentialError('Dieser Schlüssel ist ungültig oder zu lang.')
        try:
            backend = self.backend()
            if value:
                backend.set_password(SERVICE + '.' + name, 'credential', value)
            elif backend.get_password(SERVICE + '.' + name, 'credential'):
                backend.delete_password(SERVICE + '.' + name, 'credential')
        except CredentialError:
            raise
        except Exception:
            raise CredentialError('Der Zugang konnte nicht sicher im Betriebssystem-Tresor gespeichert werden.') from None


credentials = CredentialStore()
