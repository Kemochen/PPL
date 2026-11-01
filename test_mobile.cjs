const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const { webcrypto } = require('node:crypto');
const source = readFileSync(require('node:path').join(__dirname, 'static/platform.js'), 'utf8');

test('UUID fallback works without crypto.randomUUID', () => {
  const window = { crypto: { getRandomValues: b => webcrypto.getRandomValues(b) } };
  runInNewContext(source, { window, Uint8Array });
  const ids = new Set(Array.from({ length: 1000 }, () => window.pplPlatform.newId()));
  assert.equal(ids.size, 1000);
  for (const id of ids) assert.match(id, /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/);
});

test('iOS exports use native sharing instead of unsupported blob navigation', () => {
  const messages = [];
  const window = { webkit: { messageHandlers: { pplExport: { postMessage: value => messages.push(value) } } } };
  runInNewContext(source, { window });
  window.pplPlatform.download('{"profiles":[]}', 'aircraft.json', 'application/json');
  assert.equal(messages.length, 1);
  assert.equal(messages[0].filename, 'aircraft.json');
  assert.equal(messages[0].content, '{"profiles":[]}');
});

test('browser export creates, clicks and cleans up a temporary link', () => {
  let clicked = false, removed = false, revoked = false, attached = false;
  const link = { click: () => { clicked = true; }, remove: () => { removed = true; } };
  const window = {};
  runInNewContext(source, {
    window, Blob,
    URL: { createObjectURL: () => 'blob:test', revokeObjectURL: () => { revoked = true; } },
    document: { createElement: () => link, body: { appendChild: () => { attached = true; } } },
    setTimeout: callback => callback()
  });
  window.pplPlatform.download('a,b\r\n', 'poh.csv', 'text/csv');
  assert.equal(link.download, 'poh.csv');
  assert.ok(clicked && removed && revoked && attached);
});
