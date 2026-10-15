import asyncio
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.config import settings
from backend import integrations
from backend.plan import file_sha256
from backend.setup import TOKEN
from tests.test_settings_api import request


class MemoryCredentials:
    def __init__(self):
        self.values = {}
    def get(self, name):
        return self.values.get(name, '')
    def set(self, name, value):
        self.values[name] = value


class IntegrationTests(unittest.TestCase):
    def test_video_folder_keeps_original_and_never_overwrites_a_different_file(self):
        from backend import video_storage
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / 'jobs' / 'test' / 'v1' / 'video.mp4'
            source.parent.mkdir(parents=True)
            source.write_bytes(b'finished-fixture')
            job = {'id':'fixture', 'render_version':1, 'render_outputs': {'9:16': {'path':str(source.relative_to(root / 'jobs')), 'sha256':file_sha256(source)}}}
            with patch.object(video_storage, 'settings', replace(settings, data_dir=root)), patch.object(video_storage, 'load', return_value=integrations.Preferences(archive_directory=str(root / 'chosen'))):
                output = Path(video_storage.archive_video(job)[0])
                self.assertEqual(output.read_bytes(), source.read_bytes())
                self.assertTrue(source.exists())
                output.write_bytes(b'other-user-file')
                with self.assertRaisesRegex(RuntimeError, 'nicht überschrieben'):
                    video_storage.archive_video(job)
                self.assertEqual(output.read_bytes(), b'other-user-file')

    def test_youtube_oauth_uses_only_temporary_loopback_and_never_uploads(self):
        from backend import oauth
        from types import SimpleNamespace
        import time
        fake = MemoryCredentials()
        fake.set('youtube_client_secret', 'fixture-secret')
        with patch.object(oauth, 'credentials', fake), patch.object(oauth, 'load', return_value=integrations.Preferences(youtube_client_id='fixture.apps.googleusercontent.com')), patch('google_auth_oauthlib.flow.InstalledAppFlow') as flow:
            flow.from_client_config.return_value.run_local_server.return_value = SimpleNamespace(refresh_token='fixture-refresh')
            oauth.connect_youtube()
            deadline = time.monotonic() + 2
            while oauth.status()['status'] == 'running' and time.monotonic() < deadline:
                time.sleep(.01)
            options = flow.from_client_config.return_value.run_local_server.call_args.kwargs
            self.assertEqual(options['host'], '127.0.0.1')
            self.assertEqual(options['bind_addr'], '127.0.0.1')
            self.assertEqual(options['port'], 0)
            self.assertIsNone(options['authorization_prompt_message'])
            self.assertEqual(fake.get('youtube_refresh_token'), 'fixture-refresh')

    def test_tokens_never_enter_config_or_responses_and_foreign_requests_cannot_save(self):
        with tempfile.TemporaryDirectory() as name:
            fake = MemoryCredentials()
            with patch.object(integrations, 'settings', replace(settings, data_dir=Path(name))), patch.object(integrations, 'credentials', fake):
                value = {'preferences': integrations.Preferences().model_dump(), 'secrets': {'discord_bot_token': 'sensitive-fixture'}}
                status, _ = asyncio.run(request('PUT', '/api/settings/integrations', value))
                self.assertEqual(status, 403)
                self.assertFalse(fake.values)
                status, result = asyncio.run(request('PUT', '/api/settings/integrations', value, {'x-setup-token': TOKEN}))
                self.assertEqual(status, 200)
                self.assertTrue(result['secrets_present']['discord_bot_token'])
                self.assertNotIn('sensitive-fixture', json.dumps(result))
                self.assertNotIn('sensitive-fixture', integrations.path().read_text())
                value['secrets']['discord_bot_token'] = 'sensitive-fixture\ninvalid'
                status, result = asyncio.run(request('PUT', '/api/settings/integrations', value, {'x-setup-token': TOKEN}))
                self.assertEqual(status, 422)
                self.assertNotIn('sensitive-fixture', json.dumps(result))
                self.assertEqual(fake.get('discord_bot_token'), 'sensitive-fixture')

    def test_discord_requires_an_explicit_approver_and_server_channel(self):
        with tempfile.TemporaryDirectory() as name, patch.object(integrations, 'settings', replace(settings, data_dir=Path(name))):
            value = {'preferences': integrations.Preferences(discord_enabled=True).model_dump()}
            status, _ = asyncio.run(request('PUT', '/api/settings/integrations', value, {'x-setup-token': TOKEN}))
            self.assertEqual(status, 422)
            self.assertFalse(integrations.path().exists())
