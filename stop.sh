#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$project_dir"

result=3
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys' >/dev/null 2>&1; then
  if python3 "$project_dir/stop_pipeline.py" --quiet-if-none "$@"; then
    result=0
  else
    result=$?
  fi
fi

if [[ $result -ne 0 && $result -ne 2 && $result -ne 3 ]]; then
  exit "$result"
fi

if [[ $# -eq 0 ]] && command -v docker >/dev/null 2>&1 \
  && docker compose version >/dev/null 2>&1 \
  && [[ -n "$(docker compose ps --status running -q pipeline 2>/dev/null)" ]]; then
  docker compose stop pipeline
  echo "Compose-Webdienst der Pipeline gestoppt. Daten und andere Dienste bleiben erhalten."
  if [[ $result -eq 2 ]]; then
    exit 2
  fi
  result=0
fi

if [[ $result -eq 0 || $result -eq 2 ]]; then
  exit "$result"
fi
echo "Keine über den Projekt-Starter laufende Pipeline gefunden."
exit 0
