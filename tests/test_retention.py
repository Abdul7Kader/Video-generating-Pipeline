from dataclasses import replace
from datetime import datetime,timedelta,timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend import retention,video_storage
from backend.config import settings
from backend.db import Database
from backend.integrations import Preferences
from backend.operations import operations
from backend.plan import file_sha256
from tests.test_workflow import VALUES,SCRIPT


class RetentionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.config = replace(settings,data_dir=self.root)
        self.db = Database(self.config.database_path)
        self.db.initialize()
        self.job_id = self.db.create_job(VALUES,SCRIPT)
        fingerprint = self.db.get_job(self.job_id)['script']['content_hash']
        self.db.approve_script(self.job_id,1,fingerprint)
        self.db.queue_render(self.job_id,1,fingerprint)
        self.work = self.config.jobs_dir / self.job_id / 'v1'
        self.work.mkdir(parents=True)
        self.video = self.work / 'video.mp4'
        self.video.write_bytes(b'fixture-approved-video')
        self.digest = file_sha256(self.video)
        self.db.finish_render(self.job_id,1,str(self.video.relative_to(self.config.jobs_dir)),self.digest,'fixture')
        self.wav = self.work / 'audio' / 'scene.wav'
        self.wav.parent.mkdir()
        self.wav.write_bytes(b'fixture-wave')
        self.asset = self.work / 'assets' / 'scene.svg'
        self.asset.parent.mkdir()
        self.asset.write_text('<svg/>')
        self.proof = self.work / 'quality-report.json'
        self.proof.write_text('{}')
        self.unknown = self.work / 'my-notes.txt'
        self.unknown.write_text('keep')
        self.preference = Preferences()
        for module in (video_storage,retention):
            setting = patch.object(module,'settings',self.config)
            setting.start();self.addCleanup(setting.stop)
            preference = patch.object(module,'load',side_effect=lambda:self.preference)
            preference.start();self.addCleanup(preference.stop)

    def age(self):
        old = datetime.now(timezone.utc)-timedelta(days=60)
        with self.db.connect() as connection:
            connection.execute('UPDATE jobs SET updated_at=? WHERE id=?',(old.isoformat(),self.job_id))
            connection.commit()
        for file in (self.wav,self.asset):
            os.utime(file,(old.timestamp(),old.timestamp()))

    def clean(self,**options):
        return retention.clean_expired_work(self.db,job_id=self.job_id,expected=(1,self.digest),**options)

    def test_default_is_manual_and_final_video_can_be_served_after_cleanup(self):
        self.age()
        self.assertEqual(retention.clean_expired_work(self.db),0)
        self.assertTrue(self.video.exists())
        self.assertEqual(self.clean(),2)
        job = self.db.get_job(self.job_id)
        final = video_storage.primary_output(job)
        self.assertEqual(final.parent,self.root / 'videos')
        self.assertEqual(final.read_bytes(),b'fixture-approved-video')
        self.assertFalse(self.video.exists())
        self.assertFalse(self.wav.exists())
        self.assertFalse(self.asset.exists())
        self.assertTrue(self.proof.exists())
        self.assertTrue(self.unknown.exists())
        self.assertTrue(job['script']['integrity_verified'])
        self.assertTrue(job['work_cleaned_at'])
        from backend import main
        with patch.object(main,'db',self.db),patch.object(main,'settings',self.config):
            response = main.get_video(self.job_id,'9:16')
            self.assertEqual(Path(response.path),final)
        self.assertEqual(self.clean(),0)
        revised = self.db.update_script(self.job_id,1,{**SCRIPT,'title':'Weiterbearbeitet'})
        self.assertEqual(revised['script_version'],2)
        self.assertEqual(revised['status'],'script_review')
        self.assertTrue(final.exists())

    def test_pin_active_operation_and_stale_version_prevent_deletion(self):
        self.db.retain_project(self.job_id,True)
        self.assertEqual(self.clean(),0)
        self.db.retain_project(self.job_id,False)
        with operations.start(self.job_id,self.db):
            self.assertEqual(self.clean(),0)
        self.assertEqual(retention.clean_expired_work(self.db,job_id=self.job_id,expected=(2,'changed')),0)
        self.assertTrue(self.wav.exists())

    def test_automatic_expiry_is_opt_in_and_waits_for_recent_work(self):
        self.preference = Preferences(work_retention_days=30)
        self.age()
        os.utime(self.wav,None)
        self.assertEqual(retention.clean_expired_work(self.db),0)
        self.age()
        self.assertEqual(retention.clean_expired_work(self.db),2)

    def test_missing_final_drive_or_failed_copy_preserves_work(self):
        with patch.object(video_storage,'copy_verified',side_effect=OSError('fixture full')):
            self.assertEqual(self.clean(),0)
        self.assertTrue(self.video.exists())
        self.assertTrue(self.wav.exists())
        paths = video_storage.separate_finished_video(self.db,self.db.get_job(self.job_id))
        Path(paths[0]).unlink()
        self.assertEqual(self.clean(),0)
        self.assertTrue(self.wav.exists())

    def test_uncertain_upload_and_linked_project_are_protected(self):
        with self.db.connect() as connection:
            connection.execute("UPDATE publication_targets SET status='unknown' WHERE job_id=?",(self.job_id,))
            connection.commit()
        self.assertEqual(self.clean(),0)
        with patch.object(retention,'linked',return_value=True):
            self.assertEqual(self.clean(),0)
        self.assertTrue(self.wav.exists())

    def test_every_other_mp4_survives_and_new_folder_keeps_previous_end_product(self):
        other = self.work / 'older.mp4'
        other.write_bytes(b'older-keep')
        first = video_storage.separate_finished_video(self.db,self.db.get_job(self.job_id))[0]
        self.preference = Preferences(archive_directory=str(self.root / 'chosen'))
        second = video_storage.separate_finished_video(self.db,self.db.get_job(self.job_id))[0]
        self.assertTrue(Path(first).exists())
        self.assertTrue(Path(second).exists())
        self.assertEqual(self.clean(),2)
        self.assertTrue(other.exists())
