"""Native desktop entry point. Each OS must contain all Electron descendants."""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.platforms import electron_binary, process_group, runtime_directory, runtime_key


def main():
    electron = electron_binary()
    package = runtime_directory() / 'node_modules/electron/package.json'
    required = json.loads((ROOT / 'desktop/package.json').read_text())['dependencies']['electron']
    if not electron.is_file() or not package.is_file() or json.loads(package.read_text())['version'] != required:
        raise RuntimeError('Die Desktop-Laufzeit für dieses System fehlt oder passt nicht. Starte zuerst Desktop-Einrichten.cmd (Windows), Desktop-Einrichten.sh (Linux) oder Desktop-Einrichten.command (macOS) im Projektordner.')
    # Native dependencies/credentials remain configured by the existing pipeline.
    # Never accept injected Node flags or turn Electron into a generic Node host.
    environment = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith(('ELECTRON_', 'NODE_OPTIONS', 'NODE_PATH', 'PYTHONPATH', 'PYTHONHOME',
                       'PIPELINE_DESKTOP_', 'PIPELINE_PROCESS_REGISTRY', 'PIPELINE_CHILD_PYTHON', 'PIPELINE_BROWSER_WRAPPER', 'PIPELINE_REAL_BROWSER'))}
    python = Path(sys.executable).with_name('python.exe') if os.name == 'nt' else Path(sys.executable)
    environment.update(PIPELINE_DESKTOP_GUARDED='1', PIPELINE_DESKTOP_PYTHON=str(python))
    node_directory = ROOT / '.runtime/node' / runtime_key() / 'bin'
    if (node_directory / 'node').is_file():
        environment['PATH'] = str(node_directory) + os.pathsep + environment.get('PATH', '')
    with process_group() as group:
        process = group.start([str(electron), str(ROOT / 'desktop'), *(['--stop'] if '--stop' in sys.argv else [])],
                              cwd=ROOT, env=environment)
        return group.wait(process)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        message = str(error) if isinstance(error, RuntimeError) else 'Die Desktop-Anwendung konnte nicht sicher gestartet werden. Prüfe die lokale Einrichtung.'
        if os.name == 'nt':
            ctypes.windll.user32.MessageBoxW(None, message, 'Video Pipeline – Start fehlgeschlagen', 0x10)
        else:
            print(message, file=sys.stderr)
        raise SystemExit(1)
