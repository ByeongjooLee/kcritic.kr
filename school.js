// 학풍(學風) 탭 — 학맥 위에 연구 주제를 얹는다 (2026-11-02)
// 데이터: /site/data/school-style-public.json (export_school_style.py). 벡터·초록·본문은 들어 있지 않고,
// 2차원 좌표(t-SNE)·토픽 비중(LDA 50)·잔차 유사도·지도교수 순위·공개 서지만 쓴다. 교수 간 지도 간선은 같은 파일의 edges.
(() => {
const PALETTE = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948'], OTHER = '#9aa6b8';
const SEQ = ['#eef4fc', '#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281'];
const REPS = [['bge', 'bge-m3'], ['ko_sroberta', 'ko-sroberta'], ['e5_large', 'e5-large'], ['mpnet_multilingual', 'MPNet'], ['tfidf', 'TF-IDF'], ['lsa300', 'LSA'], ['lda50', 'LDA']];
const el = id => document.getElementById(id), fmt = n => Number(n).toLocaleString('ko-KR'), esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = v => v == null ? '—' : (v * 100).toFixed(v * 100 >= 10 ? 0 : 1) + '%';
const sgn = v => v == null ? '—' : (v >= 0 ? '+' : '') + v.toFixed(4);
let D, P = new Map(), T = new Map(), L = new Map(), byAdv = new Map(), colorBy = 'group', lineageFocus = null, selected = null, showTheses = true, showEdges = true, query = '';
let topRoots = [], topUnis = [], rootColor = new Map(), uniColor = new Map();
const svgNS = 'http://www.w3.org/2000/svg';
const svg = el('map'), g = document.createElementNS(svgNS, 'g'); svg.append(g);
const adviseeG = document.createElementNS(svgNS, 'g'); adviseeG.setAttribute('class', 'sc-advisee-lines');   // 선택한 교수 → 그 제자 논문 선 (지도교수 효과가 '평균적 쏠림'임을 보이기 위해)
let k = 1, tx = 0, ty = 0;   // 확대 배율·이동

function colorOf(n) {
  if (colorBy === 'group') return n.group == null ? OTHER : (n.group === 7 ? OTHER : PALETTE[n.group]);
  if (colorBy === 'root') return rootColor.get(n.root) || OTHER;
  const u = n.unis ? n.unis[0] : n.uni; return uniColor.get(u) || OTHER;
}
function groupLabel(i) { const gr = D.groups.find(x => x.i === i); return gr ? gr.label : '기타'; }
function topicLabel(k, n = 3) { const t = D.topics.find(x => x.id === k); return t ? `t${k} ` + t.words.slice(0, n).join('·') : `t${k}`; }
function nameOf(id) { return P.get(id)?.name || id; }

// ── 범례와 목록
function renderLegend() {
  const items = colorBy === 'group' ? D.groups.map(gr => [gr.i === 7 ? OTHER : PALETTE[gr.i], gr.label, gr.words.slice(0, 5).join(' · ')])
    : colorBy === 'root' ? [...topRoots.map(r => [rootColor.get(r), nameOf(r) + ' 계보', '']), [OTHER, '그 밖의 계보', '']]
    : [...topUnis.map(u => [uniColor.get(u), u, '']), [OTHER, '그 밖의 대학', '']];
  el('legend').innerHTML = items.map(([c, l, t]) => `<span title="${esc(t)}"><i style="background:${c}"></i>${esc(l)}</span>`).join('') +
    `<span><i class="small" style="background:${OTHER}"></i>박사논문(작은 점)</span><span><i class="virtual"></i>KCI 묶음 없는 상위 지도교수(제자 평균 위치)</span><span><s></s>교수→교수 지도 간선</span>`;
}
function renderLineages() {
  const box = el('lineages'); box.innerHTML = '';
  for (const ln of D.lineages) {
    const b = document.createElement('button'); b.className = 'sc-lin' + (lineageFocus === ln.root ? ' on' : ''); b.type = 'button';
    b.innerHTML = `<i style="background:${rootColor.get(ln.root) || OTHER}"></i><strong>${esc(ln.name)} 계보</strong><span class="n">${fmt(ln.n_theses)}편</span><small>교수 ${ln.n_professors}명 · ${esc(ln.topics.slice(0, 2).map(([k]) => topicLabel(k, 2)).join(' / '))}</small>`;
    b.onclick = () => { lineageFocus = lineageFocus === ln.root ? null : ln.root; renderLineages(); paint(); markHeatRow(); el('clearFocus').disabled = !lineageFocus; };
    box.append(b);
  }
  el('lin-count').textContent = `계보 ${D.lineages.length}개 (박사논문 수 순)`;
}

// ── 지도 그리기
function draw() {
  g.innerHTML = '';
  if (showEdges) for (const e of D.edges) {
    const s = P.get(e.s), t = P.get(e.t); if (!s || !t) continue;
    const ln = document.createElementNS(svgNS, 'line'); ln.setAttribute('x1', s.x); ln.setAttribute('y1', s.y); ln.setAttribute('x2', t.x); ln.setAttribute('y2', t.y);
    ln.setAttribute('class', 'sc-edge ' + (e.status === '확정' ? 'confirmed' : e.status === '추론' ? 'inferred' : 'unconfirmed')); ln.dataset.s = e.s; ln.dataset.t = e.t; g.append(ln);
  }
  if (showTheses) for (const t of D.theses) {
    const gr = node(t, 'thesis', 2.6); g.append(gr);
  }
  for (const p of D.professors) g.append(node(p, 'prof' + (p.source === 'descendants' ? ' virtual' : ''), p.source === 'descendants' ? 7 : 5 + Math.min(4, Math.sqrt(p.n_advisees || 0))));
  paint();
}
function node(n, cls, r) {
  const gr = document.createElementNS(svgNS, 'g'); gr.setAttribute('class', 'sc-node ' + cls); gr.setAttribute('transform', `translate(${n.x},${n.y})`); gr.dataset.id = n.id; gr.dataset.kind = cls.startsWith('prof') ? 'prof' : 'thesis';
  const c = document.createElementNS(svgNS, 'circle'); c.setAttribute('r', r); c.setAttribute('fill', colorOf(n)); if (cls.includes('virtual')) c.setAttribute('stroke', colorOf(n)); gr.append(c);
  if (cls.startsWith('prof') && (n.source === 'descendants' || (n.n_advisees || 0) >= 8)) { const tx_ = document.createElementNS(svgNS, 'text'); tx_.setAttribute('x', r + 3); tx_.setAttribute('y', 4); tx_.textContent = n.name; gr.append(tx_); }
  gr.onmouseenter = ev => tip(n, gr.dataset.kind, ev); gr.onmousemove = ev => moveTip(ev); gr.onmouseleave = hideTip;
  gr.onclick = ev => { ev.stopPropagation(); select(n.id, gr.dataset.kind); };
  return gr;
}
function visible(n, kind) {
  if (query) { const q = query.toLowerCase(); const hit = kind === 'prof' ? n.name.toLowerCase().includes(q) : (n.title.toLowerCase().includes(q) || nameOf(n.advisor).toLowerCase().includes(q)); if (!hit) return false; }
  if (lineageFocus && n.root !== lineageFocus && !(kind === 'prof' && n.id === lineageFocus)) return false;
  return true;
}
function paint() {
  const sel = selected ? (P.get(selected.id) || T.get(selected.id)) : null;
  const related = new Set();
  if (sel) {
    if (selected.kind === 'prof') { related.add(sel.id); for (const t of byAdv.get(sel.id) || []) related.add(t.id); for (const e of D.edges) { if (e.s === sel.id) related.add(e.t); if (e.t === sel.id) related.add(e.s); } }
    else { related.add(sel.id); related.add(sel.advisor); }
  }
  g.querySelectorAll('.sc-node').forEach(x => {
    const n = x.dataset.kind === 'prof' ? P.get(x.dataset.id) : T.get(x.dataset.id); const vis = visible(n, x.dataset.kind);
    x.classList.toggle('dim', !vis || (sel && !related.has(n.id)) && !(!sel && vis)); x.classList.toggle('hi', !!sel && related.has(n.id));
    x.querySelector('circle').setAttribute('fill', x.classList.contains('virtual') ? '#fff' : colorOf(n)); if (x.classList.contains('virtual')) x.querySelector('circle').setAttribute('stroke', colorOf(n));
  });
  g.querySelectorAll('.sc-edge').forEach(x => { const s = P.get(x.dataset.s), t = P.get(x.dataset.t); const vis = visible(s, 'prof') || visible(t, 'prof'); const hi = sel && (x.dataset.s === sel.id || x.dataset.t === sel.id); x.classList.toggle('dim', !vis || (sel && !hi)); x.classList.toggle('hi', !!hi); });
  adviseeG.innerHTML = '';
  if (sel && selected.kind === 'prof') { for (const t of byAdv.get(sel.id) || []) { const ln = document.createElementNS(svgNS, 'line'); ln.setAttribute('x1', sel.x); ln.setAttribute('y1', sel.y); ln.setAttribute('x2', t.x); ln.setAttribute('y2', t.y); ln.setAttribute('class', 'sc-advisee'); adviseeG.append(ln); } g.prepend(adviseeG); }
  else if (sel && selected.kind === 'thesis') { const a = P.get(sel.advisor); if (a) { const ln = document.createElementNS(svgNS, 'line'); ln.setAttribute('x1', a.x); ln.setAttribute('y1', a.y); ln.setAttribute('x2', sel.x); ln.setAttribute('y2', sel.y); ln.setAttribute('class', 'sc-advisee'); adviseeG.append(ln); g.prepend(adviseeG); } }
}
function tip(n, kind, ev) {
  const t = el('tip');
  t.innerHTML = kind === 'prof' ? `<b>${esc(n.name)}</b><span class="k">${esc((n.unis || []).join(' · ') || '소속 미확인')}${n.source === 'descendants' ? ' · KCI 묶음 없음(제자 평균 위치)' : ` · KCI 논문 ${fmt(n.n_articles)}편`}</span><br>${esc(nameOf(n.root))} 계보 · 표본 안 지도논문 ${n.n_advisees}편<br>${n.topics ? '주제 ' + esc(n.topics.slice(0, 2).map(([k, v]) => topicLabel(k, 2) + ' ' + pct(v)).join(', ')) : ''}`
    : `<b>${esc(n.title)}</b><span class="k">${esc(n.year)} · ${esc(n.uni)} · 지도 ${esc(nameOf(n.advisor))}</span><br>${n.rank_uni ? `지도교수 묶음 순위 같은 대학 ${n.rank_uni}/${n.n_uni} · 전체 ${n.rank_all}/${D.summary.professors}` : ''}${n.topics ? '<br>주제 ' + esc(n.topics.slice(0, 2).map(([k, v]) => topicLabel(k, 2) + ' ' + pct(v)).join(', ')) : ''}`;
  t.style.display = 'block'; moveTip(ev);
}
function moveTip(ev) { const r = el('viewport').getBoundingClientRect(), t = el('tip'); let x = ev.clientX - r.left + 14, y = ev.clientY - r.top + 14; if (x + t.offsetWidth > r.width - 8) x = ev.clientX - r.left - t.offsetWidth - 10; if (y + t.offsetHeight > r.height - 8) y = ev.clientY - r.top - t.offsetHeight - 10; t.style.left = x + 'px'; t.style.top = y + 'px'; }
function hideTip() { el('tip').style.display = 'none'; }

// ── 확대·이동
function apply() { g.setAttribute('transform', `translate(${tx},${ty}) scale(${k})`); el('zoomLabel').textContent = Math.round(k * 100) + '%'; }
function fitAll() { const r = svg.getBoundingClientRect(); k = Math.min(r.width, r.height) / 1080; tx = (r.width - 1000 * k) / 2; ty = (r.height - 1000 * k) / 2; apply(); }
function zoomTo(nk, ax, ay) { nk = Math.max(.3, Math.min(8, nk)); tx = ax - (ax - tx) * nk / k; ty = ay - (ay - ty) * nk / k; k = nk; apply(); }
svg.addEventListener('wheel', e => { e.preventDefault(); const r = svg.getBoundingClientRect(); zoomTo(k * (e.deltaY < 0 ? 1.15 : 1 / 1.15), e.clientX - r.left, e.clientY - r.top); }, { passive: false });
let drag = null;
svg.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY, tx, ty, moved: false }; svg.classList.add('drag'); svg.setPointerCapture(e.pointerId); });
svg.addEventListener('pointermove', e => { if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true; tx = drag.tx + dx; ty = drag.ty + dy; apply(); });
svg.addEventListener('pointerup', e => { if (drag && !drag.moved && e.target === svg) { selected = null; showDetail(); paint(); } drag = null; svg.classList.remove('drag'); });
svg.addEventListener('pointerleave', () => { drag = null; svg.classList.remove('drag'); });
el('plus').onclick = () => { const r = svg.getBoundingClientRect(); zoomTo(k * 1.3, r.width / 2, r.height / 2); };
el('minus').onclick = () => { const r = svg.getBoundingClientRect(); zoomTo(k / 1.3, r.width / 2, r.height / 2); };
el('zoomReset').onclick = fitAll;
function flyTo(n) { const r = svg.getBoundingClientRect(); const nk = Math.max(k, 2.2); k = nk; tx = r.width / 2 - n.x * k; ty = r.height / 2 - n.y * k; apply(); }

