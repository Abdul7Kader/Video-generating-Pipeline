from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import settings
from .plan import SOURCE_BY_VISUAL_TYPE, finalize_scene_plan
from .schemas import JobCreate, ScriptDraft


class ScriptProviderUnavailable(RuntimeError):
    """No deliberately configured AI script provider is available."""


class ProviderHTTPError(RuntimeError):
    """Sanitized upstream HTTP failure with retry information but no credentials."""

    def __init__(self, status_code: int, reason: str = "", *, retry_after: float | None = None):
        super().__init__(f"Anbieter antwortete mit HTTP {status_code}.")
        self.status_code = status_code
        self.reason = reason
        self.retry_after = retry_after


class ProviderConnectionError(RuntimeError):
    """Upstream could not be reached without exposing request details."""


_OLLAMA_CALL_LOCK = threading.Lock()
_LOCAL_OLLAMA_HOSTS = {"127.0.0.1", "localhost", "ollama"}
_RETRYABLE_GEMINI_STATUS = {429, 500, 502, 503, 504}


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
        "narration": {"type": "string", "minLength": 2, "maxLength": 400, "description": "Only the naturally spoken voice-over for this scene."},
        "visual": {"type": "string", "minLength": 10, "maxLength": 280, "description": "A natural-language description of what is visibly on screen, never a media-type enum."},
        "visual_type": {
            "type": "string",
            "enum": ["stickman", "generated_image", "generated_video", "stock_image", "stock_video", "motion_graphics", "talking_head", "waveform"],
        },
        "asset_query": {"type": "string", "maxLength": 120, "description": "Two to eight concrete English search terms for a stock library, or empty if not stock."},
        "asset_prompt": {"type": "string", "minLength": 10, "maxLength": 500, "description": "Concise standalone prompt or search brief used to obtain the visual asset; no captions."},
        "on_screen_text": {"type": "string", "maxLength": 80, "description": "Exact short text intentionally shown on screen, or an empty string."},
        "camera": {"type": "string", "maxLength": 120, "description": "Concise framing and camera or graphic movement."},
        "transition": {"type": "string", "enum": ["cut", "dissolve", "wipe", "zoom", "match_cut", "none"]},
        "duration_seconds": {"type": "number", "minimum": 0.1, "maximum": 180},
        "action": {"type": "string", "enum": ["intro", "stand", "walk", "point", "think", "explain", "celebrate", "outro"]},
        "accent": {
            "type": "string",
            "enum": ACCENTS,
            "description": "Choose exactly one hexadecimal accent color from this production palette.",
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string", "minLength": 2, "maxLength": 100},
            "description": {"type": "string", "maxLength": 280},
            "audience": {"type": "string", "minLength": 2, "maxLength": 120},
            "tone": {"type": "string", "minLength": 2, "maxLength": 120},
            "fact_check_notes": {
                "type": "array",
                "items": {"type": "string", "maxLength": 240},
                "maxItems": 6,
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
        "verification into fact_check_notes, but never use a note as permission to keep an unsupported claim in narration. If the brief supplies no "
        "source, omit exact quantities, rankings and comparative performance claims from narration and visuals. You have no web access: never say "
        "or imply that you researched, verified, browsed or sourced a claim. "
        "Treat visual as an instruction for production, never as text that should be displayed. Only "
        "on_screen_text may be rendered as text. Use polished, grammatically correct language consistently in every audience-facing field. "
        "Never emit placeholders such as %s, TODO or template variables. Return JSON matching the supplied schema and nothing else."
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
- Without supplied sources, avoid exact numbers, rankings, superlatives and claims of certainty. State only robust high-level mechanisms, and quote every claim needing verification precisely in fact_check_notes.
- An analogy may clarify one aspect but must never pretend to reproduce the scientific mechanism. Explain where necessary what the analogy does and does not mean.
- Narration must sound natural when spoken aloud; do not include headings, stage directions or citation markers in narration.
- Do not add a commercial, political or donation call to action unless the brief explicitly asks for one.
- Do not add follow, subscribe, like, next-episode or teaser cards unless explicitly requested. End with the subject's clearest conclusion.
- Keep deliberate on-screen text short. Never copy the visual instruction or full narration into on_screen_text.
- Keep each visual under 20 words, each asset_prompt under 35 words and each camera instruction under 10 words. Be concrete, not verbose.
- visual is a natural-language description of the visible shot. It must never contain only a value such as generated_image or stock_video.
- Assign a stable scene_id to every scene. When revising, preserve the id if the scene's purpose remains; create a new id for a replacement scene.
- Set duration_seconds per scene so their sum is the target duration. Match time to spoken length and visual complexity.
- For stock_image or stock_video, set asset_query to two to eight concrete English search terms. Do not put camera instructions into the search query.
- Make adjacent shots visually distinct while maintaining continuity of people, places, era, palette and art direction.
- asset_prompt must be directly usable for image/video generation or asset search and must not ask the image model to draw words.
- Choose accent only from the hexadecimal colors allowed by the response schema; accent never means a language or locale.
- Use generated_video sparingly where visible motion matters; prefer generated_image with camera movement for controllable shots.
- For factual/current topics, avoid unsupported certainty and list every claim needing verification in fact_check_notes.
- Before returning, silently check every narration sentence for grammar, unsupported quantities/comparisons, internal contradictions and generic filler; correct or remove failures.
{revision_block}"""


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Das Modell hat kein JSON-Objekt geliefert")
    try:
        raw = json.loads(match.group(0))
        for scene in raw.get("scenes", []):
            visual_type = scene.get("visual_type")
            scene["source_strategy"] = SOURCE_BY_VISUAL_TYPE.get(visual_type)
            scene["source_ref"] = ""
            if str(scene.get("visual", "")).strip() in SOURCE_BY_VISUAL_TYPE:
                scene["visual"] = scene.get("asset_prompt", "")
            if visual_type not in {"stock_image", "stock_video"}:
                scene["asset_query"] = ""
            elif not str(scene.get("asset_query", "")).strip():
                raise ValueError("Stock-Szene enthält keinen konkreten Suchbegriff")
        draft = ScriptDraft.model_validate(raw)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Ungültiges strukturiertes Skript: {exc}") from exc
    return draft.model_dump()


def _validate_editorial_output(script: dict[str, Any]) -> None:
    placeholder = re.compile(r"%s|\bTODO\b|\{\{[^}]+\}\}|\$\{[^}]+\}", re.IGNORECASE)
    fields: list[str] = [
        str(script.get("title", "")),
        str(script.get("description", "")),
        *(str(note) for note in script.get("fact_check_notes", [])),
    ]
    for scene in script.get("scenes", []):
        fields.extend(str(scene.get(key, "")) for key in (
            "narration", "visual", "asset_query", "asset_prompt", "on_screen_text", "camera"
        ))
    if any(placeholder.search(value) for value in fields):
        raise ValueError("Das lokale Modell lieferte einen nicht ausgefüllten Platzhalter im Szenenplan.")


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
        retry_after: float | None = None
        retry_header = exc.headers.get("Retry-After") if exc.headers else None
        if retry_header:
            try:
                retry_after = max(0.0, min(30.0, float(retry_header)))
            except ValueError:
                retry_after = None
        try:
            body = json.loads(exc.read().decode("utf-8", errors="replace"))
            reason = str(body.get("error", {}).get("status", ""))[:80]
        except Exception:
            reason = ""
        raise ProviderHTTPError(exc.code, reason, retry_after=retry_after) from exc
    except urllib.error.URLError as exc:
        raise ProviderConnectionError("Anbieter ist nicht erreichbar.") from exc


def _post_gemini(payload: dict[str, Any]) -> dict[str, Any]:
    """Use Google's documented bounded exponential backoff for transient API errors."""
    attempts = max(0, min(3, settings.gemini_max_retries)) + 1
    for attempt in range(attempts):
        try:
            return _post_json(
                "https://generativelanguage.googleapis.com/v1beta/interactions",
                payload,
                {"x-goog-api-key": settings.gemini_api_key},
            )
        except ProviderHTTPError as exc:
            if exc.status_code not in _RETRYABLE_GEMINI_STATUS or attempt == attempts - 1:
                raise
            delay = exc.retry_after
            if delay is None:
                delay = min(30.0, settings.gemini_retry_base_seconds * (2**attempt))
            time.sleep(delay)
    raise RuntimeError("Gemini-Wiederholungslogik endete unerwartet.")


def _ollama_url(path: str) -> str:
    parsed = urllib.parse.urlparse(settings.ollama_base_url)
    if parsed.scheme != "http" or parsed.hostname not in _LOCAL_OLLAMA_HOSTS:
        raise ScriptProviderUnavailable(
            "OLLAMA_BASE_URL muss lokal (127.0.0.1/localhost) oder der interne Containerdienst 'ollama' sein."
        )
    return f"{settings.ollama_base_url}{path}"


def _post_ollama(payload: dict[str, Any], *, timeout: int | None = None) -> dict[str, Any]:
    request = urllib.request.Request(
        _ollama_url("/api/chat"),
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout or settings.ollama_timeout_seconds) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")[:600]
        raise RuntimeError(f"Lokales Ollama antwortete mit HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise ScriptProviderUnavailable(
            f"Lokales Ollama ist unter {settings.ollama_base_url} nicht erreichbar. Starte den lokalen Modelldienst."
        ) from exc
    except TimeoutError as exc:
        raise RuntimeError(
            f"Das lokale Modell überschritt das Zeitlimit von {timeout or settings.ollama_timeout_seconds} Sekunden."
        ) from exc


def _generate_with_ollama(prompt: str, model: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": prompt},
        ],
        "format": _response_schema(),
        "stream": False,
        "think": False,
        "keep_alive": settings.ollama_keep_alive,
        "options": {
            "num_ctx": settings.ollama_num_ctx,
            "num_predict": settings.ollama_num_predict,
            "temperature": 0.35,
            "top_p": 0.9,
            "seed": 42,
        },
    }
    if not _OLLAMA_CALL_LOCK.acquire(blocking=False):
        raise ScriptProviderUnavailable(
            "Das lokale Modell erstellt bereits ein Skript. Bitte den laufenden Entwurf abwarten und dann erneut versuchen."
        )
    try:
        data = _post_ollama(payload)
    finally:
        _OLLAMA_CALL_LOCK.release()
    try:
        script = _extract_json(data["message"]["content"])
    except (KeyError, TypeError) as exc:
        raise ValueError("Lokales Ollama lieferte keine verwertbare Skriptantwort.") from exc
    metrics = {
        "total_duration_ms": round(int(data.get("total_duration") or 0) / 1_000_000),
        "load_duration_ms": round(int(data.get("load_duration") or 0) / 1_000_000),
        "prompt_tokens": data.get("prompt_eval_count"),
        "output_tokens": data.get("eval_count"),
        "done_reason": data.get("done_reason"),
        "num_ctx": settings.ollama_num_ctx,
        "num_predict": settings.ollama_num_predict,
    }
    return script, metrics


def _generate_with_gemini(prompt: str, model: str) -> tuple[dict[str, Any], dict[str, Any]]:
    data = _post_gemini({
        "model": model,
        "input": f"{_system_prompt()}\n\n{prompt}",
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": _response_schema(),
        },
    })
    try:
        return _extract_json(data["output_text"]), {}
    except (KeyError, TypeError) as exc:
        raise ValueError("Gemini lieferte keine verwertbare Skriptantwort.") from exc


