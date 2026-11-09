const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('reviewed summaries expose only the approved fields and ids', () => {
  const data = JSON.parse(fs.readFileSync('site/data/v2/changbi_summaries.json', 'utf8'));
  assert.deepEqual(Object.keys(data), ['7335', '7374', '7375']);
  for (const entry of Object.values(data)) {
    assert.deepEqual(Object.keys(entry).sort(), ['u','t','a','y','l','s','h','kw','c'].sort());
    assert.equal(entry.c.length, 5);
    assert.ok(!JSON.stringify(entry).includes('@'));
  }
});

test('entity inline script parses and escapes summary content', () => {
  const html = fs.readFileSync('entity.html', 'utf8');
  for (const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]);
  for (const field of ['t', 'a', 'l', 's', 'h']) assert.ok(html.includes(`esc(entry.${field})`));
  assert.ok(html.includes('esc(claim[0])'));
});
