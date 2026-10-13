import builtins
import unittest
from unittest.mock import patch

import setup_pipeline


class BootstrapTests(unittest.TestCase):
    def test_existing_runtime_starts_without_installing_or_requesting_permission(self):
        with patch('setup_pipeline.subprocess.call',return_value=0) as start,patch('setup_pipeline.subprocess.run') as install,patch('builtins.input',side_effect=AssertionError('not needed')):
            self.assertEqual(setup_pipeline.main(),0)
        self.assertTrue(start.call_args.args[0][-1].endswith('start_pipeline.py'))
        install.assert_not_called()

    def test_declining_first_run_does_not_install_anything(self):
        original=builtins.__import__
        def missing(name,*args,**kwargs):
            if name=='fastapi':raise ImportError('missing')
            return original(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=missing),patch('builtins.input',return_value='n'),patch('setup_pipeline.subprocess.run') as install,patch('setup_pipeline.subprocess.call') as start:
            self.assertEqual(setup_pipeline.main(),1)
        install.assert_not_called();start.assert_not_called()
