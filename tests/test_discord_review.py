from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from backend.config import settings
from backend.db import Database
from backend.discord_review import DiscordReviewService
from backend.discord_http import DiscordError
from backend.integrations import Preferences
from backend.plan import file_sha256
from tests.test_workflow import VALUES, SCRIPT


class DiscordReviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.db = Database(self.root / 'test.sqlite3')
        self.db.initialize()
        self.job = self.db.create_job(VALUES,SCRIPT)
        fingerprint = self.db.get_job(self.job)['script']['content_hash']
        self.db.approve_script(self.job,1,fingerprint)
        self.db.queue_render(self.job,1,fingerprint)
        self.file = self.root / 'jobs' / self.job / 'v1/video.mp4'
        self.file.parent.mkdir(parents=True)
        self.file.write_bytes(b'fixture-video-not-a-real-render')
        self.db.finish_render(self.job,1,str(self.file.relative_to(self.root / 'jobs')),file_sha256(self.file),'fixture')
        self.preference = Preferences(discord_enabled=True,discord_guild_id='111111111111111111',
            discord_channel_id='222222222222222222',discord_approver_ids=['333333333333333333'],publish_targets=['youtube'])
        self.approve = Mock(side_effect=lambda job,action:self.db.approve_video(job,action.expected_version,action.expected_hash,{'youtube'},action.target_platforms))
        self.service = DiscordReviewService(self.db,self.approve,Mock())
        self.ticket = self.service.reviews.enqueue(self.job,self.preference)
        self.service.reviews.transition(self.ticket['id'],{'queued'},'sent',message_id='444444444444444444')
        self.packet = {'id':'555555555555555555','token':'fixture-token','application_id':'666666666666666666',
            'type':3,'guild_id':self.preference.discord_guild_id,'channel_id':self.preference.discord_channel_id,
            'member':{'user':{'id':self.preference.discord_approver_ids[0]}},'message':{'id':'444444444444444444'},
            'data':{'custom_id':f"vp:{self.ticket['id']}:approve"}}
        self.patch = patch('backend.discord_review.load',return_value=self.preference)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_foreign_actor_channel_or_message_can_never_approve(self):
        import copy
        for field in ('actor','channel','message'):
            packet = copy.deepcopy(self.packet)
            if field == 'actor': packet['member']['user']['id'] = '777777777777777777'
            if field == 'channel': packet['channel_id'] = '777777777777777777'
            if field == 'message': packet['message']['id'] = '777777777777777777'
            with patch('backend.discord_review.request'):
                self.service.handle(packet)
        self.approve.assert_not_called()
        self.assertEqual(self.service.reviews.get(self.ticket['id'])['state'],'sent')

    def test_approval_is_exactly_once_and_never_for_changed_channels(self):
        with patch('backend.discord_review.request'):
            self.preference.connection_revision = 1
            self.service.handle(self.packet)
            self.approve.assert_not_called()
            self.preference.connection_revision = 0
            self.service.handle(self.packet)
            self.service.handle(self.packet)
        self.approve.assert_called_once()
        self.assertEqual(self.service.reviews.get(self.ticket['id'])['state'],'approved')
        self.assertEqual(self.db.get_job(self.job)['status'],'publish_queued')

    def test_rejection_retains_local_file_without_publication(self):
        self.packet['data']['custom_id'] = f"vp:{self.ticket['id']}:reject"
        with patch('backend.discord_review.request'):
            self.service.handle(self.packet)
        self.approve.assert_not_called()
        self.assertEqual(self.db.get_job(self.job)['status'],'video_rejected')
        self.assertTrue(self.file.exists())

    def test_changed_attachment_or_uncertain_send_cannot_be_silently_retried(self):
        self.service.reviews.transition(self.ticket['id'],{'sent'},'sending')
        self.file.write_bytes(b'changed')
        with patch('backend.discord_review.settings',replace(settings,data_dir=self.root)), patch('backend.discord_review.request') as send:
            with self.assertRaises(DiscordError):
                self.service.send(self.service.reviews.get(self.ticket['id']))
            send.assert_not_called()
        self.service.reviews.recover()
        self.assertEqual(self.service.reviews.get(self.ticket['id'])['state'],'unknown')
        self.assertIsNone(self.service.reviews.claim())

    def test_feedback_only_queues_ai_revision_and_requires_another_text_and_video_approval(self):
        self.packet['type'] = 5
        self.packet.pop('message')
        self.packet['data'] = {'custom_id':f"vp:{self.ticket['id']}:feedback:{self.preference.discord_approver_ids[0]}",
            'components':[{'components':[{'custom_id':'instructions','value':'Zeige die Katze deutlicher.'}]}]}
        with patch('backend.discord_review.request'):
            self.service.handle(self.packet)
        self.approve.assert_not_called()
        ticket = self.service.reviews.get(self.ticket['id'])
        self.assertEqual(ticket['state'],'revision_requested')
        self.assertEqual(ticket['instructions'],'Zeige die Katze deutlicher.')
        self.assertEqual(self.db.get_job(self.job)['status'],'video_review')

    def test_revision_produces_a_new_text_review_before_any_new_render_or_publication(self):
        import copy
        self.service.reviews.transition(self.ticket['id'],{'sent'},'revision_requested',instructions='Mehr Details zur Katze.')
        ticket = self.service.reviews.claim()
        revised = copy.deepcopy(SCRIPT)
        revised['scenes'][0]['narration'] += ' Die Katze ist deutlich zu sehen.'
        with patch('backend.operations.Operation.run',return_value=revised):
            self.service.process(ticket)
        latest = self.service.reviews.latest(self.job)
        self.assertEqual(latest['kind'],'script')
        self.assertEqual(latest['state'],'queued')
        self.assertEqual(latest['version'],2)
        self.assertEqual(self.db.get_job(self.job)['status'],'script_review')
        self.approve.assert_not_called()
        self.service.plan.assert_not_called()
        self.assertTrue(self.file.exists())
