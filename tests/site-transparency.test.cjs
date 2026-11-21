// 데이터와 출처(data.html) — 운영 주체·이용 조건·자료별 출처 안내가 깨지지 않았는지 본다.
// 실행: node --test tests/site-transparency.test.cjs
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const root = path.join(__dirname, '..');
const read = f => fs.readFileSync(path.join(root, f), 'utf8');
const cat = JSON.parse(read('site/data/datasets.json'));
const page = read('data.html');

test('모든 화면의 바닥글에서 데이터와 출처로 간다', () => {
  assert.ok(read('kc.js').includes('${KC}data.html'), 'kc.js 바닥글');
  assert.ok(read('kc-shell.js').includes('${R}data.html'), 'kc-shell.js 바닥글');
  assert.ok(read('about.html').includes('href="data.html"'), '소개');
  assert.ok(read('maker.html').includes('href="data.html"'), '만든 사람');
});

test('자료 묶음마다 출처·가공·한계·파일이 있고, 가리키는 파일이 실제로 있다', () => {
  const ids = new Set();
  for (const d of cat.datasets) {
    assert.ok(!ids.has(d.id), `id 중복 ${d.id}`); ids.add(d.id);
    for (const k of ['group', 'title', 'what', 'processing', 'license_key']) assert.ok(d[k], `${d.id}.${k}`);
    assert.ok(d.sources.length && d.limitations.length && d.files.length, `${d.id} 출처·한계·파일`);
    assert.ok(cat.licenses[d.license_key], `${d.id} license_key`);
    if (d.license_key_extra) assert.ok(cat.licenses[d.license_key_extra], `${d.id} license_key_extra`);
    assert.strictEqual(typeof d.personal_data, 'boolean', `${d.id}.personal_data`);
    assert.ok(Array.isArray(d.counts) && d.counts.length, `${d.id} 규모(build_site_meta.py 를 돌렸는가)`);
    for (const f of d.files) {
      if (f.includes('*')) assert.ok(fs.existsSync(path.join(root, path.dirname(f))), `${d.id} 폴더 ${f}`);
      else assert.ok(fs.existsSync(path.join(root, f)), `${d.id} 파일 ${f}`);
    }
    for (const s of d.sources) {
      assert.ok(s.ref || s.name, `${d.id} 출처 이름`);
      if (s.ref) assert.ok(cat.third_party.some(t => t.id === s.ref), `${d.id} 출처 ${s.ref} 가 third_party 에 없음`);
    }
  }
});

test('정해지지 않은 것은 비워 둔다 — 라이선스·운영 주체·연락처를 지어내지 않는다', () => {
  for (const [k, l] of Object.entries(cat.licenses)) {
    assert.ok(['undecided', 'fixed', 'decided'].includes(l.status), `${k}.status`);
    if (l.status === 'undecided') { assert.strictEqual(l.license, null, `${k}.license`); assert.strictEqual(l.license_url, null, `${k}.license_url`); }
    else assert.ok(l.license, `${k}: 정해졌으면 조건을 적는다`);
  }
  for (const k of ['operator', 'contact', 'funding', 'correction_channel']) {
    if (cat.site[`${k}_status`] === 'undecided') assert.strictEqual(cat.site[k], null, `site.${k}`);
    else assert.ok(cat.site[k], `site.${k}`);
  }
  for (const t of cat.third_party) {
    assert.ok(['confirmed', 'partial', 'unconfirmed'].includes(t.terms_status), `${t.id}.terms_status`);
    if (t.terms_status === 'unconfirmed') assert.strictEqual(t.terms, null, `${t.id}: 확인하지 못한 조건을 적지 않는다`);
    else assert.ok(t.terms && t.terms_url && t.checked, `${t.id}: 확인한 조건에는 근거 주소와 확인한 날`);
  }
});

test('화면의 자리 표시가 목록의 상태와 맞는다', () => {
  const marks = [...page.matchAll(/data-tbd="([a-z_]+)"/g)].map(m => m[1]).sort();
  const pending = ['operator', 'contact', 'funding', 'correction_channel'].filter(k => cat.site[`${k}_status`] === 'undecided').sort();
  assert.deepStrictEqual(marks, pending, '결정이 끝난 항목의 「결정 대기」 표시는 지우고 내용을 적는다');
});

test('JSON-LD 는 읽히고, 정해지지 않은 라이선스·운영 주체를 싣지 않는다', () => {
  const ld = f => JSON.parse(read(f).match(/<!-- JSONLD-START -->\s*<script type="application\/ld\+json">([\s\S]*?)<\/script>\s*<!-- JSONLD-END -->/)[1]);
  const dc = ld('data.html'), ws = ld('index.html');
  assert.strictEqual(dc['@type'], 'DataCatalog');
  assert.strictEqual(ws['@type'], 'WebSite');
  assert.strictEqual(dc.dataset.length, cat.datasets.length);
  for (const d of dc.dataset) {
    const src = cat.datasets.find(x => d['@id'].endsWith('#' + x.id));
    const lic = cat.licenses[src.license_key];
    assert.strictEqual(d.license, lic.license_url || undefined, `${src.id} license`);
  }
  if (!cat.site.operator) { assert.strictEqual(dc.publisher, undefined); assert.strictEqual(ws.publisher, undefined); }
});

test('공개 파일에 메일 주소·로컬 경로·원문 경로가 없다', () => {
  for (const f of ['data.html', 'site/data/datasets.json', 'site/data/void.ttl']) {
    const s = read(f);
    assert.ok(!/[\w.+-]+@[\w-]+(\.[\w-]+)*\.[a-z]{2,}/i.test(s), `${f} 메일 주소`);   // pretendard@v1.3.9 같은 판 표기는 걸리지 않는다
    assert.ok(!/mailto:/.test(s), `${f} mailto`);
    assert.ok(!/(?<![A-Za-z])[A-Za-z]:[\\/](?!\/)|OneDrive|worker\/private|essays\/[^*"<\s]+\.(xml|txt)/.test(s), `${f} 로컬·비공개 경로`);
  }
  const voidTtl = read('site/data/void.ttl');
  const undecided = Object.values(cat.licenses).filter(l => l.status === 'undecided').length;
  if (undecided === Object.values(cat.licenses).filter(l => l.status !== 'fixed').length) assert.ok(!voidTtl.includes('dcterms:license <'), 'void.ttl 에 정해지지 않은 라이선스');
});
