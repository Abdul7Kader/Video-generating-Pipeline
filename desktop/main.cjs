const {app, BrowserWindow, Menu, dialog, session, shell} = require('electron');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {pathToFileURL} = require('node:url');
const {setTimeout: delay} = require('node:timers/promises');
const {BackendClient, localNavigation, externalLink, clipboardWriteAllowed} = require('./lifecycle.cjs');

const root = path.resolve(__dirname, '..');
const loading = pathToFileURL(path.join(__dirname, 'loading.html')).href;

async function readyPage(origin, backend) {
  const deadline = Date.now() + 120000;
  while (Date.now() < deadline && !backend.exited) {
    const ready = await new Promise(resolve => {
      const request = http.get(origin + '/', {timeout: 1000}, response => {
        response.resume();
        resolve(response.statusCode === 200);
      });
      request.on('timeout', () => request.destroy());
      request.on('error', () => resolve(false));
    });
    if (ready) return;
    await delay(250);
  }
  throw new Error('Die Pipeline wurde nicht bereit. Prüfe, ob eine Browser-Pipeline bereits läuft oder die Python-Einrichtung fehlt.');
}

async function startDesktop() {
  if (process.env.PIPELINE_DESKTOP_GUARDED !== '1' || !path.isAbsolute(process.env.PIPELINE_DESKTOP_PYTHON || '')) {
    dialog.showErrorBox('Video Pipeline', 'Bitte über Start-Desktop.cmd starten. Die Prozessüberwachung ist erforderlich.');
    app.exit(1);
    return null;
  }
  app.setName('Video Pipeline');
  app.setPath('userData', path.join(root, '.runtime', 'electron-profile', process.platform + '-' + process.arch));
  const stop = process.argv.includes('--stop');
  if (!app.requestSingleInstanceLock({stop})) {
    app.exit(0);
    return null;
  }
  if (stop) { app.exit(0); return null; }

  let window, backend, origin;
  let deciding = false;
  let draining = false;
  let exiting = false;

  const quitNow = () => {
    exiting = true;
    // The native guard waits for this process and removes its owned descendants.
    app.exit(0);
  };

  async function requestQuit() {
    if (deciding || exiting) return;
    deciding = true;
    try {
      if (!backend || backend.exited) { quitNow(); return; }
      let status;
      try { status = await backend.request('status'); }
      catch {
        const result = await dialog.showMessageBox(window, {type: 'warning', title: 'Pipeline antwortet nicht',
          message: 'Die Anwendung und ihre Prozesse jetzt beenden?',
          detail: 'Eine laufende Erstellung wird unterbrochen. Bereits gespeicherte Skripte und Videos bleiben erhalten.',
          buttons: ['Weiter geöffnet lassen', 'Alles beenden'], defaultId: 0, cancelId: 0});
        if (result.response === 1) quitNow();
        return;
      }
      let action = 1;
      if (status.busy || draining) {
        const result = await dialog.showMessageBox(window, {type: 'question', title: 'Pipeline beenden',
          message: draining ? 'Die laufende Arbeit wird noch abgeschlossen.' : 'Die Pipeline arbeitet gerade.',
          detail: 'Beim Beenden werden Backend, Stimme und Schnitt ebenfalls beendet. Das Fenster bleibt während des Wartens sichtbar.',
          buttons: [draining ? 'Weiter warten' : 'Weiter geöffnet lassen', 'Nach Abschluss beenden', 'Abbrechen und beenden'],
          defaultId: 0, cancelId: 0, noLink: true});
        action = result.response;
        if (action === 0) return;
      }
      if (action === 2) {
        draining = true;
        window.setTitle('Video Pipeline – wird beendet');
        await backend.request('abort').catch(() => {});
        // Bounded grace period, then the guard forcibly clears the owned process tree.
        await Promise.race([backend.exit, delay(2000)]);
        quitNow();
        return;
      }
      if (!draining) {
        draining = true;
        window.setTitle('Video Pipeline – wird nach Abschluss beendet');
        window.setProgressBar(2);
        await backend.request('drain');
        backend.exit.then(quitNow);
      }
    } catch {
      dialog.showErrorBox('Beenden noch nicht abgeschlossen', 'Die Pipeline antwortet nicht. Schließe das Fenster erneut und wähle „Alles beenden“.');
    } finally { deciding = false; }
  }

  app.on('before-quit', event => {
    if (!exiting) { event.preventDefault(); void requestQuit(); }
  });
  app.on('second-instance', (_event, _commandLine, _workingDirectory, data) => {
    if (window) { if (window.isMinimized()) window.restore(); window.show(); window.focus(); }
    if (data?.stop) void requestQuit();
  });
  await app.whenReady();
  await session.defaultSession.setProxy({mode: 'direct'});
  // This dedicated local UI must load the current pipeline after an application update.
  await session.defaultSession.clearCache();
  session.defaultSession.setPermissionRequestHandler((contents, permission, callback, details) => {
    callback(contents === window?.webContents && clipboardWriteAllowed(permission, details.requestingUrl, origin, details.isMainFrame));
  });
  session.defaultSession.setPermissionCheckHandler((contents, permission, requestingOrigin, details) =>
    contents === window?.webContents && clipboardWriteAllowed(permission, requestingOrigin, origin, details.isMainFrame));
  session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
    const allowed = details.url === loading || (origin && (localNavigation(details.url, origin)
      || details.url.startsWith('blob:' + origin + '/')));
    callback({cancel: !allowed});
  });
  window = new BrowserWindow({width: 1280, height: 900, minWidth: 800, minHeight: 600,
    title: 'Video Pipeline', backgroundColor: '#f6f5f1',
    webPreferences: {nodeIntegration: false, contextIsolation: true, sandbox: true,
      webSecurity: true, allowRunningInsecureContent: false, webviewTag: false, devTools: false}});
  window.on('close', event => { if (!exiting) { event.preventDefault(); void requestQuit(); } });
  window.webContents.on('will-attach-webview', event => event.preventDefault());
  window.webContents.on('will-navigate', (event, url) => {
    if (!origin || !localNavigation(url, origin)) event.preventDefault();
  });
  window.webContents.on('will-redirect', (event, url) => {
    if (!origin || !localNavigation(url, origin)) event.preventDefault();
  });
  window.webContents.setWindowOpenHandler(({url}) => {
    if (externalLink(url)) void shell.openExternal(url).catch(() => {});
    return {action: 'deny'};
  });
  window.webContents.on('render-process-gone', () => {
    if (!exiting) {
      dialog.showErrorBox('Oberfläche beendet', 'Die Oberfläche wurde unerwartet beendet. Die Pipeline wird ebenfalls gestoppt. Gespeicherte Aufträge bleiben erhalten.');
      quitNow();
    }
  });
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    {label: 'Anwendung', submenu: [{label: 'Beenden', accelerator: process.platform === 'darwin' ? 'Command+Q' : 'Alt+F4', click: requestQuit}]},
    {label: 'Bearbeiten', submenu: [{role: 'undo'}, {role: 'redo'}, {type: 'separator'},
      {role: 'cut'}, {role: 'copy'}, {role: 'paste'}, {role: 'selectAll'}]},
    {label: 'Ansicht', submenu: [{role: 'resetZoom'}, {role: 'zoomIn'}, {role: 'zoomOut'}, {role: 'togglefullscreen'}]},
  ]));
  await window.loadURL(loading);
  const logDirectory = path.join(root, 'data', 'desktop');
  fs.mkdirSync(logDirectory, {recursive: true});
  const log = fs.openSync(path.join(logDirectory, 'backend.log'), 'a');
  const environment = {...process.env, PYTHONUNBUFFERED: '1', PYTHONUTF8: '1'};
  delete environment.PIPELINE_DESKTOP_PYTHON;
  delete environment.PIPELINE_DESKTOP_GUARDED;
  const child = spawn(process.env.PIPELINE_DESKTOP_PYTHON, [path.join(__dirname, 'backend.py')],
    {cwd: root, env: environment, windowsHide: true, stdio: ['pipe', 'pipe', log]});
  fs.closeSync(log);
  backend = new BackendClient(child);
  backend.chooseFolder = async () => {
    const result = await dialog.showOpenDialog(window, {title:'Ordner für fertige Videos auswählen',
      properties:['openDirectory', 'createDirectory']});
    return result.canceled ? null : result.filePaths[0] || null;
  };
  backend.exit.then(() => {
    if (!draining && !exiting) {
      dialog.showErrorBox('Pipeline beendet', 'Die Pipeline konnte nicht weiterlaufen. Falls sie bereits im Browser gestartet ist, beende sie zuerst mit stop.cmd. Andernfalls prüfe data/desktop/backend.log und die lokale Einrichtung.');
      quitNow();
    }
  });
  let startupTimer;
  const port = await Promise.race([backend.starting, new Promise((_resolve, reject) => {
    startupTimer = setTimeout(() => reject(new Error('Startzeit überschritten')), 120000);
  })]).finally(() => clearTimeout(startupTimer));
  origin = `http://127.0.0.1:${port}`;
  await readyPage(origin, backend);
  await window.loadURL(origin + '/');
  return {window, backend, origin, requestQuit};
}

module.exports = {startDesktop};
