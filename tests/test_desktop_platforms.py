import unittest
from unittest.mock import patch
from desktop import platforms


class DesktopPlatformTests(unittest.TestCase):
    def test_runtime_paths_separate_systems_and_architectures(self):
        keys = {platforms.runtime_key(system, machine) for system in ['Windows', 'Linux', 'Darwin']
                for machine in ['x86_64', 'arm64']}
        self.assertEqual(len(keys), 6)
        self.assertEqual(platforms.runtime_key('Windows', 'AMD64'), 'win32-x64')
        with self.assertRaises(RuntimeError):
            platforms.runtime_key('Linux', 'armv7l')

    def test_windows_module_is_not_imported_to_choose_linux(self):
        with patch('desktop.platforms.platform.system', return_value='Linux'), patch('desktop.linux_service.ProcessGroup') as group:
            platforms.process_group()
        group.assert_called_once_with()

    def test_macos_does_not_fall_back_to_an_unprotected_process(self):
        with patch('desktop.platforms.platform.system', return_value='Darwin'), patch('desktop.mac_selfcheck.ensure_verified', side_effect=RuntimeError('macOS-Abnahme fehlgeschlagen')), patch('desktop.macos_service.ProcessGroup') as group:
            with self.assertRaisesRegex(RuntimeError, 'macOS-Abnahme'):
                platforms.process_group()
        group.assert_not_called()