def _selected_provider() -> tuple[str, str]:
    provider = settings.script_provider
    if provider == "auto":
        # Local inference is always preferred. Cloud adapters remain available
        # only when explicitly selected; they are never an automatic fallback.
        return "ollama", settings.ollama_model
    if provider == "ollama" and settings.ollama_model:
        _ollama_url("")
        return provider, settings.ollama_model
    if provider == "gemini" and settings.gemini_api_key:
        return provider, settings.gemini_model
    if provider == "gemini_ollama" and settings.ollama_model:
        _ollama_url("")
        models = f"{settings.gemini_model} → {settings.ollama_model}" if settings.gemini_api_key else settings.ollama_model
        return provider, models
    if provider == "openai" and settings.openai_api_key:
        return provider, settings.openai_model
    if provider == "openrouter" and settings.openrouter_api_key and settings.openrouter_model:
        return provider, settings.openrouter_model
    if provider == "template" and settings.allow_template_script:
        return provider, "development-template"
    if provider not in {"ollama", "gemini", "gemini_ollama", "openai", "openrouter", "template", "auto"}:
        raise ScriptProviderUnavailable(f"Unbekannter SCRIPT_PROVIDER: {provider}")
    if provider == "template":
        raise ScriptProviderUnavailable("Der Vorlagenplaner ist deaktiviert. ALLOW_TEMPLATE_SCRIPT=1 ist nur für Entwicklungstests gedacht.")
    raise ScriptProviderUnavailable(f"{provider} ist gewählt, aber API-Schlüssel oder Modell fehlen.")


