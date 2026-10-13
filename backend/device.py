"""Read-only, local hardware detection and conservative model budgets."""
from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
PREFERENCES_PATH = ROOT / '.runtime' / 'machine-settings.json'
# Memory budgets include weights, working memory and a reserve for the OS/renderer.
# These are conservative application estimates, not vendor performance promises.
MODELS = {'qwen3.5:0.8b': (8, 3, 2), 'qwen3.5:2b': (12, 5, 4),
          'qwen3.5:4b': (16, 7, 4), 'qwen3.5:9b': (24, 11, 8),
          'qwen3.5:9b-q8_0': (32, 16, 8), 'qwen3.5:27b': (64, 26, 8)}
ModelName = Literal['qwen3.5:0.8b', 'qwen3.5:2b', 'qwen3.5:4b', 'qwen3.5:9b', 'qwen3.5:9b-q8_0', 'qwen3.5:27b']


class ManualHardware(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ram_gb: float = Field(ge=2, le=2048)
    cpu_threads: int = Field(ge=1, le=256)
    gpu_gb: float = Field(default=0, ge=0, le=256)


class MachinePreferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    model: ModelName
    voice: Literal['piper', 'qwen_tts'] = 'piper'
    script: Literal['local', 'antigravity'] = 'local'
    antigravity_model: str | None = Field(default=None, max_length=87, pattern=r'^gemini-[a-z0-9][a-z0-9.-]{0,79}$')
    hardware: ManualHardware | None = None


def hardware():
    ram = available = None
    try:
        if os.name == 'nt':
            class Memory(ctypes.Structure):
                _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                            *[(name, ctypes.c_ulonglong) for name in ('total', 'available', 'page_total', 'page_available', 'virtual_total', 'virtual_available', 'extended')]]
            memory = Memory()
            memory.length = ctypes.sizeof(memory)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
                ram, available = memory.total / 2**30, memory.available / 2**30
        elif platform.system() == 'Darwin':
            ram = int(subprocess.check_output(['sysctl', '-n', 'hw.memsize'], timeout=3)) / 2**30
            # Available memory is not reliably comparable on macOS; keep a 40% reserve.
            available = ram * .6
        else:
            info = {line.split(':')[0]: int(line.split()[1]) / 2**20 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:', 'MemAvailable:'))}
            ram, available = info.get('MemTotal'), info.get('MemAvailable')
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        pass
    gpu_gb, gpu_name = 0, 'Nicht sicher erkannt; Auswahl berücksichtigt CPU und RAM.'
    try:
        if shutil.which('nvidia-smi'):
            lines = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.total,name', '--format=csv,noheader,nounits'], timeout=3, text=True,
                                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).splitlines()
            gpu_gb, gpu_name = max((float(line.split(',', 1)[0]) / 1024, line.split(',', 1)[1].strip()[:100]) for line in lines)
        elif platform.system() == 'Darwin' and platform.machine() == 'arm64':
            gpu_name = 'Apple Silicon · gemeinsamer Arbeitsspeicher'
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return {'os': platform.system(), 'architecture': platform.machine(), 'cpu_threads': os.cpu_count(),
            'ram_gb': round(ram, 1) if ram else None, 'available_gb': round(available, 1) if available else None,
            'gpu_gb': round(gpu_gb, 1), 'gpu_name': gpu_name,
            'disk_free_gb': round(shutil.disk_usage(ROOT).free / 2**30, 1), 'manual': False}


def device_info(manual=None):
    info = dict(hardware())
    if manual:
        info.update(ram_gb=min(info['ram_gb'],manual.ram_gb) if info['ram_gb'] else manual.ram_gb,
                    cpu_threads=min(info['cpu_threads'],manual.cpu_threads) if info['cpu_threads'] else manual.cpu_threads,
                    gpu_gb=manual.gpu_gb, manual=True)
        info['available_gb'] = min(manual.ram_gb * .6, info['available_gb']) if info['available_gb'] else manual.ram_gb * .6
    return info


