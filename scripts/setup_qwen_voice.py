"""Download the pinned official model once. Rendering subsequently stays offline."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import settings
from backend.qwen_tts import MODEL_ID, MODEL_REVISION


if __name__ == "__main__":
    import json
    from importlib.metadata import version
    from huggingface_hub import snapshot_download

    if version("qwen-tts") != "0.1.1":
        raise SystemExit("Bitte zuerst die dokumentierte isolierte Qwen-Laufzeit installieren.")
    destination = settings.qwen_tts_model_dir
    snapshot_download(
        MODEL_ID, revision=MODEL_REVISION, local_dir=str(destination), token=False,
        allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "LICENSE", "README.md"],
    )
    (destination / "pipeline-install.json").write_text(json.dumps({
        "model": MODEL_ID, "revision": MODEL_REVISION, "runtime": "qwen-tts==0.1.1",
    }), encoding="utf-8")
    print("Qwen-Modell vollständig eingerichtet:", destination)
