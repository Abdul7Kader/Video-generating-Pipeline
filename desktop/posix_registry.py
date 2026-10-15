"""Private registration before exec for macOS children that create new sessions."""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import signal
import stat
import sys
import time


class BsdInfo(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in ('flags', 'status', 'xstatus', 'pid', 'ppid',
                'uid', 'gid', 'ruid', 'rgid', 'svuid', 'svgid', 'reserved')] + [
                ('comm', ctypes.c_char * 16), ('name', ctypes.c_char * 32)] + [
                (name, ctypes.c_uint32) for name in ('nfiles', 'pgid', 'jobc', 'tdev', 'tpgid')] + [
                ('nice', ctypes.c_int32), ('seconds', ctypes.c_uint64), ('microseconds', ctypes.c_uint64)]


def identity(pid):
    if sys.platform == 'darwin':
        library = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
        library.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
        library.proc_pidinfo.restype = ctypes.c_int
        info = BsdInfo()
        count = library.proc_pidinfo(pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info))
        if not count:
            # Missing PID is normal; permission/ABI failures must fail closed.
            if ctypes.get_errno() in {0, 3}:
                return None
            raise OSError(ctypes.get_errno(), 'Prozessidentität nicht lesbar')
        if count != ctypes.sizeof(info):
            raise RuntimeError('Die macOS-Prozessinformationen haben ein unbekanntes Format.')
        return {'pid': info.pid, 'pgid': info.pgid, 'uid': info.uid,
                'birth': [info.seconds, info.microseconds]}
    # The same registration protocol is exercised with real processes on Linux.
    if sys.platform.startswith('linux'):
        try:
            path = Path('/proc') / str(pid)
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            return {'pid': pid, 'pgid': int(fields[2]), 'uid': path.stat().st_uid, 'birth': [int(fields[19]), 0]}
        except FileNotFoundError:
            return None
    raise RuntimeError('POSIX-Prozessinformationen fehlen für dieses System.')


def private_directory(value):
    path = Path(value)
    info = path.lstat()
    if not path.is_absolute() or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RuntimeError('Die private Desktop-Prozessregistrierung ist nicht geschützt.')
    return path


def records(directory):
    paths = list(directory.glob('*.json'))
    if len(paths) > 2048:
        raise RuntimeError('Zu viele Desktop-Prozessgruppen.')
    for path in paths:
        if not path.stem.isdecimal() or path.stat().st_size > 4096:
            continue
        record = json.loads(path.read_text())
        if (not isinstance(record, dict) or set(record) != {'pid', 'pgid', 'uid', 'birth'}
                or type(record['pid']) is not int or record['pid'] <= 1 or record['pgid'] != record['pid']
                or record['pid'] != int(path.stem) or record['uid'] != os.getuid()
                or not isinstance(record['birth'], list) or len(record['birth']) != 2
                or not all(type(item) is int and item >= 0 for item in record['birth'])):
            raise RuntimeError('Ungültige Desktop-Prozessregistrierung.')
        yield record


def acknowledgement(directory, record):
    return directory / ('ack-' + str(record['pid']) + '-' + '-'.join(map(str, record['birth'])))


def acknowledge(directory):
    if (directory / 'closing').exists():
        return
    for record in records(directory):
        if acknowledgement(directory, record).exists():
            continue
        if identity(record['pid']) == record:
            acknowledgement(directory, record).touch(mode=0o600, exist_ok=True)


def signal_owned(record, signum):
    if record['pgid'] == os.getpgrp():
        raise RuntimeError('Die eigene Wächtergruppe darf nicht beendet werden.')
    current = identity(record['pid'])
    if current is not None and current != record:
        return False  # PID was reused: never touch its new owner.
    try:
        os.killpg(record['pgid'], signum)
        return True
    except ProcessLookupError:
        return False


def cleanup(directory):
    (directory / 'closing').touch(mode=0o600, exist_ok=True)
    for record in records(directory):
        if acknowledgement(directory, record).exists():
            signal_owned(record, signal.SIGTERM)
    time.sleep(.2)
    # Include registrations committed just as closing started; pending wrappers
    # also observe the closing marker and exit before running their command.
    for record in records(directory):
        signal_owned(record, signal.SIGKILL)


def register_and_exec(command):
    if not command or not Path(command[0]).is_absolute():
        raise RuntimeError('Der Prozess benötigt einen absoluten Programmpfad.')
    directory = private_directory(os.environ['PIPELINE_PROCESS_REGISTRY'])
    if (directory / 'closing').exists():
        raise RuntimeError('Die Anwendung wird bereits beendet.')
    if os.getpgrp() != os.getpid():
        os.setpgid(0, 0)
    record = identity(os.getpid())
    if not record or record['pgid'] != record['pid']:
        raise RuntimeError('Die eigene Prozessgruppe fehlt.')
    temporary = directory / (str(record['pid']) + '.pending')
    with temporary.open('x', encoding='utf-8') as handle:
        os.chmod(temporary, 0o600)
        json.dump(record, handle)
    temporary.replace(directory / (str(record['pid']) + '.json'))
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if (directory / 'closing').exists():
            break
        if acknowledgement(directory, record).exists():
            os.execve(command[0], command, dict(os.environ))
        time.sleep(.02)
    raise RuntimeError('Die Prozessüberwachung hat den Start nicht bestätigt.')
