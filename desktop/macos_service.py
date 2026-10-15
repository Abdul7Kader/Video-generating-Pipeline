"""Transient GUI-session launchd guard; no persistent LaunchAgent or autostart."""
from __future__ import annotations

import json
import os
from pathlib import Path
import plistlib
import shutil
import shlex
import socket
import subprocess
import sys
import tempfile
import uuid

from .posix_registry import cleanup, private_directory


def launch_spec(label, directory):
    return {'Label': label, 'ProgramArguments': [sys.executable, '-I',
            str(Path(__file__).with_name('mac_host.py').resolve()), str(directory)],
            'RunAtLoad': True, 'KeepAlive': {'SuccessfulExit': False},
            'ThrottleInterval': 1, 'AbandonProcessGroup': False,
            'ProcessType': 'Interactive', 'ExitTimeOut': 3,
            'StandardOutPath': str(directory / 'guard.log'),
            'StandardErrorPath': str(directory / 'guard.log')}


class ProcessGroup:
    def __init__(self):
        if sys.platform != 'darwin' or os.geteuid() == 0 or not Path('/bin/launchctl').is_file():
            raise RuntimeError('Die macOS-Desktopanwendung braucht eine reguläre grafische Benutzersitzung, ohne sudo.')
        self.groups = []

    def start(self, command, *, cwd, env=None):
        directory = Path(tempfile.mkdtemp(prefix='video-pipeline-', dir='/tmp'))
        os.chmod(directory, 0o700)
        registry = directory / 'groups'
        registry.mkdir(mode=0o700)
        label = 'org.videopipeline.session-' + uuid.uuid4().hex
        target = f'gui/{os.getuid()}/{label}'
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.bind(str(directory / 'control.sock'))
        os.chmod(directory / 'control.sock', 0o600)
        connection.listen(1)
        connection.settimeout(15)
        entry = {'directory': directory, 'registry': registry, 'target': target,
                 'server': connection, 'connection': None, 'result': None}
        self.groups.append(entry)
        plist = directory / 'guard.plist'
        plist.write_bytes(plistlib.dumps(launch_spec(label, directory)))
        os.chmod(plist, 0o600)
        subprocess.run(['/bin/launchctl', 'bootstrap', f'gui/{os.getuid()}', str(plist)],
                       check=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client, _ = connection.accept()
        entry['connection'] = client
        client.settimeout(15)
        environment = dict(os.environ if env is None else env)
        environment.update(PIPELINE_PROCESS_REGISTRY=str(registry), PIPELINE_CHILD_PYTHON=sys.executable,
                           PIPELINE_BROWSER_WRAPPER=str(directory / 'browser-wrapper'))
        # Remotion creates its browser in a new session. Register that browser
        # before exec as well, rather than relying only on the UI process group.
        wrapper = directory / 'browser-wrapper'
        wrapper.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' -I '
            + shlex.quote(str(Path(__file__).with_name('mac_child.py').resolve()))
            + ' "$PIPELINE_REAL_BROWSER" "$@"\n', encoding='utf-8')
        wrapper.chmod(0o700)
        payload = json.dumps({'command': command, 'cwd': str(cwd), 'environment': environment}).encode() + b'\n'
        if len(payload) > 512 * 1024:
            raise RuntimeError('Die lokale Desktop-Konfiguration ist unerwartet groß.')
        client.sendall(payload)
        if self._line(client) != b'PIPELINE_GROUP_READY':
            raise RuntimeError('Die macOS-Prozessüberwachung wurde nicht bereit.')
        client.settimeout(None)
        return entry

    @staticmethod
    def _line(connection):
        data = bytearray()
        while len(data) <= 512 * 1024:
            item = connection.recv(1)
            if not item:
                raise RuntimeError('Die macOS-Prozessüberwachung wurde unerwartet beendet.')
            if item == b'\n':
                return bytes(data)
            data.extend(item)
        raise RuntimeError('Ungültige lokale Desktop-Antwort.')

    def wait(self, process):
        result = json.loads(self._line(process['connection']))
        if not isinstance(result, dict) or type(result.get('exit_code')) is not int:
            raise RuntimeError('Ungültiger macOS-Abschlussstatus.')
        process['result'] = result['exit_code']
        return process['result']

    def close(self):
        for entry in self.groups:
            if entry['connection']:
                entry['connection'].close()
            try:
                cleanup(private_directory(entry['registry']))
            finally:
                stopped = subprocess.run(['/bin/launchctl', 'bootout', entry['target']], timeout=12,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                entry['server'].close()
            if stopped.returncode:
                remaining = subprocess.run(['/bin/launchctl', 'print', entry['target']], timeout=5,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if remaining.returncode == 0:
                    raise RuntimeError('Die macOS-Wächterregistrierung wurde noch nicht vollständig beendet. Diagnose bleibt im privaten Sitzungsordner erhalten.')
            # Only the fresh, private directory returned by mkdtemp is removed.
            shutil.rmtree(entry['directory'])
        self.groups.clear()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
