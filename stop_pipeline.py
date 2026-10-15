"""Request graceful shutdown of local servers started by start_pipeline.py."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from start_pipeline import CONTROL_DIR


def _process_started_ns(pid: int) -> int | None:
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = (wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4))
        kernel.GetProcessTimes.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        times = [wintypes.FILETIME() for _ in range(4)]
        try:
            if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
                return None
            ticks = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
            return (ticks - 116444736000000000) * 100
        finally:
            kernel.CloseHandle(handle)
    try:
        if sys.platform.startswith('linux'):
            fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
            boot = next(int(line.split()[1]) for line in Path('/proc/stat').read_text().splitlines() if line.startswith('btime '))
            return boot * 1000000000 + int(fields[19]) * 1000000000 // os.sysconf('SC_CLK_TCK')
        if sys.platform == 'darwin':
            from desktop.posix_registry import identity
            value = identity(pid)
            return value['birth'][0] * 1000000000 + value['birth'][1] * 1000 if value else None
    except (OSError, ValueError, StopIteration):
        return None
    return None


def _managed_record_alive(record: dict, state_path: Path) -> bool:
    if not _pid_alive(record['pid']):
        return False
    if 'process_identity' in record:
        actual_identity = _process_identity(record['pid'])
        return actual_identity is None or actual_identity == record['process_identity']
    actual = _process_started_ns(record['pid'])
    expected = record.get('process_started_ns')
    if actual is None:
        return True  # Unknown ownership remains blocked; never silently take it over.
    if expected is not None:
        return type(expected) is int and actual == expected
    # Legacy records predate the birth field. A newer process is conclusively
    # unrelated; genuinely old live launchers still drain normally.
    try:
        return actual <= state_path.stat().st_mtime_ns
    except FileNotFoundError:
        return False


def _process_identity(pid: int) -> str | None:
    if sys.platform.startswith('linux'):
        try:
            fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
            boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            return f'linux:{boot}:{fields[19]}'
        except OSError:
            return None
    started = _process_started_ns(pid)
    return f'{sys.platform}:{started}' if started is not None else None


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5
        code = wintypes.DWORD()
        try:
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def stop_managed(control_dir: Path, *, port: int | None = None, timeout: float = 15) -> tuple[int, int, int]:
    stopped = stale = pending = 0
    for state_path in sorted(control_dir.glob("pipeline-*.json")):
        match = re.fullmatch(r"pipeline-(\d+)-(\d+)\.json", state_path.name)
        if not match:
            continue
        try:
            record = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        pid, recorded_port = int(match[2]), int(match[1])
        token = record.get("token")
        if (
            record.get("pid") != pid or record.get("port") != recorded_port
            or not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{32}", token)
            or (port is not None and port != recorded_port)
        ):
            continue
        request_path = control_dir / f"stop-{token}.request"
        if not _managed_record_alive(record, state_path):
            state_path.unlink(missing_ok=True)
            request_path.unlink(missing_ok=True)
            stale += 1
            continue
        request_path.write_text(token, encoding="utf-8")
        deadline = time.monotonic() + timeout
        while state_path.exists() and _managed_record_alive(record, state_path) and time.monotonic() < deadline:
            time.sleep(0.1)
        if not state_path.exists() or not _managed_record_alive(record, state_path):
            state_path.unlink(missing_ok=True)
            request_path.unlink(missing_ok=True)
            stopped += 1
        else:
            pending += 1
    return stopped, stale, pending


def main() -> int:
    parser = argparse.ArgumentParser(description="Projektlokale Pipeline beenden")
    parser.add_argument("--port", type=int, help="Nur diese gestartete Instanz stoppen")
    parser.add_argument("--quiet-if-none", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    stopped, stale, pending = stop_managed(CONTROL_DIR, port=args.port)
    if stopped:
        print(f"Pipeline beendet: {stopped} Instanz(en).")
    if stale:
        print(f"Verwaiste Startereinträge entfernt: {stale}.")
    if pending:
        print(
            f"Stop angefordert; {pending} Instanz(en) warten noch auf laufende Arbeit. ",
            "Der Server beendet sich anschließend selbst.",
            file=sys.stderr,
        )
        return 2
    if not stopped and not stale:
        if not args.quiet_if_none:
            print("Keine über den Projekt-Starter laufende Pipeline gefunden.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
