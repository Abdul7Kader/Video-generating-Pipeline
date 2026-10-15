#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$project_dir"
if [[ -x "$project_dir/.runtime/node/bin/node" ]]; then
  export PATH="$project_dir/.runtime/node/bin:$PATH"
fi
case "$(uname -s)" in Linux) desktop_system=linux;; Darwin) desktop_system=darwin;; *) exit 1;; esac
case "$(uname -m)" in x86_64) desktop_arch=x64;; arm64|aarch64) desktop_arch=arm64;; *) exit 1;; esac
if [[ -x "$project_dir/.runtime/node/$desktop_system-$desktop_arch/bin/node" ]]; then
  export PATH="$project_dir/.runtime/node/$desktop_system-$desktop_arch/bin:$PATH"
fi
pipeline_python="$project_dir/.runtime/python/$desktop_system-$desktop_arch/bin/python"
if [[ ! -x "$pipeline_python" ]]; then pipeline_python="$project_dir/.runtime/pipeline-python/bin/python"; fi
if [[ ! -x "$pipeline_python" ]]; then
  echo 'Bitte zuerst Desktop-Einrichten.sh ausführen.' >&2
  exit 1
fi
exec "$pipeline_python" "$project_dir/desktop/launcher.py"