// ── 상세
function bars(topics, color) {
  if (!topics) return '<p class="muted">토픽 비중 없음(본문 색인이 없는 논문)</p>';
  const max = Math.max(...topics.map(([, v]) => v), .01);
  return `<div class="sc-bars">${topics.map(([kk, v]) => `<span>${esc(topicLabel(kk, 3))}</span><div class="bar"><i style="width:${(v / max * 100).toFixed(0)}%;background:${color}"></i></div><span class="v">${pct(v)}</span>`).join('')}</div>`;
}
function tile(v, label, sub) { return `<div class="sc-tile"><b>${v}</b><span>${label}</span>${sub ? `<small>${sub}</small>` : ''}</div>`; }
function select(id, kind) { selected = { id, kind }; showDetail(); paint(); }
function showDetail() {
  const box = el('detail'); if (!selected) { box.innerHTML = ''; return; }
  if (selected.kind === 'prof') {
    const p = P.get(selected.id), adv = (byAdv.get(p.id) || []).slice().sort((a, b) => (a.year || '').localeCompare(b.year || '')), col = colorOf(p), rs = p.resid;
    const edgesIn = D.edges.filter(e => e.t === p.id), edgesOut = D.edges.filter(e => e.s === p.id);
    box.innerHTML = `<div class="sc-detail-head"><div><h2>${esc(p.name)}<span class="sc-badge">${p.source === 'descendants' ? 'KCI 묶음 없음 · 제자 평균' : `KCI 논문 ${fmt(p.n_articles)}편 묶음`}</span></h2>
<p class="muted">${esc((p.unis || []).join(' · ') || '소속 미확인')} · ${esc(nameOf(p.root))} 계보${p.advisor ? ` · 지도교수 ${esc(nameOf(p.advisor))}` : ''}${p.phd_year ? ` · 박사 ${esc(p.phd_year)}` : ''} · 동일인 판정 ${esc(p.identity || '—')}</p></div>
<div class="actions"><a class="sc-btn" href="/lineage.html?person=${encodeURIComponent(p.id)}">학맥에서 보기 →</a><a class="sc-btn" href="/academic-network.html?name=${encodeURIComponent(p.name)}#faculty">학교·소속 →</a><button class="sc-btn" id="flyBtn" type="button">지도에서 찾기</button></div></div>
<h3>연구 주제 (LDA 토픽 비중 상위 5)</h3>${bars(p.topics, col)}
${p.source === 'descendants' ? `<p class="muted">이 교수는 KCI 수집 범위(2000년 이후) 안에 본인 논문 묶음이 없어, 토픽은 ${esc(nameOf(p.root))} 계보 박사논문의 평균이고 위치는 표본 안 제자 교수 ${p.n_student_profs}명의 평균입니다.</p>` : `
<h3>학풍 지표 (bge-m3, 수집 범위 안)</h3><div class="sc-tiles">${tile(fmt(p.n_advisees), '표본 안 지도논문', '본인이 지도한 박사논문')}${tile(p.top1_uni == null ? '—' : pct(p.top1_uni), '지도교수 묶음 1위 비율', `같은 대학 교수 묶음 중 · ${p.n_ranked}편 기준`)}${tile(sgn(rs?.advisees), '제자 논문과의 잔차', '지도한 논문 평균 (양수 = 더 닮음)')}${tile(sgn(rs?.sibling), '형제 교수 제자와의 잔차', '같은 지도교수의 다른 교수 제자')}${tile(sgn(rs?.same_uni), '계보 밖 같은 대학과의 잔차', '학위 대학만 같은 논문')}</div>`}
${adv.length ? `<h3>표본 안 지도논문 ${adv.length}편</h3><ol>${adv.map(t => `<li><a href="#" data-thesis="${esc(t.id)}">${esc(t.title)}</a> <span class="muted">${esc(t.year)} · ${esc(t.uni)}${t.rank_uni ? ` · 지도교수 묶음 순위 ${t.rank_uni}/${t.n_uni}` : ''}</span></li>`).join('')}</ol>` : ''}
${edgesIn.length || edgesOut.length ? `<h3>교수 간 지도 간선</h3><p>${edgesIn.map(e => `${esc(nameOf(e.s))} → <b>${esc(p.name)}</b> (${esc(e.year || '연도 미상')}, ${esc(e.status)})`).concat(edgesOut.map(e => `<b>${esc(p.name)}</b> → ${esc(nameOf(e.t))} (${esc(e.year || '연도 미상')}, ${esc(e.status)})`)).join('<br>')}</p>` : ''}
<div class="callout">잔차 유사도는 논문×교수 코사인에서 논문 평균과 교수 평균을 뺀 값이라 교수 묶음의 '일반성' 차이를 걷어낸 것입니다. 모두 수집 자료 안의 연결만 센 값입니다.</div>`;
    el('flyBtn').onclick = () => flyTo(p);
  } else {
    const t = T.get(selected.id), a = P.get(t.advisor), col = colorOf(t);
    box.innerHTML = `<div class="sc-detail-head"><div><h2>${esc(t.title)}</h2><p class="muted">${esc(t.year)} · ${esc(t.uni)} · 지도교수 <a href="#" data-prof="${esc(t.advisor)}">${esc(nameOf(t.advisor))}</a> · ${esc(nameOf(t.root))} 계보 · 학위자 동일인 판정 ${esc(t.identity)}</p></div>
<div class="actions">${t.riss ? `<a class="sc-btn" href="${esc(t.riss)}" target="_blank" rel="noopener">RISS 서지 →</a>` : ''}<button class="sc-btn" id="flyBtn" type="button">지도에서 찾기</button></div></div>
<h3>연구 주제 (박사논문 본문 LDA 토픽 상위 5)</h3>${bars(t.topics, col)}
<h3>지도교수와의 닮음 (bge-m3)</h3><div class="sc-tiles">${tile(t.sim_advisor == null ? '—' : t.sim_advisor.toFixed(3), '지도교수 묶음과의 코사인', a ? `${esc(a.name)} 묶음 ${fmt(a.n_articles)}편` : '')}${tile(t.rank_uni ? `${t.rank_uni} / ${t.n_uni}` : '—', '같은 대학 교수 중 순위', '1위 = 지도교수 묶음이 가장 닮음')}${tile(t.rank_all ? `${t.rank_all} / ${D.summary.professors}` : '—', '교수 전체 중 순위', '')}</div>
<div class="callout">순위는 이 논문과 교수 묶음 전체의 코사인을 비교한 것입니다. 지도교수가 1위가 아니어도 지도 관계가 틀렸다는 뜻은 아니며, 주제가 넓거나 묶음이 작은 교수는 뒤로 밀립니다.</div>`;
    el('flyBtn').onclick = () => flyTo(t);
  }
  box.querySelectorAll('[data-thesis]').forEach(x => x.onclick = e => { e.preventDefault(); select(x.dataset.thesis, 'thesis'); });
  box.querySelectorAll('[data-prof]').forEach(x => x.onclick = e => { e.preventDefault(); select(x.dataset.prof, 'prof'); });
  box.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

// ── 계보 × 토픽 히트맵
let heatCols = [];
function renderHeat() {
  const lns = D.lineages.slice(0, 12); const cols = new Set(D.groups.filter(gr => gr.topic != null).map(gr => gr.topic));
  for (const ln of lns) ln.topics.slice(0, 3).forEach(([kk]) => cols.add(kk));
  heatCols = [...cols].sort((a, b) => lns.reduce((s, l) => s + l.theta[b], 0) - lns.reduce((s, l) => s + l.theta[a], 0)).slice(0, 14);
  const max = Math.max(...lns.flatMap(l => heatCols.map(c => l.theta[c])));
  const cell = v => { const i = Math.min(SEQ.length - 1, Math.round(v / max * (SEQ.length - 1))); return `<td style="background:${SEQ[i]}" class="${i >= 8 ? 'dark' : ''}" title="${pct(v)}">${(v * 100).toFixed(0)}</td>`; };
  el('heat').innerHTML = `<table class="sc-heat"><thead><tr><th></th>${heatCols.map(c => `<th title="${esc(D.topics.find(t => t.id === c)?.words.join(' '))}">t${c}<br>${esc(topicLabel(c, 3).split(' ')[1])}</th>`).join('')}</tr></thead><tbody>${lns.map(l => `<tr data-root="${esc(l.root)}"><th class="row" scope="row">${esc(l.name)} <span class="sc-muted">(${l.n_theses})</span></th>${heatCols.map(c => cell(l.theta[c])).join('')}</tr>`).join('')}</tbody></table>`;
  el('heat').querySelectorAll('th.row').forEach(th => th.onclick = () => { const r = th.parentElement.dataset.root; lineageFocus = lineageFocus === r ? null : r; renderLineages(); paint(); markHeatRow(); el('clearFocus').disabled = !lineageFocus; });
  markHeatRow();
}
function markHeatRow() { el('heat').querySelectorAll('tr[data-root]').forEach(tr => tr.classList.toggle('on', tr.dataset.root === lineageFocus)); }

// ── 관계 효과 표
function renderEffects() {
  const rels = ['advisor', 'sibling', 'uncle', 'grand', 'lineage_other', 'same_uni_outside_lineage'];
  const get = (rep, tier, rel) => D.effects.find(e => e.rep === rep && e.tier === tier && e.relation === rel);
  const cell = e => e ? `<td class="${e.p_holm < .05 ? '' : 'ns'}" title="t ${e.t} · Holm p ${e.p_holm < .001 ? '<0.001' : e.p_holm.toFixed(3)} · 쌍 ${fmt(e.n_pairs)}">${e.std >= 0 ? '+' : ''}${e.std.toFixed(2)}${e.p_holm < .05 ? '' : ' <small>n.s.</small>'}</td>` : '<td>—</td>';
  el('effects').innerHTML = `<table class="sc-effects"><thead><tr><th>관계 (기준 = 다른 대학·계보 밖)</th>${REPS.map(([, l]) => `<th>${l}</th>`).join('')}<th>bge-m3 확정 간선만</th></tr></thead><tbody>${rels.map(r => `<tr><td>${esc(get('bge', 'all', r)?.label || r)}</td>${REPS.map(([rep]) => cell(get(rep, 'all', r))).join('')}${cell(get('bge', 'confirmed', r))}</tr>`).join('')}</tbody></table>`;
}

// ── 조작
el('colorBy').onchange = e => { colorBy = e.target.value; renderLegend(); renderLineages(); paint(); };
el('showTheses').onchange = e => { showTheses = e.target.checked; draw(); };
el('showEdges').onchange = e => { showEdges = e.target.checked; draw(); };
el('search').oninput = e => { query = e.target.value.trim(); paint(); };
el('clearFocus').onclick = () => { lineageFocus = null; renderLineages(); paint(); markHeatRow(); el('clearFocus').disabled = true; };
el('clearSel').onclick = () => { selected = null; showDetail(); paint(); };
el('csv').onclick = () => {
  const rows = [['id', 'name', 'universities', 'lineage_root', 'source', 'n_kci_articles', 'n_advisees_in_sample', 'top1_share_same_uni', 'resid_advisees', 'resid_sibling', 'resid_uncle', 'resid_same_uni', 'top_topics', 'x', 'y']];
  for (const p of D.professors) rows.push([p.id, p.name, (p.unis || []).join(';'), nameOf(p.root), p.source, p.n_articles, p.n_advisees, p.top1_uni ?? '', p.resid?.advisees ?? '', p.resid?.sibling ?? '', p.resid?.uncle ?? '', p.resid?.same_uni ?? '', (p.topics || []).map(([kk, v]) => `t${kk}:${v}`).join(' '), p.x, p.y]);
  const blob = new Blob(['﻿' + rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `학풍_교수_${D.as_of}.csv`; a.click(); URL.revokeObjectURL(a.href);
};

// ── 시작
fetch('/site/data/school-style-public.json').then(r => { if (!r.ok) throw Error(r.status); return r.json(); }).then(d => {
  D = d; P = new Map(D.professors.map(p => [p.id, p])); T = new Map(D.theses.map(t => [t.id, t])); L = new Map(D.lineages.map(l => [l.root, l]));
  D.theses.forEach(t => { if (!byAdv.has(t.advisor)) byAdv.set(t.advisor, []); byAdv.get(t.advisor).push(t); });
  topRoots = D.lineages.slice(0, 7).map(l => l.root); topRoots.forEach((r, i) => rootColor.set(r, PALETTE[i]));
  const uc = new Map(); D.theses.forEach(t => uc.set(t.uni, (uc.get(t.uni) || 0) + 1)); topUnis = [...uc.entries()].sort((a, b) => b[1] - a[1]).slice(0, 7).map(([u]) => u); topUnis.forEach((u, i) => uniColor.set(u, PALETTE[i]));
  el('status').textContent = '';
  el('totals').textContent = `교수 ${fmt(D.summary.professors)}명(KCI 논문 ${fmt(D.summary.kci_articles)}편 묶음) · 박사논문 ${fmt(D.summary.theses)}편 · 교수 간 지도 간선 ${fmt(D.summary.edges)}건 · ${D.as_of} 기준`;
  renderLegend(); renderLineages(); draw(); renderHeat(); renderEffects();
  requestAnimationFrame(fitAll);   // 스테이지가 배치된 뒤 크기를 재야 한다
  let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(fitAll, 150); });
  const pc = D.projection_check; if (pc) el('projNote').textContent = `투영 점검: 2차원에서 논문과 가장 가까운 교수가 지도교수인 비율 ${pct(pc.nearest_is_advisor)}(우연 ${pct(pc.chance)}), 지도교수 묶음의 2차원 순위 중앙값 ${pc.median_rank_advisor_2d}/${D.summary.professors}. 원 공간에서도 지도교수 묶음이 1위인 논문은 4%뿐이라, 지도교수 효과는 '가장 가까움'이 아니라 다른 교수보다 평균적으로 더 닮는 쏠림입니다. 교수를 누르면 그 교수의 제자 논문으로 선이 그어져 이 쏠림을 볼 수 있습니다.`;
  el('coverage').innerHTML = `<p>${D.caveats.map(esc).join('. ')}.</p><p>방법 — ${esc(D.method.embedding)}. ${esc(D.method.topics)}. ${esc(D.method.resid)}. <a href="/site/data/school-style-public.json">공개 데이터(JSON)</a> · 학맥 데이터 ${esc(D.summary.genealogy_as_of)} 기준.</p>`;
  const q = new URLSearchParams(location.search); const want = q.get('prof'), lin = q.get('root');
  if (want && P.has(want)) { select(want, 'prof'); flyTo(P.get(want)); }
  if (lin && L.has(lin)) { lineageFocus = lin; renderLineages(); paint(); markHeatRow(); el('clearFocus').disabled = false; }
  window.schoolState = () => ({ colorBy, lineageFocus, selected, professors: D.professors.length, theses: D.theses.length, heatCols });
}).catch(err => { console.error(err); el('status').textContent = '학풍 데이터를 불러오지 못했습니다. 새로고침해 주세요.'; });
})();
