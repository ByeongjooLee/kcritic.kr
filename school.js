// 학풍(學風) 탭 — 학맥 위에 연구 주제를 얹는다 (2026-11-02, 2026-11-22 「주제로 보기」를 기본 보기로)
// 데이터: /site/data/school-style-public.json (export_school_style.py → export_school_style_k20.py). 벡터·초록·본문은 들어 있지 않고,
// 2차원 좌표(t-SNE)·토픽 비중(정식 LDA 20개, 교수·논문마다 상위 5개)·잔차 유사도·지도교수 순위·공개 서지만 쓴다. 교수 간 지도 간선은 같은 파일의 edges.
// 보기 둘: topic = 주제를 골라 그 주제의 낱말·계보·박사논문을 본다(기본) / map = 교수·논문 지도 + 계보별 주제 분포 + 관계 효과 표(처음 만든 화면).
// 보기는 ?view=topic|map 과 localStorage kc-school-view 로 기억한다. ?prof= · ?root= 로 들어오면 지도 보기를 연다.
(() => {
const PALETTE = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948'], OTHER = '#9aa6b8';
const SEQ = ['#eef4fc', '#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281'];
const REPS = [['bge', 'bge-m3'], ['ko_sroberta', 'ko-sroberta'], ['e5_large', 'e5-large'], ['mpnet_multilingual', 'MPNet'], ['tfidf', 'TF-IDF'], ['lsa300', 'LSA'], ['lda50', '토픽 50개(옛 모형)'], ['lda20', '토픽 20개']];
const BAR = '#2a78d6', VIEWS = ['topic', 'map'], PAGE = 20, MIN_LIN = 10, SMALL = .03;   // 막대 색(크기 = 한 가지 색) · 보기 · 논문 목록 한 번에 · 계보 최소 논문 수 · '작은 주제' 기준
const el = id => document.getElementById(id), fmt = n => Number(n).toLocaleString('ko-KR'), esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = v => v == null ? '—' : (v * 100).toFixed(v * 100 >= 10 ? 0 : 1) + '%';
const sgn = v => v == null ? '—' : (v >= 0 ? '+' : '') + v.toFixed(4);
let D, P = new Map(), T = new Map(), L = new Map(), byAdv = new Map(), colorBy = 'group', lineageFocus = null, selected = null, showTheses = true, showEdges = true, query = '';
let topRoots = [], topUnis = [], rootColor = new Map(), uniColor = new Map();
let view = 'topic', topicSel = null, topicLin = null, topicShown = PAGE, showSmall = false, topicFocus = null, mapShown = false, TP = new Map();
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
function topicLabel(k, n = 3) { const t = TP.get(k); return t ? (t.name || t.words.slice(0, n).join('·')) : `t${k}`; }   // 번호(t2) 대신 상위 낱말. 연구자가 이름을 정하면 name 을 쓴다
function nameOf(id) { return P.get(id)?.name || id; }

// ── 범례와 목록
function renderLegend() {
  const items = colorBy === 'group' ? D.groups.map(gr => [gr.i === 7 ? OTHER : PALETTE[gr.i], gr.label + (TP.get(gr.topic)?.review ? ' (검토 중)' : ''), gr.words.slice(0, 5).join(' · ')])
    : colorBy === 'root' ? [...topRoots.map(r => [rootColor.get(r), nameOf(r) + ' 계보', '']), [OTHER, '그 밖의 계보', '']]
    : [...topUnis.map(u => [uniColor.get(u), u, '']), [OTHER, '그 밖의 대학', '']];
  el('legend').innerHTML = items.map(([c, l, t]) => `<span title="${esc(t)}"><i style="background:${c}"></i>${esc(l)}</span>`).join('') +
    `<span><i class="small" style="background:${OTHER}"></i>박사논문(작은 점)</span><span><i class="virtual"></i>KCI 묶음 없는 상위 지도교수(제자 평균 위치)</span><span><s></s>교수→교수 지도 간선</span>`;
}
function renderLineages() {
  const box = el('lineages'); box.innerHTML = '';
  for (const ln of D.lineages) {
    const b = document.createElement('button'); b.className = 'sc-lin' + (lineageFocus === ln.root ? ' on' : ''); b.type = 'button';
    b.innerHTML = `<i style="background:${rootColor.get(ln.root) || OTHER}"></i><strong>${esc(ln.name)} 계보</strong><span class="n">${fmt(ln.n_theses)}편</span><small>교수 ${ln.n_professors}명${ln.topics ? ' · ' + esc(ln.topics.slice(0, 2).map(([k]) => topicLabel(k, 2)).join(' / ')) : ''}</small>`;
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
  if (topicFocus != null && !(n.topics && n.topics[0][0] === topicFocus)) return false;   // 주제 강조: 그 주제가 가장 큰 교수·논문만
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
  if (!topics) return '<p class="muted">토픽 비중 없음(토픽 모형 표본 밖: 분야 거름을 통과한 논문이 3편 미만인 교수이거나 그 교수가 지도한 논문)</p>';
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
<h3>연구 주제 (토픽 비중 상위 5)</h3>${bars(p.topics, col)}
${p.source === 'descendants' ? `<p class="muted">이 교수는 KCI 수집 범위(2000년 이후) 안에 본인 논문 묶음이 없어, 토픽은 ${esc(nameOf(p.root))} 계보 박사논문의 평균이고 위치는 표본 안 제자 교수 ${p.n_student_profs}명의 평균입니다.</p>` : `
<h3>학풍 지표 (bge-m3, 수집 범위 안)</h3><div class="sc-tiles">${tile(fmt(p.n_advisees), '표본 안 지도논문', '본인이 지도한 박사논문')}${tile(p.top1_uni == null ? '—' : pct(p.top1_uni), '지도교수 묶음 1위 비율', `같은 대학 교수 묶음 중 · ${p.n_ranked}편 기준`)}${tile(sgn(rs?.advisees), '제자 논문과의 잔차', '지도한 논문 평균 (양수 = 더 닮음)')}${tile(sgn(rs?.sibling), '동문 교수 제자와의 잔차', '같은 지도교수에게서 배운 다른 교수의 제자')}${tile(sgn(rs?.same_uni), '계보 밖 같은 대학과의 잔차', '학위 대학만 같은 논문')}</div>`}
${adv.length ? `<h3>표본 안 지도논문 ${adv.length}편</h3><ol>${adv.map(t => `<li><a href="#" data-thesis="${esc(t.id)}">${esc(t.title)}</a> <span class="muted">${esc(t.year)} · ${esc(t.uni)}${t.rank_uni ? ` · 지도교수 묶음 순위 ${t.rank_uni}/${t.n_uni}` : ''}</span></li>`).join('')}</ol>` : ''}
${edgesIn.length || edgesOut.length ? `<h3>교수 간 지도 간선</h3><p>${edgesIn.map(e => `${esc(nameOf(e.s))} → <b>${esc(p.name)}</b> (${esc(e.year || '연도 미상')}, ${esc(e.status)})`).concat(edgesOut.map(e => `<b>${esc(p.name)}</b> → ${esc(nameOf(e.t))} (${esc(e.year || '연도 미상')}, ${esc(e.status)})`)).join('<br>')}</p>` : ''}
<div class="callout">잔차 유사도는 논문×교수 코사인에서 논문 평균과 교수 평균을 뺀 값이라 교수 묶음의 '일반성' 차이를 걷어낸 것입니다. 모두 수집 자료 안의 연결만 센 값입니다.</div>`;
    el('flyBtn').onclick = () => flyTo(p);
  } else {
    const t = T.get(selected.id), a = P.get(t.advisor), col = colorOf(t);
    box.innerHTML = `<div class="sc-detail-head"><div><h2>${esc(t.title)}</h2><p class="muted">${esc(t.year)} · ${esc(t.uni)} · 지도교수 <a href="#" data-prof="${esc(t.advisor)}">${esc(nameOf(t.advisor))}</a> · ${esc(nameOf(t.root))} 계보 · 학위자 동일인 판정 ${esc(t.identity)}</p></div>
<div class="actions">${t.riss ? `<a class="sc-btn" href="${esc(t.riss)}" target="_blank" rel="noopener">RISS 서지 →</a>` : ''}<button class="sc-btn" id="flyBtn" type="button">지도에서 찾기</button></div></div>
<h3>연구 주제 (박사논문 본문 토픽 상위 5)</h3>${bars(t.topics, col)}
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
  const lns = D.lineages.filter(l => l.theta && l.n_topic >= MIN_LIN).sort((a, b) => b.n_topic - a.n_topic).slice(0, 12); const cols = new Set(D.groups.filter(gr => gr.topic != null).map(gr => gr.topic));
  for (const ln of lns) ln.topics.slice(0, 3).forEach(([kk]) => cols.add(kk));
  heatCols = [...cols].sort((a, b) => lns.reduce((s, l) => s + l.theta[b], 0) - lns.reduce((s, l) => s + l.theta[a], 0)).slice(0, 14);
  const max = Math.max(...lns.flatMap(l => heatCols.map(c => l.theta[c])));
  const cell = v => { const i = Math.min(SEQ.length - 1, Math.round(v / max * (SEQ.length - 1))); return `<td style="background:${SEQ[i]}" class="${i >= 8 ? 'dark' : ''}" title="${pct(v)}">${(v * 100).toFixed(0)}</td>`; };
  el('heat').innerHTML = `<table class="sc-heat"><thead><tr><th></th>${heatCols.map(c => `<th title="${esc(TP.get(c)?.words.join(' '))}">${esc(topicLabel(c, 3)).split('·').join('<br>')}</th>`).join('')}</tr></thead><tbody>${lns.map(l => `<tr data-root="${esc(l.root)}"><th class="row" scope="row">${esc(l.name)} <span class="sc-muted">(${l.n_topic})</span></th>${heatCols.map(c => cell(l.theta[c])).join('')}</tr>`).join('')}</tbody></table>`;
  el('heat').querySelectorAll('th.row').forEach(th => th.onclick = () => { const r = th.parentElement.dataset.root; lineageFocus = lineageFocus === r ? null : r; renderLineages(); paint(); markHeatRow(); el('clearFocus').disabled = !lineageFocus; });
  markHeatRow();
}
function markHeatRow() { el('heat').querySelectorAll('tr[data-root]').forEach(tr => tr.classList.toggle('on', tr.dataset.root === lineageFocus)); }

// ── 관계 효과 표
function renderEffects() {
  const rels = ['advisor', 'sibling', 'uncle', 'grand', 'lineage_other', 'same_uni_outside_lineage'];
  const get = (rep, tier, rel) => D.effects.find(e => e.rep === rep && e.tier === tier && e.relation === rel);
  const cell = e => e ? `<td class="${e.p_holm < .05 ? '' : 'ns'}" title="t ${e.t} · Holm p ${e.p_holm < .001 ? '<0.001' : e.p_holm.toFixed(3)} · 쌍 ${fmt(e.n_pairs)}">${e.std >= 0 ? '+' : ''}${e.std.toFixed(2)}${e.p_holm < .05 ? '' : ' <small>n.s.</small>'}</td>` : '<td>—</td>';
  el('effects').innerHTML = `<table class="sc-effects"><thead><tr><th>관계 (기준 = 다른 대학·계보 밖)</th>${REPS.map(([rep, l]) => `<th${rep === 'lda20' ? ' title="토픽이 붙은 표본(교수 295명·논문 1,115편)에서 계산"' : ''}>${l}</th>`).join('')}<th>bge-m3 확정 간선만</th></tr></thead><tbody>${rels.map(r => `<tr><td>${esc(get('bge', 'all', r)?.label || r)}</td>${REPS.map(([rep]) => cell(get(rep, 'all', r))).join('')}${cell(get('bge', 'confirmed', r))}</tr>`).join('')}</tbody></table>`;
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

// ── 보기 전환 (주제로 보기 / 지도·표로 보기)
function setUrl(fn) { const u = new URL(location.href); fn(u.searchParams); history.replaceState(null, '', u); }
function showView(v) {
  view = v; el('view-topic').hidden = v !== 'topic'; el('view-map').hidden = v !== 'map';
  document.querySelectorAll('.sc-view button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === v)));
  if (v === 'map' && !mapShown) requestAnimationFrame(() => { mapShown = true; fitAll(); const n = selected && (P.get(selected.id) || T.get(selected.id)); if (n) flyTo(n); });   // 숨겨진 동안에는 크기를 잴 수 없어, 보일 때 맞춘다
}
function setView(v) {
  try { localStorage.setItem('kc-school-view', v); } catch (_) {}
  showView(v);
  setUrl(q => { q.set('view', v); if (v === 'topic') { q.delete('prof'); q.delete('root'); if (topicSel != null) q.set('topic', topicSel); } else q.delete('topic'); });
}
document.querySelectorAll('.sc-view button').forEach(b => b.onclick = () => setView(b.dataset.view));

// ── 주제로 보기
function topicOrder() { const by = (a, b) => b.share_thesis - a.share_thesis || a.id - b.id; return { stable: D.topics.filter(t => t.stable).sort(by), rest: D.topics.filter(t => !t.stable).sort(by) }; }
function renderTopicList() {
  const { stable, rest } = topicOrder(), max = Math.max(...D.topics.map(t => t.share_thesis));
  const big = rest.filter(t => t.share_thesis >= SMALL), small = rest.filter(t => t.share_thesis < SMALL), open = showSmall || small.some(t => t.id === topicSel);
  const item = t => `<button type="button" class="sc-topic${t.id === topicSel ? ' on' : ''}" data-topic="${t.id}"${t.id === topicSel ? ' aria-current="true"' : ''}><strong>${esc(topicLabel(t.id, 3))}</strong><span class="n">${pct(t.share_thesis)}</span><small>${esc(t.words.slice(3, 7).join(' · '))}${t.review ? ' <em>검토 중</em>' : ''}</small><span class="bar"><i style="width:${(t.share_thesis / max * 100).toFixed(1)}%"></i></span></button>`;
  el('topicList').innerHTML = `<h4>되풀이되는 주제 <span>${stable.length}</span></h4><p class="sc-muted">모형을 스무 번 다시 맞춰도 거의 매번 나오는 주제입니다.</p>${stable.map(item).join('')}
<h4>그 밖의 주제 <span>${rest.length}</span></h4><p class="sc-muted">다시 맞추면 모습이 달라질 수 있는 낱말 묶음입니다.</p>${big.map(item).join('')}${open ? small.map(item).join('') : ''}
${small.length ? `<button type="button" class="sc-btn sc-more" id="smallToggle" aria-expanded="${open}">${open ? '작은 주제 접기' : `작은 주제 ${small.length}개 더 보기`}</button>` : ''}`;
  el('topicList').querySelectorAll('.sc-topic').forEach(b => b.onclick = () => selectTopic(+b.dataset.topic));
  const tg = el('smallToggle'); if (tg) tg.onclick = () => { showSmall = !open; renderTopicList(); el('smallToggle')?.focus(); };
  const opt = t => `<option value="${t.id}"${t.id === topicSel ? ' selected' : ''}>${esc(topicLabel(t.id, 3))} (${pct(t.share_thesis)})${t.review ? ' · 검토 중' : ''}</option>`;
  el('topicSelect').innerHTML = `<optgroup label="되풀이되는 주제">${stable.map(opt).join('')}</optgroup><optgroup label="그 밖의 주제">${rest.map(opt).join('')}</optgroup>`;
}
el('topicList').addEventListener('keydown', e => {   // 위·아래 화살표로 주제 사이를 옮긴다
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key) || !e.target.classList.contains('sc-topic')) return;
  const all = [...el('topicList').querySelectorAll('.sc-topic')], i = all.indexOf(e.target); e.preventDefault();
  (e.key === 'Home' ? all[0] : e.key === 'End' ? all[all.length - 1] : all[Math.max(0, Math.min(all.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))]).focus();
});
el('topicSelect').onchange = e => selectTopic(+e.target.value);
function selectTopic(k) {
  const had = document.activeElement && document.activeElement.classList.contains('sc-topic');
  topicSel = k; topicLin = null; topicShown = PAGE; renderTopicList(); renderTopicPanel();
  if (view === 'topic') setUrl(q => q.set('topic', k));
  if (had) el('topicList').querySelector('.sc-topic.on')?.focus();
}
function topicTheses(k) {   // 이 주제가 상위 5개 안에 들고 비중이 10% 이상인 논문, 비중 큰 순
  const out = []; for (const t of D.theses) { const hit = t.topics && t.topics.find(([kk]) => kk === k); if (hit && hit[1] >= .1) out.push([t, hit[1]]); }
  return out.sort((a, b) => b[1] - a[1] || (a[0].year || '').localeCompare(b[0].year || '') || a[0].id.localeCompare(b[0].id));
}
function renderTopicPanel() {
  const t = TP.get(topicSel), box = el('topicPanel'); if (!t) { box.innerHTML = ''; return; }
  const all = topicTheses(t.id), list = topicLin ? all.filter(([x]) => x.root === topicLin) : all;
  const lins = D.lineages.filter(l => l.theta && l.n_topic >= MIN_LIN).map(l => [l, l.theta[t.id]]).sort((a, b) => b[1] - a[1] || a[0].name.localeCompare(b[0].name)).slice(0, 10);
  const max = Math.max(...lins.map(([, v]) => v), t.share_thesis, .01), avgX = (t.share_thesis / max * 100).toFixed(1);
  const runs = `다른 ${t.runs_other}번 중 ${t.runs_matched}번 다시 나옴`;
  const badge = t.stable ? `<span class="sc-badge ok">되풀이되는 주제 · ${runs}</span>` : `<span class="sc-badge">다시 맞추면 달라질 수 있음 · ${runs}</span>`;
  box.innerHTML = `<div class="sc-topic-head"><div><h2>${esc(topicLabel(t.id, 3))}</h2><p class="sc-badges">${badge}${t.review ? '<span class="sc-badge warn">검토 중</span>' : ''}</p></div>
<div class="actions"><button class="sc-btn" id="toMap" type="button">지도에서 이 주제 보기 →</button></div></div>
<p class="sc-words" aria-label="이 주제에 많이 나오는 낱말">${t.words.map(w => `<span>${esc(w)}</span>`).join('')}</p>
${t.review ? '<p class="callout">이 낱말 묶음은 다른 방식의 토픽 모형에서는 나오지 않아, 하나의 주제로 볼 수 있는지 검토하고 있습니다. 연구 주제의 이름이 아니라 함께 자주 쓰이는 낱말의 묶음으로 읽어 주세요.</p>' : ''}
${!t.stable && !t.review ? '<p class="callout">이 묶음은 모형을 다시 맞출 때마다 조금씩 다른 모습으로 나옵니다. 특정 작가·작품에 묶인 낱말일 수 있으니 참고로만 보세요.</p>' : ''}
<div class="sc-tiles">${tile(pct(t.share_thesis), '박사논문 평균 비중', `토픽이 붙은 ${fmt(D.summary.theses_with_topics)}편 기준`)}${tile(fmt(t.n_top) + '편', '이 주제가 가장 큰 논문', '')}${tile(fmt(all.length) + '편', '비중 10% 이상인 논문', '아래 목록')}</div>
<section class="sc-sec" aria-labelledby="tl-title"><h3 id="tl-title">이 주제를 많이 다루는 계보</h3><p class="sc-muted">계보는 지도교수를 거슬러 올라간 맨 위 교수의 이름으로 부릅니다. 막대는 그 계보 박사논문의 평균 비중, 세로선은 전체 평균(${pct(t.share_thesis)})입니다. 계보를 누르면 아래 목록에 그 계보의 논문만 남습니다.</p>
<div class="sc-linbars" role="group" aria-label="계보별 평균 비중">${lins.map(([l, v]) => `<button type="button" class="sc-linbar${topicLin === l.root ? ' on' : ''}" data-root="${esc(l.root)}" aria-pressed="${topicLin === l.root}" title="${esc(l.name)} 계보 · 평균 ${pct(v)} · 전체 평균의 ${(v / Math.max(t.share_thesis, 1e-6)).toFixed(1)}배 · 토픽이 붙은 논문 ${l.n_topic}편"><span class="nm">${esc(l.name)} <small>${l.n_topic}편</small></span><span class="track"><i style="width:${(v / max * 100).toFixed(1)}%"></i><b style="left:${avgX}%"></b></span><span class="v">${pct(v)}</span></button>`).join('')}</div>
<p class="sc-muted">토픽이 붙은 논문이 ${MIN_LIN}편 이상인 계보 가운데 위에서 열 개입니다.</p></section>
<section class="sc-sec" aria-labelledby="tt-title"><div class="sc-sec-head"><div><h3 id="tt-title">박사논문 <span class="sc-muted">${fmt(list.length)}편${topicLin ? ` · ${esc(nameOf(topicLin))} 계보만` : ''}</span></h3><p class="sc-muted">이 주제의 비중이 큰 순서입니다. 제목을 누르면 RISS 서지가 새 창에서 열립니다.</p></div>${topicLin ? '<button class="sc-btn" id="linClear" type="button">계보 고르기 해제</button>' : ''}</div>
${list.length ? `<ol class="sc-tlist">${list.slice(0, topicShown).map(([x, v]) => `<li><span class="w" title="이 논문에서 이 주제의 비중 ${pct(v)}"><i style="width:${Math.round(v * 100)}%"></i></span><span class="pv">${pct(v)}</span><span class="tt">${x.riss ? `<a href="${esc(x.riss)}" target="_blank" rel="noopener">${esc(x.title)}</a>` : esc(x.title)}<small>${esc(x.year)} · ${esc(x.uni)} · 지도교수 <a href="/school.html?view=map&amp;prof=${encodeURIComponent(x.advisor)}">${esc(nameOf(x.advisor))}</a> · ${esc(nameOf(x.root))} 계보</small></span></li>`).join('')}</ol>` : '<p class="sc-muted">해당하는 논문이 없습니다.</p>'}
${list.length > topicShown ? `<button class="sc-btn sc-more" id="moreTheses" type="button">더 보기 (${fmt(list.length - topicShown)}편 남음)</button>` : ''}</section>`;
  box.querySelectorAll('.sc-linbar').forEach(b => b.onclick = () => { const r = b.dataset.root; topicLin = topicLin === r ? null : r; topicShown = PAGE; renderTopicPanel(); [...box.querySelectorAll('.sc-linbar')].find(x => x.dataset.root === r)?.focus(); });
  const lc = el('linClear'); if (lc) lc.onclick = () => { topicLin = null; topicShown = PAGE; renderTopicPanel(); };
  const mt = el('moreTheses'); if (mt) mt.onclick = () => { const from = topicShown; topicShown += PAGE; renderTopicPanel(); box.querySelectorAll('.sc-tlist li')[from]?.querySelector('a')?.focus(); };
  el('toMap').onclick = () => { setTopicFocus(t.id); setView('map'); el('view-map').scrollIntoView({ block: 'start' }); };
}
function setTopicFocus(k) {
  topicFocus = k; const note = el('topicFocusNote'); note.hidden = k == null;
  if (k != null) { note.innerHTML = `주제 강조: <b>${esc(topicLabel(k, 3))}</b> — 이 주제가 가장 큰 교수·논문만 진하게 보입니다. <button class="sc-btn sc-btn-sm" type="button" id="topicFocusClear">해제</button>`; el('topicFocusClear').onclick = () => setTopicFocus(null); }
  paint();
}

// ── 시작
fetch('/site/data/school-style-public.json').then(r => { if (!r.ok) throw Error(r.status); return r.json(); }).then(d => {
  D = d; P = new Map(D.professors.map(p => [p.id, p])); T = new Map(D.theses.map(t => [t.id, t])); L = new Map(D.lineages.map(l => [l.root, l])); TP = new Map(D.topics.map(t => [t.id, t]));
  D.theses.forEach(t => { if (!byAdv.has(t.advisor)) byAdv.set(t.advisor, []); byAdv.get(t.advisor).push(t); });
  topRoots = D.lineages.slice(0, 7).map(l => l.root); topRoots.forEach((r, i) => rootColor.set(r, PALETTE[i]));
  const uc = new Map(); D.theses.forEach(t => uc.set(t.uni, (uc.get(t.uni) || 0) + 1)); topUnis = [...uc.entries()].sort((a, b) => b[1] - a[1]).slice(0, 7).map(([u]) => u); topUnis.forEach((u, i) => uniColor.set(u, PALETTE[i]));
  el('status').hidden = true;
  el('totals').textContent = `교수 ${fmt(D.summary.professors)}명 · 박사논문 ${fmt(D.summary.theses)}편 · 토픽 ${D.topics.length}개`;
  renderLegend(); renderLineages(); draw(); renderHeat(); renderEffects();
  let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { if (view === 'map') fitAll(); else mapShown = false; }, 150); });
  const pc = D.projection_check; if (pc) el('projNote').textContent = `투영 점검: 2차원에서 논문과 가장 가까운 교수가 지도교수인 비율 ${pct(pc.nearest_is_advisor)}(우연 ${pct(pc.chance)}), 지도교수 묶음의 2차원 순위 중앙값 ${pc.median_rank_advisor_2d}/${D.summary.professors}. 원 공간에서도 지도교수 묶음이 1위인 논문은 4%뿐이라, 지도교수 효과는 '가장 가까움'이 아니라 다른 교수보다 평균적으로 더 닮는 쏠림입니다. 교수를 누르면 그 교수의 제자 논문으로 선이 그어져 이 쏠림을 볼 수 있습니다.`;
  el('coverage').innerHTML = `<p>교수 ${fmt(D.summary.professors)}명(KCI 논문 ${fmt(D.summary.kci_articles)}편 묶음) · 박사논문 ${fmt(D.summary.theses)}편 · 교수 간 지도 간선 ${fmt(D.summary.edges)}건 · ${esc(D.as_of)} 기준${D.topics_as_of ? `(토픽 모형 ${esc(D.topics_as_of)})` : ''}. ${D.caveats.map(esc).join('. ')}.</p><p>방법 — ${esc(D.method.embedding)}. ${esc(D.method.topics)}. ${esc(D.method.resid)}. <a href="/site/data/school-style-public.json">공개 데이터(JSON)</a> · 학맥 데이터 ${esc(D.summary.genealogy_as_of)} 기준.</p>`;
  const q = new URLSearchParams(location.search); const want = q.get('prof'), lin = q.get('root'), qv = q.get('view'), qt = q.get('topic');
  const first = topicOrder().stable[0] || D.topics[0];
  topicSel = qt != null && qt !== '' && TP.has(+qt) ? +qt : first.id; renderTopicList(); renderTopicPanel();
  let saved = null; try { saved = localStorage.getItem('kc-school-view'); } catch (_) {}
  const deep = (want && P.has(want)) || (lin && L.has(lin));   // 교수·계보를 가리키는 주소는 지도 보기에서만 뜻이 있다
  const v0 = VIEWS.includes(qv) ? qv : deep ? 'map' : qt != null ? 'topic' : VIEWS.includes(saved) ? saved : 'topic';
  if (v0 === 'map') {
    if (want && P.has(want)) select(want, 'prof');
    if (lin && L.has(lin)) { lineageFocus = lin; renderLineages(); paint(); markHeatRow(); el('clearFocus').disabled = false; }
  }
  showView(v0);
  window.schoolState = () => ({ view, topic: topicSel, topicLineage: topicLin, topicFocus, colorBy, lineageFocus, selected, professors: D.professors.length, theses: D.theses.length, heatCols });
}).catch(err => { console.error(err); el('status').hidden = false; el('status').textContent = '학풍 데이터를 불러오지 못했습니다. 새로고침해 주세요.'; });
})();
