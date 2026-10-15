"""Explicit native Linux GUI acceptance; never generates videos or model requests."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.linux_service import ProcessGroup
from desktop.platforms import electron_binary, runtime_key
from stop_pipeline import _pid_alive


def tree(root):
    parents = {}
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            parents[int(path.parent.name)] = int(fields[1])
        except (OSError, ValueError):
            pass
    owned = {root}
    for _ in range(20):
        owned |= {pid for pid, parent in parents.items() if parent in owned}
    return owned


def endpoints(owned):
    inodes = set()
    for pid in owned:
        for path in (Path('/proc') / str(pid) / 'fd').glob('*'):
            try:
                target = os.readlink(path)
                if target.startswith('socket:['):
                    inodes.add(target[8:-1])
            except OSError:
                pass
    endpoints = []
    for kind in ('tcp', 'tcp6', 'udp', 'udp6'):
        for line in (Path('/proc/net') / kind).read_text().splitlines()[1:]:
            fields = line.split()
            if fields[9] not in inodes or (kind.startswith('tcp') and fields[3] != '0A'):
                continue
            address, port = fields[1].split(':')
            assert address in {'0100007F', '00000000000000000000000001000000'}, (kind, address, port)
            endpoints.append({'kind': kind, 'loopback': True, 'port': int(port, 16)})
    return endpoints


def check(mode):
    assert mode in {'normal', 'abort', 'crash'}
    directory = ROOT / 'data/desktop' / ('linux-acceptance-' + mode + '-' + str(time.time_ns()))
    directory.mkdir(parents=True)
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith(
        ('ELECTRON_', 'NODE_OPTIONS', 'NODE_PATH', 'PIPELINE_DESKTOP_'))}
    env.update(PIPELINE_DESKTOP_GUARDED='1', PIPELINE_DESKTOP_PYTHON=sys.executable,
               DESKTOP_SMOKE_DIRECTORY=str(directory), DATA_DIR=str(directory / 'isolated-data'),
               APP_PORT='18183', SCRIPT_PROVIDER='web_import', ANTIGRAVITY_ENABLED='0',
               GEMINI_CLI_ENABLED='0')
    env['PATH'] = str(ROOT / '.runtime/node' / runtime_key() / 'bin') + ':/usr/local/bin:/usr/bin:/bin'
    with ProcessGroup() as group:
        process = group.start([str(electron_binary()), str(ROOT / 'tests/desktop-smoke.cjs'),
                               *([] if mode == 'normal' else ['--' + mode])], cwd=ROOT, env=env)
        deadline = time.monotonic() + 120
        while not (directory / 'ready.json').exists():
            if (directory / 'error.json').exists():
                raise RuntimeError((directory / 'error.json').read_text())
            if time.monotonic() > deadline or process.poll() is not None:
                raise RuntimeError('Linux GUI did not become ready; see ' + str(directory))
            time.sleep(.2)
        report = json.loads((directory / 'ready.json').read_text())
        owned = tree(report['electron'])
        listeners = endpoints(owned)
        assert any(item['kind'] == 'tcp' and item['port'] == 18183 for item in listeners), listeners
        if mode == 'normal':
            second = subprocess.run([sys.executable, '-c', 'from desktop.launcher import main; raise SystemExit(main())'],
                                    cwd=ROOT, env=env, timeout=30)
            assert second.returncode == 0 and _pid_alive(report['backend']), {
                'second_exit': second.returncode, 'backend_alive': _pid_alive(report['backend'])}
        (directory / 'close').touch()
        code = group.wait(process)
        assert (code != 0 if mode == 'crash' else code == 0), code
    deadline = time.monotonic() + 10
    while any(_pid_alive(pid) for pid in owned) and time.monotonic() < deadline:
        time.sleep(.1)
    leftovers = [pid for pid in owned if _pid_alive(pid)]
    assert not leftovers, leftovers
    report.update(exit_code=code, endpoints=listeners, owned_pids=sorted(owned), leftovers=leftovers)
    (directory / 'result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'mode': mode, 'passed': True, 'endpoints': listeners, 'leftovers': leftovers}), flush=True)


if __name__ == '__main__':
    for mode in (sys.argv[1:] or ['normal', 'crash', 'abort']):
        check(mode)
