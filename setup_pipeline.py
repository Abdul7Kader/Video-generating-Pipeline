"""Bootstrap only a project-local Python environment, then open normal settings."""
from __future__ import annotations

import os
import subprocess
import sys
import re
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / '.runtime' / 'pipeline-python'
PYTHON = RUNTIME / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def main(*, start: bool = True, runtime: Path | None = None):
    require_project_runtime = runtime is not None
    runtime = runtime or RUNTIME
    python = runtime / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if sys.version_info < (3, 11):
        print('Python 3.11 oder neuer ist nötig; empfohlen: Python 3.12. Download: https://www.python.org/downloads/')
        return 1
    try:
        environment={key:value for key,value in os.environ.items() if not key.upper().startswith(('PIP_','PYTHONPATH'))}
        environment['PIP_CONFIG_FILE']=os.devnull
        if require_project_runtime and Path(sys.prefix).resolve() != runtime.resolve():
            # Avoid loading native inference libraries from the wrong interpreter.
            raise ImportError('Projektlokale Laufzeit wird benötigt')
        import fastapi, uvicorn, dotenv, piper
        minimum={'fastapi':(0,116,1),'uvicorn':(0,35,0),'pydantic':(2,0,0),'piper-tts':(1,4,2)}
        ready = all(tuple(int(value) for value in re.findall(r'\d+',version(package))[:3]) >= required for package,required in minimum.items())
    except (ImportError,PackageNotFoundError):
        ready = False
    if ready:
        return subprocess.call([sys.executable, str(ROOT / 'start_pipeline.py')], cwd=ROOT) if start else 0
    print('Die lokale Python-Umgebung fehlt oder ist nicht kompatibel. Die Einrichtung installiert ausschließlich im Projektordner.')
    print('Quelle: https://pypi.org · festgelegte Pakete aus requirements.txt. Keine Administratorrechte oder Firewalländerungen.')
    if input('Projektlokale Laufzeit jetzt einrichten? [j/N] ').strip().lower() not in {'j','ja','y','yes'}:
        return 1
    try:
        if not runtime.resolve().is_relative_to(ROOT):
            raise OSError('Die Laufzeit muss im Projektordner bleiben.')
        if not python.is_file() or not (runtime / 'pyvenv.cfg').is_file():
            subprocess.run([sys.executable, '-m', 'venv', str(runtime)], check=True, cwd=ROOT)
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt'), '--index-url', 'https://pypi.org/simple'], check=True, cwd=ROOT, env=environment)
        subprocess.run([str(python), '-m', 'pip', 'check'], check=True, cwd=ROOT, env=environment)
        return subprocess.call([str(python), str(ROOT / 'start_pipeline.py')], cwd=ROOT) if start else 0
    except (OSError, subprocess.SubprocessError):
        print('Einrichtung fehlgeschlagen. Prüfe Internetverbindung und Python-Version und starte erneut.')
        return 1


if __name__ == '__main__':
    if '--desktop' in sys.argv:
        from desktop.platforms import python_binary
        selected = python_binary()
        raise SystemExit(main(start=False, runtime=selected.parent.parent))
    raise SystemExit(main(start='--setup-only' not in sys.argv))
