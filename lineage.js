// 학맥(學脈) 탭 — 박사 지도교수를 시작점으로 제자와 다음 세대를 시간축(학위 연도) 위에 펼치는 계보 트리
// 데이터: /site/data/genealogy-library.json (노드 교수·학위자, 간선 지도논문). 배치·지표 계산과 데이터는 분리되어 있다.
(() => { 'use strict';
const el = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = n => Number(n || 0).toLocaleString('ko-KR');
const pct = (a, b) => b ? Math.round(a / b * 100) + '%' : '—';

// 배치 상수 (px, 화면 배율 1 기준)
const PX_YEAR = 32, PAD_L = 150, MENTOR_ZONE = 190, PAD_R = 210, PAD_TOP = 54, PAD_BOTTOM = 30;
const ROW = { student: 27, professor: 60, root: 80, mentor: 50 }, GAP = 12, MENTOR_GAP = 54;
const RADIUS = { student: 4.5, professor: 7.5, mentor: 7.5, root: 10 };
// 대학 색: 검증된 범주형 8색을 전체 자료에서 지도논문이 많은 대학 순으로 고정 배정. 나머지는 회색 '기타'.
const PALETTE = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948'], OTHER = '#9aa6b8';

const COL = 250;                                       // 간단 보기: 세대 사이 열 간격
let D, N, adj, root, selected, selectedEdge = null, highlight = null, uniFocus = null, view = null, uniColor = new Map(), metricsCache = new Map(), sortKey = 'descendants', sortDir = -1;
// 기본은 간단 보기. 시간축 보기는 ?view=time 이나 버튼으로 고르고, 마지막 선택은 localStorage 에 남긴다.
let mode = (new URLSearchParams(location.search).get('view') === 'time' || (!new URLSearchParams(location.search).has('view') && (() => { try { return localStorage.getItem('kc-lineage-view') === 'time'; } catch (_) { return false; } })())) ? 'time' : 'simple';   // 'simple' = 세대 열·역할 색, 'time' = 시간축·대학 색
const simple = () => mode === 'simple';
const trail = [], Z = { k: 1, x: 0, y: 0 };

// 소속·학위 대학 표기: 한자 교명을 한글로, 대학원·학과·전공을 떼고 대학명(+캠퍼스)만 남긴다. 서지 원표기는 상세에서 그대로 보존한다.
const HANJA = [['忠南', '충남'], ['高麗', '고려'], ['延世', '연세'], ['梨花女子', '이화여자'], ['慶熙', '경희'], ['漢陽', '한양'], ['東國', '동국'], ['全南', '전남'], ['西江', '서강'], ['成均館', '성균관'], ['中央', '중앙'], ['檀國', '단국'], ['釜山', '부산'], ['嶺南', '영남'], ['亞洲', '아주'], ['國民', '국민'], ['全州', '전주'], ['朝鮮', '조선'], ['昌原', '창원'], ['韓南', '한남'], ['淑明女子', '숙명여자'], ['韓國外國語', '한국외국어'], ['慶北', '경북'], ['崇實', '숭실'], ['弘益', '홍익'], ['世宗', '세종'], ['仁川', '인천'], ['蔚山', '울산'], ['公州', '공주'], ['東亞', '동아'], ['順天', '순천'], ['牧園', '목원'], ['忠北', '충북'], ['慶南', '경남'], ['鮮文', '선문'], ['大學校', '대학교'], ['大學院', '대학원']];
function affiliationName(value) {
  let s = String(value || '').trim().replace(/韓國學中央硏究院/g, '한국학중앙연구원').replace(/韓國學大學院/g, '');
  for (const [h, k] of HANJA) s = s.split(h).join(k);
  s = s.replace(/^국립\s*/, '').replace(/^경상국립대학교/, '경상대학교');
  const campus = s.match(/(?:[가-힣A-Za-z]+캠퍼스|\((?:강릉|원주|세종|천안|서울|용인|에리카|ERICA)[^)]*\))/)?.[0];
  const school = s.match(/^.*?(?:대학교|사관학교|과학기술원|중앙연구원)/)?.[0];
  return school ? school + (campus ? ' ' + campus : '') : s.replace(/\s*(?:일반|전문|특수|교육)?대학원.*$/, '').trim();
}
const shortUni = s => s.replace(/대학교/, '대').replace(/여자대/, '여대');
const nameOf = n => n.display_name || n.name;
const affOf = n => n.kind === 'professor' ? n.affiliations.join(' / ') : '';
const cut = (s, n) => s.length > n ? s.slice(0, n - 1) + '…' : s;
const urls = arr => [...new Set(arr || [])].filter(x => /^https?:\/\//.test(x)).map((u, i) => `<a href="${esc(u)}" target="_blank" rel="noopener">근거 ${i + 1}</a>`).join(' · ');
const yearOf = e => { const y = Number(e?.year); return y > 1900 && y < 2100 ? y : null; };
const colorOf = u => uniColor.get(u) || OTHER;

const showInferred = () => el('inferred').checked, profOnly = () => el('profOnly').checked;
const kidsAll = id => (adj.get(id) || []).filter(e => showInferred() || !e.student_is_inferred_professor);
const studentCount = id => new Set((adj.get(id) || []).map(e => e.target)).size;
const incoming = id => D.edges.filter(e => e.target === id && (showInferred() || !e.student_is_inferred_professor));
function children(id) {
  return kidsAll(id).filter(e => !profOnly() || N.get(e.target).kind === 'professor')
    .sort((a, b) => (yearOf(a) || 9999) - (yearOf(b) || 9999)                      // 학위 연도순 (시간축과 같은 방향)
      || Number(N.get(b.target).kind === 'professor') - Number(N.get(a.target).kind === 'professor')
      || N.get(a.target).name.localeCompare(N.get(b.target).name, 'ko'));
}

// ── 학맥 지표 (Rossi 외 2018의 계보 지표를 이 자료에 맞게 줄인 것)
function metrics(id) {
  const key = id + '|' + Number(showInferred());
  if (metricsCache.has(key)) return metricsCache.get(key);
  const direct = kidsAll(id), byTarget = new Map();
  for (const e of direct) if (!byTarget.has(e.target) || (yearOf(e) || 0) < (yearOf(byTarget.get(e.target)) || 0)) byTarget.set(e.target, e);
  const years = direct.map(yearOf).filter(Boolean);
  const profs = [...byTarget.keys()].filter(t => N.get(t).kind === 'professor');
  const desc = new Set(); let generations = 0;
  (function walk(x, d, path) { for (const e of kidsAll(x)) { if (path.has(e.target)) continue; desc.add(e.target); generations = Math.max(generations, d); walk(e.target, d + 1, new Set([...path, e.target])); } })(id, 1, new Set([id]));
  const lags = [];
  for (const t of profs) { const e = byTarget.get(t), ys = kidsAll(t).map(yearOf).filter(Boolean); if (ys.length && yearOf(e)) lags.push(Math.min(...ys) - yearOf(e)); }
  const stay = profs.filter(t => N.get(t).affiliations.includes(affiliationName(byTarget.get(t).university))).length;
  const unis = new Map(); for (const e of direct) { const u = affiliationName(e.university); unis.set(u, (unis.get(u) || 0) + 1); }
  const m = { direct: byTarget.size, theses: direct.length, profs: profs.length, descendants: desc.size, generations,
    first: years.length ? Math.min(...years) : null, last: years.length ? Math.max(...years) : null,
    lag: lags.length ? lags.reduce((a, b) => a + b, 0) / lags.length : null, lagN: lags.length, stay, unis: unis.size,
    mainUni: [...unis.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] || '' };
  m.span = m.first ? m.last - m.first : null;
  metricsCache.set(key, m); return m;
}

// ── 배치: 가로는 학위 연도, 세로는 같은 지도교수의 제자를 쌓는 정돈 트리. 말단 이름은 접지 않고 모두 표시한다.
function layout() {
  const items = [], lines = []; let cycles = 0;
  function walk(id, depth, via, parent, path) {
    if (path.has(id)) { cycles++; return null; }
    const n = N.get(id), item = { id, n, depth, via, parent, kids: [], kind: depth === 0 ? 'root' : n.kind, year: via ? yearOf(via) : null, uni: via ? affiliationName(via.university) : '' };
    items.push(item);
    const next = new Set(path); next.add(id);
    for (const e of children(id)) { const c = walk(e.target, depth + 1, e, item, next); if (c) { item.kids.push(c); lines.push({ a: item, b: c, e }); } }
    return item;
  }
  const tree = walk(root, 0, null, null, new Set());
  const gapBetween = (a, b) => (a.kids.length || b.kids.length || a.kind !== 'student' || b.kind !== 'student') ? GAP : 0;
  function measure(it) {
    it.own = ROW[it.kind] || ROW.student; let kh = 0;
    it.kids.forEach((k, i) => { measure(k); kh += k.h; if (i) kh += gapBetween(it.kids[i - 1], k); });
    it.kh = kh; it.h = Math.max(it.own, kh);
  }
  function place(it, top) {
    if (it.kids.length) {
      let c = top + (it.h - it.kh) / 2;
      it.kids.forEach((k, i) => { if (i) c += gapBetween(it.kids[i - 1], k); place(k, c); c += k.h; });
      it.y = (it.kids[0].y + it.kids[it.kids.length - 1].y) / 2;
    } else it.y = top + it.h / 2;
  }
  measure(tree);
  // 시작 교수의 상위 지도교수(들)는 왼쪽 '지도교수' 구역에 둔다 (연도 미상)
  const mentors = [], seen = new Set();
  for (const e of incoming(root)) { if (seen.has(e.source) || e.source === root) continue; seen.add(e.source); mentors.push({ id: e.source, n: N.get(e.source), depth: -1, via: e, parent: null, kids: [], kind: 'mentor', year: null, uni: N.get(e.source).affiliations[0] || '' }); }
  const colOffset = mentors.length ? MENTOR_ZONE : 0, mh = mentors.length * MENTOR_GAP;
  const top = PAD_TOP + Math.max(0, (mh - tree.h) / 2);
  place(tree, top);
  // 시간축: 시작 교수의 학위 연도(상위 지도 간선에 있으면)부터, 없으면 첫 제자보다 4년 앞에서 시작
  const rootIn = incoming(root).map(yearOf).filter(Boolean);
  tree.year = rootIn.length ? Math.min(...rootIn) : null;
  tree.uni = rootIn.length ? affiliationName(incoming(root).find(e => yearOf(e) === tree.year).university) : (N.get(root).affiliations[0] || '');
  const known = items.map(x => x.year).filter(Boolean);
  const y0 = tree.year || (known.length ? Math.min(...known) - 4 : 2000), y1 = (known.length ? Math.max(...known) : y0 + 10) + 1;
  const x0 = PAD_L + colOffset, maxDepth = Math.max(...items.map(x => x.depth)), ticks = [];
  if (simple()) {                                       // 간단 보기: 세대마다 같은 간격의 열
    items.forEach(x => { x.x = x0 + x.depth * COL; });
    for (let d = 0; d <= maxDepth; d++) ticks.push([x0 + d * COL, d ? `제자 ${d}세대` : '시작 교수']);
  } else {                                              // 시간축 보기: 가로 = 학위 연도
    const xOf = y => x0 + (y - y0) * PX_YEAR;
    tree.x = xOf(tree.year || y0); tree.unknown = !tree.year;
    (function setX(it) { for (const k of it.kids) { if (k.year) k.x = xOf(k.year); else { k.x = it.x + 3 * PX_YEAR; k.unknown = true; } setX(k); } })(tree);
    for (let y = Math.ceil(y0 / 5) * 5; y <= y1; y += 5) ticks.push([xOf(y), String(y)]);
  }
  const maxX = Math.max(...items.map(x => x.x), ticks.length ? ticks[ticks.length - 1][0] : 0);
  mentors.forEach((m, i) => { m.x = PAD_L + 10; m.y = tree.y - (mentors.length - 1) * MENTOR_GAP / 2 + i * MENTOR_GAP; lines.push({ a: m, b: tree, e: m.via, mentor: true }); });
  const bottom = Math.max(top + tree.h, mentors.length ? mentors[mentors.length - 1].y + MENTOR_GAP / 2 : 0);
  return { items: [...mentors, ...items], tree, mentors, lines, cycles, maxDepth, ticks, x0, y0, y1, width: maxX + PAD_R, height: bottom + PAD_BOTTOM };
}

// ── 그리기
function draw() {
  view = layout(); const v = view, svg = el('network');
  svg.classList.toggle('simple', simple());
  let s = '<g id="scene">';
  s += v.ticks.map(([x]) => `<line class="ln-grid" x1="${x}" x2="${x}" y1="0" y2="${v.height - PAD_BOTTOM + 8}"/>`).join('');
  // 지도 기간 띠 (시간축 보기에서만: 제자를 둔 사람마다 첫 제자부터 마지막 제자까지)
  if (!simple()) s += v.items.filter(x => x.kids.length).map(x => { const xs = x.kids.map(k => k.x); return `<line class="ln-span" x1="${x.x}" x2="${Math.max(...xs)}" y1="${x.y}" y2="${x.y}" stroke="${colorOf(x.uni)}"/>`; }).join('');
  s += v.lines.map(({ a, b, e, mentor }, i) => {
    const x1 = a.x + RADIUS[a.kind] + 3, x2 = b.x - RADIUS[b.kind] - 3, mx = (x1 + x2) / 2;
    return `<path class="ln-link${e.student_is_inferred_professor ? ' inferred' : ''}${mentor ? ' mentor' : ''}${b.kids.length ? ' toprof' : ''}" data-line="${i}" d="M${x1} ${a.y}C${mx} ${a.y},${mx} ${b.y},${x2} ${b.y}"/>`;
  }).join('');
  s += v.items.map((x, i) => {
    const n = x.n, r = RADIUS[x.kind], inferred = x.kind !== 'mentor' && x.via?.student_is_inferred_professor;
    const aff = affOf(n), yr = x.kind === 'mentor' ? '' : (x.year ? String(x.year) : '연도 미상');
    // 이름 자리: 시작 교수·상위 지도교수는 왼쪽(들어오는 선이 없는 쪽), 제자를 둔 교수는 시간축에서는 점 위(들어오는 선과 나가는 선 모두 피함), 간단 보기에서는 오른쪽(다음 열까지 여유가 있음), 말단은 오른쪽
    const left = x.kind === 'root' || x.kind === 'mentor', above = !left && !simple() && x.kids.length > 0;
    const tx = left ? -(r + 8) : above ? -r : r + 7, anchor = left ? 'end' : 'start';
    const name = `${esc(nameOf(n))}${yr ? `<tspan class="yr"> ${esc(yr)}</tspan>` : ''}`;
    let label;
    if (x.kind === 'student') label = `<text class="name" x="${tx}" y="5" text-anchor="${anchor}">${name}</text>`;
    else {
      const sub = [cut(aff, 22) || (x.kind === 'root' ? shortUni(x.uni) : '소속 미확인'), n.advisee_thesis_count ? `지도 ${n.advisee_thesis_count}편` : ''].filter(Boolean).join(' · ');
      const big = x.kind === 'root';
      const ny = above ? -24 : big ? -4 : 5, sy = above ? -10 : big ? 17 : 22;
      label = `<text class="name" x="${tx}" y="${ny}" text-anchor="${anchor}">${name}</text><text class="sub" x="${tx}" y="${sy}" text-anchor="${anchor}">${esc(sub)}</text>`;
    }
    const cls = ['ln-node', x.kind, inferred ? 'inferred' : '', x.id === selected ? 'selected' : ''].filter(Boolean).join(' ');
    const tip = [nameOf(n), x.uni ? '학위 ' + x.uni : '', yr ? '박사 ' + yr : '', aff ? '재직 ' + aff : ''].filter(Boolean).join(' · ');
    return `<g class="${cls}" transform="translate(${x.x} ${x.y})" tabindex="0" role="button" data-i="${i}" aria-label="${esc(tip)} 상세 보기"><title>${esc(tip)}</title><circle r="${r}" fill="${colorOf(x.uni)}"/>${label}</g>`;
  }).join('');
  // 연도 눈금은 화면 위에 고정(세로로는 따라 움직이지 않음). 가로 위치는 apply() 가 배율·이동에 맞춰 갱신한다.
  s += '</g><g id="ruler"><rect class="ln-ruler-bg" x="0" y="0" width="100%" height="30"/>' + v.ticks.map(([x, t]) => `<text class="${simple() ? 'ln-col' : 'ln-tick'}" data-x="${x}" y="20" text-anchor="middle">${t}</text>`).join('') + (v.mentors.length ? `<text class="ln-col" data-x="${PAD_L + 10}" y="20" text-anchor="middle">지도교수</text>` : '') + '</g>';
  svg.innerHTML = s;
  svg.querySelectorAll('.ln-node').forEach(g => {
    const item = () => v.items[+g.dataset.i];
    g.onclick = e => { e.stopPropagation(); select(item()); };
    g.ondblclick = e => { e.preventDefault(); e.stopPropagation(); reroot(item()); };
    g.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (e.shiftKey) reroot(item()); else select(item()); } };
  });
  el('mentorNav').innerHTML = v.mentors.map(m => `<button data-mentor="${esc(m.id)}">← 지도교수 ${esc(nameOf(m.n))}</button>`).join('');
  el('mentorNav').querySelectorAll('[data-mentor]').forEach(b => b.onclick = () => setRoot(b.dataset.mentor));
  const R = N.get(root), shown = v.items.length - v.mentors.length;
  el('selected-title').textContent = nameOf(R) + '의 학맥';
  el('count').textContent = `표시 ${shown - 1}명 · ${v.maxDepth}세대${simple() ? '' : ` · 시간축 ${v.y0}–${v.y1 - 1}`}${v.cycles ? ' · 순환 연결 제외' : ''}`;
  el('legendTime').hidden = simple(); el('uniLegend').hidden = simple(); el('legendSimple').hidden = !simple();
  el('modeTime').setAttribute('aria-pressed', String(!simple())); el('modeSimple').setAttribute('aria-pressed', String(simple()));
  svg.setAttribute('aria-label', `${nameOf(R)}의 학맥: 제자 ${shown - 1}명, ${v.maxDepth}세대, ${v.y0}년부터 ${v.y1 - 1}년`);
  renderUniLegend(); renderMetrics(); paint();
}

