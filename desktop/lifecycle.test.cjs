const test = require('node:test');
const assert = require('node:assert/strict');
const {EventEmitter} = require('node:events');
const {PassThrough} = require('node:stream');
const {BackendClient, localNavigation, externalLink, clipboardWriteAllowed} = require('./lifecycle.cjs');

test('only the local main frame can copy text; clipboard reading and devices remain denied', () => {
  const origin = 'http://127.0.0.1:8080';
  assert.equal(clipboardWriteAllowed('clipboard-sanitized-write', origin + '/', origin, true), true);
  for (const permission of ['clipboard-read', 'media', 'geolocation', 'loopback-network', 'unknown']) {
    assert.equal(clipboardWriteAllowed(permission, origin, origin, true), false);
  }
  assert.equal(clipboardWriteAllowed('clipboard-sanitized-write', 'https://foreign.example', origin, true), false);
  assert.equal(clipboardWriteAllowed('clipboard-sanitized-write', origin, origin, false), false);
  assert.equal(clipboardWriteAllowed('clipboard-sanitized-write', origin, origin, undefined), false);
});

test('desktop navigation cannot escape loopback or launch arbitrary protocols', () => {
  const origin = 'http://127.0.0.1:8080';
  assert.equal(localNavigation(origin + '/?test=1', origin), true);
  for (const url of ['http://127.0.0.1:8080.evil.test/', 'http://localhost:8080/',
    'http://127.0.0.1:8081/', 'javascript:alert(1)', 'file:///C:/Windows/win.ini']) {
    assert.equal(localNavigation(url, origin), false);
  }
  assert.equal(externalLink('https://gemini.google.com/'), true);
  for (const url of ['https://gemini.google.com.evil.test/', 'https://user@gemini.google.com/',
    'http://gemini.google.com/', 'file:///C:/test.exe', 'ms-settings:privacy', 'https://evil.test/']) {
    assert.equal(externalLink(url), false);
  }
});

test('backend control matches replies and rejects pending work on backend exit', async () => {
  const child = new EventEmitter();
  child.stdout = new PassThrough();
  child.stdin = new PassThrough();
  const client = new BackendClient(child);
  child.stdout.write('normal log line\nPIPELINE_DESKTOP {"type":"starting","port":8080}\n');
  assert.equal(await client.starting, 8080);
  const reply = client.request('status');
  child.stdout.write('PIPELINE_DESKTOP {"type":"reply","id":"1","busy":true}\n');
  assert.equal((await reply).busy, true);
  const pending = client.request('drain');
  child.emit('exit', 1);
  await assert.rejects(pending, /beendet/);
  assert.equal(client.exited, true);
  child.stdout.end();
});

test('an invalid backend port never becomes a navigation target', async () => {
  const child = new EventEmitter();
  child.stdout = new PassThrough();
  child.stdin = new PassThrough();
  const client = new BackendClient(child);
  child.stdout.write('PIPELINE_DESKTOP {"type":"starting","port":"https://evil.test"}\n');
  child.emit('exit', 1);
  await assert.rejects(client.starting, /beendet/);
  child.stdout.end();
});
