"""Start suspended, assign to a private Windows job, then run. No escape window."""
from __future__ import annotations

import ctypes
from ctypes import wintypes as w
import os
import subprocess
import time


class STARTUPINFO(ctypes.Structure):
    _fields_ = [('cb', w.DWORD), ('lpReserved', w.LPWSTR), ('lpDesktop', w.LPWSTR),
                ('lpTitle', w.LPWSTR), ('dwX', w.DWORD), ('dwY', w.DWORD),
                ('dwXSize', w.DWORD), ('dwYSize', w.DWORD), ('dwXCountChars', w.DWORD),
                ('dwYCountChars', w.DWORD), ('dwFillAttribute', w.DWORD),
                ('dwFlags', w.DWORD), ('wShowWindow', w.WORD), ('cbReserved2', w.WORD),
                ('lpReserved2', ctypes.c_void_p), ('hStdInput', w.HANDLE),
                ('hStdOutput', w.HANDLE), ('hStdError', w.HANDLE)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', w.HANDLE), ('hThread', w.HANDLE),
                ('dwProcessId', w.DWORD), ('dwThreadId', w.DWORD)]


class BASIC_LIMIT(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                ('LimitFlags', w.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', w.DWORD),
                ('Affinity', ctypes.c_size_t), ('PriorityClass', w.DWORD), ('SchedulingClass', w.DWORD)]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in ('ReadOperationCount', 'WriteOperationCount',
                'OtherOperationCount', 'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class EXTENDED_LIMIT(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', BASIC_LIMIT), ('IoInfo', IO_COUNTERS),
                ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]


class ACCOUNTING(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int64) for name in ('TotalUserTime', 'TotalKernelTime',
                'ThisPeriodTotalUserTime', 'ThisPeriodTotalKernelTime')] + [
                (name, w.DWORD) for name in ('TotalPageFaultCount', 'TotalProcesses',
                'ActiveProcesses', 'TotalTerminatedProcesses')]


class ProcessGroup:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Der überwachte Desktopstarter unterstützt derzeit Windows.')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'CreateJobObjectW': ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            'SetInformationJobObject': ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            'QueryInformationJobObject': ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
            'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], w.BOOL),
            'CreateProcessW': ([w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, w.BOOL,
                                w.DWORD, ctypes.c_void_p, w.LPCWSTR,
                                ctypes.POINTER(STARTUPINFO), ctypes.POINTER(PROCESS_INFORMATION)], w.BOOL),
            'ResumeThread': ([w.HANDLE], w.DWORD),
            'TerminateProcess': ([w.HANDLE, w.UINT], w.BOOL),
            'TerminateJobObject': ([w.HANDLE, w.UINT], w.BOOL),
            'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
            'GetExitCodeProcess': ([w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL),
            'CloseHandle': ([w.HANDLE], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = args, result
        self.job = self.kernel.CreateJobObjectW(None, None)
        if not self.job:
            raise ctypes.WinError(ctypes.get_last_error())
        self.processes = []
        limits = EXTENDED_LIMIT()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.kernel.CloseHandle(self.job)
            raise error

    def start(self, command, *, cwd, env=None):
        startup = STARTUPINFO()
        startup.cb = ctypes.sizeof(startup)
        info = PROCESS_INFORMATION()
        environment = ctypes.create_unicode_buffer('\0'.join(
            f'{key}={value}' for key, value in sorted((env or os.environ).items(), key=lambda item: item[0].upper())
        ) + '\0\0')
        if not self.kernel.CreateProcessW(str(command[0]), ctypes.create_unicode_buffer(subprocess.list2cmdline(command)),
                None, None, False, 0x4 | 0x08000000 | 0x400, environment, str(cwd), ctypes.byref(startup), ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.kernel.AssignProcessToJobObject(self.job, info.hProcess):
                raise ctypes.WinError(ctypes.get_last_error())
            if self.kernel.ResumeThread(info.hThread) == 0xFFFFFFFF:
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            self.kernel.TerminateProcess(info.hProcess, 1)
            self.kernel.WaitForSingleObject(info.hProcess, 5000)
            self.kernel.CloseHandle(info.hProcess)
            raise
        finally:
            self.kernel.CloseHandle(info.hThread)
        self.processes.append(info.hProcess)
        return info.hProcess

    def wait(self, process):
        if self.kernel.WaitForSingleObject(process, 0xFFFFFFFF) != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        code = w.DWORD()
        if not self.kernel.GetExitCodeProcess(process, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        return code.value

    def poll(self, process):
        state = self.kernel.WaitForSingleObject(process, 0)
        if state == 258:
            return None
        if state != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        return self.wait(process)

    def close(self):
        if not self.job:
            return
        self.kernel.TerminateJobObject(self.job, 1)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            accounting = ACCOUNTING()
            if not self.kernel.QueryInformationJobObject(self.job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None):
                break
            if not accounting.ActiveProcesses:
                break
            time.sleep(.05)
        self.kernel.CloseHandle(self.job)
        self.job = None
        for process in self.processes:
            self.kernel.CloseHandle(process)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