function renderUniLegend() {
  const counts = new Map();
  for (const x of view.items) if (x.kind !== 'mentor' && x.kind !== 'root' && x.uni) counts.set(x.uni, (counts.get(x.uni) || 0) + 1);
  const rows = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'ko'));
  el('uniLegend').innerHTML = rows.length ? `<span class="ln-legend-title">학위 수여 대학</span>` + rows.map(([u, c]) => `<button class="ln-chip${uniFocus === u ? ' on' : ''}" data-uni="${esc(u)}" aria-pressed="${uniFocus === u}"><i style="background:${colorOf(u)}"></i>${esc(shortUni(u))} <b>${c}</b></button>`).join('') : '';
  el('uniLegend').querySelectorAll('[data-uni]').forEach(b => b.onclick = () => { uniFocus = uniFocus === b.dataset.uni ? null : b.dataset.uni; renderUniLegend(); paint(); });
}
function tile(value, label, sub, cls = '') { return `<div class="ln-tile ${cls}"><b>${value}</b><span>${label}</span>${sub ? `<small>${sub}</small>` : ''}</div>`; }
function renderMetrics() {
  const m = metrics(root), n = N.get(root);
  el('metrics').innerHTML =
    tile(`${fmt(m.direct)}명`, '직접 제자', `지도논문 ${fmt(m.theses)}편`) +
    tile(`${fmt(m.profs)}명`, '교수가 된 제자', `직접 제자의 ${pct(m.profs, m.direct)}`) +
    tile(`${fmt(m.descendants)}명`, '후손', `${m.generations}세대`) +
    tile(m.first ? `${m.first}–${m.last}` : '—', '지도 기간', m.first ? `${m.span + 1}년` : '연도 미상', 'range') +
    tile(m.lag == null ? '—' : `${m.lag.toFixed(1)}년`, '다음 세대까지', m.lag == null ? '제자의 지도논문 없음' : `제자가 첫 제자를 내기까지 · ${m.lagN}명`) +
    tile(m.profs ? `${m.stay}/${m.profs}` : '—', '모교 잔류', '학위 대학에 재직 중인 교수 제자') +
    tile(`${m.unis}곳`, '학위 대학', m.mainUni ? shortUni(m.mainUni) + (m.unis > 1 ? ' 외' : '') : '');
  el('metrics-note').textContent = `${nameOf(n)} · 수집 자료 안에서 연결된 지도논문만 집계합니다. 실제 제자 전체나 교수 배출 총수가 아닙니다.`;
}

