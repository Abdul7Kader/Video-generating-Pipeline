import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from dataclasses import replace

from backend.config import settings
from backend.db import Database
from backend.operations import Operation, OperationCancelled
from tests.test_workflow import VALUES, SCRIPT


class CancellationTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Native private worker protocol')
    def test_private_worker_rejects_any_action_other_than_fixed_production_steps(self):
        with tempfile.TemporaryDirectory() as name, patch('backend.operations.settings', replace(settings, data_dir=Path(name))):
            with self.assertRaisesRegex(RuntimeError, 'Unbekannter Produktionsschritt'):
                Operation().run('shell', {})

    def test_cancelled_work_cannot_be_finished_or_failed_by_a_late_result(self):
        with tempfile.TemporaryDirectory() as name:
            db = Database(Path(name) / 'test.sqlite3')
            db.initialize()
            job_id = db.create_job(VALUES, SCRIPT)
            fingerprint = db.get_job(job_id)['script']['content_hash']
            db.approve_script(job_id, 1, fingerprint)
            db.queue_render(job_id, 1, fingerprint)
            db.claim_render()
            self.assertEqual(db.cancel_production(job_id, running=True)['status'], 'cancelling')
            db.finish_render(job_id, 1, 'must-not-appear.mp4', 'a' * 64, 'piper')
            db.fail_render(job_id, 'late failure')
            self.assertEqual(db.get_job(job_id)['status'], 'cancelling')
            db.finish_cancel(job_id)
            self.assertEqual(db.get_job(job_id)['status'], 'cancelled')
            self.assertIsNone(db.get_job(job_id)['output_path'])
            self.assertEqual(db.get_job(job_id)['script']['content_hash'], fingerprint)

    @unittest.skipUnless(sys.platform == 'win32', 'Real Windows nested job cancellation')
    def test_cancel_ends_only_its_worker_and_grandchild(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            marker = root / 'children.json'
            worker = root / 'worker.py'
            worker.write_text('import json,os,subprocess,sys,time\n'
                'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(120)"])\n'
                f'open({str(marker)!r},"w").write(json.dumps([os.getpid(),p.pid]))\n'
                'time.sleep(120)\n', encoding='utf-8')
            operation, errors = Operation(), []
            unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
            def work():
                try:
                    with patch('backend.operations.settings', replace(settings, data_dir=root)):
                        operation.run('render', {}, worker=worker)
                except Exception as error:
                    errors.append(error)
            thread = threading.Thread(target=work)
            thread.start()
            try:
                deadline = time.monotonic() + 10
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(.05)
                pids = json.loads(marker.read_text())
                operation.cancel.set()
                thread.join(timeout=15)
                self.assertFalse(thread.is_alive())
                self.assertIsInstance(errors[0], OperationCancelled)
                from stop_pipeline import _pid_alive
                self.assertFalse(any(_pid_alive(pid) for pid in pids))
                self.assertIsNone(unrelated.poll())
            finally:
                operation.cancel.set()
                thread.join(timeout=15)
                unrelated.terminate()
                unrelated.wait(timeout=5)
