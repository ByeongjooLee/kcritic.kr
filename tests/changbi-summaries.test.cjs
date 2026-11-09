const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('reviewed summaries expose only the approved fields and ids', () => {
  const data = JSON.parse(fs.readFileSync('site/data/v2/changbi_summaries.json', 'utf8'));
  for (const id of ['7335', '7374', '7375']) assert.ok(data[id]);
  for (const [id, entry] of Object.entries(data)) {
    assert.equal(entry.u, `CB-${id.padStart(5, '0')}`);
    assert.deepEqual(Object.keys(entry).sort(), ['u','t','a','y','l','s','h','kw','c'].sort());
    assert.ok(Array.isArray(entry.c));
    for (const claim of entry.c) assert.ok(['주장', '논거', '비판', '제언'].includes(claim[1]));
    assert.ok(!JSON.stringify(entry).includes('@'));
  }
});

test('entity inline script parses and escapes summary content', () => {
  const html = fs.readFileSync('entity.html', 'utf8');
  for (const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]);
  for (const field of ['t', 'a', 'l', 's', 'h']) assert.ok(html.includes(`esc(entry.${field})`));
  assert.ok(html.includes('esc(claim[0])'));
});
