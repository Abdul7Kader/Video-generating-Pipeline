const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../web/progress.js'), 'utf8');

function setup(saved = null, unavailableStorage = false) {
  let now = 0, nextTimer = 0;
  const timers = new Map(), storage = new Map();
  if (saved !== null) storage.set('pipeline-process-times-v2', saved);
  class Element {
    constructor() {
      this.children = []; this.attributes = {}; this.isConnected = true;
      this.classList = {add: value => { this.className += ` ${value}`; }};
    }
    setAttribute(key, value) { this.attributes[key] = value; }
    removeAttribute(key) { delete this.attributes[key]; }
    append(...items) { this.children.push(...items); }
    replaceChildren(...items) { this.children.forEach(item => { item.isConnected = false; }); items.forEach(item => { item.isConnected = true; }); this.children = items; }
  }
  const context = {
    window: {}, document: {createElement: () => new Element()}, performance: {now: () => now},
    localStorage: {
      getItem: key => { if (unavailableStorage) throw new Error('Storage disabled'); return storage.get(key); },
      setItem: (key, value) => { if (unavailableStorage) throw new Error('Storage disabled'); storage.set(key, value); }
    },
    setInterval: callback => { timers.set(++nextTimer, callback); return nextTimer; },
    clearInterval: id => timers.delete(id)
  };
  vm.runInNewContext(source, context);
  const host = new Element();
  return {
    progress: context.window.ProcessProgress, host, storage, timers, context,
    tick(seconds) { now += seconds * 1000; [...timers.values()].forEach(callback => callback()); },
    parts() { return host.children[0].children; }
  };
}

test('counts elapsed time, estimates remaining time, and never completes before the response', () => {
  const ui = setup('{"flow":[1,1,1]}');
  const run = ui.progress.start(ui.host, {label: 'Skript und Zeichnungen', key:'flow', baseline: 60});
  assert.equal(ui.progress.busy, true);
  ui.tick(30);
  assert.equal(ui.parts()[1].value, undefined);
  assert.match(ui.parts()[2].textContent, /Vergangen: 30 Sek.*noch ca. 30 Sek/);
  ui.tick(30);
  assert.match(ui.parts()[3].textContent, /Vorgang läuft weiter/);
  assert.doesNotMatch(ui.parts()[2].textContent, /Noch ca. 0/);
  ui.tick(3600);
  assert.equal(ui.parts()[1].value, undefined);
  run.finish();
  assert.equal(ui.parts()[1].value, 100);
  assert.match(ui.parts()[1].attributes['aria-label'],/abgeschlossen/);
  assert.equal(ui.host.children[0].attributes['aria-busy'], 'false');
  assert.equal(ui.progress.busy, false);
  assert.equal(ui.timers.size, 0);
  ui.tick(50);
  assert.equal(ui.parts()[1].value, 100);
});

