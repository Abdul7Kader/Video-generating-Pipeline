#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$project_dir"

if [[ -x "$project_dir/.runtime/node/bin/node" && -d "$project_dir/.runtime/python/fastapi" \
  && -d "$project_dir/renderer/node_modules/@remotion/renderer" ]]; then
  export PYTHONPATH="$project_dir/.runtime/python:$project_dir"
  export PATH="$project_dir/.runtime/node/bin:$project_dir/.runtime/python/bin:$PATH"
  export DATA_DIR="$project_dir/data"
  export RENDERER_DIR="$project_dir/renderer"
  export PIPER_AUTO_DOWNLOAD="${PIPER_AUTO_DOWNLOAD:-1}"
  exec python3 "$project_dir/start_pipeline.py"
fi

if [[ -d "$project_dir/renderer/node_modules/@remotion/renderer" ]] \
  && command -v python3 >/dev/null 2>&1 && command -v node >/dev/null 2>&1 \
  && python3 -c 'import uvicorn, fastapi, dotenv' >/dev/null 2>&1; then
  exec python3 "$project_dir/start_pipeline.py"
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 \
  && docker info >/dev/null 2>&1; then
  docker compose up --build -d
  address=$(docker compose port pipeline 8080)
  url="http://$address/"
  echo "Pipeline gestartet: $url"
  if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] && command -v xdg-open >/dev/null 2>&1 \
    && command -v curl >/dev/null 2>&1; then
    (
      for ((attempt=0; attempt<60; attempt++)); do
        if curl --fail --silent --max-time 2 "${url}api/health" >/dev/null; then
          xdg-open "$url" >/dev/null 2>&1 || true
          exit 0
        fi
        sleep 1
      done
    ) >/dev/null 2>&1 &
  fi
  exit 0
fi

echo "Keine nutzbare lokale Python-/Node-Laufzeit und kein Docker-Compose-Dienst gefunden." >&2
echo "Bitte die Laufzeit gemäß README.md einrichten. Es wurde nichts installiert." >&2
exit 1
