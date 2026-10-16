import asyncio
import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from backend import frame, main
from backend.db import Database
from backend.failures import PipelineFailure
from backend.plan import object_sha256
from backend.schemas import JobCreate, ProductionConfig, VersionAction, ScriptRevision
from backend.config import settings
from test_settings_api import request as http_request

CONFIG={'profile_id':'cloud_stickman','video_type':'stickman','script_provider':'antigravity',
        'media_provider':'procedural_stickman','voice_provider':'piper','editor':'remotion','voice_id':'thorsten','voice_speed':1}


def request(**values):
    return JobCreate(topic='Eine neue Idee erklären',generation_mode='frame',production_config=ProductionConfig(**CONFIG),**values)


def script_for(text):
    from backend.plan import script_hash
    script=frame.build_script(request(),text)
    script.update(version=1,content_hash=script_hash(script))
    return script


def batch_for(text, name='Katze', kind='animal', composition='literal_scene'):
    return {'new_entities':[{'id':'subject','name':name,'kind':kind,'appearance':'Klar erkennbares zentrales Motiv','source_quote':name}],
            'images':[{'quote':text,'composition':composition,'setting':'Passender Ort der Erzählung',
                       'action':'Das genannte Motiv wird im beschriebenen Zustand gezeigt.',
                       'visible_change':'Die beschriebene Folge ist sichtbar.',
                       'depictions':[{'entity_id':'subject','source_quote':name}]}]}


def plan_answer(batch):
    return lambda req,prompt,schema: ({'issues':[]} if schema is frame.PlanReview else copy.deepcopy(batch),'fixture','none')


