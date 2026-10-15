"""Install the pinned desktop runtime into an OS/architecture-specific directory."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.platforms import runtime_directory


def main():
    node = shutil.which('node')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not node or not npm:
        raise RuntimeError('Node.js LTS ab 22.12 mit npm muss auf diesem System installiert sein: https://nodejs.org/en/download')
    candidates = [Path(node).resolve().parent / 'node_modules/npm/bin/npm-cli.js',
                  Path(npm).resolve().parent / 'node_modules/npm/bin/npm-cli.js', Path(npm).resolve()]
    npm_cli = next((path for path in candidates if path.name == 'npm-cli.js' and path.is_file()), None)
    if not npm_cli:
        raise RuntimeError('Die offizielle npm-Laufzeit wurde nicht gefunden. Prüfe die Node.js-Installation.')
    directory = runtime_directory()
    directory.mkdir(parents=True, exist_ok=True)
    for name in ('package.json', 'package-lock.json'):
        shutil.copyfile(ROOT / 'desktop' / name, directory / name)
    environment = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith(('ELECTRON_', 'NODE_OPTIONS', 'NODE_PATH', 'NPM_CONFIG_'))}
    environment['NPM_CONFIG_CACHE'] = str(ROOT / '.runtime/desktop-npm-cache')
    subprocess.run([node, str(npm_cli), 'ci', '--ignore-scripts', '--no-audit', '--no-fund',
                    '--registry=https://registry.npmjs.org'], cwd=directory, env=environment, check=True)
    subprocess.run([node, str(ROOT / 'desktop/install.cjs')], cwd=directory, env=environment, check=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error) if isinstance(error, RuntimeError) else 'Die projektlokale Desktop-Einrichtung ist fehlgeschlagen.', file=sys.stderr)
        raise SystemExit(1)
