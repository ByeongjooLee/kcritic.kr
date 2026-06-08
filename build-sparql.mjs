// Comunica + N3 브라우저 번들 빌드 스크립트
// 실행: node build-sparql.mjs
import { build } from 'esbuild';
import { writeFileSync } from 'fs';

// 진입점 코드 (인라인)
const entry = `
import { QueryEngine } from '@comunica/query-sparql-rdfjs';
import { Store, Parser } from 'n3';

let _store = null;
let _engine = null;

async function getStore() {
  if (_store) return _store;
  const ttlUrl = new URL('site/data/graph.ttl', window.location.href).href;
  const resp = await fetch(ttlUrl);
  if (!resp.ok) throw new Error('graph.ttl 로드 실패: ' + resp.status);
  const text = await resp.text();
  const store = new Store();
  await new Promise((resolve, reject) => {
    new Parser({ format: 'text/turtle' }).parse(text, (err, quad) => {
      if (err) return reject(err);
      if (quad) store.addQuad(quad);
      else resolve();
    });
  });
  _store = store;
  return store;
}

function getEngine() {
  if (!_engine) _engine = new QueryEngine();
  return _engine;
}

window.doSparql = async function() {
  const query = document.getElementById('sparql-input').value.trim();
  if (!query) return;

  const btn = document.getElementById('sparql-btn');
  const resultEl = document.getElementById('sparql-result');
  btn.disabled = true;
  btn.textContent = '실행 중…';
  resultEl.innerHTML = '<div class="sparql-result-placeholder"><span class="spinner"></span> 쿼리 실행 중…</div>';

  try {
    const [engine, store] = await Promise.all([getEngine(), getStore()]);
    const bindingsStream = await engine.queryBindings(query, {
      sources: [store],
    });

    const bindings = await bindingsStream.toArray();

    if (bindings.length === 0) {
      resultEl.innerHTML = '<div class="sparql-result-placeholder">결과가 없습니다.</div>';
      return;
    }

    const vars = [...bindings[0].keys()].map(k => k.value);
    const thead = \`<thead><tr>\${vars.map(v => \`<th>\${v}</th>\`).join('')}</tr></thead>\`;
    const tbody = \`<tbody>\${bindings.map(b =>
      \`<tr>\${vars.map(v => {
        const term = b.get(v);
        if (!term) return '<td>—</td>';
        const val = term.termType === 'NamedNode'
          ? \`<a href="\${term.value}" target="_blank" title="\${term.value}">\${term.value.split(/[\\/#]/).pop()}</a>\`
          : term.value;
        return \`<td>\${val}</td>\`;
      }).join('')}</tr>\`
    ).join('')}</tbody>\`;

    resultEl.innerHTML =
      \`<div style="overflow-x:auto"><table class="sparql-result-table">\${thead}\${tbody}</table></div>\` +
      \`<div class="sparql-count">\${bindings.length}개 결과</div>\`;

  } catch (e) {
    resultEl.innerHTML = \`<div class="sparql-error">오류:\\n\${e.message || String(e)}</div>\`;
  } finally {
    btn.disabled = false;
    btn.textContent = '실행';
  }
};
`;

writeFileSync('sparql-entry.mjs', entry);

await build({
  entryPoints: ['sparql-entry.mjs'],
  bundle: true,
  minify: true,
  format: 'iife',
  globalName: 'SparqlBundle',
  outfile: 'site/sparql-bundle.js',
  platform: 'browser',
  define: {
    'process.env.NODE_ENV': '"production"',
  },
});

// 진입점 파일 삭제
import { unlinkSync } from 'fs';
unlinkSync('sparql-entry.mjs');

console.log('✓ site/sparql-bundle.js 생성 완료');