test('failure stops the clock, keeps progress below 100, and renders errors as text', () => {
  const ui = setup();
  const run = ui.progress.start(ui.host, {label: 'Stimme', baseline: 100, key: 'voice:qwen_narrator'});
  ui.tick(20);
  run.fail('<img src=x onerror=alert(1)>');
  const timing = ui.parts()[2].textContent;
  ui.tick(30);
  assert.equal(ui.parts()[2].textContent, timing);
  assert.equal(ui.parts()[3].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(ui.parts()[1].value, undefined);
  assert.equal(ui.parts()[1].hidden, true);
  assert.equal(ui.storage.size, 0);
  assert.equal(ui.progress.busy, false);
  run.finish();
  assert.equal(ui.parts()[1].value, undefined);
});

test('removing a progress panel releases its timer and busy state', () => {
  const ui = setup();
  ui.progress.start(ui.host, {label: 'Stimme', baseline: 100});
  ui.host.replaceChildren();
  ui.tick(1);
  assert.equal(ui.timers.size, 0);
  assert.equal(ui.progress.busy, false);
});

test('learns completed runtime without storing text and ignores fast cache responses', () => {
  const ui = setup();
  const options = ui.progress.voiceOptions({id: 'qwen_narrator', label: 'Erzähler', provider: 'qwen_tts'}, 'Ein kurzer Text.');
  const cached = ui.progress.start(ui.host, options);
  ui.tick(0.5); cached.finish();
  assert.equal(ui.storage.size, 0);
  const generation = ui.progress.start(ui.host, options);
  ui.tick(options.baseline * 2); generation.finish();
  const saved = ui.storage.get('pipeline-process-times-v2');
  assert.deepEqual(JSON.parse(saved), {[options.key]: [2]});
  assert.doesNotMatch(saved, /kurzer Text|Erzähler/);
  ui.progress.start(ui.host, options).dispose();
  assert.match(ui.parts()[3].textContent, /noch nicht messbar/);
  for(let i=0;i<2;i++){const run=ui.progress.start(ui.host,options);ui.tick(options.baseline*2);run.finish()}
  ui.progress.start(ui.host, options);
  assert.match(ui.parts()[3].textContent, /Erfahrungswert aus 3.*ca. 2 Min/);
});

test('invalid or unavailable local storage does not break generation', () => {
  for (const saved of ['null', '[]', '{bad json', '{"voice:qwen_narrator":999}', '{"voice:qwen_narrator":"2"}']) {
    const ui = setup(saved);
    const run = ui.progress.start(ui.host, {label: 'Stimme', key: 'voice:qwen_narrator', baseline: 120});
    assert.match(ui.parts()[3].textContent, /noch nicht messbar/);
    run.finish();
    assert.equal(ui.progress.busy, false);
  }
  const ui = setup(null, true);
  const run = ui.progress.start(ui.host, {label: 'Stimme', key: 'voice:qwen_narrator', baseline: 120});
  ui.tick(120); run.finish();
  assert.equal(ui.parts()[1].value, 100);
  assert.equal(ui.progress.busy, false);
});

test('script estimates account for provider and duration; scene revisions are identified', () => {
  const ui = setup();
  const full = ui.progress.scriptOptions('antigravity', 60);
  assert.ok(ui.progress.scriptOptions('antigravity', 180).baseline > full.baseline);
  assert.ok(ui.progress.scriptOptions('qwen', 60).baseline > full.baseline);
  const scene = ui.progress.scriptOptions('antigravity', 60, true);
  assert.match(scene.label, /Szene überarbeiten/);
  assert.notEqual(scene.key, full.key);
  assert.match(ui.progress.scriptOptions('antigravity', 60, false, true).label, /überarbeiten/);
  ui.context.window.PipelineScriptModel='other-model';
  assert.notEqual(ui.progress.scriptOptions('antigravity',60).key,full.key);
  const voice={id:'thorsten',provider:'piper',installed:true};
  assert.notEqual(ui.progress.voiceOptions(voice,'Ein Test',1).key,ui.progress.voiceOptions(voice,'Ein Test',1.2).key);
});

test('render polling preserves elapsed time without blocking navigation; queues have no invented ETA', () => {
  const ui = setup();
  const run = ui.progress.start(ui.host, {label: 'Video erzeugen', baseline: 120, elapsedSeconds: 30, blocking: false});
  assert.equal(ui.progress.busy, false);
  assert.match(ui.parts()[2].textContent, /Vergangen: 30 Sek/);
  ui.tick(5);
  run.attach(ui.host);
  assert.equal(ui.timers.size, 1);
  assert.match(ui.parts()[2].textContent, /Vergangen: 35 Sek/);
  run.dispose();
  assert.equal(ui.timers.size, 0);
  ui.progress.start(ui.host, {label: 'Warteschlange', baseline: 120, waiting: true, blocking: false});
  ui.tick(10);
  assert.match(ui.parts()[2].textContent, /Wartezeit bisher: 10 Sek/);
  assert.match(ui.parts()[3].textContent, /noch nicht messbar/);
  assert.doesNotMatch(ui.parts()[3].textContent, /ca\./);
});

test('inconsistent measurements never create a confident ETA or a fake percentage',()=>{
  const ui=setup('{"slow":[1,2,4]}');
  const run=ui.progress.start(ui.host,{label:'Skript',key:'slow',baseline:60});
  ui.tick(60);
  assert.equal(ui.parts()[1].value,undefined);
  assert.match(ui.parts()[2].textContent,/Restzeit noch nicht messbar/);
  assert.doesNotMatch(ui.parts()[2].textContent,/noch ca\./);
  run.finish();
  assert.equal(ui.parts()[1].value,100);
});
