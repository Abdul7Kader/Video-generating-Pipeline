import tempfile
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from starlette.requests import Request
from pydantic import ValidationError

from backend.device import MachinePreferences, recommendation, save_preferences, load_preferences, apply_preferences
from backend import setup


def device(ram=32, free=24, cores=16, gpu=0):
    return {'os':'Windows', 'architecture':'AMD64', 'ram_gb':ram, 'available_gb':free,
            'cpu_threads':cores, 'gpu_gb':gpu, 'disk_free_gb':100, 'manual':False}


class DeviceSetupTests(unittest.TestCase):
    def test_model_scales_with_capacity_and_keeps_memory_and_disk_reserves(self):
        self.assertEqual(recommendation(device(8,5,2))['model'], 'qwen3.5:0.8b')
        self.assertEqual(recommendation(device(16,10,8))['model'], 'qwen3.5:4b')
        self.assertEqual(recommendation(device())['model'], 'qwen3.5:9b-q8_0')
        self.assertEqual(recommendation(device(64,40,16,24))['model'], 'qwen3.5:27b')
        self.assertNotIn('qwen3.5:27b', recommendation(device(64,40,16))['allowed_models'])
        self.assertIsNone(recommendation(device(None,None))['model'])
        self.assertIsNone(recommendation(device(4,2,2))['model'])
        self.assertIsNone(recommendation({**device(), 'disk_free_gb':2})['model'])
        self.assertEqual(recommendation(device(16,10,4))['voice'], 'piper')
        self.assertEqual(recommendation(device())['voice'], 'qwen_tts')

    def test_saved_preferences_roundtrip_and_do_not_touch_credentials_or_ports(self):
        with tempfile.TemporaryDirectory() as folder, patch('backend.device.ROOT',Path(folder)), patch('backend.device.PREFERENCES_PATH', Path(folder)/'machine.json'):
            values = SimpleNamespace(secret='unchanged', ollama_base_url='http://127.0.0.1:11434')
            preferences = MachinePreferences(model='qwen3.5:4b', voice='piper')
            save_preferences(preferences, values)
            self.assertEqual(load_preferences(), preferences)
            self.assertEqual(values.ollama_model, preferences.model)
            self.assertEqual(values.script_provider, 'ollama')
            self.assertEqual(values.secret, 'unchanged')
            self.assertEqual(values.ollama_base_url, 'http://127.0.0.1:11434')
            Path(folder,'machine.json').write_text('{"model":"unknown", "API_KEY":"secret"}')
            self.assertIsNone(load_preferences())

    def test_setup_rejects_arbitrary_commands_urls_models_and_unknown_fields(self):
        for payload in [{'action':'run', 'command':'anything'}, {'action':'script_model','model':'../other'}, {'action':'piper_voice','url':'https://evil.test/model'}]:
            with self.assertRaises(ValidationError):
                setup.SetupAction.model_validate(payload)

    def test_startup_adapts_existing_large_preferences_to_a_smaller_computer(self):
        values=SimpleNamespace()
        preferences=MachinePreferences(model='qwen3.5:9b-q8_0',voice='qwen_tts')
        with patch('backend.device.device_info',return_value=device(8,5,2)):
            apply_preferences(values,preferences,adapt=True)
        self.assertEqual(values.ollama_model,'qwen3.5:0.8b')
        self.assertEqual(values.tts_provider,'piper')
        with patch('backend.device.device_info',return_value=device(None,None)):
            apply_preferences(values,preferences,adapt=True)
        self.assertEqual(values.ollama_model,'')

    def test_installer_subprocess_does_not_inherit_tokens_or_user_package_configs(self):
        manager=setup.SetupManager()
        code="import os,pathlib; assert 'OPENAI_API_KEY' not in os.environ; assert 'NPM_TOKEN' not in os.environ; a=os.environ['NPM_CONFIG_USERCONFIG']; b=os.environ['NPM_CONFIG_GLOBALCONFIG']; assert a!=b; assert pathlib.Path(a).read_text()==pathlib.Path(b).read_text()==''"
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only-value','NPM_TOKEN':'test-only-value'}):
            manager.run([sys.executable,'-c',code],timeout=10)

    def test_public_or_unverified_ollama_listener_is_not_reused(self):
        from io import BytesIO
        for safe in [False,True]:
            with patch('backend.setup.local_request',return_value=BytesIO(b'{"models":[{"name":"qwen3.5:4b"}]}')),patch('backend.setup.local_service_safe',return_value=safe):
                self.assertEqual(setup.ollama_models(),['qwen3.5:4b'] if safe else None)

    def test_mac_voice_install_keeps_pins_and_uses_matching_cpu_wheels(self):
        manager=setup.SetupManager()
        commands=[]
        def run(command,**kwargs):
            commands.append(command)
            if '-r' in command:
                lock=Path(command[command.index('-r')+1]).read_text(encoding='utf-8')
                self.assertIn('torch==2.9.1\n',lock)
                self.assertIn('torchaudio==2.9.1\n',lock)
                self.assertNotIn('+cpu',lock)
                self.assertIn('qwen-tts==0.1.1',lock)
        with tempfile.TemporaryDirectory() as folder:
            python=Path(folder,'bin','python')
            python.parent.mkdir();python.touch();Path(folder,'pyvenv.cfg').touch()
            with patch('backend.setup.settings',SimpleNamespace(qwen_tts_python=python,qwen_tts_model_dir=Path(folder,'model'))),patch('backend.setup.platform.system',return_value='Darwin'),patch.object(manager,'run',side_effect=run),patch('backend.setup.voice_status',return_value={'ready':True}):
                manager.install_qwen()
            self.assertFalse(Path(folder,'.pipeline-setup-pending').exists())
        self.assertIn('torch==2.9.1',commands[0])
        self.assertIn('https://pypi.org/simple',commands[0])

    def test_interrupted_voice_install_is_not_reported_ready(self):
        from backend import qwen_tts
        manager=setup.SetupManager()
        with tempfile.TemporaryDirectory() as folder:
            python=Path(folder,'bin','python');python.parent.mkdir();python.touch();Path(folder,'pyvenv.cfg').touch()
            config=SimpleNamespace(qwen_tts_python=python,qwen_tts_model_dir=Path(folder,'model'))
            with patch('backend.setup.settings',config),patch.object(manager,'run',side_effect=RuntimeError('interrupted')),self.assertRaises(RuntimeError):
                manager.install_qwen()
            with patch('backend.qwen_tts.settings',config):
                self.assertFalse(qwen_tts.voice_status()['ready'])

    def test_large_download_cannot_be_started_on_small_device_and_duplicate_setup_is_blocked(self):
        manager = setup.SetupManager()
        with patch('backend.setup.device_info', return_value=device(8,5,2)):
            with self.assertRaises(setup.HTTPException) as failed:
                manager.start(setup.SetupAction(action='script_model', model='qwen3.5:9b'))
            self.assertEqual(failed.exception.status_code, 422)
        manager.task['status']='running'
        with self.assertRaises(setup.HTTPException) as duplicate:
            manager.require_idle()
        self.assertEqual(duplicate.exception.status_code,409)
        manager.task['status']='idle'
        manager.production_requests=1
        with self.assertRaises(setup.HTTPException):
            manager.require_idle()

    def test_foreign_origin_remote_host_and_missing_token_cannot_change_host(self):
        def request(headers, client='127.0.0.1'):
            values={'host':'127.0.0.1:8080', **headers}
            return Request({'type':'http', 'method':'POST', 'path':'/api/settings/actions', 'scheme':'http', 'query_string':b'',
                            'server':('127.0.0.1',8080), 'client':(client,50000),
                            'headers':[(key.encode(),value.encode()) for key,value in values.items()]})
        with patch('backend.setup.manager.start', return_value={'status':'running'}) as start:
            for headers in [{}, {'x-setup-token':'wrong'}, {'x-setup-token':setup.TOKEN,'origin':'https://evil.test'}, {'x-setup-token':setup.TOKEN,'sec-fetch-site':'cross-site'}, {'x-setup-token':setup.TOKEN,'host':'evil.test'}]:
                with self.assertRaises(setup.HTTPException) as result:
                    setup.setup_action(request(headers),setup.SetupAction(action='piper_voice'))
                self.assertEqual(result.exception.status_code,403)
            start.assert_not_called()
            self.assertEqual(setup.setup_action(request({'x-setup-token':setup.TOKEN,'origin':'http://127.0.0.1:8080'}),setup.SetupAction(action='piper_voice'))['status'],'running')
            start.assert_called_once()
        with self.assertRaises(setup.HTTPException) as remote:
            setup.require_local(request({'x-setup-token':setup.TOKEN}, '192.0.2.1'))
        self.assertEqual(remote.exception.status_code,403)


if __name__ == '__main__':
    unittest.main()
