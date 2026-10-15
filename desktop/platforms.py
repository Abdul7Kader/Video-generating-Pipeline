"""Native runtime paths, separated by OS and architecture."""
from pathlib import Path
import platform

ROOT = Path(__file__).resolve().parents[1]


def runtime_key(system=None, machine=None):
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    systems = {'Windows': 'win32', 'Linux': 'linux', 'Darwin': 'darwin'}
    architectures = {'amd64': 'x64', 'x86_64': 'x64', 'x64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}
    if system not in systems or machine not in architectures:
        raise RuntimeError('Für diesen Desktop werden Windows, Linux oder macOS auf x64/arm64 benötigt.')
    return systems[system] + '-' + architectures[machine]


def runtime_directory():
    return ROOT / '.runtime' / 'desktop' / runtime_key()


def python_binary():
    return ROOT / '.runtime' / 'python' / runtime_key() / ('Scripts/python.exe' if platform.system() == 'Windows' else 'bin/python')


def electron_binary():
    relative = {'Windows': 'electron.exe', 'Linux': 'electron',
                'Darwin': 'Electron.app/Contents/MacOS/Electron'}[platform.system()]
    return runtime_directory() / 'node_modules/electron/dist' / relative


def process_group():
    if platform.system() == 'Windows':
        from .windows_job import ProcessGroup
    elif platform.system() == 'Linux':
        from .linux_service import ProcessGroup
    elif platform.system() == 'Darwin':
        from .mac_selfcheck import ensure_verified
        ensure_verified()
        from .macos_service import ProcessGroup
    else:
        raise RuntimeError('Für dieses System ist keine sichere Desktop-Prozessverwaltung verfügbar.')
    return ProcessGroup()
