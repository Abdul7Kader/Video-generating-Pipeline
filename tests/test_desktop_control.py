import io
import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock


class DesktopControlTests(unittest.TestCase):
    def controller(self):
        from desktop.backend import DesktopControl
        app = SimpleNamespace(state=SimpleNamespace(shutdown_requested=threading.Event(), worker_claim_lock=threading.Lock()))
        manager = SimpleNamespace(lock=threading.RLock(), busy=False, production_requests=0, cancel=threading.Event())
        db = Mock()
        db.list_jobs.return_value = []
        output = io.StringIO()
        server = SimpleNamespace(should_exit=False)
        control = DesktopControl(server, app, db, manager, output=output)
        return control, server, app, manager, db, output

    def test_drain_blocks_new_work_and_waits_for_all_kinds_of_work(self):
        control, server, app, manager, db, output = self.controller()
        manager.production_requests = 1
        control.handle({'id': '1', 'command': 'drain'})
        self.assertTrue(app.state.shutdown_requested.is_set())
        self.assertFalse(control.finish_if_idle())
        self.assertFalse(server.should_exit)
        manager.production_requests = 0
        db.list_jobs.return_value = [{'status': 'rendering'}]
        self.assertFalse(control.finish_if_idle())
        db.list_jobs.return_value = []
        manager.busy = True
        self.assertFalse(control.finish_if_idle())
        manager.busy = False
        self.assertTrue(control.finish_if_idle())
        self.assertTrue(server.should_exit)

    def test_abort_cancels_setup_and_stops_accepting_work(self):
        control, server, app, manager, db, output = self.controller()
        control.handle({'id': '2', 'command': 'abort'})
        self.assertTrue(server.should_exit)
        self.assertTrue(manager.cancel.is_set())
        self.assertTrue(app.state.shutdown_requested.is_set())

    def test_protocol_does_not_accept_arbitrary_operations(self):
        control, server, app, manager, db, output = self.controller()
        with self.assertRaises(ValueError):
            control.handle({'id': '3', 'command': 'shell', 'path': 'anything'})
        self.assertFalse(server.should_exit)
        self.assertFalse(app.state.shutdown_requested.is_set())

    def test_shutdown_rejects_new_http_work(self):
        import asyncio
        from unittest.mock import patch
        from backend import main
        from tests.test_settings_api import request
        shutdown = threading.Event()
        shutdown.set()
        with patch.object(main.app.state, 'shutdown_requested', shutdown):
            status, value = asyncio.run(request('POST', '/api/jobs', {'topic': 'must not start'}))
        self.assertEqual(status, 503)
        self.assertIn('beendet', value['detail'])


if __name__ == '__main__':
    unittest.main()
