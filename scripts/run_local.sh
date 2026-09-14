#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
if [[ ! -x "$project_dir/.runtime/node/bin/node" || ! -d "$project_dir/.runtime/python/fastapi" ]]; then
  echo "Projektlokale Laufzeit fehlt. Nutze den vorgesehenen Docker-Start aus README.md."
  exit 1
fi
export PYTHONPATH="$project_dir/.runtime/python:$project_dir"
export PATH="$project_dir/.runtime/node/bin:$project_dir/.runtime/python/bin:$PATH"
export DATA_DIR="$project_dir/data"
export RENDERER_DIR="$project_dir/renderer"
export PIPER_AUTO_DOWNLOAD=${PIPER_AUTO_DOWNLOAD:-1}
exec python3 -m uvicorn backend.main:app --app-dir "$project_dir" --host 127.0.0.1 --port "${APP_PORT:-8080}"
