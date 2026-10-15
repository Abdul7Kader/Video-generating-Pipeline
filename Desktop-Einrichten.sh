#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$project_dir"
if [[ -x "$project_dir/.runtime/node/bin/node" ]]; then
  export PATH="$project_dir/.runtime/node/bin:$PATH"
fi
pipeline_python=python3
case "$(uname -s)" in Linux) desktop_system=linux;; Darwin) desktop_system=darwin;; *) echo 'Dieses System wird nicht unterstützt.' >&2; exit 1;; esac
case "$(uname -m)" in x86_64) desktop_arch=x64;; arm64|aarch64) desktop_arch=arm64;; *) echo 'Die Desktop-App braucht x64 oder arm64.' >&2; exit 1;; esac
native_python="$project_dir/.runtime/python/$desktop_system-$desktop_arch/bin/python"
if [[ -x "$project_dir/.runtime/node/$desktop_system-$desktop_arch/bin/node" ]]; then
  export PATH="$project_dir/.runtime/node/$desktop_system-$desktop_arch/bin:$PATH"
fi
if [[ -x "$project_dir/.runtime/pipeline-python/bin/python" ]]; then
  pipeline_python="$project_dir/.runtime/pipeline-python/bin/python"
fi
if [[ -x "$native_python" ]]; then pipeline_python="$native_python"; fi
"$pipeline_python" "$project_dir/setup_pipeline.py" --desktop
if [[ -x "$native_python" ]]; then
  pipeline_python="$native_python"
fi
"$pipeline_python" "$project_dir/desktop/install_runtime.py"
"$pipeline_python" "$project_dir/desktop/install_shortcuts.py"
echo 'Fertig. Starte die passende Startdatei. Modelle und Konten stehen unter Einstellungen.'
