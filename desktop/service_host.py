"""Linux user-service main process. Private stdin owns its lifetime."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading


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

    def parent_gone():
        sys.stdin.buffer.read(1)
        # Exiting the unit's main process makes systemd kill the whole control group.
        os._exit(1)

    with subprocess.Popen(command, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                          stdout=sys.stderr, stderr=sys.stderr) as process:
        threading.Thread(target=parent_gone, daemon=True).start()
        print('PIPELINE_GROUP_READY', flush=True)
        return process.wait()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError, RuntimeError):
        print('Die Desktop-Prozessgruppe konnte nicht sicher gestartet werden.', file=sys.stderr)
        raise SystemExit(1)
