"""One cancellable native process group per production operation, never global kills."""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import sys
import tempfile
import threading
import time

from .config import settings

ROOT = Path(__file__).resolve().parents[1]


class OperationCancelled(RuntimeError):
    pass


class Operation:
    def __init__(self):
        self.cancel = threading.Event()

    def check(self):
        if self.cancel.is_set():
            raise OperationCancelled('Die Erstellung wurde abgebrochen. Gespeicherte Dateien bleiben erhalten.')

    def run(self, kind, payload, *, worker=None, timeout=7200):
        from desktop.platforms import process_group
        self.check()
        directory = settings.data_dir / 'operations'
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='operation-', dir=directory) as name:
            folder = Path(name)
            folder.chmod(0o700)
            request, result = folder / 'request.json', folder / 'result.json'
            request.write_text(json.dumps({'kind': kind, 'payload': payload}), encoding='utf-8')
            request.chmod(0o600)
            environment = dict(os.environ)
            # A nested native group supplies its own private registration values.
            for key in ('PIPELINE_PROCESS_REGISTRY', 'PIPELINE_CHILD_PYTHON', 'PIPELINE_BROWSER_WRAPPER', 'PIPELINE_REAL_BROWSER'):
                environment.pop(key, None)
            with process_group() as group:
                process = group.start([sys.executable, '-I', str(worker or ROOT / 'backend/operation_worker.py'),
                                       str(request), str(result)], cwd=ROOT, env=environment)
                deadline = time.monotonic() + timeout
                while group.poll(process) is None:
                    self.check()
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Das Zeitlimit dieses Vorgangs wurde erreicht; seine Prozesse werden beendet.')
                    self.cancel.wait(.1)
                self.check()
                if not result.is_file() or result.stat().st_size > 4 * 1024 * 1024:
                    raise RuntimeError('Die Erstellung endete ohne vollständiges Ergebnis. Vorhandene Dateien bleiben erhalten.')
                value = json.loads(result.read_text(encoding='utf-8'))
                if value.get('error'):
                    raise RuntimeError(value['error'])
                return value['value']


class Operations:
    def __init__(self):
        self.lock = threading.RLock()
        self.active = {}

    @contextmanager
    def start(self, job_id, db):
        operation = Operation()
        with self.lock:
            job = db.get_job(job_id)
            if not job or job['status'] in {'cancelling', 'cancelled'}:
                raise OperationCancelled('Der Auftrag wurde abgebrochen.')
            if job_id in self.active:
                raise RuntimeError('Dieser Auftrag wird bereits bearbeitet.')
            self.active[job_id] = operation
        try:
            yield operation
        finally:
            with self.lock:
                if operation.cancel.is_set():
                    db.finish_cancel(job_id)
                self.active.pop(job_id, None)

    def cancel(self, job_id, db):
        with self.lock:
            active = self.active.get(job_id)
            result = db.cancel_production(job_id, running=active is not None)
            if active:
                active.cancel.set()
            return result


operations = Operations()
