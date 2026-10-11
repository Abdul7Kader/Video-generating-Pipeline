"""Fixed, local voice choices. No client-controlled paths, URLs or downloads."""
from __future__ import annotations

VOICE_CHOICES = (
    {"id": "thorsten", "label": "Thorsten · klar", "language": "de", "model": "de_DE-thorsten-high", "speaker_id": None, "quality": "high", "license": "CC0"},
    {"id": "thorsten_amused", "label": "Thorsten · lebhaft", "language": "de", "model": "de_DE-thorsten_emotional-medium", "speaker_id": 0, "quality": "medium", "license": "CC0"},
    {"id": "kerstin", "label": "Kerstin · andere Stimme", "language": "de", "model": "de_DE-kerstin-low", "speaker_id": None, "quality": "low", "license": "CC0"},
    {"id": "ljspeech", "label": "LJ · English", "language": "en", "model": "en_US-ljspeech-high", "speaker_id": None, "quality": "high", "license": "public domain"},
)


def voice_choice(identifier: str) -> dict:
    choice = next((item for item in VOICE_CHOICES if item["id"] == identifier), None)
    if choice is None:
        raise ValueError("Unbekannte lokale Stimme.")
    return dict(choice)


def estimated_words_per_minute(identifier: str) -> int:
    # Rough local calibration with the same 25-word comparison passage, not ASR.
    return {"thorsten": 210, "thorsten_amused": 180, "kerstin": 185, "ljspeech": 170}[voice_choice(identifier)["id"]]


def validate_voice_language(config: dict, language: str) -> None:
    if config.get("voice_id"):
        if config.get("voice_provider") != "piper":
            raise ValueError("Die gewählte lokale Stimme benötigt Piper.")
        if voice_choice(config["voice_id"])["language"] != language:
            raise ValueError("Stimme und Skriptsprache müssen übereinstimmen.")
