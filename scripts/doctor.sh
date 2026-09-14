#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Video Pipeline – Systemcheck"
docker --version
docker compose version
docker compose config --quiet
docker compose ps
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:${APP_PORT:-8080}/api/health', timeout=3).read().decode())"
echo