def recommendation(info):
    ram, free, cores = info['ram_gb'], info['available_gb'], info['cpu_threads']
    allowed = []
    supported = info['os'] in {'Windows','Linux','Darwin'} and info['architecture'].lower() in {'amd64','x86_64','arm64','aarch64'}
    if supported and ram and free and cores:
        for name, (minimum, working, threads) in MODELS.items():
            if ram >= minimum - .5 and free >= working and cores >= threads and info['disk_free_gb'] >= working + 4:
                if name == 'qwen3.5:27b' and not (info['gpu_gb'] >= 24 or info['os'] == 'Darwin' and info['architecture'] == 'arm64'):
                    continue
                allowed.append(name)
    qwen = bool(ram and ram >= 23.5 and free and free >= 12 and cores and cores >= 4)
    qwen_platform = info['os'] in {'Windows','Linux'} and info['architecture'].lower() in {'amd64','x86_64'} or info['os'] == 'Darwin' and info['architecture'].lower() in {'arm64','x86_64'}
    return {'model': allowed[-1] if allowed else None, 'allowed_models': allowed,
            'voice': 'qwen_tts' if qwen and qwen_platform else 'piper', 'qwen_suitable': qwen,
            'reason': 'Größtes Modell innerhalb der lokalen Speicher- und CPU-Budgets. Die tatsächliche Geschwindigkeit hängt vom Gerät ab.' if allowed else
                      'Keine sichere Modellwahl möglich. Prüfe freien Speicher oder ergänze RAM und CPU-Angaben. Für lokale Skripte sind mindestens 8 GB RAM vorgesehen.',
            'voice_reason': 'Qwen klingt natürlicher, braucht auf einer CPU aber deutlich länger.' if qwen and qwen_platform else 'Piper benötigt wenig Arbeitsspeicher und ist auf diesem Gerät die sparsame Wahl.'}


def load_preferences():
    try:
        if PREFERENCES_PATH.stat().st_size > 4096:
            return None
        return MachinePreferences.model_validate_json(PREFERENCES_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def apply_preferences(settings, preferences, *, adapt=False):
    detected = os.cpu_count()
    cores = min(detected,preferences.hardware.cpu_threads) if detected and preferences.hardware else (detected or (preferences.hardware.cpu_threads if preferences.hardware else 2))
    values = {'script_provider': 'ollama' if preferences.script == 'local' else 'antigravity',
              'ollama_base_url': 'http://127.0.0.1:11434',
              'ollama_model': preferences.model, 'tts_provider': preferences.voice,
              'render_concurrency': 1 if cores < 8 else 2, 'qwen_tts_threads': max(1, min(8, cores // 2)),
              'ollama_num_ctx': 8192, 'ollama_num_predict': 4096}
    if preferences.script == 'antigravity':
        values['antigravity_fallback_to_qwen'] = False
        if preferences.antigravity_model:
            values['antigravity_model'] = preferences.antigravity_model
    if adapt:
        # A copied configuration must not treat old manual device values as a
        # fresh measurement. Unknown hardware needs confirmation in settings.
        choice = recommendation(device_info())
        if preferences.model not in choice['allowed_models']:
            values['ollama_model'] = choice['model'] or ''
        if not choice['qwen_suitable']:
            values['tts_provider'] = 'piper'
    # One existing Settings instance is shared by every backend module.
    # Only these bounded non-secret fields may be changed by the UI.
    for key, value in values.items():
        object.__setattr__(settings, key, value)


def save_preferences(preferences, settings):
    if not PREFERENCES_PATH.parent.resolve().is_relative_to(ROOT):
        raise ValueError('Geräteeinstellungen müssen im Projektordner bleiben.')
    PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=PREFERENCES_PATH.parent, delete=False) as output:
        output.write(preferences.model_dump_json())
        temporary = Path(output.name)
    if os.name != 'nt':
        temporary.chmod(0o600)
    temporary.replace(PREFERENCES_PATH)
    apply_preferences(settings, preferences)
