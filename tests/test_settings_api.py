import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit

from backend import main, setup


async def request(method, path, value=None, headers=None):
    url=urlsplit(path)
    content=json.dumps(value).encode() if value is not None else b''
    values={'host':'127.0.0.1:8080','content-type':'application/json','content-length':str(len(content)),**(headers or {})}
    scope={'type':'http','http_version':'1.1','asgi':{'version':'3.0','spec_version':'2.4'},'method':method,'scheme':'http',
           'path':url.path,'raw_path':url.path.encode(),'query_string':url.query.encode(), 'root_path':'',
           'server':('127.0.0.1',8080),'client':('127.0.0.1',50000),'headers':[(k.encode(),v.encode()) for k,v in values.items()]}
    sent=[]
    delivered=False
    async def receive():
        nonlocal delivered
        if not delivered:
            delivered=True
            return {'type':'http.request','body':content,'more_body':False}
        await asyncio.Event().wait()
    async def send(message):
        sent.append(message)
    await asyncio.wait_for(main.app(scope,receive,send),timeout=10)
    status=next(item['status'] for item in sent if item['type']=='http.response.start')
    body=b''.join(item.get('body',b'') for item in sent if item['type']=='http.response.body')
    return status,json.loads(body)


class SettingsApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_personal_cloud_access_needs_no_subscription_claim_and_leaks_no_cli_identity(self):
        config=SimpleNamespace(antigravity_enabled=True,antigravity_command='agy',antigravity_model='gemini-3.8-flash-high')
        result=SimpleNamespace(returncode=0,stdout='private-test-session\ngemini-3.8-flash-high\tGemini Flash\n',stderr='')
        with patch('backend.antigravity.settings',config),patch('backend.antigravity._STATUS_CACHE',None),patch('backend.antigravity.shutil.which',return_value='agy'),patch('backend.antigravity.subprocess.run',return_value=result):
            status,value=await request('GET','/api/settings/accounts?provider=antigravity')
        self.assertEqual(status,200)
        self.assertTrue(value['antigravity']['ready'])
        self.assertTrue(value['antigravity']['account_required'])
        self.assertFalse(value['antigravity']['subscription_required'])
        self.assertEqual(value['antigravity']['billing'],'not_checked')
        self.assertNotIn('private-test-session',json.dumps(value))

    async def test_local_access_needs_a_running_model_and_does_not_contact_cloud(self):
        with patch('backend.setup.settings', SimpleNamespace(ollama_model='qwen3.5:4b')), patch('backend.setup.ollama_executable', return_value='ollama'), patch('backend.setup.ollama_models', return_value=None), patch('backend.antigravity.antigravity_status') as cloud:
            status, value = await request('GET', '/api/settings/accounts?provider=local')
        self.assertEqual(status, 200)
        self.assertFalse(value['local']['ready'])
        self.assertEqual(value['local']['code'], 'service_unavailable')
        cloud.assert_not_called()

    async def test_cloud_model_saves_only_after_verified_explicit_choice_without_local_model_budget(self):
        valid={'x-setup-token':setup.TOKEN,'origin':'http://127.0.0.1:8080'}
        info={'os':'Windows','architecture':'AMD64','ram_gb':4,'available_gb':1,'cpu_threads':2,'gpu_gb':0,'disk_free_gb':50,'gpu_name':'unknown','manual':False}
        chosen=SimpleNamespace(antigravity_model='gemini-3.1-pro-high')
        with tempfile.TemporaryDirectory() as folder, patch('backend.device.ROOT',Path(folder)), patch('backend.device.PREFERENCES_PATH',Path(folder)/'machine.json'), patch('backend.setup.device_info',return_value=info), patch('backend.setup.settings',chosen), patch('backend.setup.manager',setup.SetupManager()), patch('backend.antigravity.antigravity_status',return_value={'ready':True}) as access:
            status,_=await request('PUT','/api/settings/preferences',{'model':'qwen3.5:4b','voice':'piper','script':'antigravity','antigravity_model':'gemini-3.8-flash-high'},valid)
            self.assertEqual(status,200)
            self.assertEqual(chosen.antigravity_model,'gemini-3.8-flash-high')
            self.assertFalse(chosen.antigravity_fallback_to_qwen)
            access.assert_called_once_with(model='gemini-3.8-flash-high',refresh=True)
            for model in ['../outside','--model evil','https://evil.test']:
                status,_=await request('PUT','/api/settings/preferences',{'model':'qwen3.5:4b','script':'antigravity','antigravity_model':model},valid)
                self.assertEqual(status,422)

    async def test_http_boundary_requires_token_origin_and_bounded_schema_before_installing(self):
        valid={'x-setup-token':setup.TOKEN,'origin':'http://127.0.0.1:8080'}
        with patch('backend.setup.manager.start',return_value={'status':'running'}) as start:
            for headers in [{},{**valid,'origin':'https://evil.test'},{**valid,'host':'evil.test'},{**valid,'sec-fetch-site':'cross-site'}]:
                status,_=await request('POST','/api/settings/actions',{'action':'piper_voice'},headers)
                self.assertEqual(status,403)
            for payload in [{'action':'execute','command':'anything'},{'action':'script_model','model':'../outside'},{'action':'piper_voice','url':'https://evil.test'}]:
                status,_=await request('POST','/api/settings/actions',payload,valid)
                self.assertEqual(status,422)
            status,_=await request('POST','/api/settings/actions',{'action':'piper_voice'}, {**valid,'content-length':'9000'})
            self.assertEqual(status,413)
            start.assert_not_called()
            status,_=await request('POST','/api/settings/actions',{'action':'piper_voice'},valid)
            self.assertEqual(status,200)
            start.assert_called_once()

    async def test_saved_settings_activate_locally_and_setup_excludes_production(self):
        valid={'x-setup-token':setup.TOKEN,'origin':'http://127.0.0.1:8080'}
        info={'os':'Windows','architecture':'AMD64','ram_gb':16,'available_gb':10,'cpu_threads':4,'gpu_gb':0,'disk_free_gb':50,'gpu_name':'unknown','manual':False}
        manager=setup.SetupManager()
        with tempfile.TemporaryDirectory() as folder, patch('backend.device.ROOT',Path(folder)), patch('backend.device.PREFERENCES_PATH',Path(folder)/'machine.json'), patch('backend.setup.device_info',return_value=info), patch('backend.setup.ollama_models',return_value=['qwen3.5:4b']), patch('backend.setup.manager',manager), patch('backend.setup.settings',SimpleNamespace()):
            status,_=await request('PUT','/api/settings/preferences',{'model':'qwen3.5:4b','voice':'piper','script':'local'},valid)
            self.assertEqual(status,200)
            self.assertTrue(Path(folder,'machine.json').exists())
            self.assertEqual(setup.settings.ollama_model,'qwen3.5:4b')
            self.assertEqual(setup.settings.ollama_base_url,'http://127.0.0.1:11434')
            manager.task['status']='running'
            for path in ['/api/jobs','/api/voice-previews']:
                status,_=await request('POST',path,{},valid)
                self.assertEqual(status,409)
            status,_=await request('PUT','/api/settings/preferences',{'model':'qwen3.5:4b'},valid)
            self.assertEqual(status,409)
            self.assertEqual(manager.production_requests,0)


if __name__ == '__main__':
    unittest.main()
