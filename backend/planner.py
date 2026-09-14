from __future__ import annotations

import json
import re
import urllib.request
from typing import Any

from .config import settings
from .schemas import JobCreate, Scene


ACTIONS = ["intro", "walk", "point", "think", "explain", "celebrate", "outro"]
ACCENTS = ["#ff6b4a", "#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#fb7185"]


def _template(request: JobCreate) -> dict[str, Any]:
    topic = request.topic.rstrip(".?!")
    if request.language == "en":
        beats = [
            (f"Today we make {topic} easy to understand.", "A character opens the topic on a clean stage."),
            (f"First, let us identify what really matters about {topic}.", "The character walks toward three simple cards."),
            ("The key is to turn the big idea into a few clear steps.", "The character points at a growing step diagram."),
            ("Now compare the options and remove anything that adds effort without value.", "Two paths appear; the simpler path lights up."),
            (f"That gives you a practical way to use {topic} right away.", "The character celebrates beside a concise checklist."),
            ("Save this idea and follow for the next practical explanation.", "A final card and call to action appear."),
        ]
        title = f"{topic}: simply explained"
        description = f"A concise visual explanation of {topic}."
    else:
        beats = [
            (f"Heute machen wir {topic} einfach verständlich.", "Eine Figur eröffnet das Thema auf einer klaren Bühne."),
            (f"Zuerst schauen wir, was bei {topic} wirklich wichtig ist.", "Die Figur geht zu drei übersichtlichen Karten."),
            ("Der Schlüssel ist, die große Idee in wenige klare Schritte zu zerlegen.", "Die Figur zeigt auf ein wachsendes Stufendiagramm."),
            ("Dann vergleichen wir die Möglichkeiten und streichen unnötigen Aufwand.", "Zwei Wege erscheinen; der einfachere leuchtet auf."),
            (f"So kannst du {topic} direkt und praktisch anwenden.", "Die Figur feiert neben einer kurzen Checkliste."),
            ("Speichere die Idee und folge für die nächste praktische Erklärung.", "Eine Schlusskarte mit Handlungsaufforderung erscheint."),
        ]
        title = f"{topic}: einfach erklärt"
        description = f"Eine kompakte visuelle Erklärung zu {topic}."
    count = max(3, min(len(beats), round(request.duration_seconds / 10)))
    scenes = [
        {"narration": narration, "visual": visual, "action": ACTIONS[min(i, len(ACTIONS) - 1)], "accent": ACCENTS[i % len(ACCENTS)]}
        for i, (narration, visual) in enumerate(beats[:count])
    ]
    scenes[-1]["action"] = "outro"
    return {"title": title[:140], "description": description, "scenes": scenes}


def _prompt(request: JobCreate) -> str:
    return f"""Create a production-ready video script as strict JSON.
Language: {request.language}. Target duration: {request.duration_seconds} seconds.
Format: {request.aspect_ratio}. Video type: {request.video_type}. Topic: {request.topic}
Return exactly: {{"title":"...","description":"...","scenes":[{{"narration":"...","visual":"...","action":"intro|stand|walk|point|think|explain|celebrate|outro","accent":"#RRGGBB"}}]}}
Use 3-10 scenes, concise spoken language, a strong hook, useful original substance, and a natural call to action. Do not use markdown."""


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Model returned no JSON object")
    data = json.loads(match.group(0))
    scenes = [Scene.model_validate(scene).model_dump() for scene in data["scenes"]]
    if not 1 <= len(scenes) <= 30:
        raise ValueError("Invalid scene count")
    return {"title": str(data["title"])[:140], "description": str(data.get("description", ""))[:5000], "scenes": scenes}


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read())


def generate_script(request: JobCreate) -> dict[str, Any]:
    provider = settings.script_provider
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY fehlt")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        data = _post_json(url, {"contents": [{"parts": [{"text": _prompt(request)}]}], "generationConfig": {"responseMimeType": "application/json"}}, {})
        return _extract_json(data["candidates"][0]["content"]["parts"][0]["text"])
    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY fehlt")
        data = _post_json(
            "https://openrouter.ai/api/v1/chat/completions",
            {"model": settings.openrouter_model, "messages": [{"role": "user", "content": _prompt(request)}], "response_format": {"type": "json_object"}},
            {"Authorization": f"Bearer {settings.openrouter_api_key}"},
        )
        return _extract_json(data["choices"][0]["message"]["content"])
    return _template(request)
