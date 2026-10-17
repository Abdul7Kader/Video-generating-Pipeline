import base64
import json
from pathlib import Path
import tempfile
import zlib
import struct
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from backend import images, image_guard


class ImageProviderTests(unittest.TestCase):
    def test_google_exports_only_this_runs_image_and_never_accepts_external_paths(self):
        from backend import antigravity_images as google
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            artifact=root/'fake-home/.gemini/antigravity-cli/brain/11111111-1111-1111-1111-111111111111'
            artifact.mkdir(parents=True)
            escape=False
            def invoke(mode,workspace,message=None,timeout=30):
                if mode=='inspect':return google.GUARD_NAME
                config=json.loads((workspace/'image-request.json').read_text())
                source=(root if escape else artifact)/(config['image_name']+'.png')
                source.write_bytes(b'fixture-png')
                (workspace/'guard-ready.json').write_text(json.dumps({'artifact':str(artifact)}))
                (workspace/'image-called').touch()
                return json.dumps({'event':'result','result':{'status':'SUCCESS',**({'structured_output':{'image_path':str(source)}} if escape else {})}})
            with patch.object(google,'settings',SimpleNamespace(data_dir=root,antigravity_model='gemini-fixture',antigravity_effort='high')),patch.object(google,'_executable',return_value='agy'),patch.object(google,'credit_guard'),patch.object(google,'invoke',side_effect=invoke),patch.object(google,'normalize_image',return_value={'width':1024,'height':1024}) as normalize:
                result=google.generate('A unique new idea',root/'output.png')
                self.assertEqual(result['provider'],'antigravity')
                self.assertEqual(normalize.call_args.args[0],b'fixture-png')
                escape=True
                with self.assertRaises(images.ImageError) as error: google.generate('A different idea',root/'second.png')
                self.assertEqual(error.exception.code,'policy')
                self.assertEqual(normalize.call_count,1)

    def test_http_rejects_non_allowlisted_targets_before_sending_a_token(self):
        with patch.object(images.urllib.request,'build_opener') as opener:
            for url in ['https://evil.example/image','http://api.cloudflare.com/image','https://api.cloudflare.com@evil.example/image']:
                with self.assertRaises(images.ImageError):images.http_json(url,{}, {'Authorization':'Bearer fixture-secret'})
            opener.assert_not_called()
        with self.assertRaises(images.ImageError): images.NoRedirect().redirect_request(None,None,None,None,None,None)

    def test_guard_denies_shell_browser_delegation_files_and_extra_images(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory)
            (workspace/'image-request.json').write_text(json.dumps({'prompt':'fixed image prompt','image_name':'frame_fixture'}))
            artifact=Path.home()/'.gemini/antigravity-cli/brain/11111111-1111-1111-1111-111111111111'
            payload={'artifactDirectoryPath':str(artifact),'workspacePaths':[str(workspace)]}
            image_guard.handle('session',payload,workspace)
            self.assertTrue((workspace/'guard-ready.json').exists())
            for name in ['run_command','read_url_content','invoke_subagent','view_file','write_to_file','ask_permission']:
                result=image_guard.handle('tool',{**payload,'toolCall':{'name':name,'args':{}}},workspace)
                self.assertEqual(result['decision'],'deny')
            with patch.object(image_guard.Path,'home',return_value=Path(directory)/'fake-home'):
                # With an independently configured home the prior artifact must be rejected.
                result=image_guard.handle('tool',{**payload,'toolCall':{'name':'generate_image','args':{}}},workspace)
                self.assertEqual(result['decision'],'deny')
            with patch.object(image_guard.Path,'exists',return_value=False):
                request={**payload,'toolCall':{'name':'generate_image','args':json.dumps({'Prompt':'model changed prompt','toolAction':'Generate image','toolSummary':'Only UI metadata'})}}
                result=image_guard.handle('tool',request,workspace)
                self.assertEqual(result['decision'],'auto_approve')
                self.assertEqual(result['overwrite']['Prompt'],'fixed image prompt')
                self.assertEqual(image_guard.handle('tool',request,workspace)['decision'],'deny')

    def test_raster_validation_decodes_real_pixels_rejects_svg_and_preserves_existing_files(self):
        def chunk(kind,data):
            return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',128,128,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\xff\xff\xff'*128)*128))+chunk(b'IEND',b'')
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'decoded.png'
            self.assertEqual(images.normalize_image(png,target),{'width':128,'height':128})
            self.assertTrue(target.read_bytes().startswith(b'\x89PNG'))
            with self.assertRaises(images.ImageError): images.normalize_image(b'<svg/>',Path(directory)/'bad.png')
            with self.assertRaises(images.ImageError): images.normalize_image(png,target)

    def test_cloudflare_requires_free_confirmation_and_credentials_before_network(self):
        with patch.object(images, 'credentials') as vault, patch.object(images, 'http_json') as network:
            vault.get.return_value = 'fixture-secret'
            for preferences in [images.Preferences(), images.Preferences(cloudflare_account_id='a'*32)]:
                with self.assertRaises(images.ImageError) as error:
                    images.generate('A specific story', Path('unused.png'), preferences)
                self.assertEqual(error.exception.code, 'not_configured')
            network.assert_not_called()

    def test_cloudflare_fixed_endpoint_no_extra_fields_and_sanitized_quota(self):
        preferences = images.Preferences(cloudflare_account_id='a'*32, cloudflare_free_confirmed=True)
        with tempfile.TemporaryDirectory() as directory, patch.object(images, 'credentials') as vault, \
                patch.object(images, 'http_json', return_value={'success': True, 'result': {'image': base64.b64encode(b'jpeg-fixture').decode()}}) as network, \
                patch.object(images, 'normalize_image', return_value={'width':1024,'height':1024}) as normalize:
            vault.get.return_value = 'fixture-secret'
            result = images.generate('A cat enters a basket', Path(directory)/'own.png', preferences)
            url, payload, headers = network.call_args.args
            self.assertEqual(url, 'https://api.cloudflare.com/client/v4/accounts/'+'a'*32+'/ai/run/@cf/black-forest-labs/flux-1-schnell')
            self.assertEqual(payload, {'prompt':'A cat enters a basket', 'steps':4})
            self.assertEqual(headers, {'Authorization':'Bearer fixture-secret'})
            self.assertEqual(result['provider'], 'cloudflare')
            normalize.assert_called_once()
            network.return_value = {'success':False,'errors':[{'code':3036,'message':'private quota fixture-secret'}]}
            with self.assertRaises(images.ImageError) as error:
                images.generate('A cat', Path(directory)/'next.png', preferences)
            self.assertEqual(error.exception.code, 'rate_limit')
            self.assertNotIn('fixture-secret',str(error.exception))

    def test_invalid_or_external_image_is_never_downloaded(self):
        preferences = images.Preferences(cloudflare_account_id='a'*32, cloudflare_free_confirmed=True)
        with patch.object(images,'credentials') as vault, patch.object(images,'http_json') as network:
            vault.get.return_value='fixture-secret'
            for image in ['https://evil.example/picture.png','<svg>','!!!!',None]:
                network.return_value={'success':True,'result':{'image':image}}
                with self.assertRaises(images.ImageError):
                    images.generate('A cat',Path('unused.png'),preferences)

    def test_configuration_stores_only_public_fields_and_rolls_back_vault_on_write_error(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(images,'settings',SimpleNamespace(data_dir=Path(directory))), patch.object(images,'credentials') as vault:
            vault.get.return_value='old-fixture'
            preferences=images.Preferences(cloudflare_account_id='a'*32)
            images.save(preferences,'new-fixture')
            self.assertNotIn('fixture',images.config_path().read_text())
            with patch.object(images.os,'replace',side_effect=OSError()):
                with self.assertRaises(OSError): images.save(preferences,'replacement-fixture')
            self.assertEqual(vault.set.call_args.args,('cloudflare_api_token','old-fixture'))


if __name__ == '__main__':
    unittest.main()
