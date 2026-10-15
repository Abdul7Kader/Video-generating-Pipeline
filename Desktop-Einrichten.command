#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "$0")" && pwd)
exec /bin/bash "$project_dir/Desktop-Einrichten.sh"
