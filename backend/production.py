from __future__ import annotations

from typing import Any


PROFILE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "cloud_stickman",
        "label": "Cloud-Qualität · Strichmännchen",
        "description": "Antigravity für Skript und Szenenplan, programmatische Strichmännchen, Piper und Remotion.",
        "config": {
            "profile_id": "cloud_stickman",
            "video_type": "stickman",
            "script_provider": "antigravity",
            "media_provider": "procedural_stickman",
            "voice_provider": "piper",
            "editor": "remotion",
        },
    },
    {
        "id": "local_stickman",
        "label": "Lokal · Strichmännchen",
        "description": "Qwen, programmatische Strichmännchen, Piper und Remotion.",
        "config": {
            "profile_id": "local_stickman",
            "video_type": "stickman",
            "script_provider": "qwen",
            "media_provider": "procedural_stickman",
            "voice_provider": "piper",
            "editor": "remotion",
        },
    },
    {
        "id": "stock_explainer",
        "label": "Stock · Erklärvideo",
        "description": "Qwen, Pexels-Stockmedien, Piper und Remotion.",
        "config": {
            "profile_id": "stock_explainer",
            "video_type": "explainer",
            "script_provider": "qwen",
            "media_provider": "pexels_stock",
            "voice_provider": "piper",
            "editor": "remotion",
        },
    },
    {
        "id": "stock_social",
        "label": "Stock · Social Clip",
        "description": "Qwen, Pexels-Stockmedien, Piper und Remotion im Social-Stil.",
        "config": {
            "profile_id": "stock_social",
            "video_type": "social",
            "script_provider": "qwen",
            "media_provider": "pexels_stock",
            "voice_provider": "piper",
            "editor": "remotion",
        },
    },
    {
        "id": "cloud_stock",
        "label": "Cloud-Qualität · Stockvideo",
        "description": "Antigravity, Pexels-Stockmedien, Piper und Remotion.",
        "config": {
            "profile_id": "cloud_stock",
            "video_type": "explainer",
            "script_provider": "antigravity",
            "media_provider": "pexels_stock",
            "voice_provider": "piper",
            "editor": "remotion",
        },
    },
    {
        "id": "moneyprinter_pilot",
        "label": "MoneyPrinterTurbo · Pilot",
        "description": "Kontrollierter Schnittvergleich mit demselben Antigravity-Skript, denselben Pexels-Medien und derselben Piper-Stimme.",
        "config": {
            "profile_id": "moneyprinter_pilot",
            "video_type": "social",
            "script_provider": "antigravity",
            "media_provider": "pexels_stock",
            "voice_provider": "piper",
            "editor": "moneyprinter",
        },
    },
    {
        "id": "podcast_video",
        "label": "Podcastvideo · Studio",
        "description": "Podcast-Layout und spezialisierter Schnitt sind als spätere Etappe geplant.",
        "config": {
            "profile_id": "podcast_video",
            "video_type": "podcast",
            "script_provider": "antigravity",
            "media_provider": "podcast_layout",
            "voice_provider": "piper",
            "editor": "podcast_editor",
        },
    },
    {
        "id": "generated_video",
        "label": "Generatives Video · Cloud",
        "description": "Generierte Bilder und Videos benötigen einen später freigegebenen Medienadapter.",
        "config": {
            "profile_id": "generated_video",
            "video_type": "generated",
            "script_provider": "antigravity",
            "media_provider": "generated_media",
            "voice_provider": "piper",
            "editor": "remotion",
        },
    },
)


PROVIDER_IDS = {
    "script": {"qwen", "gemini_cli", "antigravity"},
    "media": {"procedural_stickman", "pexels_stock", "generated_media", "moneyprinter_media", "podcast_layout"},
    "voice": {"piper", "gemini_tts", "moneyprinter_voice"},
    "editor": {"remotion", "moneyprinter", "podcast_editor"},
}

IMPLEMENTED_PROVIDER_IDS = {
    "script": {"qwen", "gemini_cli", "antigravity"},
    "media": {"procedural_stickman", "pexels_stock"},
    "voice": {"piper", "gemini_tts"},
    "editor": {"remotion", "moneyprinter"},
}


def _provider(identifier: str, label: str, available: bool, reason: str = "") -> dict[str, Any]:
    return {"id": identifier, "label": label, "available": available, "reason": "" if available else reason}


