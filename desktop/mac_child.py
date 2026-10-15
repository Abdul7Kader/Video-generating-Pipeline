"""Executed before a new macOS process group may run application work."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop.posix_registry import register_and_exec

if __name__ == '__main__':
    try:
        register_and_exec(sys.argv[1:])
    except (OSError, RuntimeError, ValueError, KeyError):
        print('Der eigene Prozess konnte nicht unter Desktop-Aufsicht gestartet werden.', file=sys.stderr)
        raise SystemExit(1)