function lineageSet(id) {
  const set = new Set([id]); const item = view.items.find(x => x.id === id); if (!item) return set;
  for (let p = item.parent; p; p = p.parent) set.add(p.id);
  (function down(it) { for (const k of it.kids) { set.add(k.id); down(k); } })(item);
  if (item.kind === 'mentor') set.add(root);
  if (item.kind === 'root') view.mentors.forEach(m => set.add(m.id));
  return set;
}
function paint() {
  const on = highlight ? lineageSet(highlight) : null, svg = el('network');
  const vis = x => (!on || on.has(x.id)) && (!uniFocus || x.uni === uniFocus || x.kind === 'root' || x.kind === 'mentor');
  svg.querySelectorAll('.ln-node').forEach(g => { const x = view.items[+g.dataset.i], ok = vis(x); g.classList.toggle('dim', !ok); g.classList.toggle('hi', !!on && on.has(x.id) && ok); g.classList.toggle('selected', x.id === selected); });
  svg.querySelectorAll('.ln-link').forEach(p => { const l = view.lines[+p.dataset.line], k = !!on && on.has(l.a.id) && on.has(l.b.id); p.classList.toggle('dim', (!!on && !k) || (!!uniFocus && !vis(l.b))); p.classList.toggle('hi', k); });
  svg.querySelectorAll('.ln-span').forEach((p, i) => { p.style.opacity = on || uniFocus ? '.06' : ''; });
  el('clearHighlight').disabled = !highlight && !uniFocus;
}
function select(item) { selected = item.id; selectedEdge = item.kind === 'mentor' ? null : item.via; highlight = item.id; showDetail(); paint(); }
function reroot(item) { if (item.n.kind === 'professor' && item.id !== root) setRoot(item.id); else select(item); }

