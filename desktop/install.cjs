// Execute only the pinned official Electron downloader; package lifecycle scripts stay disabled.
const {spawnSync} = require('node:child_process');
const path = require('node:path');
const [major, minor] = process.versions.node.split('.').map(Number);
if (major < 22 || (major === 22 && minor < 12)) {
  console.error('Für die Desktop-Einrichtung wird Node.js LTS ab 22.12 benötigt.');
  process.exit(1);
}
const environment = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
  !/^(electron_|node_options$|node_path$|npm_config_electron_|npm_config_platform$|npm_config_arch$)/i.test(key)));
environment.electron_config_cache = path.resolve(__dirname, '../.runtime/electron-download-cache');
const directory = path.resolve(__dirname, '../.runtime/desktop', process.platform + '-' + process.arch);
const result = spawnSync(process.execPath, [path.join(directory, 'node_modules/electron/install.js')],
  {cwd: directory, env: environment, stdio: 'inherit', windowsHide: true});
process.exit(result.status ?? 1);
