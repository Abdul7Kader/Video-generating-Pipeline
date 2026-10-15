"""A transient per-user systemd service owns even setsid/detached descendants."""
from __future__ import annotations

import json
import os
from pathlib import Path
import select
import subprocess
import sys
import uuid


class ProcessGroup:
    def __init__(self):
        if not sys.platform.startswith('linux') or os.geteuid() == 0:
            raise RuntimeError('Starte die Linux-Desktopanwendung als normaler Benutzer, ohne sudo.')
        self.run_tool = Path('/usr/bin/systemd-run')
        self.control_tool = Path('/usr/bin/systemctl')
        if not self.run_tool.is_file() or not self.control_tool.is_file():
            raise RuntimeError('Die sichere Linux-Desktopverwaltung benötigt eine systemd-Benutzersitzung. Es wird kein unüberwachter Server gestartet.')
        try:
            subprocess.run([str(self.control_tool), '--user', 'show', '--property=Version', '--value'],
                           check=True, timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError) as error:
            raise RuntimeError('Die systemd-Benutzersitzung ist nicht erreichbar. Melde dich regulär am Linux-Desktop an; nutze kein sudo und keinen Root-Start.') from error
        self.processes = []

    def start(self, command, *, cwd, env=None):
        unit = 'video-pipeline-' + uuid.uuid4().hex + '.service'
        host = Path(__file__).with_name('service_host.py').resolve()
        # The unit description/argv never contains the app environment or credentials.
        # Older systemd also supports $$ for literal dollars in ExecStart arguments.
        host_command = [str(sys.executable), '-I', str(host)]
        arguments = [str(self.run_tool), '--user', '--quiet', '--collect', '--wait', '--pipe',
                     '--service-type=exec', '--unit=' + unit,
                     '--property=KillMode=control-group', '--property=SendSIGKILL=yes',
                     '--property=TimeoutStopSec=8s', '--property=Restart=no',
                     *[value.replace('$', '$$') for value in host_command]]
        logs = Path(cwd) / 'data' / 'desktop'
        logs.mkdir(parents=True, exist_ok=True)
        with (logs / 'lifecycle.log').open('ab') as errors:
            process = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=errors, cwd=cwd)
        self.processes.append((unit, process))
        configuration = {'unit': unit, 'command': command, 'cwd': str(cwd),
                         'environment': dict(os.environ if env is None else env)}
        payload = json.dumps(configuration).encode('utf-8') + b'\n'
        if len(payload) > 512 * 1024:
            raise RuntimeError('Die lokale Desktop-Konfiguration ist unerwartet groß.')
        try:
            process.stdin.write(payload)
            process.stdin.flush()
            readable, _, _ = select.select([process.stdout], [], [], 15)
            if not readable or process.stdout.readline(128) != b'PIPELINE_GROUP_READY\n':
                raise RuntimeError('Die Linux-Prozessüberwachung wurde nicht bereit. Prüfe data/desktop/lifecycle.log; es wird keine ungeschützte Ersatzinstanz gestartet.')
        except (OSError, ValueError) as error:
            raise RuntimeError('Die Linux-Prozessüberwachung konnte nicht sicher gestartet werden.') from error
        return process

    def wait(self, process):
        return process.wait()

    def close(self):
        for unit, process in self.processes:
            # EOF is a private parent-death signal to the service host.
            if process.stdin and not process.stdin.closed:
                try:
                    process.stdin.close()
                except BrokenPipeError:
                    pass
            subprocess.run([str(self.control_tool), '--user', 'stop', unit], timeout=12,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if process.poll() is None:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired as error:
                    raise RuntimeError('Das Ende der eigenen Linux-Prozessgruppe konnte nicht bestätigt werden.') from error
            state = subprocess.run([str(self.control_tool), '--user', 'is-active', '--quiet', unit],
                                   timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if state.returncode not in {3, 4}:
                raise RuntimeError('Das vollständige Ende der eigenen Linux-Prozessgruppe ist nicht bestätigt.')
            process.stdout.close()
        self.processes.clear()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