def script_provider_status() -> dict[str, Any]:
    try:
        provider, model = _selected_provider()
        status = {"ready": provider != "template", "provider": provider, "model": model, "requested": settings.script_provider}
        if provider in {"ollama", "gemini_ollama"}:
            local_model = settings.ollama_model
            request = urllib.request.Request(_ollama_url("/api/tags"), method="GET")
            try:
                with urllib.request.urlopen(request, timeout=2) as response:
                    installed = {item.get("name") for item in json.loads(response.read()).get("models", [])}
                local_ready = local_model in installed
            except (OSError, ValueError, urllib.error.URLError):
                local_ready = False
            if provider == "ollama":
                status["ready"] = local_ready
                if not local_ready:
                    status["message"] = f"Lokales Ollama oder Modell {local_model} ist nicht erreichbar."
            else:
                status["cloud_configured"] = bool(settings.gemini_api_key)
                status["fallback_model"] = local_model
                status["fallback_ready"] = local_ready
                status["ready"] = bool(settings.gemini_api_key) or local_ready
                if not settings.gemini_api_key and local_ready:
                    status["message"] = "Gemini API ist nicht konfiguriert; lokales Qwen wird direkt verwendet."
                elif not local_ready:
                    status["message"] = "Gemini ist konfiguriert; lokaler Qwen-Fallback ist derzeit nicht bereit."
        return status
    except ScriptProviderUnavailable as exc:
        return {"ready": False, "provider": None, "model": None, "requested": settings.script_provider, "message": str(exc)}


