// 『창작과비평』 낱말 검색 (2026-11-10): cb_search.json 형식·공개 필드, kc.js cbSearch 순위, 세 검색 화면 연결
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const read = f => fs.readFileSync(path.join(root, f), 'utf8');
const rows = JSON.parse(read('site/data/v2/cb_search.json'));
const summaries = JSON.parse(read('site/data/v2/changbi_summaries.json'));

function kc() {   // kc.js 의 검색 함수만 꺼내 돌린다
  const src = read('kc.js');
  const start = src.indexOf('const CB = {'), end = src.indexOf('const LODN');
  const ctx = { href: { issue: id => `/entity.html?t=issue&id=${id}`, essay: id => `/entity.html?t=essay&id=${id}` } };
  vm.runInNewContext(src.slice(start, end) + ';this.cbSearch=cbSearch;this.cbHref=cbHref;this.cbMeta=cbMeta;', ctx);
  return ctx;
}

test('index rows carry only public TOC fields plus reviewed keywords and gist', () => {
  assert.ok(rows.length > 4000);
  const withSummary = rows.filter(r => r[7]);
  assert.equal(withSummary.length, Object.keys(summaries).length);
  for (const r of rows) {
    assert.equal(r.length, 8);
    const s = summaries[String(r[0])];
    if (s) { assert.equal(r[6], s.kw.join('|')); assert.equal(r[7], s.s); }
    else { assert.equal(r[6], ''); assert.equal(r[7], ''); }
  }
  assert.ok(!JSON.stringify(rows).includes('@'));
});

test('cbSearch finds by title, author and keyword, ignoring spaces', () => {
  const { cbSearch } = kc();
  const kwRow = rows.find(r => r[6].includes('민족문학론'));
  assert.ok(cbSearch('민족문학론', rows, 1e9).includes(kwRow), 'keyword hit');
  assert.ok(cbSearch('민족 문학론', rows, 1e9).includes(kwRow), 'spaces ignored');
  const t = rows.find(r => r[7]);
  assert.equal(cbSearch(t[3], rows, 1)[0][3], t[3], 'exact title first');
  assert.ok(cbSearch('백낙청', rows, 50).every(r => [r[3], r[4], r[6], r[7], r[5]].join(' ').replace(/\s/g, '').includes('백낙청')));
  assert.equal(cbSearch('', rows).length, 0);
});

test('loose mode ranks sentence questions by matched words', () => {
  const { cbSearch } = kc();
  const hits = cbSearch('리얼리즘과 민족문학론은 어떻게 만났나', rows, 10, true);
  assert.ok(hits.length > 0);
  assert.ok([hits[0][3], hits[0][6], hits[0][7]].join('').includes('리얼리즘'));
});

test('links go to the Changbi essay page when reviewed, otherwise to the webzine', () => {
  const { cbHref } = kc();
  const a = rows.find(r => r[7]), b = rows.find(r => !r[7]);
  assert.equal(cbHref(a), `/entity.html?t=essay&id=cb${a[0]}`);
  assert.equal(cbHref(b), `https://magazine.changbi.com/MCQuarterly/Item/${b[0]}`);
  assert.ok(read('entity.html').includes('T === "essay" && /^cb'), 'entity.html has a Changbi essay page');
});

test('header searches, explore and unified search all use the index', () => {
  for (const f of ['kc.js', 'kc-shell.js']) assert.ok(read(f).includes('cb_search') && read(f).includes('『창작과비평』 글'), f);
  assert.ok(read('explore.html').includes('renderCB(S.q)'));
  assert.ok(read('search.js').includes('cbSearch(q,rows,10,true)') && !read('search.html').includes('changbi-results'), 'unified search merges Changbi into the criticism column');
  for (const f of ['explore.html', 'entity.html']) for (const m of read(f).matchAll(/<script>([\s\S]*?)<\/script>/g)) new vm.Script(m[1]);
  for (const f of ['kc.js', 'kc-shell.js', 'search.js']) new vm.Script(read(f));
});

test('Changbi essays are in essays.json with person/concept relations (publish_cb.py, 2026-11-10)', () => {
  const essays = JSON.parse(read('site/data/v2/essays.json'));
  const cb = essays.filter(e => e.coll === 'cb');
  assert.ok(cb.length > 1500 && cb.length <= rows.filter(r => r[7]).length);
  for (const e of cb) { assert.match(e.id, /^cb\d+$/); assert.ok(summaries[e.id.slice(2)], e.id); assert.ok(Number.isInteger(e.issue)); }
  assert.ok(cb.some(e => e.subjects.length) && cb.some(e => e.theorists.length) && cb.some(e => e.concepts.length));
  const people = new Set(JSON.parse(read('site/data/v2/people.json')).map(p => p.id));
  assert.ok(cb.every(e => people.has(e.critic)), 'every Changbi author has a person page');
  for (const f of ['explore.html', 'index.html', 'about.html']) assert.ok(!read(f).includes('cbEssays'), f);
  assert.ok(read('entity.html').includes('D.E.get(ID)') && read('kc.js').includes('const venueLine'));
});
