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

test('issue page attaches only summaries belonging to that issue', async () => {
  const html = fs.readFileSync('entity.html', 'utf8');
  const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];
  const attached = [];
  const root = { innerHTML: '' };
  const rows = { innerHTML: '', parentElement: { appendChild: section => attached.push(section) } };
  const summary = { t: '<unsafe>', a: '필자', l: '호', s: '요지', h: '해제', kw: ['낱말'], c: [['논지', '주장']] };
  const issue = { id: 'cb212', no: 212, year: 2026, season: '여름', list: 212, n: 1, n_crit: 1 };
  const context = {
    qs: new Map([['t', 'issue'], ['id', 'cb212']]), shell() {},
    document: { getElementById: id => id === 'root' ? root : rows, createElement: () => ({}) },
    db: () => Promise.resolve({ cb: [issue], P: new Map() }),
    esc: value => String(value).replaceAll('<', '&lt;').replaceAll('>', '&gt;'),
    CB: { name: '창작과비평', pub: '창비', list: id => String(id), item: id => String(id) },
    cbNo: value => String(value.no), href: { issue: id => id },
    load: name => Promise.resolve(name === 'issues_cb_items' ? { cb212: [{ i: 1, s: 1, t: '표제', a: '필자', sec: '촌평' }] } : { '1': summary, '2': { ...summary, t: '다른 호' } })
  };
  vm.runInNewContext(script, context);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(attached.length, 1);
  assert.ok(attached[0].innerHTML.includes('&lt;unsafe&gt;'));
  assert.ok(!attached[0].innerHTML.includes('다른 호'));
});