// ── 화면 이동·배율
function apply() {
  el('scene')?.setAttribute('transform', `translate(${Z.x} ${Z.y}) scale(${Z.k})`);
  el('network').querySelectorAll('#ruler [data-x]').forEach(t => t.setAttribute('x', Z.x + t.dataset.x * Z.k));
  el('zoomLabel').textContent = Math.round(Z.k * 100) + '%';
}
function zoomTo(k, ax, ay) {
  const vp = el('viewport'); k = Math.max(.2, Math.min(3, k));
  if (ax == null) { ax = vp.clientWidth / 2; ay = vp.clientHeight / 2; }
  Z.x = ax - (ax - Z.x) * k / Z.k; Z.y = ay - (ay - Z.y) * k / Z.k; Z.k = k; apply();
}
function fitAll() {
  const vp = el('viewport'), k = Math.min(1.2, (vp.clientWidth - 24) / view.width, (vp.clientHeight - 24) / view.height);
  Z.k = k; Z.x = (vp.clientWidth - view.width * k) / 2; Z.y = (vp.clientHeight - view.height * k) / 2; apply();
}
function home() {   // 글자를 실제 크기(100%)로 두고, 왼쪽(시작 교수)부터 보이게 하며 시작 교수를 세로 중앙에 둔다
  const vp = el('viewport'), fit = Math.min((vp.clientWidth - 24) / view.width, (vp.clientHeight - 24) / view.height);
  const k = Math.max(1, Math.min(1.15, fit)); Z.k = k;
  Z.x = view.width * k <= vp.clientWidth ? (vp.clientWidth - view.width * k) / 2 : 0;
  Z.y = view.height * k <= vp.clientHeight ? (vp.clientHeight - view.height * k) / 2 : Math.min(8, vp.clientHeight / 2 - view.tree.y * k);
  apply();
}

