const readline = require('node:readline');

function localNavigation(value, origin) {
  try {
    const url = new URL(value);
    return url.origin === origin && !url.username && !url.password;
  } catch { return false; }
}

function externalLink(value) {
  const hosts = new Set(['antigravity.google', 'www.antigravity.google', 'developers.google.com',
    'gemini.google.com', 'chatgpt.com', 'nodejs.org', 'www.python.org', 'pypi.org',
    'discord.com', 'developers.facebook.com', 'console.cloud.google.com', 'developers.tiktok.com', 'www.tiktok.com', 'ffmpeg.org', 'www.google.com', 'ollama.com', 'www.remotion.dev', 'huggingface.co']);
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password && !url.port && hosts.has(url.hostname);
  } catch { return false; }
}

function clipboardWriteAllowed(permission, url, origin, isMainFrame) {
  return permission === 'clipboard-sanitized-write' && isMainFrame === true
    && Boolean(origin) && localNavigation(url, origin);
}

class BackendClient {
  constructor(child) {
    this.child = child;
    this.exited = false;
    this.pending = new Map();
    this.nextId = 0;
    this.starting = new Promise((resolve, reject) => {
      this.resolveStarting = resolve;
      this.rejectStarting = reject;
    });
    // Startup failures may arrive while Electron is still creating its window.
    this.starting.catch(() => {});
    this.exit = new Promise(resolve => { this.resolveExit = resolve; });
    readline.createInterface({input: child.stdout}).on('line', line => {
      if (!line.startsWith('PIPELINE_DESKTOP ') || line.length > 4096) return;
      let value;
      try { value = JSON.parse(line.slice('PIPELINE_DESKTOP '.length)); } catch { return; }
      if (value.type === 'starting' && Number.isInteger(value.port) && value.port >= 1024 && value.port <= 65535) {
        this.resolveStarting(value.port);
      } else if (value.type === 'folder' && /^[0-9a-f]{32}$/.test(value.id) && this.chooseFolder) {
        Promise.resolve().then(() => this.chooseFolder()).catch(() => null).then(folder => {
          if (!this.exited) child.stdin.write(JSON.stringify({id: value.id, command:'folder-result', path: folder}) + '\n');
        });
      } else if (value.type === 'reply' && this.pending.has(value.id)) {
        const pending = this.pending.get(value.id);
        clearTimeout(pending.timer);
        this.pending.delete(value.id);
        pending.resolve(value);
      }
    });
    const ended = () => {
      this.exited = true;
      const error = new Error('Das Backend wurde beendet.');
      this.rejectStarting(error);
      for (const value of this.pending.values()) {
        clearTimeout(value.timer);
        value.reject(error);
      }
      this.pending.clear();
      this.resolveExit();
    };
    child.once('exit', ended);
    child.once('error', ended);
    child.stdin.on('error', () => {}); // Broken pipe is handled by process exit/timeout.
  }

  request(command) {
    if (this.exited) return Promise.reject(new Error('Das Backend wurde beendet.'));
    const id = String(++this.nextId);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error('Das Backend antwortet nicht.'));
      }, 5000);
      this.pending.set(id, {resolve, reject, timer});
      this.child.stdin.write(JSON.stringify({id, command}) + '\n');
    });
  }
}

module.exports = {BackendClient, localNavigation, externalLink, clipboardWriteAllowed};
