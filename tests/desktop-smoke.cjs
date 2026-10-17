// Explicit native GUI acceptance, launched inside the platform's ProcessGroup.
// Reads the real UI and closes its own test window. Does not generate a video.
const {app, dialog} = require('electron');
const {startDesktop} = require('../desktop/main.cjs');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {spawn} = require('node:child_process');
const {setTimeout: delay} = require('node:timers/promises');

const folder = process.env.DESKTOP_SMOKE_DIRECTORY;
if (!folder || !path.isAbsolute(folder)) throw new Error('Explicit local test directory required');
const trace = value => fs.appendFileSync(path.join(folder, 'trace.txt'), value + '\n');
app.on('browser-window-created', (_event, window) => {
  trace('window created');
  try {
    window.webContents.debugger.attach('1.3');
    window.webContents.debugger.sendCommand('Network.enable').catch(() => {});
    window.webContents.debugger.on('message', (_event, method, parameters) => {
      if (method === 'Network.loadingFailed') trace('network failed: ' + JSON.stringify(parameters));
      if (method === 'Network.responseReceived') trace('response: ' + parameters.response.status + ' ' + parameters.response.url.split('?')[0]);
    });
  } catch (error) { trace('Private test diagnostics unavailable: ' + String(error)); }
  window.webContents.on('did-start-loading', () => trace('loading'));
  window.webContents.on('did-finish-load', () => trace('loaded: ' + window.webContents.getURL()));
  window.webContents.on('did-fail-load', (_e, code, text, url) => trace(JSON.stringify({code, text, url})));
  window.webContents.on('console-message', (_e, details, message) => trace('console: ' + JSON.stringify(message||details)));
  window.webContents.on('render-process-gone', (_e, details) => trace('renderer gone: ' + JSON.stringify(details)));
});
dialog.showErrorBox = (title, content) => {
  fs.writeFileSync(path.join(folder, 'error.json'), JSON.stringify({title, content}));
  app.exit(1);
};

function status(origin, headers) {
  return new Promise((resolve, reject) => {
    http.get(origin + '/api/jobs', {headers}, response => {
      response.resume();
      resolve(response.statusCode);
    }).on('error', reject);
  });
}

