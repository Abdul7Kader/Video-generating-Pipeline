"""Explicit GUI acceptance: python tests/check_desktop_runtime.py [normal|crash|abort]."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.windows_job import ProcessGroup
from desktop.platforms import electron_binary
from stop_pipeline import _pid_alive


def powershell(script):
    result = subprocess.check_output(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script], text=True)
    value = json.loads(result) if result.strip() else []
    return value if isinstance(value, list) else [value]


def check(mode):
    if mode not in {'normal', 'crash', 'abort'}:
        raise ValueError('Expected normal, crash or abort')
    directory = ROOT / 'data/desktop' / ('acceptance-' + mode + '-' + str(time.time_ns()))
    directory.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(
        ('ELECTRON_', 'NODE_OPTIONS', 'NODE_PATH', 'PIPELINE_DESKTOP_'))}
    env.update(PIPELINE_DESKTOP_GUARDED='1', PIPELINE_DESKTOP_PYTHON=sys.executable,
               DESKTOP_SMOKE_DIRECTORY=str(directory), DATA_DIR=str(directory / 'isolated-data'))
    with ProcessGroup() as group:
        process = group.start([str(electron_binary()),
            str(ROOT / 'tests/desktop-smoke.cjs'), *([] if mode == 'normal' else ['--' + mode])], cwd=ROOT, env=env)
        deadline = time.monotonic() + 80
        while not (directory / 'ready.json').exists():
            if (directory / 'error.json').exists():
                raise RuntimeError((directory / 'error.json').read_text())
            if time.monotonic() > deadline:
                raise RuntimeError('Desktop startup timed out: ' + str(directory))
            time.sleep(.2)
        report = json.loads((directory / 'ready.json').read_text())
        print(json.dumps({'mode': mode, 'loaded': report['page'], 'origin': report['origin']}), flush=True)
        processes = powershell('Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId | ConvertTo-Json -Compress')
        owned = {report['electron']}
        for _ in range(12):
            owned |= {p['ProcessId'] for p in processes if p['ParentProcessId'] in owned}
        own_ids = ','.join(str(pid) for pid in sorted(owned))
        sockets = powershell('Get-NetTCPConnection -State Listen -OwningProcess ' + own_ids + ' -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress')
        listeners = [s for s in sockets if s['OwningProcess'] in owned]
        assert listeners and all(s['LocalAddress'] in {'127.0.0.1', '::1'} for s in listeners), listeners
        udp = powershell('try { Get-NetUDPEndpoint -OwningProcess ' + own_ids + ' -ErrorAction Stop | Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress } catch { if ($_.CategoryInfo.Category -ne "ObjectNotFound") { throw } }; exit 0')
        owned_udp = [s for s in udp if s['OwningProcess'] in owned]
        assert all(s['LocalAddress'] in {'127.0.0.1', '::1'} for s in owned_udp), owned_udp
        report.update(listeners=listeners, udp=owned_udp, owned_pids=sorted(owned))
        if mode == 'normal':
            second = subprocess.run([sys.executable, '-c',
                'from desktop.launcher import main; raise SystemExit(main())'], cwd=ROOT, timeout=30)
            assert second.returncode == 0, second.returncode
            assert _pid_alive(report['backend'])
            report['second_start'] = 'existing instance retained'
        (directory / 'close').touch()
        code = group.wait(process)
        assert (code != 0 if mode == 'crash' else code == 0), code
        report['exit_code'] = code
    deadline = time.monotonic() + 10
    while any(_pid_alive(pid) for pid in owned) and time.monotonic() < deadline:
        time.sleep(.1)
    leftovers = [pid for pid in owned if _pid_alive(pid)]
    assert not leftovers, leftovers
    report['leftovers'] = leftovers
    (directory / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'mode': mode, 'passed': True, 'listeners': listeners,
                      'leftovers': leftovers, 'report': str(directory / 'result.json')}), flush=True)


if __name__ == '__main__':
    for mode in (sys.argv[1:] or ['normal', 'crash', 'abort']):
        check(mode)
