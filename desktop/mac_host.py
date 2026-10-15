"""launchd-managed macOS host; a restart cleans up instead of relaunching the UI."""
from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop.posix_registry import acknowledge, cleanup, private_directory


def main():
    directory = private_directory(sys.argv[1])
    registry = private_directory(directory / 'groups')
    if (directory / 'started').exists():
        cleanup(registry)
        return 0  # After a guard crash, never restart an unattended production.
    (directory / 'started').touch(mode=0o600)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(15)
        connection.connect(str(directory / 'control.sock'))
        data = bytearray()
        while len(data) <= 512 * 1024:
            item = connection.recv(1)
            if not item:
                raise RuntimeError('Desktopstarter wurde beendet.')
            if item == b'\n':
                break
            data.extend(item)
        value = json.loads(data)
        if (not isinstance(value, dict) or set(value) != {'command', 'cwd', 'environment'}
                or not isinstance(value['command'], list) or not value['command']
                or not all(isinstance(item, str) and '\0' not in item for item in value['command'])
                or not Path(value['command'][0]).is_absolute() or not isinstance(value['cwd'], str)
                or not Path(value['cwd']).is_absolute() or not isinstance(value['environment'], dict)
                or not all(isinstance(key, str) and isinstance(item, str) and key and '=' not in key
                           and '\0' not in key + item for key, item in value['environment'].items())):
            raise ValueError('Ungültige lokale Desktop-Konfiguration')
        connection.settimeout(None)
        parent_gone = threading.Event()

        def watch_parent():
            try:
                connection.recv(1)
            finally:
                parent_gone.set()

        threading.Thread(target=watch_parent, daemon=True).start()
        command = [sys.executable, '-I', str(Path(__file__).with_name('mac_child.py')), *value['command']]
        process = subprocess.Popen(command, cwd=value['cwd'], env=value['environment'], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=sys.stderr, start_new_session=True)
        try:
            deadline = time.monotonic() + 10
            while not list(registry.glob('*.json')) and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            acknowledge(registry)
            if process.poll() is not None:
                raise RuntimeError('Die macOS-Prozessregistrierung ist fehlgeschlagen.')
            connection.sendall(b'PIPELINE_GROUP_READY\n')
            previous_change = None
            next_scan = 0
            while process.poll() is None and not parent_gone.is_set():
                changed = registry.stat().st_mtime_ns
                if changed != previous_change or time.monotonic() >= next_scan:
                    acknowledge(registry)
                    previous_change = changed
                    next_scan = time.monotonic() + 1
                time.sleep(.05)
        finally:
            cleanup(registry)
            process.wait(timeout=5)
        if not parent_gone.is_set():
            connection.sendall(json.dumps({'exit_code': process.returncode}).encode() + b'\n')
        return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        # KeepAlive restarts only this guard after failure, to clean registered
        # groups. Credentials and command payloads are never logged or persisted.
        print('Die macOS-Desktopüberwachung wurde unterbrochen; eigene Gruppen werden aufgeräumt.', file=sys.stderr)
        raise SystemExit(1)
