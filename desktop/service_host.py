"""Linux user-service main process. Private stdin owns its lifetime."""
from __future__ import annotations

import json
import ctypes
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time


def contain_orphans():
    # Chromium can move into an XDG portal scope outside our systemd cgroup.
    # The kernel still reparents its abandoned descendants to this subreaper.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'Linux-Unterprozessüberwachung fehlt')
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise RuntimeError('Der sichere Linux-Desktop benötigt pidfd-Unterstützung.')
    descriptor = os.pidfd_open(os.getpid())
    os.close(descriptor)


def cleanup_descendants():
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        found = False
        # Children from every thread, including orphans moved into other cgroups.
        pending = [os.getpid()]
        visited = set()
        while pending:
            parent = pending.pop()
            if parent in visited:
                continue
            visited.add(parent)
            for path in Path(f'/proc/{parent}/task').glob('*/children'):
                try:
                    children = path.read_text().split()
                except FileNotFoundError:
                    continue
                for item in children:
                    pid = int(item)
                    descriptor = None
                    try:
                        descriptor = os.pidfd_open(pid)
                        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
                        if int(fields[1]) != parent:
                            continue  # The PID has gone or changed ownership.
                        found = True
                        signal.pidfd_send_signal(descriptor, signal.SIGSTOP)
                        pending.append(pid)
                        signal.pidfd_send_signal(descriptor, signal.SIGKILL)
                    except (ProcessLookupError, FileNotFoundError):
                        pass
                    finally:
                        if descriptor is not None:
                            os.close(descriptor)
        # Reap adopted grandchildren; Popen also handles an already-reaped root.
        while True:
            try:
                if os.waitpid(-1, os.WNOHANG)[0] == 0:
                    break
            except ChildProcessError:
                break
        if not found:
            return
        time.sleep(.02)
    raise RuntimeError('Eigene Linux-Unterprozesse wurden nicht vollständig beendet.')


def main():
    line = sys.stdin.buffer.readline(512 * 1024 + 1)
    if len(line) > 512 * 1024 or not line.endswith(b'\n'):
        raise ValueError('Ungültige lokale Desktop-Konfiguration')
    value = json.loads(line)
    if not isinstance(value, dict) or set(value) != {'unit', 'command', 'cwd', 'environment'}:
        raise ValueError('Ungültige lokale Desktop-Konfiguration')
    unit, command, cwd, environment = (value[key] for key in ('unit', 'command', 'cwd', 'environment'))
    if (not isinstance(unit, str) or not re.fullmatch(r'video-pipeline-[0-9a-f]{32}\.service', unit)
            or not isinstance(command, list) or not command or not all(isinstance(item, str) and '\0' not in item for item in command)
            or not Path(command[0]).is_absolute() or not isinstance(cwd, str) or not Path(cwd).is_absolute()
            or not isinstance(environment, dict) or not all(isinstance(key, str) and isinstance(item, str)
                and key and '=' not in key and '\0' not in key + item for key, item in environment.items())):
        raise ValueError('Ungültige lokale Desktop-Konfiguration')
    # A launch flag alone is insufficient: the OS must already contain this host.
    groups = Path('/proc/self/cgroup').read_text()
    if not any(line.rsplit(':', 1)[-1].endswith('/' + unit) for line in groups.splitlines()):
        raise RuntimeError('Die erforderliche Linux-Prozessgruppe fehlt.')

    contain_orphans()
    stopping = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopping.set())

    def parent_gone():
        sys.stdin.buffer.read(1)
        stopping.set()

    with subprocess.Popen(command, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                          stdout=sys.stderr, stderr=sys.stderr) as process:
        threading.Thread(target=parent_gone, daemon=True).start()
        print('PIPELINE_GROUP_READY', flush=True)
        try:
            while process.poll() is None and not stopping.wait(.05):
                pass
            result = process.poll()
        finally:
            cleanup_descendants()
        return result if result is not None else 1


if __name__ == '__main__':
    try:
        result = main()
    except (OSError, ValueError, TypeError, RuntimeError):
        print('Die Desktop-Prozessgruppe konnte nicht sicher gestartet werden.', file=sys.stderr)
        result = 1
    # The parent-death watcher can still hold stdin's buffered-reader lock.
    # Avoid interpreter finalization with that live reader; systemd owns cleanup.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(result if 0 <= result <= 255 else 1)
