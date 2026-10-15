"""Real Windows descendants must die with their owning desktop group."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from stop_pipeline import _pid_alive


@unittest.skipUnless(os.name == 'nt', 'Windows Job Objects')
class DesktopProcessTests(unittest.TestCase):
    def run_tree(self, crash):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = root / 'children.json'
            child = root / 'child.py'
            child.write_text(
                'import subprocess, sys, time, json, os\n'
                'p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])\n'
                f'open({str(record)!r}, "w").write(json.dumps([os.getpid(), p.pid]))\n'
                'time.sleep(120)\n', encoding='utf-8')
            supervisor = root / 'supervisor.py'
            supervisor.write_text(
                'import sys, time\n'
                f'sys.path.insert(0, {str(Path(__file__).resolve().parents[1])!r})\n'
                'from desktop.windows_job import ProcessGroup\n'
                'with ProcessGroup() as group:\n'
                f'    child = group.start([sys.executable, {str(child)!r}], cwd={str(root)!r})\n'
                '    print("ready", flush=True)\n'
                '    sys.stdin.readline()\n', encoding='utf-8')
            process = subprocess.Popen([sys.executable, str(supervisor)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            pids = []
            unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
            try:
                self.assertEqual(process.stdout.readline().strip(), 'ready')
                deadline = time.monotonic() + 8
                while not record.exists() and time.monotonic() < deadline:
                    time.sleep(.05)
                pids = json.loads(record.read_text())
                self.assertTrue(all(_pid_alive(pid) for pid in pids))
                if crash:
                    process.kill()
                else:
                    process.stdin.write('close\n')
                    process.stdin.flush()
                self.assertEqual(process.wait(timeout=10), 1 if crash else 0)
                deadline = time.monotonic() + 8
                while any(_pid_alive(pid) for pid in pids) and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(all(not _pid_alive(pid) for pid in pids), 'Kind und Enkel müssen beendet sein')
                self.assertIsNone(unrelated.poll(), 'Fremde Prozesse dürfen nicht beendet werden')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                process.stdin.close()
                process.stdout.close()
                unrelated.terminate()
                unrelated.wait(timeout=5)

    def test_normal_close_removes_children_and_grandchildren(self):
        self.run_tree(False)

    def test_supervisor_crash_removes_children_and_grandchildren(self):
        self.run_tree(True)

    def test_assignment_failure_never_runs_the_child(self):
        from desktop.windows_job import ProcessGroup
        with tempfile.TemporaryDirectory() as directory, ProcessGroup() as group:
            marker = Path(directory) / 'must-not-exist'
            with patch.object(group.kernel, 'AssignProcessToJobObject', return_value=False):
                with self.assertRaises(OSError):
                    group.start([sys.executable, '-c', 'from pathlib import Path; import sys; Path(sys.argv[1]).touch()', str(marker)], cwd=directory)
            self.assertFalse(marker.exists(), 'Ohne Prozessüberwachung darf kein Anwendungscode laufen')


if __name__ == '__main__':
    unittest.main()