def generate_script(
    request: JobCreate,
    *,
    previous: dict[str, Any] | None = None,
    instructions: str | None = None,
) -> dict[str, Any]:
    provider, model = _selected_provider()
    requested_provider = provider
    actual_provider = provider
    actual_model = model
    fallback_metadata: dict[str, Any] = {}
    prompt = _prompt(request, previous, instructions)
    if provider == "template":
        script = _template(request)
        metrics: dict[str, Any] = {}
    elif provider == "ollama":
        script, metrics = _generate_with_ollama(prompt, model)
    elif provider == "gemini":
        script, metrics = _generate_with_gemini(prompt, model)
    elif provider == "gemini_ollama":
        if not settings.gemini_api_key:
            actual_provider = "ollama"
            actual_model = settings.ollama_model
            fallback_metadata = {"fallback_from": "gemini", "fallback_reason": "gemini_not_configured"}
            script, metrics = _generate_with_ollama(prompt, actual_model)
        else:
            try:
                actual_provider = "gemini"
                actual_model = settings.gemini_model
                script, metrics = _generate_with_gemini(prompt, actual_model)
            except ProviderHTTPError as exc:
                if exc.status_code not in _RETRYABLE_GEMINI_STATUS:
                    raise
                actual_provider = "ollama"
                actual_model = settings.ollama_model
                fallback_metadata = {"fallback_from": "gemini", "fallback_reason": "quota_or_capacity"}
                script, metrics = _generate_with_ollama(prompt, actual_model)
            except ProviderConnectionError:
                actual_provider = "ollama"
                actual_model = settings.ollama_model
                fallback_metadata = {"fallback_from": "gemini", "fallback_reason": "connectivity"}
                script, metrics = _generate_with_ollama(prompt, actual_model)
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
        metrics = {}
    _validate_editorial_output(script)
    fact_check_notes = script.pop("fact_check_notes", [])
    audience = script.pop("audience", "")
    tone = script.pop("tone", "")
    script["metadata"] = {
        "provider": actual_provider,
        "model": actual_model,
        "audience": audience,
        "tone": tone,
        "fact_check_notes": fact_check_notes,
        "revision": bool(previous),
        "generation_metrics": metrics,
        **({"requested_provider": requested_provider} if requested_provider == "gemini_ollama" else {}),
        **fallback_metadata,
    }
    return finalize_scene_plan(script, request.duration_seconds, previous)


def unload_script_model() -> bool:
    """Unload local model memory before CPU/RAM-heavy rendering; never blocks a render on failure."""
    try:
        provider, model = _selected_provider()
        if provider not in {"ollama", "gemini_ollama"}:
            return False
        model = settings.ollama_model
        request = urllib.request.Request(
            _ollama_url("/api/generate"),
            data=json.dumps({"model": model, "keep_alive": 0, "stream": False}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10):
            return True
    except Exception:
        return False