// ── 상세
function metricLine(id) {
  const m = metrics(id);
  return `<p class="ln-mline">직접 제자 <b>${m.direct}</b> · 교수 배출 <b>${m.profs}</b> · 후손 <b>${m.descendants}</b> · <b>${m.generations}</b>세대 · 지도 기간 <b>${m.first ? `${m.first}–${m.last}` : '—'}</b> · 학위 대학 <b>${m.unis}</b>곳</p>`;
}
function showDetail() {
  const t = N.get(selected), e = selectedEdge; if (!t) { el('detail').innerHTML = ''; return; }
  const professors = (adj.get(selected) || []).filter(x => N.get(x.target).kind === 'professor');
  const advisees = (adj.get(selected) || []).slice().sort((a, b) => (yearOf(a) || 0) - (yearOf(b) || 0));
  const profile = '/academic-network.html?name=' + encodeURIComponent(t.name) + '#faculty';
  el('detail').innerHTML = `
<div class="ln-detail-head"><div><h2>${esc(nameOf(t))}</h2><p>${esc(affOf(t) || (t.kind === 'professor' ? '교수 소속 미확인' : '학위자 · 교수 여부 미확인'))}</p><p class="muted">${esc(t.faculty_statuses.join(' / ') || t.identity_status)}</p></div>
<div class="ln-detail-actions">${t.kind === 'professor' && studentCount(t.id) > 0 && t.id !== root ? '<button id="makeRoot" class="ln-btn">이 교수부터 보기</button>' : ''}<a class="ln-btn" href="${profile}">학교·소속·사제관계 →</a></div></div>
${urls(t.urls) ? `<p>${urls(t.urls)}</p>` : ''}
${t.kind === 'professor' && studentCount(t.id) ? `<h3>학맥 지표</h3>${metricLine(t.id)}` : ''}
${t.kind === 'professor' ? `<h3>다음 세대</h3><p>지도논문 ${t.advisee_thesis_count}편 · 교수로 연결된 제자 ${professors.length}명</p>${advisees.length ? `<details><summary>지도논문 ${advisees.length}편 보기</summary><ol>${advisees.map(a => `<li>${esc(nameOf(N.get(a.target)))} · ${esc(a.year || '연도 미상')} · ${esc(affiliationName(a.university))} · ${esc(a.title)}</li>`).join('')}</ol></details>` : ''}` : ''}
<div class="callout">${esc(e?.student_identity.note || t.identity_note)}</div>
${e ? `<h3>지도 관계</h3><p><b>${esc(nameOf(N.get(e.source)))} → ${esc(nameOf(t))}</b></p><p class="thesis">${esc(e.title)}</p><p class="muted">${esc(affiliationName(e.university))} · 서지 연도 ${esc(e.year || '미확인')} · 지도교수 원표기 ${esc(e.advisor_raw || '미확인')} · 수여기관 원표기 ${esc(e.university || '미확인')}</p>${e.advisor_conflict ? '<p class="callout">근거 충돌 검토: 기존 관계와 도서관 기록이 달라 해당 학위논문의 확정 지도교수로 표시하지 않습니다.</p>' : ''}<p class="muted">관계 연결: ${esc(e.basis)} · 학생 동일인: ${esc(e.student_identity.status)}</p>${urls(e.urls) ? `<p>${urls(e.urls)}</p>` : ''}<details><summary>저장된 지도교수 검수 근거</summary><pre>${esc(JSON.stringify(e.advisor_evidence, null, 2))}</pre></details>` : ''}
<h3>표시 범위</h3><p class="muted">현재 수집자료에서 연결된 논문만 표시합니다. 다음 세대가 표시되지 않아도 실제 지도학생이 없다는 뜻은 아닙니다. 학생 이름만으로 교수 노드에 합치지 않았습니다.</p>`;
  const b = el('makeRoot'); if (b) b.onclick = () => setRoot(selected);
}

