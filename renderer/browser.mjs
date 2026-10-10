import {existsSync} from 'node:fs';
import {win32} from 'node:path';

export function resolveBrowserExecutable({platform = process.platform, env = process.env, exists = existsSync} = {}) {
  const configured = env.REMOTION_BROWSER_EXECUTABLE;
  if (configured) {
    if (!exists(configured)) throw new Error('REMOTION_BROWSER_EXECUTABLE wurde nicht gefunden. Bitte einen installierten Chrome- oder Edge-Browser angeben.');
    return configured;
  }
  if (platform !== 'win32') return undefined;

  const baseDirs = [env.PROGRAMFILES, env['PROGRAMFILES(X86)'], 'C:\\Program Files', 'C:\\Program Files (x86)']
    .filter(Boolean);
  const candidates = baseDirs.flatMap((base) => [
    win32.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe'),
    win32.join(base, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
  ]);
  if (env.LOCALAPPDATA) candidates.push(win32.join(env.LOCALAPPDATA, 'Google', 'Chrome', 'Application', 'chrome.exe'));
  const browser = candidates.find(exists);
  if (!browser) throw new Error('Chrome oder Edge wurde lokal nicht gefunden. Bitte einen Browser installieren oder REMOTION_BROWSER_EXECUTABLE auf dessen ausführbare Datei setzen. Es wird kein Browser automatisch heruntergeladen.');
  return browser;
}
