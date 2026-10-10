from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _chunks(text: str, max_words: int = 8) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(current) >= max_words or re.search(r"[.!?…][\"')\]]?$", word):
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks or [text]


def add_scene_captions(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for scene in scenes:
        chunks = _chunks(str(scene["narration"]))
        weights = [max(1, len(chunk.split())) for chunk in chunks]
        total_weight = sum(weights)
        duration = float(scene["duration"])
        cursor = 0.0
        captions = []
        words = scene.get('words') or []
        word_index = 0
        for index, (chunk, weight) in enumerate(zip(chunks, weights)):
            chunk_duration = duration - cursor if index == len(chunks) - 1 else duration * weight / total_weight
            if words:
                end_index = word_index+weight-1
                start = words[word_index]['start']
                end = words[min(end_index, len(words)-1)]['end']
                captions.append({'text':chunk, 'start':round(start,3), 'duration':round(end-start,3)})
                word_index += weight
            else:
                captions.append({"text": chunk, "start": round(cursor, 3), "duration": round(chunk_duration, 3)})
            cursor += chunk_duration
        scene["captions"] = captions
    return scenes


def _timestamp(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(scenes: list[dict[str, Any]], destination: Path) -> int:
    lines: list[str] = []
    cue = 1
    for scene in scenes:
        scene_start = float(scene["start"])
        for caption in scene.get("captions") or []:
            start = scene_start + float(caption["start"])
            end = start + float(caption["duration"])
            lines.extend([str(cue), f"{_timestamp(start)} --> {_timestamp(end)}", str(caption["text"]), ""])
            cue += 1
    destination.write_text("\n".join(lines), encoding="utf-8")
    return cue - 1
