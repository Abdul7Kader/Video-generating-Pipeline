from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from .config import settings
from .plan import finalize_scene_plan
from .schemas import JobCreate, ScriptDraft


class ScriptProviderUnavailable(RuntimeError):
    """No deliberately configured AI script provider is available."""


ACTIONS = ["intro", "walk", "point", "think", "explain", "celebrate", "outro"]
ACCENTS = ["#ff6b4a", "#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#fb7185"]

STYLE_DIRECTIONS = {
    "stickman": (
        "Use intentional stick-figure animation with visual metaphors, props and diagrams. "
        "Set visual_type to stickman; asset_prompt describes the actual pose, props and background."
    ),
    "explainer": (
        "Design a polished explainer using a varied mix of generated imagery and motion graphics. "
        "Prefer concrete demonstrations, relevant stock footage or photography, diagrams and meaningful objects; never default to a presenter or stick figure."
    ),
    "social": (
        "Design a fast, visually varied social clip with a strong first-second hook, purposeful B-roll, "
        "pattern interrupts and concise on-screen emphasis. Avoid generic motivational cards."
    ),
    "podcast": (
        "Design a podcast-style edit around a speaker/talking-head or waveform layout, enhanced with relevant B-roll, "
        "chapter cards and restrained motion graphics. Do not invent a visible speaker identity."
    ),
    "generated": (
        "Design cinematic AI-generated shots. Use generated_video where motion materially helps and generated_image "
        "for controlled stills with camera movement. Prompts must specify subject, setting, composition, light, lens and motion."
    ),
}


def _response_schema() -> dict[str, Any]:
    scene_properties: dict[str, Any] = {
        "scene_id": {"type": "string", "description": "Stable id such as scene-a1b2c3; preserve it when revising the same scene."},
        "narration": {"type": "string", "description": "Only the naturally spoken voice-over for this scene."},
        "visual": {"type": "string", "description": "A concrete description of what is visibly on screen."},
        "visual_type": {
            "type": "string",
            "enum": ["stickman", "generated_image", "generated_video", "stock_image", "stock_video", "motion_graphics", "talking_head", "waveform"],
        },
        "source_strategy": {"type": "string", "enum": ["generate", "stock", "provided", "procedural", "recorded"]},
        "source_ref": {"type": "string", "description": "Provided/local source reference, or empty until production resolves the asset."},
        "asset_query": {"type": "string", "description": "Two to eight concrete English search terms for a stock library, or empty if not stock."},
        "asset_prompt": {"type": "string", "description": "Standalone prompt or search brief used to obtain the visual asset; no captions."},
        "on_screen_text": {"type": "string", "description": "Exact short text intentionally shown on screen, or an empty string."},
        "camera": {"type": "string", "description": "Framing and camera or graphic movement."},
        "transition": {"type": "string", "enum": ["cut", "dissolve", "wipe", "zoom", "match_cut", "none"]},
        "duration_seconds": {"type": "number", "minimum": 0.1, "maximum": 180},
        "action": {"type": "string", "enum": ["intro", "stand", "walk", "point", "think", "explain", "celebrate", "outro"]},
        "accent": {"type": "string", "description": "A six-digit hexadecimal accent color such as #38bdf8."},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "audience": {"type": "string"},
            "tone": {"type": "string"},
            "fact_check_notes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Claims that need a current source check; empty for timeless/non-factual content.",
            },
            "scenes": {
                "type": "array",
                "minItems": 3,
                "maxItems": 30,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": scene_properties,
                    "required": list(scene_properties),
                },
            },
        },
        "required": ["title", "description", "audience", "tone", "fact_check_notes", "scenes"],
    }


