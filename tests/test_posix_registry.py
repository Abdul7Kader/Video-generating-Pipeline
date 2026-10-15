import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == 'posix', 'POSIX process registration')
class PosixRegistryTests(unittest.TestCase):
    def test_group_waits_for_guard_before_exec_and_foreign_process_survives(self):
        from desktop.posix_registry import acknowledge, cleanup, private_directory
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / 'groups'
            registry.mkdir(mode=0o700)
            marker = root / 'executed'
            env = {**os.environ, 'PIPELINE_PROCESS_REGISTRY': str(registry)}
            command = [sys.executable, '-I', str(Path(__file__).resolve().parents[1] / 'desktop/mac_child.py'),
                       sys.executable, '-c', 'import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch(); time.sleep(120)', str(marker)]
            process = subprocess.Popen(command, env=env, start_new_session=True)
            unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
            try:
                deadline = time.monotonic() + 5
                while not list(registry.glob('*.json')) and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertFalse(marker.exists(), 'No execution before ownership acknowledgement')
                acknowledge(private_directory(registry))
                deadline = time.monotonic() + 3
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(marker.exists())
                cleanup(registry)
                process.wait(timeout=5)
                self.assertIsNone(unrelated.poll())
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                unrelated.terminate()
                unrelated.wait(timeout=5)

    def test_reused_pid_is_not_signalled(self):
        from desktop.posix_registry import signal_owned
        record = {'pid': 12345, 'pgid': 12345, 'uid': os.getuid(), 'birth': [1, 2]}
        with patch('desktop.posix_registry.identity', return_value={**record, 'birth': [3, 4]}), patch('desktop.posix_registry.os.killpg') as kill:
            self.assertFalse(signal_owned(record, 9))
        kill.assert_not_called()

    def test_public_registry_is_rejected(self):
        from desktop.posix_registry import private_directory
        with tempfile.TemporaryDirectory() as directory:
            os.chmod(directory, 0o755)
            with self.assertRaises(RuntimeError):
                private_directory(directory)


if __name__ == '__main__':
    unittest.main()
