from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend import images, image_settings, setup
from backend.operations import Operation
from test_settings_api import request


class ImageSettingsTests(unittest.IsolatedAsyncioTestCase):
    async def test_secrets_not_echoed_and_mutations_require_local_token(self):
        valid={'x-setup-token':setup.TOKEN}
        payload={'preferences':{'provider':'cloudflare','cloudflare_account_id':'a'*32,'cloudflare_free_confirmed':True},'token':'fixture-secret'}
        with tempfile.TemporaryDirectory() as directory, patch.object(images,'settings',replace(images.settings,data_dir=Path(directory))),patch.object(images,'credentials') as vault,patch.object(setup,'manager',setup.SetupManager()):
            vault.get.return_value='fixture-secret'
            for headers in [{},{**valid,'origin':'https://evil.example'}]:
                code,_=await request('PUT','/api/settings/images',payload,headers)
                self.assertEqual(code,403)
            vault.set.assert_not_called()
            code,value=await request('PUT','/api/settings/images',payload,valid)
            self.assertEqual(code,200)
            self.assertTrue(value['token_present'])
            self.assertNotIn('fixture-secret',json.dumps(value))
            self.assertNotIn('fixture-secret',images.config_path().read_text())
            for changes in [{'provider':'https://evil.example'},{'cloudflare_account_id':'../outside'},{'command':'whoami'}]:
                invalid={**payload,'preferences':{**payload['preferences'],**changes}}
                code,value=await request('PUT','/api/settings/images',invalid,valid)
                self.assertEqual(code,422)
                self.assertNotIn('fixture-secret',json.dumps(value))

    async def test_preview_snapshots_selected_provider_blocks_parallel_work_and_cancels_only_own_operation(self):
        manager=setup.SetupManager()
        with tempfile.TemporaryDirectory() as directory,patch.object(setup,'manager',manager),patch.object(image_settings,'settings',replace(images.settings,data_dir=Path(directory))),patch.object(images,'load',return_value=images.Preferences(provider='antigravity')),patch.object(image_settings.threading,'Thread') as thread,patch.object(image_settings,'operation',None),patch.object(image_settings,'task',{'status':'idle'}):
            code,value=await request('POST','/api/settings/images/preview',{'prompt':'A specific new story'}, {'x-setup-token':setup.TOKEN})
            self.assertEqual(code,200)
            self.assertEqual(value['provider'],'antigravity')
            self.assertTrue(manager.busy)
            own=image_settings.operation
            code,_=await request('POST','/api/settings/images/preview',{'prompt':'A second story'}, {'x-setup-token':setup.TOKEN})
            self.assertEqual(code,409)
            code,_=await request('POST','/api/settings/images/cancel',{}, {'x-setup-token':setup.TOKEN})
            self.assertEqual(code,200)
            self.assertTrue(own.cancel.is_set())
            self.assertTrue(manager.busy)
            image_settings.perform(own,value['id'],'A specific new story',images.Preferences(provider='antigravity'))
            self.assertEqual(image_settings.task['status'],'cancelled')
            self.assertFalse(manager.busy)
            thread.return_value.start.assert_called_once()

    async def test_cloudflare_cannot_generate_without_free_confirmation_and_read_status_never_calls_provider(self):
        with patch.object(images,'load',return_value=images.Preferences()),patch.object(setup,'manager',setup.SetupManager()),patch.object(images,'credentials'),patch.object(images,'generate') as generate:
            code,_=await request('POST','/api/settings/images/preview',{'prompt':'A cat enters a carrier'}, {'x-setup-token':setup.TOKEN})
            self.assertEqual(code,409)
            code,value=await request('GET','/api/settings/images')
            self.assertEqual(code,200)
            self.assertEqual(value['vision'],'not_verified')
            generate.assert_not_called()