// ── 비교표: 지도논문이 있는 교수 전원
const COLS = [
  ['name', '교수', 'ko'], ['aff', '소속', 'ko'], ['direct', '직접 제자', 'num'], ['theses', '지도논문', 'num'], ['profs', '교수 배출', 'num'], ['profRate', '배출률', 'num'],
  ['descendants', '후손', 'num'], ['generations', '세대', 'num'], ['first', '지도 기간', 'num'], ['span', '연수', 'num'], ['lag', '다음 세대까지', 'num'], ['stay', '모교 잔류', 'num'], ['unis', '학위 대학', 'num']];
function compareRows() {
  return D.nodes.filter(n => n.kind === 'professor' && kidsAll(n.id).length).map(n => { const m = metrics(n.id); return { id: n.id, name: nameOf(n), aff: n.affiliations.join(' / '), ...m, profRate: m.direct ? m.profs / m.direct : 0, span: m.span == null ? null : m.span + 1 }; });
}
const median = a => { const s = a.filter(x => x != null).sort((x, y) => x - y); return s.length ? (s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : null; };
function cell(r, k) {
  switch (k) {
    case 'name': return `<b>${esc(r.name)}</b>`; case 'aff': return esc(r.aff || '—');
    case 'profRate': return pct(r.profs, r.direct); case 'first': return r.first ? `${r.first}–${r.last}` : '—';
    case 'lag': return r.lag == null ? '—' : r.lag.toFixed(1) + '년'; case 'stay': return r.profs ? `${r.stay}/${r.profs}` : '—';
    default: return r[k] == null ? '—' : fmt(r[k]);
  }
}
function renderCompare() {
  const rows = compareRows(), col = COLS.find(c => c[0] === sortKey);
  rows.sort((a, b) => { const x = a[sortKey], y = b[sortKey]; if (col[2] === 'ko') return sortDir * String(x).localeCompare(String(y), 'ko'); if (x == null) return 1; if (y == null) return -1; return sortDir * (x - y) || b.descendants - a.descendants || a.name.localeCompare(b.name, 'ko'); });
  const med = Object.fromEntries(['direct', 'theses', 'profs', 'descendants', 'generations', 'span', 'lag', 'unis'].map(k => [k, median(rows.map(r => r[k]))]));
  el('compare-count').textContent = `교수 ${rows.length}명 · 열 머리글을 누르면 정렬 · 행을 누르면 그 교수의 학맥으로 이동`;
  el('compare').innerHTML = `<table class="ln-table"><thead><tr>${COLS.map(([k, l]) => `<th data-sort="${k}" class="${k === sortKey ? (sortDir < 0 ? 'desc' : 'asc') : ''}${k === 'name' || k === 'aff' ? ' txt' : ''}" scope="col"><button type="button">${l}</button></th>`).join('')}</tr></thead>
<tbody>${rows.map(r => `<tr data-root="${esc(r.id)}" class="${r.id === root ? 'on' : ''}" tabindex="0">${COLS.map(([k]) => `<td class="${k === 'name' || k === 'aff' ? 'txt' : 'num'}">${cell(r, k)}</td>`).join('')}</tr>`).join('')}</tbody>
<tfoot><tr><td class="txt">중앙값</td><td class="txt muted">교수 ${rows.length}명</td><td class="num">${med.direct ?? '—'}</td><td class="num">${med.theses ?? '—'}</td><td class="num">${med.profs ?? '—'}</td><td class="num">—</td><td class="num">${med.descendants ?? '—'}</td><td class="num">${med.generations ?? '—'}</td><td class="num">—</td><td class="num">${med.span ?? '—'}</td><td class="num">${med.lag == null ? '—' : med.lag.toFixed(1) + '년'}</td><td class="num">—</td><td class="num">${med.unis ?? '—'}</td></tr></tfoot></table>`;
  el('compare').querySelectorAll('th[data-sort]').forEach(th => th.querySelector('button').onclick = () => { const k = th.dataset.sort; if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = COLS.find(c => c[0] === k)[2] === 'ko' ? 1 : -1; } renderCompare(); });
  el('compare').querySelectorAll('tr[data-root]').forEach(tr => { const go = () => { setRoot(tr.dataset.root); el('selected-title').scrollIntoView({ block: 'start', behavior: 'smooth' }); }; tr.onclick = go; tr.onkeydown = e => { if (e.key === 'Enter') go(); }; });
}
function downloadCsv() {
  const rows = compareRows().sort((a, b) => b.descendants - a.descendants);
  const head = ['교수', '소속', '직접 제자', '지도논문', '교수 배출', '배출률', '후손', '세대', '지도 시작', '지도 끝', '지도 연수', '다음 세대까지 평균 연수', '모교 잔류', '학위 대학 수', '주요 학위 대학'];
  const q = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const body = rows.map(r => [r.name, r.aff, r.direct, r.theses, r.profs, r.direct ? (r.profs / r.direct).toFixed(3) : '', r.descendants, r.generations, r.first ?? '', r.last ?? '', r.span ?? '', r.lag == null ? '' : r.lag.toFixed(1), r.profs ? `${r.stay}/${r.profs}` : '', r.unis, r.mainUni].map(q).join(','));
  const blob = new Blob(['﻿' + [head.map(q).join(','), ...body].join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `kcritic_학맥지표_${D.as_of}.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ── 왼쪽 목록
function options() {
  const q = el('search').value.trim().toLowerCase();
  const list = D.nodes.filter(n => n.kind === 'professor' && studentCount(n.id) > 0 && (!q || [n.name, ...(n.aliases || []), ...n.affiliations].join(' ').toLowerCase().includes(q)))
    .sort((a, b) => studentCount(b.id) - studentCount(a.id) || a.name.localeCompare(b.name, 'ko'));
  el('list-count').textContent = `${list.length}명 · 지도학생 수 순`;
  el('people').innerHTML = list.map(n => `<button class="ln-person${n.id === root ? ' on' : ''}" data-root="${esc(n.id)}" aria-pressed="${n.id === root}"><strong>${esc(nameOf(n))}</strong><span class="ln-n">${studentCount(n.id)}명</span><small>${esc(n.affiliations.join(' / ') || '소속 미확인')}</small></button>`).join('') || '<p class="ln-muted">검색 결과가 없습니다.</p>';
  el('people').querySelectorAll('[data-root]').forEach(b => b.onclick = () => setRoot(b.dataset.root));
}
function setRoot(id, remember = true) {
  if (!N.has(id)) return;
  if (remember && id !== root) trail.push(root);
  root = id; selected = id; selectedEdge = null; highlight = null; uniFocus = null;
  const u = new URL(location.href); u.searchParams.set('person', id); history.replaceState(null, '', u);
  options(); draw(); home(); showDetail(); revealInList(); markCompareRow();
  el('backRoot').disabled = !trail.length;
}
function markCompareRow() { el('compare').querySelectorAll('tr[data-root]').forEach(tr => tr.classList.toggle('on', tr.dataset.root === root)); }
function revealInList() {   // 목록 안에서만 스크롤 (페이지 전체는 움직이지 않는다)
  const list = el('people'), on = list.querySelector('.ln-person.on');
  if (on && (on.offsetTop < list.scrollTop || on.offsetTop + on.offsetHeight > list.scrollTop + list.clientHeight)) list.scrollTop = on.offsetTop - list.clientHeight / 2 + on.offsetHeight / 2;
}

// ── 이벤트
el('search').oninput = options;
el('profOnly').onchange = () => { draw(); home(); showDetail(); };
el('inferred').onchange = () => { metricsCache.clear(); draw(); home(); showDetail(); renderCompare(); };
el('minus').onclick = () => zoomTo(Z.k / 1.25); el('plus').onclick = () => zoomTo(Z.k * 1.25);
el('zoomReset').onclick = fitAll; el('zoomHome').onclick = home;
function setMode(m) {
  mode = m; uniFocus = null; try { localStorage.setItem('kc-lineage-view', m); } catch (_) {}
  const u = new URL(location.href); u.searchParams.set('view', m); history.replaceState(null, '', u);
  draw(); home();
}
el('modeTime').onclick = () => setMode('time'); el('modeSimple').onclick = () => setMode('simple');
el('clearHighlight').onclick = () => { highlight = null; uniFocus = null; renderUniLegend(); paint(); };
el('backRoot').onclick = () => { if (trail.length) setRoot(trail.pop(), false); };
el('csv').onclick = downloadCsv;
const vp = el('viewport'); let drag = null, suppressClick = false;
// 포인터 캡처는 쓰지 않는다(캡처하면 click 대상이 바뀌어 노드 클릭이 먹지 않는다). 창 전체에서 이동·놓기를 받는다.
vp.addEventListener('wheel', e => { e.preventDefault(); const r = vp.getBoundingClientRect(); zoomTo(Z.k * Math.exp(-e.deltaY * .0012), e.clientX - r.left, e.clientY - r.top); }, { passive: false });
vp.addEventListener('pointerdown', e => { if (e.button !== 0) return; drag = { x: e.clientX, y: e.clientY, zx: Z.x, zy: Z.y, moved: false }; });
window.addEventListener('pointermove', e => { if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 4) return; drag.moved = true; vp.classList.add('dragging'); Z.x = drag.zx + dx; Z.y = drag.zy + dy; apply(); e.preventDefault(); });
const endDrag = () => { suppressClick = !!drag?.moved; drag = null; vp.classList.remove('dragging'); };
window.addEventListener('pointerup', endDrag); window.addEventListener('pointercancel', endDrag); window.addEventListener('blur', endDrag);
vp.addEventListener('click', e => { if (suppressClick) { suppressClick = false; e.stopPropagation(); e.preventDefault(); } else if (!e.target.closest('.ln-node')) { highlight = null; paint(); } }, true);
window.addEventListener('resize', () => { if (view) apply(); });

// ── 시작
fetch('/site/data/genealogy-library.json').then(r => { if (!r.ok) throw Error(r.status); return r.json(); }).then(d => {
  D = d; N = new Map(D.nodes.map(n => [n.id, n])); adj = new Map();
  D.nodes.forEach(n => { n.affiliations = [...new Set((n.affiliations || []).map(affiliationName).filter(Boolean))]; });
  D.edges.forEach(e => { if (!adj.has(e.source)) adj.set(e.source, []); adj.get(e.source).push(e); });
  // 대학 색: 전체 지도논문 수 상위 8개 대학에 고정 배정 (시작 교수가 바뀌어도 같은 대학은 같은 색)
  const uc = new Map(); D.edges.forEach(e => { const u = affiliationName(e.university); uc.set(u, (uc.get(u) || 0) + 1); });
  [...uc.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'ko')).slice(0, PALETTE.length).forEach(([u], i) => uniColor.set(u, PALETTE[i]));
  el('status').textContent = '';
  el('totals').textContent = `지도논문이 있는 교수 ${fmt(D.summary.faculty_with_advisees)}명 · 지도논문 연결 ${fmt(D.summary.advisor_thesis_edges)}건 · ${D.as_of} 기준`;
  el('coverage').innerHTML = `전체 ${fmt(D.summary.advisor_thesis_edges)}개 지도논문 연결 · 지도논문이 있는 교수 ${fmt(D.summary.faculty_with_advisees)}개 인물 ID. <a href="/site/data/genealogy-library.json">근거 포함 데이터</a> · 기본 교수 명단과 기존 학맥 검수의 교수 이력을 합쳤습니다. 동일인 미확정 교수행은 별도로 남아 있습니다. 지표는 Rossi 외(2018)의 계보 지표(직접 제자·후손·세대·교수 배출)를 이 자료에 맞게 줄인 것입니다.`;
  const want = new URLSearchParams(location.search).get('person');
  root = N.has(want) ? want : D.default_root; selected = root;
  options(); draw(); home(); showDetail(); revealInList(); renderCompare();
  window.genealogyState = () => ({ root, profOnly: profOnly(), visible: view.items.map(x => ({ name: x.n.name, kind: x.n.kind, depth: x.depth, year: x.year, uni: x.uni })), metrics: metrics(root), summary: D.summary });
}).catch(err => { console.error(err); el('status').textContent = '학맥 데이터를 불러오지 못했습니다. 새로고침해 주세요.'; });
})();