(async () => {
  const desktop = await startDesktop();
  trace('startDesktop returned');
  assert.ok(desktop);
  const {window, backend, origin} = desktop;
  const preferences = window.webContents.getLastWebPreferences();
  assert.equal(preferences.nodeIntegration, false);
  assert.equal(preferences.sandbox, true);
  assert.equal(preferences.contextIsolation, true);
  assert.equal(preferences.webSecurity, true);
  assert.equal(await status(origin, {Origin: 'https://foreign.example'}), 403);
  assert.equal(await status(origin, {Host: 'foreign.example'}), 403);
  assert.equal((await backend.request('status')).busy, false);
  const page = await window.webContents.executeJavaScript('({title: document.title, heading: document.querySelector("h1")?.innerText, node: typeof require})');
  assert.equal(page.title, 'Video Pipeline');
  assert.equal(page.node, 'undefined');
  assert.ok(page.heading);
  const modes = await window.webContents.executeJavaScript(`(()=>{
    const tabs=[...document.querySelectorAll('[role=tab]')].map(node=>node.innerText);
    document.getElementById('mode-frame').click();
    const frame={text:document.getElementById('workspace').innerText,newHidden:document.getElementById('new-button').hidden,selected:document.getElementById('mode-frame').getAttribute('aria-selected')};
    document.getElementById('mode-animated').click();
    return {tabs,frame,animated:document.getElementById('mode-animated').getAttribute('aria-selected')};
  })()`);
  assert.deepEqual(modes.tabs,['Animierte Strichmännchen','Frame']);
  assert.equal(modes.frame.newHidden,false);assert.equal(modes.frame.selected,'true');assert.equal(modes.animated,'true');
  assert.match(modes.frame.text,/Nach deiner Textfreigabe läuft die Produktion/);
  await window.setSize(590,820);
  const narrow = await window.webContents.executeJavaScript('document.documentElement.scrollWidth <= window.innerWidth');
  assert.equal(narrow,true);
  window.setSize(1280,900);
  trace('Mode tabs, guarded Frame status and narrow window passed; no generation started');
  await window.webContents.executeJavaScript('document.getElementById("settings-button").click()');
  for (let i = 0; i < 100; i++) {
    if (await window.webContents.executeJavaScript('Boolean(document.getElementById("integration-save"))')) break;
    await delay(100);
  }
  assert.equal(await window.webContents.executeJavaScript('Boolean(document.getElementById("integration-save"))'), true);
  assert.equal(await window.webContents.executeJavaScript('Boolean(document.getElementById("image-access-check"))'), true);
  assert.equal(await window.webContents.executeJavaScript('document.getElementById("image-access-result").innerText'), '');
  for(let i=0;i<50;i++) {
    if(await window.webContents.executeJavaScript('document.getElementById("image-vault").innerText.length>0'))break;
    await delay(100);
  }
  const images=await window.webContents.executeJavaScript(`(()=>{
    const provider=document.getElementById('image-provider');
    const labels=[...provider.options].map(option=>option.textContent);
    const initial={provider:provider.value,free:document.getElementById('image-free').checked,secret:document.getElementById('image-token').value,password:document.getElementById('image-token').type};
    provider.value='antigravity';provider.dispatchEvent(new Event('change'));
    const googleVisible=!document.getElementById('image-google').hidden&&document.getElementById('image-cloudflare').hidden;
    provider.value=initial.provider;provider.dispatchEvent(new Event('change'));
    return {labels,initial,googleVisible,testVisible:!document.getElementById('image-test').hidden};
  })()`);
  assert.equal(images.labels.length,2);assert.equal(images.initial.provider,'cloudflare');
  assert.equal(images.initial.free,false);assert.equal(images.initial.secret,'');assert.equal(images.initial.password,'password');
  assert.equal(images.googleVisible,true);assert.equal(images.testVisible,true);
  trace('Image provider controls, native vault hint and safe free defaults passed; no image generated');
  const creation = await window.webContents.executeJavaScript(`(()=>{
    const hidden=document.getElementById('new-production-profile').closest('[hidden]');
    return {hidden:Boolean(hidden),profileLabels:[...document.querySelectorAll('#create-form label')].filter(node=>node.innerText.includes('Produktionsprofil')).length};
  })()`);
  assert.equal(creation.hidden,true);assert.equal(creation.profileLabels,0);
  assert.equal(await window.webContents.executeJavaScript('document.querySelector("[data-integration=work_retention_days]").value'), '0');
  const picked = path.join(folder, 'chosen-video-folder');
  dialog.showOpenDialog = async () => ({canceled:false, filePaths:[picked]});
  const folderResult = await window.webContents.executeJavaScript('(async()=>{const state=await(await fetch("/api/settings")).json();return (await fetch("/api/settings/integrations/folder",{method:"POST",headers:{"X-Setup-Token":state.token}})).json()})()');
  assert.equal(folderResult.directory, picked);
  try {
    fs.writeFileSync(path.join(folder, 'settings.png'), (await window.webContents.capturePage(undefined, {stayAwake:true})).toPNG());
  } catch (error) {trace('Settings screenshot unavailable: ' + String(error));}
  await window.webContents.executeJavaScript('document.getElementById("settings-dialog").close()');
  await window.webContents.executeJavaScript(`(()=>{
    document.getElementById('mode-frame').click();document.getElementById('frame-new-button').click();
  })()`);
  for(let i=0;i<200;i++){
    if(await window.webContents.executeJavaScript('!actionPending'))break;
    await delay(100);
  }
  const ownedText='Eine Katze kommt aus dem Tierheim.\n\nSie erkundet aufmerksam ihr neues Zuhause.';
  await window.webContents.executeJavaScript(`(()=>{
    const choice=document.getElementById('frame-input-select');choice.value='narration';choice.dispatchEvent(new Event('change'));
    document.querySelector('[name=topic]').value='Native Frame-Skriptprüfung';
    document.getElementById('frame-narration').value=${JSON.stringify(ownedText)};
    document.getElementById('duration-minutes').value='30';document.getElementById('duration-extra-seconds').value='0';
    document.getElementById('create-form').requestSubmit();
  })()`);
  for(let i=0;i<100;i++){
    if(await window.webContents.executeJavaScript('Boolean(document.querySelector(".frame-narration"))'))break;
    await delay(100);
  }
  const frameDraft=await window.webContents.executeJavaScript('({text:document.querySelector(".frame-narration")?.textContent,body:document.getElementById("workspace").innerText})');
  assert.equal(frameDraft.text,ownedText);assert.match(frameDraft.body,/Zieldauer: 30 Min/);
  assert.match(frameDraft.body,/Text freigeben & Video erstellen/);
  trace('Frame own-text UI round trip, 30-minute target, exact paragraphs and approval action passed; no inference or media generated');
  trace('Integration settings and private native-folder round trip passed; no credentials/settings saved');
  const reviewPanel = await window.webContents.executeJavaScript(`(async()=>{
    const originalFetch = window.fetch;
    window.fetch = async () => ({ok:true,json:async()=>({review:null,job_status:'video_review',connection:'Fixture: keine externe Verbindung',local_path:'Fixture/video.mp4'})});
    try {
      await ReviewControls.mount({id:'fixture',status:'video_review',output_path:'fixture.mp4',render_version:1,output_sha256:'fixture'});
      return document.getElementById('discord-review-panel').innerText;
    } finally {window.fetch=originalFetch;clearTimeout(ReviewControls.timer);document.getElementById('discord-review-panel')?.remove();}
  })()`);
  assert.match(reviewPanel, /Zur Discord-Abnahme senden/);
  assert.match(reviewPanel, /Uploadpaket/);
  assert.match(reviewPanel, /Endvideo auf diesem Rechner/);
  assert.match(reviewPanel, /Projekt behalten/);
  assert.match(reviewPanel, /Arbeitsdateien jetzt bereinigen/);
  trace('Review panel rendered with fixture; no video, Discord message or upload created');
  const errorCard = await window.webContents.executeJavaScript(`(()=>{
    PipelineErrors.show({id:'0123456789abcdef',job_id:'fixture',stage:'voice',stage_label:'Erzählerstimme erzeugen',code:'timeout',message:'Fixture: Zeitlimit überschritten <img src=x>',next_action:'Stimme unter Einstellungen prüfen.',retryable:true,context:{scene_id:'scene_2'}});
    const card=document.getElementById('pipeline-error-card');
    const result={text:card.innerText,role:card.getAttribute('role'),images:card.querySelectorAll('img').length};
    card.remove();return result;
  })()`);
  assert.equal(errorCard.role,'alert');assert.equal(errorCard.images,0);
  assert.match(errorCard.text,/Erzählerstimme/);assert.match(errorCard.text,/Fehlerdetails kopieren/);assert.match(errorCard.text,/0123456789abcdef/);
  trace('Persistent error card: stage, next action and diagnostic ID rendered safely; no production failure caused');
  const clipboardPermissions = await window.webContents.executeJavaScript(
    'Promise.all(["clipboard-write", "clipboard-read"].map(async name => ({name, state: (await navigator.permissions.query({name})).state})))');
  assert.equal(clipboardPermissions[0].state, 'granted');
  assert.equal(clipboardPermissions[1].state, 'denied');
  trace('UI, sandbox, Host/Origin and idle checks passed');
  await delay(1500);
  try {
    const image = await window.webContents.capturePage(undefined, {stayAwake: true});
    fs.writeFileSync(path.join(folder, 'desktop.png'), image.toPNG());
  } catch (error) { trace('Screenshot unavailable: ' + String(error)); }

  const helperFile = path.join(folder, 'helper.json');
  const helper = spawn(process.env.PIPELINE_DESKTOP_PYTHON, ['-c',
    'import subprocess,sys,time,json,os; p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(120)"]); open(sys.argv[1],"w").write(json.dumps([os.getpid(),p.pid])); time.sleep(120)', helperFile],
    {windowsHide: true, stdio: 'ignore'});
  for (let i = 0; i < 100 && !fs.existsSync(helperFile); i++) await delay(50);
  const helperPids = JSON.parse(fs.readFileSync(helperFile));
  const decisions = [];
  const originalRequest = backend.request.bind(backend);
  backend.request = command => command === 'status' && decisions.length
    ? Promise.resolve({busy: true}) : originalRequest(command);
  dialog.showMessageBox = async (_window, options) => {
    const response = decisions.shift();
    assert.ok(Number.isInteger(response), 'Unexpected dialog: ' + options.message);
    assert.equal(options.buttons.length, 3);
    trace('Quit dialog: ' + options.buttons[response]);
    return {response};
  };
  decisions.push(0);
  await desktop.requestQuit();
  assert.equal(backend.exited, false, 'Cancel must keep the pipeline running');
  fs.writeFileSync(path.join(folder, 'ready.json'), JSON.stringify({
    origin, page, electron: process.pid, backend: backend.child.pid, helper: helper.pid, helperPids,
    screenshotAvailable: fs.existsSync(path.join(folder, 'desktop.png')),
    clipboardPermissions,
    preferences: {sandbox: preferences.sandbox, contextIsolation: preferences.contextIsolation,
      nodeIntegration: preferences.nodeIntegration, webSecurity: preferences.webSecurity},
  }));
  for (let i = 0; i < 600 && !fs.existsSync(path.join(folder, 'close')); i++) await delay(100);
  if (process.argv.includes('--crash')) process.exit(7);
  decisions.push(process.argv.includes('--abort') ? 2 : 1);
  window.close();
})().catch(error => {
  fs.writeFileSync(path.join(folder, 'error.json'), JSON.stringify({error: String(error), stack: error.stack}));
  app.exit(1);
});
