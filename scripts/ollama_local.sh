#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
ollama_bin="$project_dir/.runtime/ollama/bin/ollama"
models_dir="$project_dir/data/ollama/models"

if [[ ! -x "$ollama_bin" ]]; then
  echo "Ollama fehlt unter $ollama_bin. Installationsstand in STATUS.md prüfen."
  exit 1
fi

mkdir -p "$models_dir"
export OLLAMA_HOST="127.0.0.1:11434"
export OLLAMA_MODELS="$models_dir"
export OLLAMA_NUM_PARALLEL="1"
export OLLAMA_MAX_LOADED_MODELS="1"
export OLLAMA_MAX_QUEUE="8"
export OLLAMA_NO_CLOUD="1"
export OLLAMA_NOHISTORY="1"

case "${1:-serve}" in
  serve)
    exec "$ollama_bin" serve
    ;;
  pull)
    exec "$ollama_bin" pull "${2:-qwen3.5:9b-q4_K_M}"
    ;;
  list)
    exec "$ollama_bin" list
    ;;
  ps)
    exec "$ollama_bin" ps
    ;;
  stop-model)
    exec "$ollama_bin" stop "${2:-qwen3.5:9b-q4_K_M}"
    ;;
  *)
    echo "Nutzung: $0 {serve|pull [MODELL]|list|ps|stop-model [MODELL]}"
    exit 2
    ;;
esac
