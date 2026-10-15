from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend import social
from backend.db import Database
from backend.integrations import Preferences
from backend.plan import file_sha256
from backend.publishing import PublicationError, PendingPublication
from tests.test_workflow import VALUES, SCRIPT


class SocialAdapterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.video = Path(self.directory.name) / 'video.mp4'
        self.video.write_bytes(b'fixture-approved-video')
        self.job = {'script':{'title':'Fixture','description':'Beschreibung'},
                    'publication_target':{'approved_output_sha256':file_sha256(self.video)}}

    def upload(self, url, file, **options):
        with file.open('rb') as source:
            source.seek(options.get('start',0))
            options['digest'].update(source.read(options.get('length',file.stat().st_size)))

    def test_facebook_uses_approved_bytes_and_waits_for_publication_confirmation(self):
        config = Preferences(facebook_enabled=True,facebook_page_id='123456789')
        replies = [{'video_id':'987654321','upload_url':'https://rupload.facebook.com/video-upload/v25.0/987654321'},
                   {'success':True},{'status':{'publishing_phase':{'status':'complete'}}}]
        with patch.object(social,'load',return_value=config),patch.object(social.credentials,'get',return_value='fixture-token'),patch.object(social,'upload_file',side_effect=self.upload),patch.object(social,'json_request',side_effect=replies) as call:
            result = social.publish_facebook(self.job,self.video)
        self.assertEqual(result,('987654321','https://www.facebook.com/reel/987654321'))
        self.assertEqual(call.call_args_list[1].args[4]['video_state'],'PUBLISHED')
        self.assertNotIn('access_token',call.call_args_list[0].args[2])

    def test_instagram_uploads_local_file_without_public_media_server(self):
        config = Preferences(instagram_enabled=True,instagram_account_id='123456789')
        replies = [{'id':'987654321','uri':'https://rupload.facebook.com/ig-api-upload/v25.0/987654321'},
                   {'status_code':'FINISHED'},{'id':'123123123'},{'permalink':'https://www.instagram.com/reel/fixture/'}]
        with patch.object(social,'load',return_value=config),patch.object(social.credentials,'get',return_value='fixture-token'),patch.object(social,'upload_file',side_effect=self.upload),patch.object(social,'json_request',side_effect=replies) as call:
            result = social.publish_instagram(self.job,self.video)
        self.assertEqual(result[0],'123123123')
        initial = call.call_args_list[0]
        self.assertEqual(initial.args[0],'graph.instagram.com')
        self.assertEqual(initial.args[4]['upload_type'],'resumable')
        self.assertNotIn('video_url',initial.args[4])

    def test_tiktok_only_hands_off_to_inbox_and_never_claims_publication(self):
        replies = [{'data':{'publish_id':'draft-fixture','upload_url':'https://open-upload.tiktokapis.com/video/?upload_id=fixture'}},
                   {'data':{'status':'SEND_TO_USER_INBOX'}}]
        with patch.object(social,'load',return_value=Preferences(tiktok_enabled=True)),patch.object(social.credentials,'get',side_effect=lambda name:'fixture-token' if name == 'tiktok_access_token' else ''),patch.object(social,'upload_file',side_effect=self.upload),patch.object(social,'json_request',side_effect=replies) as call:
            result = social.upload_tiktok_draft(self.job,self.video)
        self.assertIsInstance(result,PendingPublication)
        self.assertEqual(call.call_args_list[0].args[2],'/v2/post/publish/inbox/video/init/')
        self.assertNotIn('video_url',call.call_args_list[0].args[4]['source_info'])
        self.assertIn('noch nicht',result.message)

    def test_provider_upload_url_cannot_leak_tokens_to_another_host_or_local_port(self):
        for url in ['http://rupload.facebook.com/video-upload/x','https://evil.test/video-upload/x',
                    'https://rupload.facebook.com@127.0.0.1:8080/video-upload/x',
                    'https://rupload.facebook.com.evil.test/video-upload/x']:
            with patch.object(social.http.client,'HTTPSConnection') as connection:
                with self.assertRaises(PublicationError):
                    social.upload_file(url,self.video,host='rupload.facebook.com',prefix='/video-upload/',token='never-exposed')
                connection.assert_not_called()

    def test_database_keeps_inbox_delivery_pending_and_never_reclaims_it(self):
        db = Database(Path(self.directory.name) / 'test.sqlite3')
        db.initialize()
        job_id = db.create_job({**VALUES,'aspect_ratios':['9:16'],'target_platform':'tiktok','target_platforms':['tiktok']},SCRIPT)
        digest = db.get_job(job_id)['script']['content_hash']
        db.approve_script(job_id,1,digest)
        db.queue_render(job_id,1,digest)
        db.finish_render(job_id,1,'fixture.mp4',file_sha256(self.video),'fixture')
        db.approve_video(job_id,1,file_sha256(self.video),{'tiktok'})
        self.assertEqual(db.claim_publication()['publication_target']['platform'],'tiktok')
        db.finish_publication(job_id,'tiktok','draft-fixture',None,awaiting_user=True,notice='In TikTok bestätigen')
        job = db.get_job(job_id)
        self.assertEqual(job['status'],'publish_pending')
        self.assertEqual(job['publication_targets'][0]['status'],'awaiting_user')
        self.assertIsNone(db.claim_publication())
        with patch.object(social,'load',return_value=Preferences(tiktok_enabled=True)),patch.object(social.credentials,'get',return_value='fixture-token'),patch.object(social,'json_request',return_value={'data':{'status':'PUBLISH_COMPLETE'}}) as call,patch.object(social,'upload_file') as upload:
            social.check_pending(db,job_id)
        self.assertEqual(call.call_args.args[2],'/v2/post/publish/status/fetch/')
        upload.assert_not_called()
        self.assertEqual(db.get_job(job_id)['publication_targets'][0]['status'],'published')
        self.assertIsNone(db.pending_confirmation(job_id))

    def test_instagram_missing_publication_id_is_uncertain_and_not_retryable(self):
        config = Preferences(instagram_enabled=True,instagram_account_id='123456789')
        replies = [{'id':'987654321','uri':'https://rupload.facebook.com/ig-api-upload/v25.0/987654321'}, {'status_code':'FINISHED'},{}]
        with patch.object(social,'load',return_value=config),patch.object(social.credentials,'get',return_value='fixture-token'),patch.object(social,'upload_file',side_effect=self.upload),patch.object(social,'json_request',side_effect=replies):
            with self.assertRaises(PublicationError) as result:
                social.publish_instagram(self.job,self.video)
        self.assertTrue(result.exception.uncertain)
        self.assertEqual(result.exception.remote_id,'987654321')

    def test_unconfirmed_publication_retains_remote_reference_without_retry(self):
        config = Preferences(facebook_enabled=True,facebook_page_id='123456789')
        with patch.object(social,'load',return_value=config),patch.object(social.credentials,'get',return_value='fixture-token'),patch.object(social,'upload_file',side_effect=self.upload),patch.object(social,'json_request',side_effect=[{'video_id':'987654321','upload_url':'https://rupload.facebook.com/video-upload/v25.0/987654321'},{'success':True},PublicationError('status query failed')]):
            with self.assertRaises(PublicationError) as result:
                social.publish_facebook(self.job,self.video)
        self.assertTrue(result.exception.uncertain)
        self.assertEqual(result.exception.remote_id,'987654321')
