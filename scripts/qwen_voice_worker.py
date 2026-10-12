"""Private one-shot worker. Called by the backend, never with client paths/URLs."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys

for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
    os.environ[name] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# -I keeps user site packages and PYTHONPATH out of this worker. Import only our
# fixed reference constants, without loading the backend's main application.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.qwen_tts import REFERENCE, REFERENCE_SHA256, REFERENCE_TEXT


def main():
    request = json.loads(sys.stdin.read(16384))
    text = request["text"]
    if not isinstance(text, str) or not 3 <= len(text.strip()) <= 1200:
        raise ValueError("Invalid narration")
    if hashlib.sha256(REFERENCE.read_bytes()).hexdigest() != REFERENCE_SHA256:
        raise ValueError("Invalid reference")
    with contextlib.redirect_stdout(sys.stderr):
        import numpy as np
        import soundfile as sf
        import torch
        from qwen_tts import Qwen3TTSModel

        torch.set_num_threads(max(1, min(8, int(request["threads"]))))
        torch.manual_seed(int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "big"))
        model = Qwen3TTSModel.from_pretrained(
            request["model"], device_map="cpu", dtype=torch.float32,
            attn_implementation="sdpa", local_files_only=True, trust_remote_code=False,
            use_safetensors=True,
        )
        with torch.inference_mode():
            prompt = model.create_voice_clone_prompt(
                ref_audio=str(REFERENCE), ref_text=REFERENCE_TEXT, x_vector_only_mode=False,
            )
            waves, rate = model.generate_voice_clone(
                text=text, language="German", voice_clone_prompt=prompt,
                non_streaming_mode=True, max_new_tokens=min(2048, max(256, len(text) * 4)),
            )
        audio = waves[0]
        if rate != 24000 or not np.isfinite(audio).all() or not 0.1 < len(audio) / rate <= 180:
            raise ValueError("Invalid audio")
        sf.write(request["output"], audio, rate, subtype="PCM_16")


if __name__ == "__main__":
    main()
