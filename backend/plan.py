from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any


SCENE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{2,63}$")

SOURCE_BY_VISUAL_TYPE = {
    "stickman": "procedural",
    "generated_image": "generate",
    "generated_video": "generate",
    "stock_video": "stock",
    "motion_graphics": "procedural",
    "talking_head": "provided",
    "waveform": "procedural",
}


def new_scene_id() -> str:
    return f"scene-{uuid.uuid4().hex[:12]}"


def finalize_scene_plan(
    script: dict[str, Any],
    target_duration: float,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a complete plan with unique stable scene ids and exact total duration."""
    result = copy.deepcopy(script)
    scenes = result.get("scenes") or []
    if not scenes:
        raise ValueError("Der Szenenplan ist leer")

    previous_scenes = (previous or {}).get("scenes") or []
    used_ids: set[str] = set()
    for index, scene in enumerate(scenes):
        candidate = str(scene.get("scene_id") or "")
        if (not SCENE_ID_PATTERN.fullmatch(candidate) or candidate in used_ids) and index < len(previous_scenes):
            previous_id = str(previous_scenes[index].get("scene_id") or "")
            if SCENE_ID_PATTERN.fullmatch(previous_id) and previous_id not in used_ids:
                candidate = previous_id
        if not SCENE_ID_PATTERN.fullmatch(candidate) or candidate in used_ids:
            candidate = new_scene_id()
        scene["scene_id"] = candidate
        used_ids.add(candidate)

        visual_type = scene.get("visual_type", "motion_graphics")
        scene["source_strategy"] = scene.get("source_strategy") or SOURCE_BY_VISUAL_TYPE.get(visual_type, "procedural")
        scene["source_ref"] = str(scene.get("source_ref") or "")

    raw_durations = [max(0.0, float(scene.get("duration_seconds") or 0)) for scene in scenes]
    if not any(raw_durations):
        raw_durations = [max(1.0, len(str(scene.get("narration", "")).split())) for scene in scenes]
    total_raw = sum(raw_durations)
    if total_raw <= 0:
        raise ValueError("Szenendauern können nicht berechnet werden")
    scaled = [max(0.1, target_duration * value / total_raw) for value in raw_durations]
    scaled_total = sum(scaled)
    scaled = [value * target_duration / scaled_total for value in scaled]
    rounded = [round(value, 3) for value in scaled]
    rounded[-1] = round(rounded[-1] + target_duration - sum(rounded), 3)
    for scene, duration in zip(scenes, rounded):
        scene["duration_seconds"] = duration
    return result


def canonical_script_hash(title: str, description: str, scenes: list[dict[str, Any]]) -> str:
    payload = {"title": title, "description": description, "scenes": scenes}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def script_hash(script: dict[str, Any]) -> str:
    return canonical_script_hash(script["title"], script.get("description", ""), script["scenes"])


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
