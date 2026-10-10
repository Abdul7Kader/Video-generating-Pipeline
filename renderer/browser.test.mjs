import assert from 'node:assert/strict';
import {test} from 'node:test';
import {resolveBrowserExecutable} from './browser.mjs';

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
