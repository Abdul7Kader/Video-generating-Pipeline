import copy
import json
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch

from backend import frame_media as media, frame_rendering as rendering, frame_vision, image_guard, images
from backend.failures import PipelineFailure
from backend.plan import file_sha256


def wav(path,samples):
    with wave.open(str(path),'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(media.RATE)
        block=b'\x00\x08'*media.RATE
        while samples:
            count=min(samples,media.RATE);output.writeframesraw(block[:count*2]);samples-=count


def job_for(count=20):
    words=[f'Motiv {index} wird an seinem Ort sichtbar.' for index in range(count)]
    text=' '.join(words);cursor=0;beats=[]
    for index,word in enumerate(words):
        end=cursor+len(word)+(index<count-1)
        beats.append({'id':f'frame-{index}','text_start':cursor,'text_end':end,'composition':'object_focus',
            'setting':f'Ort {index}','action':f'Eine konkrete Veränderung {index}',
            'visible_change':f'Ergebnis {index}','depictions':[{'entity_id':'subject','source_quote':'Motiv'}]})
        cursor=end
    return {'language':'de','production_config':{'voice_provider':'piper','voice_id':'thorsten','voice_speed':1},
        'script':{'content_hash':'a'*64,'scenes':[{'narration':text}]},
        'frame_plan':{'text_sha256':'b'*64,'plan_hash':'c'*64,'style':'Handgezeichnete schwarze Linien, weiße Fläche.',
            'entities':{'subject':{'name':'Motiv','appearance':'Schwarze Linien'}},'images':beats}}


class FrameAudioTests(unittest.TestCase):
    def test_one_ten_thirty_minute_sample_clocks_have_no_accumulating_drift(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            for minutes in (1,10,30):
                first=root/'a.wav';second=root/'b.wav';total=minutes*60*media.RATE+173
                wav(first,total//3);wav(second,total-total//3)
                bounds=media.join_audio([first,second],root/'narration.wav')
                self.assertEqual(media.pcm_info(root/'narration.wav'),total)
                timeline={'rate':media.RATE,'samples':total,'images':bounds}
                self.assertEqual(sum(rendering.frame_counts(timeline)),round(total*rendering.FPS/media.RATE))
                self.assertLess(abs(sum(rendering.frame_counts(timeline))/rendering.FPS-total/media.RATE),1/rendering.FPS)

    def test_exact_words_single_voice_cache_and_corruption(self):
        job=job_for(3);spoken=[]
        def synthesize(text,output,language,**options):
            spoken.append(text);wav(output,16001);return 'piper',99
        def convert(command,**kwargs):
            import shutil
            shutil.copyfile(command[command.index('-i')+1],command[-1])
        with tempfile.TemporaryDirectory() as name,patch('backend.rendering.synthesize',side_effect=synthesize),patch('backend.rendering._run',side_effect=convert),patch('backend.rendering.compact_speech'),patch('backend.rendering.normalize_narration_audio'):
            first=Path(name)/'v1';timeline,_=media.prepare_audio(job,first)
            self.assertEqual(''.join(spoken),job['script']['scenes'][0]['narration'])
            self.assertEqual(timeline['samples'],3*16001)
            self.assertEqual(timeline['images'][-1]['end_sample'],3*16001)
            self.assertNotIn('words',timeline)
            media.prepare_audio(job,Path(name)/'v2');self.assertEqual(len(spoken),3)
            entry=json.loads((first/'voice-manifest.json').read_text())['segments'][1]
            (first/entry['file']).write_bytes(b'bad')
            (Path(name)/'v2'/entry['file']).write_bytes(b'bad')
            media.prepare_audio(job,Path(name)/'v3');self.assertEqual(len(spoken),4)
            job['production_config']['voice_speed']=1.2
            media.prepare_audio(job,Path(name)/'v4');self.assertEqual(len(spoken),7)


class FrameImageCacheTests(unittest.TestCase):
    def test_failure_seven_of_twenty_resumes_only_missing_and_detects_corruption(self):
        calls=[];fail=True
        def generate(prompt,path,preferences):
            calls.append(prompt)
            if fail and len(calls)==7:raise images.ImageError('rate_limit')
            path.write_bytes(b'fixture-'+prompt.encode());return {'provider':'fixture','image_model':'fixture'}
        def review(path,expected,reference=None):
            return {'passed':True,'policy':frame_vision.POLICY,'image_sha256':file_sha256(path),
                'evidence':'guarded_view_file_pixels','issues':[]}
        with tempfile.TemporaryDirectory() as name,patch.object(media.images,'generate',side_effect=generate),patch.object(media.frame_vision,'review',side_effect=review):
            root=Path(name);job=job_for();preferences=images.Preferences(provider='antigravity')
            with self.assertRaises(PipelineFailure):media.prepare_images(job,root/'v1',preferences)
            manifest=json.loads((root/'v1/asset-manifest.json').read_text());self.assertEqual(len(manifest['assets']),6)
            fail=False
            result=media.prepare_images(job,root/'v1',preferences);self.assertEqual(len(result['assets']),20)
            self.assertEqual(len(calls),21)
            media.prepare_images(job,root/'v2',preferences);self.assertEqual(len(calls),21)
            entry=result['assets'][6]
            for version in ('v1','v2'):(root/version/entry['local_file']).write_bytes(b'broken')
            media.prepare_images(job,root/'v3',preferences);self.assertEqual(len(calls),22)
            changed=copy.deepcopy(job);changed['frame_plan']['images'][10]['action']='Neuer sichtbarer Inhalt'
            media.prepare_images(changed,root/'v4',preferences);self.assertEqual(len(calls),23)

    def test_wrong_pixels_get_one_correction_then_visible_failure_not_success(self):
        def generate(prompt,path,preferences):path.write_bytes(b'wrong');return {'provider':'fixture'}
        with tempfile.TemporaryDirectory() as name,patch.object(media.images,'generate',side_effect=generate) as provider,patch.object(media.frame_vision,'review',return_value={'passed':False,'issues':['Das genannte Tier fehlt.']}) as vision:
            with self.assertRaises(PipelineFailure) as error:media.prepare_images(job_for(1),Path(name)/'v1',images.Preferences(provider='antigravity'))
            self.assertEqual(error.exception.stage,'quality');self.assertEqual(error.exception.context['image_index'],1)
            self.assertEqual(provider.call_count,2);self.assertEqual(vision.call_count,2)
            self.assertFalse((Path(name)/'v1/asset-manifest.json').exists())

    def test_linked_work_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as name,patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(ValueError):media.safe_directory(Path(name)/'v1')

    def test_generated_pixels_survive_a_temporary_vision_failure(self):
        def generate(prompt,path,preferences):path.write_bytes(b'actual-local-fixture');return {'provider':'fixture'}
        def accepted(path,*args):return {'passed':True,'image_sha256':file_sha256(path),'issues':[],'evidence':'guarded_view_file_pixels'}
        with tempfile.TemporaryDirectory() as name,patch.object(media.images,'generate',side_effect=generate) as provider:
            root=Path(name)/'v1';preferences=images.Preferences(provider='antigravity')
            with patch.object(media.frame_vision,'review',side_effect=images.ImageError('rate_limit')),self.assertRaises(PipelineFailure):
                media.prepare_images(job_for(1),root,preferences)
            self.assertEqual(len(list((root/'assets').glob('*.pending.png'))),1)
            with patch.object(media.frame_vision,'review',side_effect=accepted):
                media.prepare_images(job_for(1),root,preferences)
            self.assertEqual(provider.call_count,1)
            self.assertFalse(list((root/'assets').glob('*.pending.png')))

    def test_concat_rejects_arbitrary_paths_before_starting_ffmpeg(self):
        timeline={'rate':48000,'samples':48000,'images':[{'id':'a','start_sample':0,'end_sample':48000}]}
        for path in ('https://example.com/image.png','../private.png','assets/evil\nfile.png'):
            with patch('backend.rendering._run') as process,self.assertRaises(ValueError):
                rendering.compose(Path('.'),timeline,{'assets':[{'local_file':path,'scene_id':'a','sha256':'x'}]},'16:9')
            process.assert_not_called()


class VisionGuardTests(unittest.TestCase):
    def test_review_can_only_view_owned_exact_pixels_once(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);workspace=root/'workspace';workspace.mkdir()
            brain=root/'.gemini/antigravity-cli/brain/11111111-1111-1111-1111-111111111111';brain.mkdir(parents=True)
            image=workspace/'candidate.png';image.write_bytes(b'own-pixels')
            (workspace/'image-request.json').write_text(json.dumps({'review_files':{str(image):file_sha256(image)}}))
            value={'artifactDirectoryPath':str(brain),'workspacePaths':[str(workspace)]}
            with patch.object(image_guard.Path,'home',return_value=root):
                self.assertEqual(image_guard.handle('session',value,workspace),{})
                for tool in ('run_command','generate_image','read_url_content'):
                    self.assertEqual(image_guard.handle('tool',value|{'toolCall':{'name':tool,'args':{}}},workspace)['decision'],'deny')
                request=value|{'toolCall':{'name':'view_file','args':{'AbsolutePath':str(image)}}}
                self.assertEqual(image_guard.handle('tool',request,workspace)['decision'],'auto_approve')
                self.assertEqual(image_guard.handle('post',request,workspace),{})
                self.assertTrue((workspace/'view-completed-candidate').exists())
                self.assertEqual(image_guard.handle('tool',request,workspace)['decision'],'deny')
                request['toolCall']['args']['AbsolutePath']=str(root/'private.txt')
                self.assertEqual(image_guard.handle('tool',request,workspace)['decision'],'deny')

    def test_provider_tool_quota_is_reported_even_if_outer_cli_claims_success(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);workspace=root/'workspace';workspace.mkdir()
            artifact=root/'.gemini/antigravity-cli/brain/11111111-1111-1111-1111-111111111111';artifact.mkdir(parents=True)
            (workspace/'image-request.json').write_text(json.dumps({'prompt':'Fixed own image','image_name':'frame_fixture'}))
            value={'artifactDirectoryPath':str(artifact),'workspacePaths':[str(workspace)],'toolCall':{'name':'generate_image','args':{}}}
            with patch.object(image_guard.Path,'home',return_value=root):
                image_guard.handle('session',value,workspace)
                self.assertEqual(image_guard.handle('tool',value,workspace)['decision'],'auto_approve')
                self.assertEqual(image_guard.handle('post',value|{'error':'429 RESOURCE_EXHAUSTED private-token-fixture'},workspace),{})
            self.assertEqual((workspace/'guard-tool-error').read_text(),'rate_limit')
            self.assertFalse((workspace/'image-completed').exists())


if __name__=='__main__':unittest.main()
