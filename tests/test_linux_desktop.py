"""Linux containment must include descendants that create new sessions."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux user-service runtime')
class LinuxDesktopTests(unittest.TestCase):
    def test_clean_child_exit_preserves_success_while_parent_pipe_is_open(self):
        from desktop.linux_service import ProcessGroup
        with tempfile.TemporaryDirectory() as folder, ProcessGroup() as group:
            child = group.start([sys.executable, '-c', 'pass'], cwd=Path(folder))
            self.assertEqual(group.wait(child), 0)

    def check_tree(self, crash, separate_scope=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record = root / 'children.json'
            worker = root / 'worker.py'
            worker.write_text(
                'import subprocess, sys, os, json, time\n'
                'p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], start_new_session=True)\n'
                f'open({str(record)!r}, "w").write(json.dumps([os.getpid(), p.pid]))\n'
                'time.sleep(120)\n', encoding='utf-8')
            supervisor = root / 'supervisor.py'
            command = [sys.executable, str(worker)]
            if separate_scope:
                command = ['/usr/bin/systemd-run', '--user', '--scope', '--quiet', '--collect',
                           '--unit=video-pipeline-test-' + uuid.uuid4().hex + '.scope', *command]
            supervisor.write_text(
                'import sys\n'
                f'sys.path.insert(0, {str(Path(__file__).resolve().parents[1])!r})\n'
                'from desktop.linux_service import ProcessGroup\n'
                'with ProcessGroup() as group:\n'
                f'    child = group.start({command!r}, cwd={str(root)!r})\n'
                '    print("ready", flush=True)\n'
                '    sys.stdin.readline()\n', encoding='utf-8')
            process = subprocess.Popen([sys.executable, str(supervisor)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
            pids = []
            try:
                self.assertEqual(process.stdout.readline().strip(), 'ready')
                deadline = time.monotonic() + 8
                while not record.exists() and time.monotonic() < deadline:
                    time.sleep(.05)
                pids = json.loads(record.read_text())
                self.assertNotEqual(os.getsid(pids[0]), os.getsid(pids[1]), 'Fixture must detach into another session')
                if crash:
                    process.kill()
                else:
                    process.stdin.write('close\n')
                    process.stdin.flush()
                process.wait(timeout=15)
                deadline = time.monotonic() + 8
                while any(Path(f'/proc/{pid}').exists() for pid in pids) and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(all(not Path(f'/proc/{pid}').exists() for pid in pids), pids)
                self.assertIsNone(unrelated.poll(), 'Foreign process must survive')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                process.stdin.close()
                process.stdout.close()
                unrelated.terminate()
                unrelated.wait(timeout=5)

    def test_normal_close_removes_detached_descendants(self):
        self.check_tree(False)

    def test_launcher_crash_removes_detached_descendants(self):
        self.check_tree(True)

    def test_close_also_removes_children_moved_into_a_portal_scope(self):
        self.check_tree(False, separate_scope=True)

    def test_launcher_crash_also_removes_children_moved_into_a_portal_scope(self):
        self.check_tree(True, separate_scope=True)


if __name__ == '__main__':
    unittest.main()
