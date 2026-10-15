"""Project-local launch files; no desktop-wide settings or autostart changes."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.platforms import python_binary


def desktop_argument(value):
    if any(character in value for character in '\r\n\0'):
        raise ValueError('Der Projektpfad darf keine Zeilenumbrüche enthalten.')
    quoted = value.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    return '"' + quoted.replace('\\', '\\\\') + '"'


def main():
    if sys.platform.startswith('linux'):
        python = python_binary()
        if not python.is_file():
            python = Path(sys.executable)
        for name, label, stop in [('Video-Pipeline.desktop', 'Video Pipeline starten', False),
                                  ('Video-Pipeline-beenden.desktop', 'Video Pipeline beenden', True)]:
            command = ' '.join(desktop_argument(str(item)) for item in [python, ROOT / 'desktop/launcher.py'])
            if stop:
                command += ' --stop'
            target = ROOT / name
            target.write_text('[Desktop Entry]\nVersion=1.0\nType=Application\nName=' + label
                + '\nExec=' + command + '\nTerminal=false\nCategories=AudioVideo;\n', encoding='utf-8')
            target.chmod(0o700)
    elif sys.platform == 'darwin':
        for name in ('Start-Desktop.command', 'Stop-Desktop.command', 'Desktop-Einrichten.command'):
            (ROOT / name).chmod(0o700)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
