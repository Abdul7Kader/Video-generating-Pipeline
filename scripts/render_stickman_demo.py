"""Render the checked-in original style sample without AI calls or publication."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.plan import finalize_scene_plan, script_hash
from backend.rendering import render_job
from backend.schemas import Scene


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "style-preview")
    parser.add_argument("--script", type=Path, default=ROOT / "examples" / "stickman-demo.json")
    args = parser.parse_args()
    script = json.loads(args.script.read_text(encoding="utf-8"))
    script["scenes"] = [Scene.model_validate(scene).model_dump() for scene in script["scenes"]]
    script = finalize_scene_plan(script, sum(scene["duration_seconds"] for scene in script["scenes"]))
    output, mode = render_job({
        "id": "stickman-style-demo", "render_version": 1, "language": "de",
        "aspect_ratio": "16:9", "script": script, "render_script_hash": script_hash(script),
        "production_config": {"editor": "remotion", "voice_provider": "piper"},
    }, job_dir_override=args.output.resolve())
    print(json.dumps({"video": output, "voice": mode}, ensure_ascii=False))


if __name__ == "__main__":
    main()
