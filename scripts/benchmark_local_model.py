#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

from backend.config import settings
from backend.planner import generate_script
from backend.schemas import JobCreate


CASES = [
    JobCreate(
        topic="Warum wiedervernässte Moore das Klima schützen",
        language="de",
        duration_seconds=45,
        aspect_ratio="16:9",
        video_type="explainer",
        target_platform="download",
    ),
    JobCreate(
        topic="Wie Schlaf neue Erinnerungen festigt",
        language="de",
        duration_seconds=45,
        aspect_ratio="9:16",
        video_type="social",
        target_platform="download",
    ),
]


def memory_snapshot() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, raw = line.split(":", 1)
        if key in {"MemAvailable", "SwapTotal", "SwapFree"}:
            values[key] = int(raw.strip().split()[0]) * 1024
    values["SwapUsed"] = values.get("SwapTotal", 0) - values.get("SwapFree", 0)
    return values


def loaded_models() -> list[dict[str, Any]]:
    try:
        with urllib.request.urlopen(f"{settings.ollama_base_url}/api/ps", timeout=5) as response:
            return json.loads(response.read()).get("models", [])
    except Exception:
        return []


def sample_memory(stop: threading.Event, peak: dict[str, int]) -> None:
    while not stop.wait(0.25):
        snapshot = memory_snapshot()
        peak["min_mem_available_bytes"] = min(
            peak["min_mem_available_bytes"], snapshot.get("MemAvailable", 0)
        )
        peak["max_swap_used_bytes"] = max(
            peak["max_swap_used_bytes"], snapshot.get("SwapUsed", 0)
        )


def run_case(label: str, request: JobCreate, **kwargs: Any) -> dict[str, Any]:
    before = memory_snapshot()
    peak = {
        "min_mem_available_bytes": before.get("MemAvailable", 0),
        "max_swap_used_bytes": before.get("SwapUsed", 0),
    }
    stop = threading.Event()
    sampler = threading.Thread(target=sample_memory, args=(stop, peak), daemon=True)
    sampler.start()
    started = time.perf_counter()
    try:
        script = generate_script(request, **kwargs)
        elapsed = time.perf_counter() - started
    finally:
        stop.set()
        sampler.join(timeout=1)
    after = memory_snapshot()
    return {
        "label": label,
        "request": request.model_dump(),
        "wall_seconds": round(elapsed, 3),
        "memory_before": before,
        "memory_after": after,
        "memory_peak": peak,
        "loaded_models": loaded_models(),
        "format_valid": True,
        "scene_count": len(script["scenes"]),
        "narration_words": sum(len(scene["narration"].split()) for scene in script["scenes"]),
        "script": script,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    results = [
        run_case("moor-original", CASES[0]),
        run_case("schlaf-original", CASES[1]),
    ]
    first_script = results[0]["script"]
    results.append(run_case(
        "moor-revision",
        CASES[0],
        previous=first_script,
        instructions=(
            "Ersetze die zweite Szene durch eine leicht verständliche Schwamm-Analogie. "
            "Formuliere sachlich, kennzeichne überprüfungsbedürftige Zahlen und bewahre die übrigen starken Szenen."
        ),
    ))
    report = {
        "model": settings.ollama_model,
        "base_url": settings.ollama_base_url,
        "num_ctx": settings.ollama_num_ctx,
        "num_predict": settings.ollama_num_predict,
        "keep_alive": settings.ollama_keep_alive,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "model": report["model"],
        "cases": [{"label": item["label"], "seconds": item["wall_seconds"], "scenes": item["scene_count"]} for item in results],
        "output": str(args.output),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
