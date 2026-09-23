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
        if not _pid_alive(pid):
            state_path.unlink(missing_ok=True)
            request_path.unlink(missing_ok=True)
            stale += 1
            continue
        request_path.write_text(token, encoding="utf-8")
        deadline = time.monotonic() + timeout
        while state_path.exists() and _pid_alive(pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        if not state_path.exists() or not _pid_alive(pid):
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
