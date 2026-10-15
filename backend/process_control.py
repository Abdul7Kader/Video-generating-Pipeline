"""Only macOS desktop workers need registration before entering new sessions."""
import os
from pathlib import Path
import shutil
import sys

CONTROL_KEYS = {'PIPELINE_PROCESS_REGISTRY', 'PIPELINE_CHILD_PYTHON', 'PIPELINE_BROWSER_WRAPPER'}


def owned_command(command):
    if sys.platform != 'darwin' or not os.environ.get('PIPELINE_PROCESS_REGISTRY'):
        return command
    executable = shutil.which(command[0])
    if not executable:
        raise RuntimeError('Das lokale Programm wurde nicht gefunden.')
    python = os.environ.get('PIPELINE_CHILD_PYTHON', '')
    if not Path(python).is_absolute():
        raise RuntimeError('Die überwachte Python-Laufzeit fehlt.')
    return [python, '-I', str(Path(__file__).resolve().parents[1] / 'desktop/mac_child.py'), executable, *command[1:]]
