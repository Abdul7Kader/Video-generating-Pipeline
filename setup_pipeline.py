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


def main():
    if sys.version_info < (3, 11):
        print('Python 3.11 oder neuer ist nötig; empfohlen: Python 3.12. Download: https://www.python.org/downloads/')
        return 1
    try:
        environment={key:value for key,value in os.environ.items() if not key.upper().startswith(('PIP_','PYTHONPATH'))}
        environment['PIP_CONFIG_FILE']=os.devnull
        import fastapi, uvicorn, dotenv, piper
        minimum={'fastapi':(0,116,1),'uvicorn':(0,35,0),'pydantic':(2,0,0),'piper-tts':(1,4,2)}
        ready = all(tuple(int(value) for value in re.findall(r'\d+',version(package))[:3]) >= required for package,required in minimum.items())
    except (ImportError,PackageNotFoundError):
        ready = False
    if ready:
        return subprocess.call([sys.executable, str(ROOT / 'start_pipeline.py')], cwd=ROOT)
    print('Die lokale Python-Umgebung fehlt oder ist nicht kompatibel. Die Einrichtung installiert ausschließlich im Projektordner.')
    print('Quelle: https://pypi.org · festgelegte Pakete aus requirements.txt. Keine Administratorrechte oder Firewalländerungen.')
    if input('Projektlokale Laufzeit jetzt einrichten? [j/N] ').strip().lower() not in {'j','ja','y','yes'}:
        return 1
    try:
        if not RUNTIME.resolve().is_relative_to(ROOT):
            raise OSError('Die Laufzeit muss im Projektordner bleiben.')
        if not PYTHON.is_file() or not (RUNTIME / 'pyvenv.cfg').is_file():
            subprocess.run([sys.executable, '-m', 'venv', str(RUNTIME)], check=True, cwd=ROOT)
        subprocess.run([str(PYTHON), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt'), '--index-url', 'https://pypi.org/simple'], check=True, cwd=ROOT, env=environment)
        subprocess.run([str(PYTHON), '-m', 'pip', 'check'], check=True, cwd=ROOT, env=environment)
        return subprocess.call([str(PYTHON), str(ROOT / 'start_pipeline.py')], cwd=ROOT)
    except (OSError, subprocess.SubprocessError):
        print('Einrichtung fehlgeschlagen. Prüfe Internetverbindung und Python-Version und starte erneut.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
