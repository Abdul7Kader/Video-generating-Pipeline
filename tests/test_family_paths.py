import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from backend import main, story, antigravity, web_import
from backend.db import Database
from backend.schemas import JobCreate, ProductionConfig


class WebImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name)/'test.sqlite3')
        self.db.initialize()
        self.request = JobCreate(topic='Mila geht spazieren', duration_seconds=15, script_mode='story',
            generation_id='fd89eb00-8a9c-4b5f-8754-292b4bc954cc',
            production_config=ProductionConfig(profile_id='web_stickman', script_provider='web_import'))
        self.text = 'Mila geht durch den Park. Nach einem langen Tag lässt sie den Stress hinter sich und nimmt sich Zeit für einen kleinen Spaziergang. Sie läuft ruhig weiter und schaut sich um. Am Ende kehrt sie mit einem klaren Kopf nach Hause zurück.'
        self.value = {'title':'Ein kleiner Spaziergang', 'description':'Mila nimmt sich Zeit.', 'narration':self.text,
            'visual_summary':'Mila geht allein durch den Park und läuft anschließend zurück nach Hause.', 'fact_check_notes':[]}
        self.board = {'title':self.value['title'], 'description':self.value['description'], 'audience':'Erwachsene', 'tone':'ruhig', 'fact_check_notes':[],
            'scenes':[{'narration':self.text, 'visual':'Mila geht durch den Park.', 'duration_seconds':15, 'visual_type':'stickman',
                       'stickman':{'setting':'nature', 'characters':[{'id':'mila','pose':'walk','end_x':75}]}}]}

    def tearDown(self):
        self.temp.cleanup()

    def create(self):
        with patch('backend.main.db', self.db):
            return main.import_web_story(web_import.WebStoryRequest(request=self.request, response=json.dumps(self.value)))

    def action(self, job, **extra):
        return {'expected_version':job['script_version'], 'expected_hash':job['script']['content_hash'], **extra}

    def test_text_import_and_retry_are_idempotent_without_model_calls(self):
        with patch('backend.story.generate_structured', side_effect=AssertionError('No LLM')):
            job = self.create()
            repeated = self.create()
        self.assertEqual(job['id'], repeated['id'])
        self.assertEqual(job['actual_script_provider'], 'web_import')
        self.assertTrue(job['script']['integrity_verified'])
        self.assertEqual(story.spoken_story(job['script']), self.text)
        self.assertIsNone(job['approved_script_version'])
        changed = dict(self.value, title='Ein anderes Thema')
        with patch('backend.main.db', self.db), self.assertRaises(HTTPException) as failure:
            main.import_web_story(web_import.WebStoryRequest(request=self.request, response=json.dumps(changed)))
        self.assertEqual(failure.exception.status_code, 409)

    def test_concurrent_identical_imports_create_only_one_job(self):
        from concurrent.futures import ThreadPoolExecutor
        payload=web_import.WebStoryRequest(request=self.request,response=json.dumps(self.value))
        with patch('backend.main.db',self.db),ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:main.import_web_story(payload),range(2)))
        self.assertEqual(results[0]['id'],results[1]['id'])
        self.assertEqual(len(self.db.list_jobs()),1)

    def test_revision_invalidates_approval_and_preserves_job_on_bad_response(self):
        job = self.create()
        self.db.approve_script(job['id'],1,job['script']['content_hash'])
        payload = web_import.WebRevision(**self.action(job, instructions='Das Ende konkreter machen', response='not json'))
        with patch('backend.main.db',self.db), self.assertRaises(HTTPException):
            main.import_web_revision(job['id'],payload)
        self.assertEqual(self.db.get_job(job['id'])['approved_script_version'],1)
        revised = dict(self.value, narration=self.text.replace('klaren Kopf','ruhigen Kopf'))
        with patch('backend.main.db',self.db):
            result=main.import_web_revision(job['id'],payload.model_copy(update={'response':json.dumps(revised)}))
        self.assertEqual(result['script_version'],2)
        self.assertIsNone(result['approved_script_version'])
        with patch('backend.main.db',self.db), self.assertRaises(HTTPException) as failure:
            main.web_board_prompt(job['id'],web_import.WebBoard(**self.action(job)))
        self.assertEqual(failure.exception.status_code,409)

    def test_board_import_requires_current_text_approval_then_queues_existing_pipeline(self):
        job=self.create()
        payload=web_import.WebBoard(**self.action(job, response=json.dumps(self.board)))
        with patch('backend.main.db',self.db), self.assertRaises(HTTPException):
            main.import_web_board(job['id'],payload)
        with patch('backend.main.db',self.db):
            prompt=main.web_board_prompt(job['id'],payload)
            self.assertIn(self.text,prompt['prompt'])
            queued=main.import_web_board(job['id'],payload)
            repeated=main.import_web_board(job['id'],payload)
        self.assertEqual(queued['status'],'render_queued')
        self.assertEqual(queued['script_version'],2)
        self.assertEqual(repeated['script_version'],2)
        self.assertEqual(story.spoken_story(queued['script']),self.text)
        self.assertEqual(queued['approved_script_hash'],queued['render_script_hash'])
        self.assertIsNone(queued['approved_output_sha256'])

    def test_changed_words_missing_motif_and_external_media_never_queue(self):
        job=self.create()
        self.db.approve_script(job['id'],1,job['script']['content_hash'])
        for mutation in ['words','path','code','cat','source-type']:
            board=copy.deepcopy(self.board)
            if mutation=='words': board['scenes'][0]['narration']='Das ist ein anderer Text.'
            if mutation=='path': board['scenes'][0]['source_ref']='file:///private-test'
            if mutation=='source-type': board['scenes'][0]['source_strategy']=[]
            if mutation=='code': board['scenes'][0]['stickman']['svg']='<script>private-test</script>'
            if mutation=='cat':
                board['scenes'][0]['narration']=self.text.replace('Park','Park mit Katze')
            with self.subTest(mutation=mutation), patch('backend.main.db',self.db), self.assertRaises(HTTPException):
                main.import_web_board(job['id'],web_import.WebBoard(**self.action(job,response=json.dumps(board))))
        self.assertEqual(self.db.get_job(job['id'])['script_version'],1)
        self.assertNotEqual(self.db.get_job(job['id'])['status'],'render_queued')

    def test_missing_cat_in_exact_approved_words_blocks_the_import(self):
        self.request=self.request.model_copy(update={'topic':'Katze im Park'})
        self.value['narration']=self.text.replace('Park','Park mit Katze')
        job=self.create()
        self.db.approve_script(job['id'],1,job['script']['content_hash'])
        self.board['scenes'][0]['narration']=self.value['narration']
        with patch('backend.main.db',self.db),self.assertRaises(HTTPException) as failure:
            main.import_web_board(job['id'],web_import.WebBoard(**self.action(job,response=json.dumps(self.board))))
        self.assertEqual(failure.exception.status_code,422)
        self.assertIn('cat',str(failure.exception))
        self.assertEqual(self.db.get_job(job['id'])['script_version'],1)

    def test_json_boundary_rejects_ambiguous_nonfinite_and_deep_inputs(self):
        for raw in ['{"a":1,"a":2}', '{"x":NaN}', '{} trailing', '[1,2]', '{"a":'+('['*30)+'0'+(']'*30)+'}']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):web_import.parse_response(raw)
        self.assertEqual(web_import.parse_response('```json\n{"a":1}\n```'),{'a':1})

    def test_free_provider_auth_or_quota_failure_preserves_version_and_approval(self):
        job=self.create()
        config=ProductionConfig(script_provider='antigravity',profile_id='cloud_stickman').model_dump()
        current=self.db.update_production_config(job['id'],1,config)
        self.db.approve_script(job['id'],current['script_version'],current['script']['content_hash'])
        from backend.schemas import ScriptRevision
        for code in ['auth_required','quota_or_capacity','credits_enabled','billing_unknown']:
            with patch('backend.main.db',self.db),patch('backend.story.generate_structured',side_effect=antigravity.AntigravityError(code)), self.assertRaises(HTTPException) as failure:
                main.revise_script(job['id'],ScriptRevision(expected_version=current['script_version'],instructions='Mach den Anfang konkreter',story_mode=True))
            self.assertEqual(failure.exception.status_code,503)
            saved=self.db.get_job(job['id'])
            self.assertEqual(saved['script_version'],current['script_version'])
            self.assertEqual(saved['approved_script_hash'],current['script']['content_hash'])

    def test_credit_guard_failure_never_triggers_a_legacy_local_fallback(self):
        from types import SimpleNamespace
        request=self.request.model_copy(update={'production_config':ProductionConfig(script_provider='antigravity')})
        with patch('backend.story.settings',SimpleNamespace(antigravity_fallback_to_qwen=True)),patch('backend.story.generate_structured',side_effect=antigravity.AntigravityError('credits_enabled')),patch('backend.story.planner._generate_with_ollama') as local:
            with self.assertRaises(main.ScriptProviderUnavailable):story.generate_story(request)
        local.assert_not_called()


class FamilyApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_foreign_sites_and_rebinding_hosts_cannot_read_or_import_jobs(self):
        from tests.test_settings_api import request
        for headers in [{'origin':'https://evil.test'}, {'sec-fetch-site':'cross-site'}, {'host':'evil.test:8080'}]:
            with self.subTest(headers=headers),patch('backend.main.db.list_jobs') as listing:
                status,_=await request('GET','/api/jobs',headers=headers)
                self.assertEqual(status,403)
                listing.assert_not_called()
            with patch('backend.main.web_request') as validate:
                status,_=await request('POST','/api/jobs/web-prompt',{'request':{'topic':'Public test'}},headers=headers)
                self.assertEqual(status,403)
                validate.assert_not_called()

    async def test_import_body_limit_and_same_origin_contract(self):
        from tests.test_settings_api import request
        status,_=await request('POST','/api/jobs/web-prompt',{'request':{'topic':'Public test'}},headers={'content-length':'1500001'})
        self.assertEqual(status,413)
        value={'request':{'topic':'Public test','production_config':{'profile_id':'web_stickman','script_provider':'web_import'}}}
        status,result=await request('POST','/api/jobs/web-prompt',value,headers={'origin':'http://127.0.0.1:8080'})
        self.assertEqual(status,200)
        self.assertTrue(result['manual'])
        self.assertIn('Public test',result['prompt'])