def build_production_catalog(
    *,
    qwen_ready: bool,
    gemini_cli_ready: bool,
    antigravity_ready: bool,
    pexels_ready: bool,
    piper_ready: bool,
    gemini_tts_ready: bool,
    remotion_ready: bool,
    moneyprinter_ready: bool,
) -> dict[str, Any]:
    providers = {
        "script": [
            _provider("qwen", "Qwen 3.5 · lokal", qwen_ready, "Ollama oder das konfigurierte Qwen-Modell ist nicht erreichbar."),
            _provider("gemini_cli", "Gemini CLI", gemini_cli_ready, "Kein unterstütztes und verfügbares Gemini-CLI-Profil ist aktiviert."),
            _provider("antigravity", "Antigravity", antigravity_ready, "Antigravity CLI ist deaktiviert oder nicht installiert."),
        ],
        "media": [
            _provider("procedural_stickman", "Programmatische Strichmännchen", True),
            _provider("pexels_stock", "Pexels Stockfoto/-video", pexels_ready, "PEXELS_API_KEY ist nicht konfiguriert."),
            _provider("generated_media", "Generierte Bilder und Videos", False, "Ein freigegebener Mediengenerator folgt in einer späteren Etappe."),
            _provider("moneyprinter_media", "MoneyPrinterTurbo Medien", False, "Im kontrollierten Pilot bleibt die Medienbeschaffung bei Pexels."),
            _provider("podcast_layout", "Podcast-/Talking-Head-Layout", False, "Der spezialisierte Renderer folgt in einer späteren Etappe."),
        ],
        "voice": [
            _provider("piper", "Piper · lokal", piper_ready, "Piper-Stimme ist nicht installiert und automatischer Download ist deaktiviert."),
            _provider("gemini_tts", "Gemini TTS · API", gemini_tts_ready, "Cloud-TTS und ein separater API-Schlüssel sind nicht freigegeben."),
            _provider("moneyprinter_voice", "MoneyPrinterTurbo Stimme", False, "Im kontrollierten Pilot bleibt die Stimme bei Piper."),
        ],
        "editor": [
            _provider("remotion", "Remotion + FFmpeg", remotion_ready, "Node, Remotion, FFmpeg oder FFprobe ist nicht vollständig verfügbar."),
            _provider("moneyprinter", "MoneyPrinterTurbo Schnitt", moneyprinter_ready, "MoneyPrinterTurbo ist nicht aktiviert oder seine isolierte Python-Umgebung fehlt."),
            _provider("podcast_editor", "Podcast-Schnitt", False, "Der spezialisierte Renderer folgt in einer späteren Etappe."),
        ],
    }
    availability = {
        slot: {item["id"]: item for item in choices}
        for slot, choices in providers.items()
    }
    profiles: list[dict[str, Any]] = []
    for definition in PROFILE_SPECS:
        config = definition["config"]
        selected = (
            ("script", config["script_provider"]),
            ("media", config["media_provider"]),
            ("voice", config["voice_provider"]),
            ("editor", config["editor"]),
        )
        reasons = [availability[slot][provider]["reason"] for slot, provider in selected if not availability[slot][provider]["available"]]
        profiles.append({
            **definition,
            "available": not reasons,
            "reason": " ".join(dict.fromkeys(reason for reason in reasons if reason)),
        })
    preferred = next((profile for profile in profiles if profile["id"] == "cloud_stickman"), None)
    default_profile_id = "cloud_stickman" if preferred and preferred["available"] else "local_stickman"
    return {"default_profile_id": default_profile_id, "profiles": profiles, "providers": providers}


def legacy_production_config(video_type: str, script_provider: str = "qwen") -> dict[str, str]:
    media_by_type = {
        "stickman": "procedural_stickman",
        "explainer": "pexels_stock",
        "social": "pexels_stock",
        "podcast": "podcast_layout",
        "generated": "generated_media",
    }
    profile_by_type = {
        "stickman": "local_stickman",
        "explainer": "stock_explainer",
        "social": "stock_social",
        "podcast": "podcast_video",
        "generated": "generated_video",
    }
    return {
        "profile_id": profile_by_type.get(video_type, "custom"),
        "video_type": video_type,
        "script_provider": script_provider if script_provider in PROVIDER_IDS["script"] else "qwen",
        "media_provider": media_by_type.get(video_type, "procedural_stickman"),
        "voice_provider": "piper",
        "editor": "remotion",
    }


def production_plan_readiness(config: dict[str, Any], scenes: list[dict[str, Any]]) -> list[str]:
    media_provider = config.get("media_provider")
    allowed = {
        "procedural_stickman": {"stickman"},
        "pexels_stock": {"stock_image", "stock_video"},
    }.get(str(media_provider))
    if allowed is None:
        return [f"Der Medienanbieter {media_provider or 'unbekannt'} ist noch nicht produktionsbereit."]
    label = "Strichmännchen" if media_provider == "procedural_stickman" else "Pexels-Stockmedien"
    return [
        f"{scene.get('scene_id') or 'unbekannte Szene'}: Das gewählte Profil verlangt {label}; "
        f"{scene.get('visual_type') or 'kein Medientyp'} gehört zu einem anderen Medienanbieter."
        for scene in scenes
        if scene.get("visual_type", "stickman") not in allowed
    ]


def normalize_production_config(
    config: dict[str, Any] | None,
    *,
    legacy_video_type: str,
    legacy_script_provider: str,
) -> dict[str, str]:
    explicit = config is not None
    candidate = dict(config or legacy_production_config(legacy_video_type, legacy_script_provider))
    required = {"profile_id", "video_type", "script_provider", "media_provider", "voice_provider", "editor"}
    if set(candidate) != required:
        raise ValueError("Die Produktionskonfiguration ist unvollständig.")
    for slot, key in (("script", "script_provider"), ("media", "media_provider"), ("voice", "voice_provider"), ("editor", "editor")):
        identifier = str(candidate[key])
        if identifier not in PROVIDER_IDS[slot]:
            raise ValueError(f"Unbekannter {slot}-Provider: {identifier}")
        if explicit and identifier not in IMPLEMENTED_PROVIDER_IDS[slot]:
            labels = {
                "moneyprinter": "MoneyPrinterTurbo",
                "moneyprinter_media": "MoneyPrinterTurbo",
                "moneyprinter_voice": "MoneyPrinterTurbo",
            }
            raise ValueError(f"{labels.get(identifier, identifier)} ist noch nicht integriert und kann nicht ausgewählt werden.")
    if candidate["video_type"] not in {"stickman", "explainer", "social", "podcast", "generated"}:
        raise ValueError("Unbekannte Videoart in der Produktionskonfiguration.")
    profile_ids = {item["id"] for item in PROFILE_SPECS}
    if candidate["profile_id"] not in profile_ids | {"custom"}:
        raise ValueError("Unbekanntes Produktionsprofil.")
    matching = next(
        (item["id"] for item in PROFILE_SPECS if all(candidate[key] == value for key, value in item["config"].items() if key != "profile_id")),
        None,
    )
    candidate["profile_id"] = matching or "custom"
    return {key: str(candidate[key]) for key in required}