class FrameContractTests(unittest.TestCase):
    def test_long_duration_is_frame_only_and_owned_text_is_preserved_exactly(self):
        for seconds in (60,600,1800):
            value=request(duration_seconds=seconds,input_kind='narration',narration='  Eine Katze kommt an.\n\nSie erkundet das Zimmer.  ')
            with patch.object(frame,'call') as provider:
                script=frame.draft(value)
            provider.assert_not_called()
            self.assertEqual(frame.narration(script),value.narration)
            self.assertIsNone(script['metadata']['story_quality']['actual_seconds'])
        for values in ({'duration_seconds':1801},{'input_kind':'narration'}, {'input_kind':'idea','narration':'x'*40}):
            with self.assertRaises(ValidationError):request(**values)
        with self.assertRaises(ValidationError):JobCreate(topic='Animiert',duration_seconds=601)
        unsupported=request().model_copy(update={'production_config':ProductionConfig(**(CONFIG|{'script_provider':'gemini_cli','profile_id':'custom'}))})
        with patch.object(frame.planner,'_provider_for_request') as provider,self.assertRaises(frame.planner.ScriptProviderUnavailable):
            frame.call(unsupported,'No fallback',frame.DraftPart)
        provider.assert_not_called()

    def test_chunks_cover_every_character_including_unicode_and_whitespace(self):
        text='  Erste Erklärung über Öl und Größe.\n\n'+' '.join(f'Satz {i} beschreibt einen neuen Zusammenhang.' for i in range(170))+'  '
        chunks=list(frame.chunks(text))
        self.assertEqual(''.join(part for _,_,part in chunks),text)
        self.assertGreater(len(chunks),2)
        self.assertTrue(all(end-start<=5000 for start,end,_ in chunks))
        self.assertEqual(chunks[-1][1],len(text))

    def test_one_ten_thirty_minute_drafts_use_bounded_content_specific_calls(self):
        for seconds in (60,600,1800):
            calls=[]
            def answer(req,prompt,schema):
                data=json.loads(prompt.split('INPUT_JSON:\n')[-1]);calls.append((data,prompt))
                words=data['target_words_for_this_part'];index=data['part']
                text=f'Gedanke {index} '+ ' '.join(f'w{index}x{i}' for i in range(words-2))+'.'
                return {'title':'Das neue Thema','description':'Erklärung','narration':text,'visual_summary':'Ein passender Vergleich erklärt dieses Thema.','fact_check_notes':[]},'fixture','none'
            with patch.object(frame,'call',side_effect=answer):
                script=frame.draft(request(duration_seconds=seconds))
            self.assertGreaterEqual(len(calls),1)
            self.assertTrue(all(data['target_words_for_this_part']<=300 for data,_ in calls))
            self.assertEqual(len(script['scenes']),1)
            self.assertAlmostEqual(len(frame.narration(script).split()),frame.word_budget(request(duration_seconds=seconds))[0],delta=len(calls))
            self.assertIn('THIS idea',calls[0][1]);self.assertIn('NO animation vocabulary restriction',calls[0][1])
            self.assertEqual(calls[0][0]['idea'],'Eine neue Idee erklären')

    def test_cat_fire_before_after_and_abstract_comparison_are_different_plans(self):
        cases=[('Eine Katze wird adoptiert und erkundet ihr neues Zuhause.','Katze','animal','literal_scene'),
               ('Das Feuer wärmt den Platz und verändert die Zubereitung von Nahrung.','Feuer','object','environment'),
               ('Der Raum ist vorher ungeordnet und nachher übersichtlich.','Raum','place','comparison'),
               ('Wissen wächst durch Verknüpfungen zwischen alten und neuen Gedanken.','Wissen','concept','diagram')]
        hashes=[]
        for text,name,kind,composition in cases:
            with patch.object(frame,'call',side_effect=plan_answer(batch_for(text,name,kind,composition))):
                plan=frame.plan_images(request(),script_for(text))
                again=frame.plan_images(request(),script_for(text))
            self.assertEqual(plan['images'][0]['composition'],composition)
            self.assertEqual(plan['entities']['subject']['kind'],kind)
            self.assertEqual(plan['images'][0]['id'],again['images'][0]['id'])
            self.assertNotIn('duration_seconds',plan['images'][0]);hashes.append(plan['plan_hash'])
        self.assertEqual(len(set(hashes)),4)

    def test_plan_rejects_omission_reorder_rewrite_missing_subject_and_unbound_evidence(self):
        text='Eine Katze kommt an. Die Katze erkundet den Raum.'
        bad=[]
        item=batch_for(text);item['images'][0]['quote']='Eine Katze kommt an.';bad.append(item)
        item=batch_for(text);item['images'][0]['quote']=text.replace('Katze','Hund');bad.append(item)
        item=batch_for(text);item['images'][0]['depictions'][0]['entity_id']='basket';bad.append(item)
        item=batch_for(text);item['images'][0]['depictions'][0]['source_quote']='Korb';bad.append(item)
        item=batch_for(text);item['new_entities'][0]['source_quote']='Bett';bad.append(item)
        for item in bad:
            with self.assertRaises(ValueError):frame.bind_batch(text,item,{})
        proper=batch_for(text);proper['images'][0]['quote']='Eine Katze kommt an.'
        second=copy.deepcopy(proper['images'][0]);second['quote']='Die Katze erkundet den Raum.';second['visible_change']='Die Katze befindet sich nun im Raum.'
        proper['images'].append(second)
        bound,_=frame.bind_batch(text,proper,{})
        self.assertEqual(bound[0]['text_end'],bound[1]['text_start'])
        self.assertEqual(bound[-1]['text_end'],len(text))
        proper['images'].reverse()
        with self.assertRaises(ValueError):frame.bind_batch(text,proper,{})

    def test_semantic_review_rejects_accessory_substitution_and_generic_gestures(self):
        text='Eine Katze wird adoptiert und erkundet ihr neues Zuhause.'
        proposed=batch_for(text)
        proposed['images'][0]['action']='Eine Person zeigt auf ein leeres Bett.'
        def rejected(req,prompt,schema):
            return ({'issues':['Die Katze fehlt; ein Bett und Zeigen ersetzen keine Adoption.']} if schema is frame.PlanReview else proposed),'fixture','none'
        with patch.object(frame,'call',side_effect=rejected) as provider,self.assertRaises(PipelineFailure) as failure:
            frame.plan_images(request(),script_for(text))
        self.assertEqual(failure.exception.stage,'planning');self.assertEqual(failure.exception.code,'invalid_response')
        self.assertEqual(provider.call_count,4)  # plan + review, one bounded correction

    def test_generic_duplicate_images_and_tampered_text_binding_are_rejected(self):
        text='Eine Katze kommt an. Die Katze erkundet den Raum.'
        proposed=batch_for(text);proposed['images'][0]['quote']='Eine Katze kommt an.'
        second=copy.deepcopy(proposed['images'][0]);second['quote']='Die Katze erkundet den Raum.'
        proposed['images'].append(second)
        with patch.object(frame,'call',side_effect=plan_answer(proposed)),self.assertRaisesRegex(ValueError,'identische Bildidee'):
            frame.plan_images(request(),script_for(text))
        tampered=script_for(text);tampered['scenes'][0]['narration']=text.replace('Katze','Hund')
        with patch.object(frame,'call') as provider,self.assertRaises(ValueError):
            frame.plan_images(request(),tampered)
        provider.assert_not_called()

    def test_revision_reads_every_part_of_long_original_and_preserves_unchanged_content(self):
        text=' '.join(f'Der Gedanke {i} erklärt diesen besonderen Zusammenhang ohne Wiederholung.' for i in range(900))
        original=script_for(text);seen=[]
        def changed(req,prompt,schema):
            data=json.loads(prompt.split('INPUT_JSON:\n')[-1]);seen.append(data['original_part'])
            return {'title':'Die Erklärung','description':'Überarbeitet','narration':data['original_part'].replace('Gedanke','Begriff'),
                    'visual_summary':'Der Zusammenhang wird passend zum Inhalt erklärt.','fact_check_notes':[]},'fixture','none'
        with patch.object(frame,'call',side_effect=changed):
            revised=frame.draft(request(duration_seconds=1800),previous=original,instructions='Ersetze Gedanke durch Begriff.')
        self.assertEqual(''.join(seen),text)
        self.assertEqual(frame.narration(revised),text.replace('Gedanke','Begriff'))
        def shortened(req,prompt,schema):
            data=json.loads(prompt.split('INPUT_JSON:\n')[-1])
            return {'title':'Gekürzt','description':'Auf Wunsch gekürzt','narration':data['original_part'].split('.')[0]+'.',
                    'visual_summary':'Nur die wesentliche Aussage wird gezeigt.','fact_check_notes':[]},'fixture','none'
        with patch.object(frame,'call',side_effect=shortened):
            short=frame.draft(request(duration_seconds=1800),previous=original,instructions='Kürze deutlich und entferne die meisten Details.')
        self.assertLess(len(frame.narration(short)),len(text)/2)


class FrameWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db=Database(Path(self.temp.name)/'jobs.db');self.db.initialize()
        self.patch=patch.object(main,'db',self.db);self.patch.start();self.addCleanup(self.patch.stop)
        self.payload=request(input_kind='narration',narration='Eine Katze wird adoptiert und erkundet ihr neues Zuhause.')

    def test_text_to_approval_to_plan_is_persistent_and_never_renders(self):
        with patch('backend.rendering.render_job') as render,patch.object(frame,'call') as provider:
            job=main.create_job(self.payload)
        provider.assert_not_called();render.assert_not_called()
        self.assertEqual(job['generation_mode'],'frame');self.assertIsNone(job['frame_plan'])
        plan=None
        with patch.object(frame,'call',side_effect=plan_answer(batch_for(self.payload.narration))):
            plan=frame.plan_images(self.payload,job['script'])
        with patch('backend.operations.Operation.run',return_value=plan) as worker:
            planned=main.approve_frame_plan(job['id'],VersionAction(expected_version=1,expected_hash=job['script']['content_hash']))
        self.assertEqual(worker.call_args.args[0],'frame_plan')
        self.assertEqual(planned['script_version'],1);self.assertEqual(planned['status'],'script_approved')
        self.assertEqual(Database(self.db.path).get_job(job['id'])['frame_plan']['plan_hash'],plan['plan_hash'])
        self.assertEqual(frame.narration(planned['script']),self.payload.narration)
        with self.assertRaises(PipelineFailure):self.db.queue_render(job['id'],1,job['script']['content_hash'])
        with self.assertRaises(PipelineFailure):main.approve_story_and_render(job['id'],VersionAction(expected_version=1,expected_hash=job['script']['content_hash']))

    def test_revision_invalidates_plan_and_requires_new_approval(self):
        job=main.create_job(self.payload)
        self.db.approve_script(job['id'],1,job['script']['content_hash'],allow_frame=True)
        self.db.begin_planning(job['id'],1)
        with patch.object(frame,'call',side_effect=plan_answer(batch_for(self.payload.narration))):
            plan=frame.plan_images(self.payload,job['script'])
        self.db.save_frame_plan(job['id'],1,job['script']['content_hash'],plan)
        revised=frame.build_script(self.payload,self.payload.narration.replace('Katze','junge Katze'),revision=True)
        with patch('backend.operations.Operation.run',return_value=revised):
            result=main.revise_script(job['id'],ScriptRevision(expected_version=1,instructions='Beschreibe eine junge Katze.'))
        self.assertEqual(result['script_version'],2);self.assertIsNone(result['frame_plan']);self.assertIsNone(result['approved_script_hash'])
        with self.assertRaises(Exception):main.approve_frame_plan(job['id'],VersionAction(expected_version=1,expected_hash=job['script']['content_hash']))

    def test_tampered_plan_or_unapproved_version_is_never_saved(self):
        job=main.create_job(self.payload)
        with patch.object(frame,'call',side_effect=plan_answer(batch_for(self.payload.narration))):
            plan=frame.plan_images(self.payload,job['script'])
        with self.assertRaises(ValueError):self.db.save_frame_plan(job['id'],1,job['script']['content_hash'],plan)
        self.db.approve_script(job['id'],1,job['script']['content_hash'],allow_frame=True);self.db.begin_planning(job['id'],1)
        plan['images'][0]['text_end']-=1;plan['plan_hash']=object_sha256({k:v for k,v in plan.items() if k!='plan_hash'})
        with self.assertRaises(ValueError):self.db.save_frame_plan(job['id'],1,job['script']['content_hash'],plan)

    def test_long_input_api_is_reachable_and_does_not_require_a_generator(self):
        text=' '.join(f'Der Gedanke {i} erklärt diesen besonderen Zusammenhang ohne Wiederholung.' for i in range(700))
        self.assertGreater(len(text),16000)
        status,job=asyncio.run(http_request('POST','/api/jobs',self.payload.model_dump()|{'duration_seconds':1800,'narration':text}))
        self.assertEqual(status,201);self.assertEqual(job['duration_seconds'],1800)
        self.assertEqual(frame.narration(job['script']),text)

    def test_voice_change_recalculates_estimate_and_stale_or_large_inputs_fail(self):
        job=main.create_job(self.payload)
        previous=job['script']['metadata']['story_quality']['estimated_speech_seconds']
        job=self.db.update_production_config(job['id'],1,CONFIG|{'voice_speed':1.25})
        self.assertLess(job['script']['metadata']['story_quality']['estimated_speech_seconds'],previous)
        self.assertIsNone(job['approved_script_hash']);self.assertIsNone(job['frame_plan'])
        status,_=asyncio.run(http_request('POST','/api/jobs',{},headers={'content-length':'1500001'}))
        self.assertEqual(status,413)

    def test_private_worker_supports_own_text_without_any_provider(self):
        from backend.operations import Operation
        with patch('backend.operations.settings',replace(settings,data_dir=Path(self.temp.name))):
            script=Operation().run('frame_draft',{'request':self.payload.model_dump()},timeout=30)
        self.assertEqual(frame.narration(script),self.payload.narration)
        self.assertEqual(script['metadata']['provider'],'user_text')
