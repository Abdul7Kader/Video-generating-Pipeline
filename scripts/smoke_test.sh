#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import json
import os
import urllib.request

base = f"http://127.0.0.1:{os.getenv('APP_PORT', '8080')}"

def call(path, method="GET", data=None):
    request = urllib.request.Request(
        base + path,
        data=None if data is None else json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    return json.load(urllib.request.urlopen(request, timeout=30))

job = call("/api/jobs", "POST", {
    "topic": "Warum kleine Schritte große Ziele erreichen",
    "language": "de", "duration_seconds": 30, "aspect_ratio": "9:16",
    "video_type": "stickman", "target_platform": "download",
})
job_id = job["id"]
version = job["script_version"]
plan_hash = job["script"]["content_hash"]
call(f"/api/jobs/{job_id}/approve-script", "POST", {"expected_version": version, "expected_hash": plan_hash})
call(f"/api/jobs/{job_id}/render", "POST", {"expected_version": version, "expected_hash": plan_hash})
print(f"Smoke-Test-Auftrag: {job_id}")
print(f"Status: {base}/api/jobs/{job_id}")
PY
