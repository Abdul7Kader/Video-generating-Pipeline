import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend import main, setup


async def request(method, path, value=None, headers=None):
    content=json.dumps(value).encode() if value is not None else b''
    values={'host':'127.0.0.1:8080','content-type':'application/json','content-length':str(len(content)),**(headers or {})}
    scope={'type':'http','http_version':'1.1','asgi':{'version':'3.0','spec_version':'2.4'},'method':method,'scheme':'http',
           'path':path,'raw_path':path.encode(),'query_string':b'', 'root_path':'',
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
