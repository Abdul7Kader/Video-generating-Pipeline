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
from .failures import PipelineFailure,describe

ROOT = Path(__file__).resolve().parents[1]


class OperationCancelled(RuntimeError):
    pass


class Operation:
    def __init__(self):
        self.cancel = threading.Event()
        self.on_progress = None

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
            def current_step():
                try:
                    progress = folder / 'progress.json'
                    if progress.stat().st_size <= 2048:
                        return PipelineFailure.from_wire(json.loads(progress.read_text(encoding='utf-8')))
                except (OSError,ValueError,TypeError):
                    pass
                return PipelineFailure({'image_preview':'image','plan':'planning','render':'render','revise':'script','frame_plan':'planning','frame_revise':'script','frame_draft':'script'}.get(kind,'request'))
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
                last_step = None
                while group.poll(process) is None:
                    self.check()
                    if time.monotonic() >= deadline:
                        raise PipelineFailure(current_step().stage,'timeout',context=current_step().context)
                    step = current_step().public()
                    identity = (step['stage'],json.dumps(step['context'],sort_keys=True))
                    if self.on_progress and identity != last_step:
                        self.on_progress(step)
                        last_step = identity
                    self.cancel.wait(.1)
                self.check()
                if not result.is_file() or result.stat().st_size > 4 * 1024 * 1024:
                    step = current_step()
                    raise PipelineFailure(step.stage,'process_failed',context=step.context)
                try:
                    value = json.loads(result.read_text(encoding='utf-8'))
                except ValueError as error:
                    raise describe(error,current_step().stage) from None
                if not isinstance(value,dict) or not any(key in value for key in ('value','failure','error')):
                    raise PipelineFailure(current_step().stage,'invalid_response')
                if isinstance(value,dict) and isinstance(value.get('failure'),dict):
                    raise PipelineFailure.from_wire(value['failure'])
                if value.get('error'):
                    raise describe(RuntimeError(value['error']),current_step().stage)
                return value['value']


class Operations:
    def __init__(self):
        self.lock = threading.RLock()
        self.active = {}

    @contextmanager
    def start(self, job_id, db, *, allow_frame=False):
        operation = Operation()
        operation.on_progress = lambda step: db.record_event(job_id,'production_step',step['stage_label'],{'stage':step['stage'],'context':step['context']})
        with self.lock:
            job = db.get_job(job_id)
            if not job or job['status'] in {'cancelling', 'cancelled'}:
                raise OperationCancelled('Der Auftrag wurde abgebrochen.')
            from .modes import require_mode
            if not allow_frame:
                require_mode(job.get('generation_mode','animated'))
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
