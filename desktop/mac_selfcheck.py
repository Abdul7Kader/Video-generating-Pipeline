"""On-device verification before the macOS guard is allowed to launch the UI."""
from pathlib import Path
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.posix_registry import identity


def fingerprint():
    digest = hashlib.sha256((platform.platform() + sys.version + sys.executable).encode())
    for name in ['macos_service.py', 'mac_host.py', 'mac_child.py', 'posix_registry.py', 'mac_selfcheck.py']:
        digest.update(Path(__file__).with_name(name).read_bytes())
    for path in [ROOT / 'backend/process_control.py', ROOT / 'renderer/browser.mjs']:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def fixture(record):
    from desktop.macos_service import ProcessGroup
    with ProcessGroup() as group:
        worker = ROOT / 'desktop/mac_child.py'
        child_ready = record.with_suffix('.ready')
        command = [sys.executable, '-c',
            'import os,subprocess,sys,time,json,pathlib\n'
            'p=subprocess.Popen([sys.executable,"-I",sys.argv[1],sys.executable,"-c","import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch(); time.sleep(120)",sys.argv[3]],start_new_session=True)\n'
            'deadline=time.monotonic()+8\n'
            'while not pathlib.Path(sys.argv[3]).exists() and time.monotonic()<deadline: time.sleep(.02)\n'
            'assert pathlib.Path(sys.argv[3]).exists(), "Detached test worker was not acknowledged"\n'
            'open(sys.argv[2],"w").write(json.dumps([os.getpid(),p.pid]))\n'
            'time.sleep(120)\n',
            str(worker), str(record), str(child_ready)]
        group.start(command, cwd=ROOT)
        print('ready', flush=True)
        sys.stdin.readline()


def verify():
    with tempfile.TemporaryDirectory(prefix='video-pipeline-check-', dir='/tmp') as directory:
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
        try:
            for crash in (False, True):
                record = Path(directory) / ('crash.json' if crash else 'normal.json')
                with subprocess.Popen([sys.executable, '-I', str(Path(__file__).resolve()), '--fixture', str(record)],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as process:
                    if process.stdout.readline().strip() != 'ready':
                        raise RuntimeError('Die macOS-Prozessüberwachung konnte nicht geprüft werden.')
                    deadline = time.monotonic() + 10
                    while not record.exists() and time.monotonic() < deadline:
                        time.sleep(.05)
                    pids = json.loads(record.read_text())
                    if not all(identity(pid) for pid in pids):
                        raise RuntimeError('Die macOS-Testprozesse wurden nicht bereit.')
                    if crash:
                        process.kill()
                    else:
                        process.stdin.write('close\n')
                        process.stdin.flush()
                    process.wait(timeout=15)
                    deadline = time.monotonic() + 10
                    while any(identity(pid) for pid in pids) and time.monotonic() < deadline:
                        time.sleep(.05)
                    if any(identity(pid) for pid in pids) or unrelated.poll() is not None:
                        raise RuntimeError('Die macOS-Prozessabnahme ist fehlgeschlagen. Die Desktop-App bleibt gesperrt.')
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=5)


def ensure_verified():
    from desktop.platforms import runtime_directory
    cache = runtime_directory() / 'guard-check.json'
    expected = fingerprint()
    try:
        if json.loads(cache.read_text()).get('fingerprint') == expected:
            return
    except (OSError, ValueError, AttributeError):
        pass
    verify()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({'fingerprint': expected, 'checked_at': time.time()}), encoding='utf-8')
    cache.chmod(0o600)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--fixture':
        fixture(Path(sys.argv[2]))
    else:
        ensure_verified()
