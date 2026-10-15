"""Private stdio lifecycle channel. No extra HTTP control endpoint or port."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class DesktopControl:
    def __init__(self, server, app, db, manager, *, output=None):
        self.server, self.app, self.db, self.manager = server, app, db, manager
        self.output = output or sys.stdout
        self.draining = False
        self.output_lock = threading.Lock()

    def emit(self, value):
        with self.output_lock:
            self.output.write('PIPELINE_DESKTOP ' + json.dumps(value) + '\n')
            self.output.flush()

    def status(self):
        with self.manager.lock:
            requests, setup = self.manager.production_requests, self.manager.busy
        jobs = sum(job['status'] in {'rendering', 'publishing'} for job in self.db.list_jobs())
        return {'busy': bool(requests or setup or jobs), 'requests': requests,
                'setup': bool(setup), 'jobs': jobs, 'draining': self.draining}

    def handle(self, value):
        if (not isinstance(value, dict) or set(value) != {'id', 'command'}
                or not isinstance(value['id'], str) or not re.fullmatch(r'[0-9]{1,9}', value['id'])
                or value['command'] not in {'status', 'drain', 'abort'}):
            raise ValueError('Ungültiger Desktop-Steuerbefehl')
        if value['command'] != 'status':
            with self.app.state.worker_claim_lock, self.manager.lock:
                self.app.state.shutdown_requested.set()
                self.draining = True
            if value['command'] == 'abort':
                self.manager.cancel.set()
                self.server.should_exit = True
        self.emit({'type': 'reply', 'id': value['id'], **self.status()})

    def finish_if_idle(self):
        if self.draining and not self.status()['busy']:
            self.server.should_exit = True
            return True
        return False

    def read_commands(self):
        try:
            while line := sys.stdin.readline(4097):
                if len(line) > 4096:
                    break
                self.handle(json.loads(line))
        except (OSError, ValueError, TypeError):
            pass
        # Loss of the parent pipe must never leave a standalone server.
        self.app.state.shutdown_requested.set()
        self.server.should_exit = True

    def watch_drain(self):
        while not self.server.should_exit:
            if self.finish_if_idle():
                return
            time.sleep(.25)


def main():
    from start_pipeline import main as start

    def attach(server, port):
        from backend.main import app, db, setup
        app.state.desktop_mode = True
        control = DesktopControl(server, app, db, setup.manager)
        threading.Thread(target=control.read_commands, daemon=True).start()
        threading.Thread(target=control.watch_drain, daemon=True).start()
        control.emit({'type': 'starting', 'port': port})

    return start(open_browser=False, exclusive=True, on_server=attach)


if __name__ == '__main__':
    raise SystemExit(main())
