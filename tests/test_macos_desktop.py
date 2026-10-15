import ctypes
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from desktop.macos_service import launch_spec
from desktop.posix_registry import BsdInfo
from backend.process_control import owned_command


class MacDesktopContractTests(unittest.TestCase):
    def test_launchd_job_is_session_local_without_saved_environment_or_login_agent(self):
        value = launch_spec('org.videopipeline.session-test', Path('/tmp/private-test'))
        self.assertEqual(value['KeepAlive'], {'SuccessfulExit': False})
        self.assertFalse(value['AbandonProcessGroup'])
        self.assertNotIn('EnvironmentVariables', value)
        self.assertEqual(ctypes.sizeof(BsdInfo), 136)

    def test_macos_new_sessions_are_wrapped_before_execution(self):
        with patch('backend.process_control.sys.platform', 'darwin'), patch.dict('os.environ',
                {'PIPELINE_PROCESS_REGISTRY': '/private/registry', 'PIPELINE_CHILD_PYTHON': sys.executable}), patch('backend.process_control.shutil.which', return_value='/usr/bin/tool'):
            result = owned_command(['tool', 'argument with spaces'])
        self.assertEqual(result[:2], [sys.executable, '-I'])
        self.assertTrue(result[2].endswith('desktop/mac_child.py') or result[2].endswith('desktop\\mac_child.py'))
        self.assertEqual(result[3:], ['/usr/bin/tool', 'argument with spaces'])

    def test_other_systems_do_not_change_worker_commands(self):
        command = ['tool', 'value']
        with patch('backend.process_control.sys.platform', 'linux'):
            self.assertIs(owned_command(command), command)

    @unittest.skipUnless(sys.platform == 'darwin', 'Native launchd GUI-session acceptance')
    def test_native_guard_removes_detached_children_and_survives_launcher_crash(self):
        from desktop.mac_selfcheck import verify
        verify()