def _template(request: JobCreate) -> dict[str, Any]:
    """Test/development fallback, available only through an explicit opt-in."""
    topic = request.topic.rstrip(".?!")
    if request.language == "en":
        beats = [
            (f"Today we make {topic} easy to understand.", "A bold visual metaphor introduces the specific topic."),
            (f"First, identify what really matters about {topic}.", "Three topic-specific objects establish the core factors."),
            ("Turn the central idea into a sequence of concrete decisions.", "A diagram connects the decisions in a clear sequence."),
            (f"Now you can apply the central idea behind {topic} deliberately.", "The opening metaphor returns with a resolved outcome."),
        ]
        title = f"{topic}: explained"
        description = f"A concise visual explanation of {topic}."
    else:
        beats = [
            (f"Heute machen wir {topic} verständlich.", "Eine prägnante visuelle Metapher führt in das konkrete Thema ein."),
            (f"Zuerst bestimmen wir, was bei {topic} wirklich zählt.", "Drei themenspezifische Objekte zeigen die Kernfaktoren."),
            ("Dann wird aus der Kernidee eine Folge konkreter Entscheidungen.", "Ein Diagramm verbindet die Entscheidungen zu einer klaren Abfolge."),
            (f"So lässt sich die zentrale Idee hinter {topic} bewusst anwenden.", "Die Anfangsmetapher kehrt mit einem sichtbaren Ergebnis zurück."),
        ]
        title = f"{topic}: erklärt"
        description = f"Eine kompakte visuelle Erklärung zu {topic}."
    visual_type = "stickman" if request.video_type == "stickman" else "motion_graphics"
    scenes = [
        {
            "narration": narration,
            "visual": visual,
            "visual_type": visual_type,
            "source_strategy": "procedural" if visual_type in {"stickman", "motion_graphics"} else "generate",
            "source_ref": "",
            "asset_query": topic,
            "asset_prompt": visual,
            "on_screen_text": "",
            "camera": "Ruhige, klare Bewegung auf das Hauptmotiv.",
            "transition": "cut",
            "duration_seconds": request.duration_seconds / len(beats),
            "action": ACTIONS[min(i, len(ACTIONS) - 1)],
            "accent": ACCENTS[i % len(ACCENTS)],
        }
        for i, (narration, visual) in enumerate(beats)
    ]
    scenes[-1]["action"] = "outro"
    return {
        "title": title[:140],
        "description": description,
        "audience": "Development test only",
        "tone": "Neutral",
        "fact_check_notes": ["Template output is not an AI-researched production script."],
        "scenes": scenes,
    }


def _system_prompt() -> str:
    return (
        "You are a senior documentary writer, visual director and editor. Create specific, useful content rather than a reusable template. "
        "Every spoken sentence must advance the subject. Do not invent facts, quotations, statistics or sources. Put claims that require current "
        "verification into fact_check_notes. Treat visual as an instruction for production, never as text that should be displayed. Only "
        "on_screen_text may be rendered as text. Return JSON matching the supplied schema and nothing else."
    )


def _prompt(request: JobCreate, previous: dict[str, Any] | None = None, instructions: str | None = None) -> str:
    words_per_minute = 130 if request.language == "de" else 145
    target_words = round(request.duration_seconds * words_per_minute / 60)
    scene_count_min = max(3, min(12, round(request.duration_seconds / 12)))
    scene_count_max = max(scene_count_min, min(20, round(request.duration_seconds / 6)))
    mode = (
        "Revise the existing draft below. Follow the requested changes precisely and preserve strong material that was not targeted."
        if previous
        else "Create a new production-ready script and shot plan from the brief."
    )
    revision_block = ""
    if previous:
        clean_previous = {key: value for key, value in previous.items() if key not in {"metadata", "created_at", "job_id", "version"}}
        revision_block = (
            f"\nRequested changes: {instructions}\n"
            f"Existing draft JSON:\n{json.dumps(clean_previous, ensure_ascii=False)}\n"
        )
    return f"""{mode}

Brief
- Topic: {request.topic}
- Language of narration and on-screen text: {request.language}
- Target duration: {request.duration_seconds} seconds
- Approximate narration target: {target_words} words (natural pacing; do not pad)
- Aspect ratio: {request.aspect_ratio}
- Video style: {request.video_type}
- Intended destination: {request.target_platform}
- Scene count: {scene_count_min}-{scene_count_max}

Style direction
{STYLE_DIRECTIONS[request.video_type]}

Editorial requirements
- Start with a subject-specific hook, then build a coherent argument or story with a satisfying conclusion.
- Prefer precise examples, causal explanations and concrete takeaways over generic advice.
- Narration must sound natural when spoken aloud; do not include headings, stage directions or citation markers in narration.
- Keep deliberate on-screen text short. Never copy the visual instruction or full narration into on_screen_text.
- Assign a stable scene_id to every scene. When revising, preserve the id if the scene's purpose remains; create a new id for a replacement scene.
- Set duration_seconds per scene so their sum is the target duration. Match time to spoken length and visual complexity.
- Choose source_strategy deliberately: generate, stock, provided, recorded or procedural. Leave source_ref empty unless the brief supplied a real source.
- For stock_image or stock_video, set asset_query to two to eight concrete English search terms. Do not put camera instructions into the search query.
- Make adjacent shots visually distinct while maintaining continuity of people, places, era, palette and art direction.
- asset_prompt must be directly usable for image/video generation or asset search and must not ask the image model to draw words.
- Use generated_video sparingly where visible motion matters; prefer generated_image with camera movement for controllable shots.
- For factual/current topics, avoid unsupported certainty and list every claim needing verification in fact_check_notes.
{revision_block}"""


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Das Modell hat kein JSON-Objekt geliefert")
    try:
        raw = json.loads(match.group(0))
        draft = ScriptDraft.model_validate(raw)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Ungültiges strukturiertes Skript: {exc}") from exc
    return draft.model_dump()


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            details = exc.read().decode("utf-8", errors="replace")[:600]
        except Exception:
            details = ""
        raise RuntimeError(f"Anbieter antwortete mit HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Anbieter ist nicht erreichbar: {exc.reason}") from exc


