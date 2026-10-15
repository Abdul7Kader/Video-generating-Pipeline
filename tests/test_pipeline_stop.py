from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import asyncio
from unittest.mock import patch
from pathlib import Path

from start_pipeline import _watch_for_stop, _managed_instance_alive
from stop_pipeline import _pid_alive, stop_managed


class PipelineStopTests(unittest.TestCase):
    def test_running_separate_python_process_is_recognized(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
        try:
            self.assertTrue(_pid_alive(process.pid))
            self.assertIsNone(process.poll(), "Existenzprüfung darf den Prozess nicht beenden")
        finally:
            process.terminate()
            process.wait(timeout=5)

    def test_stop_signal_asks_server_to_exit(self):
        class Server:
            should_exit = False

        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "stop-request"
            server = Server()
            stop_claiming = threading.Event()
            watcher = threading.Thread(
                target=_watch_for_stop, args=(server, request, "test-token"),
                kwargs={"interval": 0.01, 'on_stop':stop_claiming.set}, daemon=True,
            )
            watcher.start()
            request.write_text("wrong-token", encoding="utf-8")
            time.sleep(0.05)
            self.assertFalse(server.should_exit)
            request.write_text("test-token", encoding="utf-8")
            watcher.join(timeout=1)
            self.assertTrue(server.should_exit)
            self.assertTrue(stop_claiming.is_set())

    def test_live_managed_instance_blocks_restart_even_without_a_listener(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path=root/f'pipeline-8123-{os.getpid()}.json'
            path.write_text(json.dumps({'pid':os.getpid(),'port':8123,'token':'a'*32}),encoding='utf-8')
            self.assertTrue(_managed_instance_alive(root,8123))
            self.assertFalse(_managed_instance_alive(root,8124))
            self.assertTrue(_managed_instance_alive(root,None))

    def test_reused_pid_cannot_block_or_receive_a_stop_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / f'pipeline-8123-{os.getpid()}.json'
            path.write_text(json.dumps({'pid': os.getpid(), 'port':8123, 'token':'a'*32,
                                        'process_started_ns':1}), encoding='utf-8')
            self.assertFalse(_managed_instance_alive(root,8123))
            self.assertEqual(stop_managed(root,port=8123,timeout=.01), (0,1,0))
            self.assertFalse((root / ('stop-'+'a'*32+'.request')).exists())

    def test_stopped_worker_cannot_claim_another_job(self):
        from backend import main
        shutdown=threading.Event()
        shutdown.set()
        with patch.object(main.app.state,'shutdown_requested',shutdown), patch.object(main.db,'claim_render') as render, patch.object(main.db,'claim_publication') as publish:
            asyncio.run(main.render_worker(asyncio.Event()))
        render.assert_not_called()
        publish.assert_not_called()

    def test_stop_targets_only_matching_managed_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            owned = root / f"pipeline-8123-{os.getpid()}.json"
            other = root / f"pipeline-8124-{os.getpid()}.json"
            owned.write_text(json.dumps({"pid": os.getpid(), "port": 8123, "token": "a" * 32}), encoding="utf-8")
            other.write_text(json.dumps({"pid": os.getpid(), "port": 8124, "token": "b" * 32}), encoding="utf-8")

            def acknowledge():
                request = root / ("stop-" + "a" * 32 + ".request")
                until = time.monotonic() + 2
                while not request.exists() and time.monotonic() < until:
                    time.sleep(0.01)
                if request.exists():
                    owned.unlink()

            thread = threading.Thread(target=acknowledge, daemon=True)
            thread.start()
            result = stop_managed(root, port=8123, timeout=1)
            thread.join(timeout=1)
            self.assertEqual(result, (1, 0, 0))
            self.assertTrue(other.exists())
            self.assertFalse((root / ("stop-" + "b" * 32 + ".request")).exists())

    def test_stale_process_record_is_removed_without_signalling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stale = root / "pipeline-8123-99999999.json"
            stale.write_text(json.dumps({"pid": 99999999, "port": 8123, "token": "c" * 32}), encoding="utf-8")
            result = stop_managed(root, timeout=0.1)
            self.assertEqual(result, (0, 1, 0))
            self.assertFalse(stale.exists())
            self.assertFalse((root / ("stop-" + "c" * 32 + ".request")).exists())


if __name__ == "__main__":
    unittest.main()
