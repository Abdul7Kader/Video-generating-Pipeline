import {existsSync} from 'node:fs';
import {win32, posix} from 'node:path';

function nativeWindowsBrowser(value) {
  return win32.isAbsolute(value) && !/^[\\/]{2}/.test(value)
    && ['chrome.exe', 'msedge.exe', 'chromium.exe'].includes(win32.basename(value).toLowerCase());
}

export function guardedBrowserExecutable(browser, {platform = process.platform, env = process.env, exists = existsSync} = {}) {
  if (platform !== 'darwin' || !env.PIPELINE_PROCESS_REGISTRY) return browser;
  const wrapper = env.PIPELINE_BROWSER_WRAPPER;
  if (!wrapper || !exists(wrapper)) throw new Error('Die macOS-Prozessüberwachung für den Zeichenbrowser fehlt. Starte die Desktop-Anwendung erneut.');
  env.PIPELINE_REAL_BROWSER = browser;
  return wrapper;
}

export function resolveBrowserExecutable({platform = process.platform, env = process.env, exists = existsSync} = {}) {
  const configured = env.REMOTION_BROWSER_EXECUTABLE;
  if (configured) {
    if (platform === 'win32' && !nativeWindowsBrowser(configured)) throw new Error('Unter Windows wird ausschließlich ein lokaler nativer Chrome-/Edge-Browser verwendet; keine WSL-, Netzwerk- oder Portverbindung.');
    if (!exists(configured)) throw new Error('REMOTION_BROWSER_EXECUTABLE wurde nicht gefunden. Bitte einen installierten Chrome- oder Edge-Browser angeben.');
    return configured;
  }
  if (platform !== 'win32') {
    const names=['google-chrome','google-chrome-stable','chromium','chromium-browser'];
    const candidates=platform==='darwin'?['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge']:[];
    candidates.push(...(env.PATH||'/usr/bin:/usr/local/bin').split(':').flatMap(directory=>names.map(name=>posix.join(directory,name))));
    const browser=candidates.find(exists);
    if(!browser) throw new Error('Chrome oder Chromium wurde lokal nicht gefunden. Bitte einen Browser in den Einstellungen installieren. Es wird kein Browser automatisch heruntergeladen.');
    return browser;
  }

  const baseDirs = [env.PROGRAMFILES, env['PROGRAMFILES(X86)'], 'C:\\Program Files', 'C:\\Program Files (x86)']
    .filter(Boolean);
  const candidates = baseDirs.flatMap((base) => [
    win32.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe'),
    win32.join(base, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
  ]);
  if (env.LOCALAPPDATA) candidates.push(win32.join(env.LOCALAPPDATA, 'Google', 'Chrome', 'Application', 'chrome.exe'));
  const browser = candidates.find(candidate => nativeWindowsBrowser(candidate) && exists(candidate));
  if (!browser) throw new Error('Chrome oder Edge wurde lokal nicht gefunden. Bitte einen Browser installieren oder REMOTION_BROWSER_EXECUTABLE auf dessen ausführbare Datei setzen. Es wird kein Browser automatisch heruntergeladen.');
  return browser;
}