def _selected_provider() -> tuple[str, str]:
    provider = settings.script_provider
    if provider == "auto":
        if settings.gemini_api_key:
            return "gemini", settings.gemini_model
        if settings.openai_api_key:
            return "openai", settings.openai_model
        if settings.openrouter_api_key and settings.openrouter_model:
            return "openrouter", settings.openrouter_model
        raise ScriptProviderUnavailable(
            "Kein KI-Skriptanbieter konfiguriert. Setze bewusst SCRIPT_PROVIDER und den zugehörigen API-Schlüssel."
        )
    if provider == "gemini" and settings.gemini_api_key:
        return provider, settings.gemini_model
    if provider == "openai" and settings.openai_api_key:
        return provider, settings.openai_model
    if provider == "openrouter" and settings.openrouter_api_key and settings.openrouter_model:
        return provider, settings.openrouter_model
    if provider == "template" and settings.allow_template_script:
        return provider, "development-template"
    if provider not in {"gemini", "openai", "openrouter", "template", "auto"}:
        raise ScriptProviderUnavailable(f"Unbekannter SCRIPT_PROVIDER: {provider}")
    if provider == "template":
        raise ScriptProviderUnavailable("Der Vorlagenplaner ist deaktiviert. ALLOW_TEMPLATE_SCRIPT=1 ist nur für Entwicklungstests gedacht.")
    raise ScriptProviderUnavailable(f"{provider} ist gewählt, aber API-Schlüssel oder Modell fehlen.")


def script_provider_status() -> dict[str, Any]:
    try:
        provider, model = _selected_provider()
        return {"ready": provider != "template", "provider": provider, "model": model, "requested": settings.script_provider}
    except ScriptProviderUnavailable as exc:
        return {"ready": False, "provider": None, "model": None, "requested": settings.script_provider, "message": str(exc)}


def generate_script(
    request: JobCreate,
    *,
    previous: dict[str, Any] | None = None,
    instructions: str | None = None,
) -> dict[str, Any]:
    provider, model = _selected_provider()
    prompt = _prompt(request, previous, instructions)
    if provider == "template":
        script = _template(request)
    elif provider == "gemini":
        url = "https://generativelanguage.googleapis.com/v1beta/interactions"
        data = _post_json(
            url,
            {
                "model": model,
                "input": f"{_system_prompt()}\n\n{prompt}",
                "response_format": {
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": _response_schema(),
                },
            },
            {"x-goog-api-key": settings.gemini_api_key},
        )
        script = _extract_json(data["output_text"])
    else:
        base_url = settings.openai_base_url if provider == "openai" else "https://openrouter.ai/api/v1"
        api_key = settings.openai_api_key if provider == "openai" else settings.openrouter_api_key
        data = _post_json(
            f"{base_url}/chat/completions",
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "video_script", "strict": True, "schema": _response_schema()},
                },
            },
            {"Authorization": f"Bearer {api_key}"},
        )
        script = _extract_json(data["choices"][0]["message"]["content"])
    fact_check_notes = script.pop("fact_check_notes", [])
    audience = script.pop("audience", "")
    tone = script.pop("tone", "")
    script["metadata"] = {
        "provider": provider,
        "model": model,
        "audience": audience,
        "tone": tone,
        "fact_check_notes": fact_check_notes,
        "revision": bool(previous),
    }
    return finalize_scene_plan(script, request.duration_seconds, previous)
