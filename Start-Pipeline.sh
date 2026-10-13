#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$project_dir"

if [[ -x "$project_dir/.runtime/node/bin/node" ]]; then
  export PATH="$project_dir/.runtime/node/bin:$PATH"
fi
if [[ -x "$project_dir/.runtime/pipeline-python/bin/python" ]]; then
  exec "$project_dir/.runtime/pipeline-python/bin/python" "$project_dir/setup_pipeline.py"
fi
if [[ -d "$project_dir/.runtime/python/fastapi" ]]; then
  export PYTHONPATH="$project_dir/.runtime/python:$project_dir"
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python fehlt. Installiere Python 3.12 von https://www.python.org/downloads/ und starte erneut." >&2
  exit 1
fi
# First-run setup asks before installing project-local Python packages.
# No automatic Docker launch, model pull, system service or privileged installer.
exec python3 "$project_dir/setup_pipeline.py"
