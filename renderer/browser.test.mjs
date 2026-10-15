import assert from 'node:assert/strict';
import {test} from 'node:test';
import {resolveBrowserExecutable} from './browser.mjs';

test('uses installed browsers on macOS and Linux without downloading a fallback', () => {
  const mac='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  assert.equal(resolveBrowserExecutable({platform:'darwin',env:{},exists:path=>path===mac}),mac);
  assert.equal(resolveBrowserExecutable({platform:'linux',env:{PATH:'/usr/bin'},exists:path=>path==='/usr/bin/chromium'}),'/usr/bin/chromium');
  assert.throws(()=>resolveBrowserExecutable({platform:'linux',env:{},exists:()=>false}),/kein Browser automatisch/);
});

test('finds an installed Windows browser even when Program Files variables are wrong', () => {
  const chrome = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  const found = resolveBrowserExecutable({
    platform: 'win32',
    env: {PROGRAMFILES: 'X:\\missing', 'PROGRAMFILES(X86)': 'Y:\\missing'},
    exists: (path) => path === chrome,
  });
  assert.equal(found, chrome);
});

test('finds Chrome in a nonstandard Program Files (x86) directory', () => {
  const chrome = 'D:\\Apps (x86)\\Google\\Chrome\\Application\\chrome.exe';
  const found = resolveBrowserExecutable({
    platform: 'win32',
    env: {'PROGRAMFILES(X86)': 'D:\\Apps (x86)'},
    exists: (path) => path === chrome,
  });
  assert.equal(found, chrome);
});

test('refuses a missing explicit browser instead of attempting a download', () => {
  assert.throws(() => resolveBrowserExecutable({
    platform: 'win32',
    env: {REMOTION_BROWSER_EXECUTABLE: 'C:\\missing\\chrome.exe'},
    exists: () => false,
  }), /REMOTION_BROWSER_EXECUTABLE.*nicht gefunden/);
});

test('reports a missing Windows browser without a network request', () => {
  assert.throws(() => resolveBrowserExecutable({platform: 'win32', env: {}, exists: () => false}),
    /Chrome oder Edge.*lokal/);
});

test('Windows cannot delegate rendering to WSL, network binaries or a debug endpoint', () => {
  for (const browser of ['C:\\Windows\\System32\\wsl.exe', '\\\\wsl.localhost\\Ubuntu\\chrome.exe',
    '/usr/bin/chromium', 'http://127.0.0.1:9222', '\\\\server\\share\\chrome.exe']) {
    assert.throws(() => resolveBrowserExecutable({platform:'win32', env:{REMOTION_BROWSER_EXECUTABLE:browser}, exists:()=>true}), /nativer.*WSL/);
  }
});
import {guardedBrowserExecutable} from './browser.mjs';

test('macOS desktop registers each detached drawing browser and refuses a missing guard', () => {
  const env = {PIPELINE_PROCESS_REGISTRY: '/private/session', PIPELINE_BROWSER_WRAPPER: '/private/browser-wrapper'};
  assert.equal(guardedBrowserExecutable('/Applications/Chrome', {platform:'darwin', env, exists:()=>true}), '/private/browser-wrapper');
  assert.equal(env.PIPELINE_REAL_BROWSER, '/Applications/Chrome');
  assert.throws(() => guardedBrowserExecutable('/Applications/Chrome', {platform:'darwin', env, exists:()=>false}), /Prozessüberwachung/);
  assert.equal(guardedBrowserExecutable('/usr/bin/chromium', {platform:'linux', env}), '/usr/bin/chromium');
});
