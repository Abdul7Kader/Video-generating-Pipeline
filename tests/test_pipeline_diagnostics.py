from dataclasses import replace
import asyncio
import errno
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from backend import main
from backend.config import settings
from backend.db import Database
from backend.failures import PipelineFailure,describe,failure_stage
from backend.modes import require_mode
from backend.schemas import JobCreate
from tests.test_workflow import VALUES,SCRIPT
from tests.test_settings_api import request


class PipelineDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.root=Path(folder.name);self.db=Database(self.root/'test.sqlite3');self.db.initialize()
        self.job_id=self.db.create_job(VALUES,SCRIPT)

    def test_legacy_animation_and_script_hash_stay_identical_and_modes_are_immutable(self):
        job=self.db.get_job(self.job_id);digest=job['script']['content_hash']
        self.assertEqual(job['generation_mode'],'animated')
        self.assertEqual(job['script']['generation_mode'],'animated')
        self.db.initialize()
        self.assertEqual(self.db.get_job(self.job_id)['script']['content_hash'],digest)
        revised=self.db.update_script(self.job_id,1,{**SCRIPT,'title':'Revision'})
        self.assertEqual(revised['script']['generation_mode'],'animated')
        with self.db.connect() as connection,self.assertRaises(sqlite3.IntegrityError):
            connection.execute("UPDATE jobs SET generation_mode='frame' WHERE id=?",(self.job_id,))
        with self.assertRaisesRegex(ValueError,'generation_mode_conflict'):
            self.db.create_job({**VALUES,'generation_mode':'frame'},SCRIPT,job_id=self.job_id)

    def test_frame_is_explicit_and_never_runs_the_old_renderer_or_a_provider(self):
        self.assertEqual(JobCreate(topic='Testidee').generation_mode,'animated')
        with patch.object(main,'generate_story') as story,patch.object(main,'generate_script') as scenes:
            with self.assertRaises(PipelineFailure) as error:
                main.create_job(JobCreate(topic='Testidee',generation_mode='frame'))
        self.assertEqual(error.exception.code,'not_ready');story.assert_not_called();scenes.assert_not_called()
        require_mode('animated')
        frame_id=self.db.create_job({**VALUES,'generation_mode':'frame'},SCRIPT)
        frame=self.db.get_job(frame_id)
        self.assertEqual(frame['script']['generation_mode'],'frame')
        with self.assertRaises(PipelineFailure):
            self.db.approve_script(frame_id,1,frame['script']['content_hash'])

    def test_mode_tampering_invalidates_integrity_without_changing_the_old_hash(self):
        before=self.db.get_job(self.job_id)['script']['content_hash']
        with self.db.connect() as connection:
            connection.execute("UPDATE script_versions SET generation_mode='frame' WHERE job_id=?",(self.job_id,));connection.commit()
        job=self.db.get_job(self.job_id)
        self.assertEqual(job['script']['content_hash'],before);self.assertFalse(job['script']['integrity_verified'])
        with self.assertRaisesRegex(ValueError,'generation_mode_conflict'):
            self.db.approve_script(self.job_id,1,before)

    @unittest.skipUnless(sys.platform=='win32','Native worker diagnostic roundtrip')
    def test_native_worker_protocol_retains_stage_and_id_without_exception_body(self):
        from backend.operations import Operation
        worker=self.root/'fixture_worker.py'
        project=str(Path(__file__).resolve().parents[1])
        worker.write_text('import sys,json\nfrom pathlib import Path\n'
            f'sys.path.insert(0,{project!r})\n'
            'from backend import failures\n'
            'failures.progress_path=Path(sys.argv[2]).with_name("progress.json")\n'
            'try:\n'
            ' with failures.failure_stage("voice",scene_id="scene_2"):\n'
            '  with failures.failure_stage("voice"):\n'
            '   raise TimeoutError("access_token=private-protocol-fixture")\n'
            'except Exception as error:\n'
            ' failure=failures.describe(error)\n'
            ' Path(sys.argv[2]).write_text(json.dumps({"failure":failure.wire()}))\n',encoding='utf-8')
        with patch('backend.operations.settings',replace(settings,data_dir=self.root)),self.assertRaises(PipelineFailure) as error:
            Operation().run('render',{},worker=worker)
        self.assertEqual(error.exception.stage,'voice');self.assertEqual(error.exception.context['scene_id'],'scene_2')
        self.assertNotIn('private-protocol-fixture',json.dumps(error.exception.wire()))

    def test_stages_keep_the_original_cause_and_strip_secret_bodies_from_all_reports(self):
        secret='fixture-private-token'
        with self.assertRaises(PipelineFailure) as error:
            with failure_stage('render'):
                with failure_stage('voice',scene_id='scene_2'):
                    raise TimeoutError('https://provider.test/?access_token='+secret)
        failure=error.exception
        self.assertEqual(failure.stage,'voice');self.assertEqual(failure.code,'timeout')
        self.assertEqual(failure.context['scene_id'],'scene_2')
        self.db.record_failure(failure,self.job_id);self.db.fail_render(self.job_id,str(failure))
        loaded=Database(self.db.path).get_job(self.job_id)
        self.assertEqual(loaded['error_report']['id'],failure.identifier)
        with self.db.connect() as connection:
            stored=' '.join(str(tuple(row)) for row in connection.execute('SELECT * FROM pipeline_failures'))
        self.assertNotIn(secret,stored);self.assertNotIn(secret,json.dumps(loaded))
        self.assertEqual(describe(OSError(errno.ENOSPC,'secret'),'storage').code,'disk_full')
        self.assertFalse(describe(TimeoutError(),'publish').public()['retryable'])

    def test_worker_messages_cannot_supply_public_wording_or_leak_diagnostic_fields(self):
        failure=PipelineFailure.from_wire({'stage':'voice','code':'timeout','id':'a'*16,
            'message':'never display secret','context':{'token':'secret','scene_id':'scene_1'},
            'diagnostics':{'body':'secret','exception_type':'TimeoutError','locations':[{'function':'run','line':20,'token':'secret'}]}})
        self.assertNotIn('secret',json.dumps(failure.wire()))
        self.assertEqual(failure.identifier,'a'*16)

    def test_common_failure_categories_are_specific_without_copying_exception_messages(self):
        examples=[(PermissionError('private'),'permission'),(FileNotFoundError('private'),'missing_file'),
            (RuntimeError('HTTP 429 private'),'rate_limit'),(RuntimeError('HTTP 401 private'),'credentials'),
            (ValueError('private'),'invalid_response'),(subprocess.CalledProcessError(2,['private']),'process_failed'),
            (RuntimeError('private'),'unexpected')]
        for error,code in examples:
            with self.subTest(code=code):
                failure=describe(error,'voice')
                self.assertEqual(failure.code,code)
                self.assertNotIn('private',json.dumps(failure.public()))

    def test_unexpected_api_exception_has_safe_response_and_persistent_identifier(self):
        with patch.object(main,'db',self.db),patch.object(self.db,'get_job',side_effect=OSError(errno.ENOSPC,'private-database-error')):
            status,value=asyncio.run(request('GET','/api/jobs/'+self.job_id))
        self.assertEqual(status,500);self.assertEqual(value['failure']['code'],'disk_full')
        self.assertNotIn('private-database-error',json.dumps(value))

    def test_api_returns_and_persists_the_same_failure_without_provider_output(self):
        with patch.object(main,'db',self.db),patch.object(main,'generate_script',side_effect=RuntimeError('password=private-fixture-key')):
            status,value=asyncio.run(request('POST','/api/jobs',VALUES))
        self.assertEqual(status,502)
        self.assertEqual(value['failure']['stage'],'script')
        self.assertNotIn('private-fixture-key',json.dumps(value))
        with self.db.connect() as connection:
            found=connection.execute('SELECT id FROM pipeline_failures WHERE id=?',(value['failure']['id'],)).fetchone()
        self.assertIsNotNone(found)

    def test_frame_api_refuses_before_any_paid_or_local_generation(self):
        with patch.object(main,'db',self.db),patch.object(main,'generate_script') as provider:
            status,value=asyncio.run(request('POST','/api/jobs',{**VALUES,'generation_mode':'frame'}))
        self.assertEqual(status,409);self.assertEqual(value['failure']['code'],'not_ready');provider.assert_not_called()
