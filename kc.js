// kcritic 사이트 2판 — 공통 머리글·바닥글·데이터·작은 시각화 (build_site_v2.py 가 site/data/v2/ 를 만든다)
const KC = "/";                                  // 사이트 뿌리 기준 (현행 프로필·관계망·질문하기 등)
const TYPE = {
  essay:    { label: "글", cls: "t-essay" },
  critic:   { label: "비평가", cls: "t-critic" },
  writer:   { label: "작가",   cls: "t-writer" },
  theorist: { label: "이론가", cls: "t-theorist" },
  concept:  { label: "개념어", cls: "t-concept" },
  venue:    { label: "지면",   cls: "t-venue" },
};
// 현장비평과 학술연구를 구분하고, 비평의 인물·개념·지면 탐색을 제공한다.
const NAV = [
  ["search", "통합검색", "/search.html"],
  ["find", "현장비평", "/explore.html?p=find"],
  ["theses", "학술연구", "/theses/"],
];

const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = n => Number(n || 0).toLocaleString("ko-KR");
const ko = (a, b) => String(a).localeCompare(String(b), "ko");
const qs = new URLSearchParams(location.search);

const _cache = {};
const load = name => (_cache[name] ??= fetch(`/site/data/v2/${name}.json`).then(r => r.json()));
async function db() {
  const [essays, people, concepts, issues] = await Promise.all(["essays", "people", "concepts", "issues"].map(load));
  const E = new Map(essays.map(e => [e.id, e])), P = new Map(people.map(p => [p.id, p]));
  return { essays, people, concepts, issues, E, P };
}
const href = {
  essay: id => `/entity.html?t=essay&id=${encodeURIComponent(id)}`,
  person: id => `/entity.html?t=person&id=${encodeURIComponent(id)}`,
  concept: n => `/entity.html?t=concept&id=${encodeURIComponent(n)}`,
  issue: id => `/entity.html?t=issue&id=${encodeURIComponent(id)}`,
};
// 잡지 원문 안내 (build.py JOURNAL_LINKS 와 같게) — 원문 대신 발행처 공식 페이지로 연결
const VENUE_LINK = { mhs: { url: "https://moonji.com/literatureAndSociety/intro", label: "문학과지성사 『문학과사회』 소개·구독" } };
const LODN = { "W": "Wikidata", "NLK": "국중 LOD", "한": "민족문화대백과", "한(작품)": "민족문화대백과(작품)", "문학": "현대문학대사전" };
const lodName = b => LODN[b.label] || b.full || b.label;
const mainRole = p => p.wrote ? "critic" : (p.discussed >= p.cited ? "writer" : "theorist");

function shell(current) {
  if (["essays","people","concepts","venues","graph"].includes(current)) current="find";
  document.body.insertAdjacentHTML("afterbegin", `
  <header class="hd"><div class="wrap">
    <a class="brand" href="/index.html"><b>kcritic<i>.</i></b><span>한국 비평사 온톨로지</span></a>
    <nav class="nav">${NAV.map(([k, l, h]) => `<a href="${h}"${k === current ? ' class="on"' : ""}>${l}</a>`).join("")}</nav>
    <div class="hd-right">
      <div class="gsearch"><input id="gq" type="search" placeholder="글·인물·개념어·박사논문 찾기" autocomplete="off"><div class="suggest" id="gs"></div></div>
      <a class="btn dark" href="${KC}ask.html">질문하기</a>
      <button class="btn menu-btn" id="menu">메뉴</button>
    </div>
  </div></header>`);
  document.body.insertAdjacentHTML("beforeend", `
  <footer class="ft"><div class="wrap cols">
    <div><b style="color:var(--ink);font-size:15px">kcritic.</b><p style="margin-top:6px;max-width:360px">한국 현대 문학비평을 TEI XML로 인코딩해 비평가·작가·이론가·개념어의 관계를 연결 데이터로 공개합니다. 원문은 제공하지 않습니다.</p></div>
    <div><h6>분석</h6><a href="${KC}ask.html">질문하기 · SPARQL</a><a href="${KC}evaluate.html">태도 평가</a><a href="${KC}graph.html">관계망</a></div>
    <div><h6>참고 데이터</h6><a href="${KC}theses/">학술연구 · 박사논문 검색</a><a href="${KC}criticism.html">2000년대 시 비평 목록</a></div>
    <div><h6>프로젝트</h6><a href="${KC}about.html">소개 · 방법</a><a href="${KC}maker.html">만든 사람</a><a href="${KC}contribute.html">참여하기</a><a href="${KC}site/data/graph.ttl">데이터 내려받기 (TTL)</a><a href="${KC}critic_v8_schema.rdf">온톨로지 (OWL)</a><a href="${KC}list.html">전체 목록 (예전 화면)</a></div>
  </div></footer>`);
  document.getElementById("menu").onclick = () => document.querySelector(".nav").classList.toggle("show");
  const gq = document.getElementById("gq"), narrowQ = matchMedia("(max-width: 1180px)");   // 좁은 화면: 안내 글이 잘리지 않게 짧게
  const ph = () => { gq.placeholder = narrowQ.matches ? "이름·논문 찾기" : "글·인물·개념어·박사논문 찾기"; };
  narrowQ.addEventListener("change", ph); ph();
  globalSearch();
  const st = document.createElement("script"); st.src = "/kc-stat.js"; st.defer = true; document.head.appendChild(st);   // 방문 통계(IP 없음)
}

function globalSearch() {
  // 상단 검색: 현장비평(글·인물·개념어 이름)과 학술연구(박사논문 제목·저자)를 함께 보이고, 입력이 멈추면 학술연구 뜻 검색(/theses/api/search, bge-m3)도 덧붙인다 (2026-11-02).
  // Enter(선택 없음)는 통합검색(현장비평 + 학술연구 뜻 검색)으로 간다.
  const inp = document.getElementById("gq"), box = document.getElementById("gs");
  let D = null, R = null, sel = -1, gen = 0, timer = null; const sem = new Map();
  const thesisId = u => { try { return new URL(u).searchParams.get("control_no") || ""; } catch (e) { return ""; } };
  const thesisHref = (id, q) => `/study.html?type=thesis&id=${encodeURIComponent(id)}&q=${encodeURIComponent(q.slice(0, 160))}`;
  const loadResearch = () => R ??= fetch("/site/data/research-public.json").then(r => r.json())
    .then(d => d.theses.map(t => ({ id: thesisId(t.riss_url), title: t.title, author: t.author, year: t.year, uni: t.university, advisor: t.advisor })).filter(t => t.id)).catch(() => (R = null, []));
  inp.addEventListener("focus", async () => { D ??= await db(); loadResearch(); });
  const render = async (q, g) => {
    const has = s => (s || "").includes(q);
    const ess = D.essays.filter(e => has(e.title)).slice(0, 5);
    const ppl = D.people.filter(p => has(p.name) || has(p.en)).slice(0, 5);
    const con = D.concepts.filter(c => has(c.name)).slice(0, 5);
    const th = (await loadResearch()).filter(t => has(t.title) || has(t.author) || has(t.advisor)).slice(0, 4);   // 제목·저자·지도교수 이름
    if (g !== gen) return;
    const s = sem.get(q) || [];
    const grp = (h, items) => items.length ? `<h6>${h}</h6>` + items.join("") : "";
    box.innerHTML =
      grp("인물", ppl.map(p => `<a href="${href.person(p.id)}"><span class="dot ${TYPE[mainRole(p)].cls}"></span>${esc(p.name)}<small>${TYPE[mainRole(p)].label}</small></a>`)) +
      grp("글", ess.map(e => `<a href="${href.essay(e.id)}"><span class="dot t-essay"></span>${esc(e.title)}<small>${esc(e.critic_name)} ${e.year}</small></a>`)) +
      grp("개념어", con.map(c => `<a href="${href.concept(c.name)}"><span class="dot t-concept"></span>${esc(c.name)}<small>${c.n}편</small></a>`)) +
      grp("박사논문 (학술연구)", th.map(t => `<a href="${thesisHref(t.id, q)}"><span class="dot t-venue"></span>${esc(t.title)}<small>${esc(t.author)} ${esc(t.year)}${t.advisor ? ' · 지도 ' + esc(t.advisor) : ''}</small></a>`)) +
      grp("학술연구 · 뜻으로 찾은 논문", s.map(t => `<a href="${thesisHref(t.id, q)}"><span class="dot t-venue"></span>${esc(t.title)}<small>${esc(t.author)} ${esc(t.year)}</small></a>`)) +
      `<h6>전체 검색</h6><a href="/search.html?q=${encodeURIComponent(q)}">“${esc(q)}” 통합검색 — 현장비평·학술연구를 뜻으로 찾기 →</a><a href="/explore.html?p=essays&q=${encodeURIComponent(q)}">“${esc(q)}” 현장비평 글에서만 찾기 →</a>`;
    box.classList.add("show"); sel = -1;
  };
  const semantic = async (q, g) => {   // 입력이 멈춘 뒤 한 번만. 응답은 제목·저자·연도·RISS 번호뿐(원문 없음). 실패하면 조용히 넘어간다
    if (q.length < 2 || sem.has(q)) return;
    try {
      const r = await fetch("/theses/api/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: q }), signal: AbortSignal.timeout(12000) });
      if (!r.ok) return;
      const d = await r.json();
      sem.set(q, (d.results || []).map(t => ({ id: thesisId(t.riss_url), title: t.title, author: t.author, year: t.year })).filter(t => t.id).slice(0, 4));
    } catch (e) { return; }
    if (g === gen && inp.value.trim() === q) render(q, g);
  };
  inp.addEventListener("input", async () => {
    D ??= await db();
    const q = inp.value.trim(); const g = ++gen; clearTimeout(timer);
    if (!q) { box.classList.remove("show"); return; }
    render(q, g);
    timer = setTimeout(() => semantic(q, g), 600);
  });
  inp.addEventListener("keydown", e => {
    const items = [...box.querySelectorAll("a")];
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault(); sel = Math.max(0, Math.min(items.length - 1, sel + (e.key === "ArrowDown" ? 1 : -1)));
      items.forEach((a, i) => a.classList.toggle("sel", i === sel));
    } else if (e.key === "Enter") {
      if (items[sel]) { window.kcStat?.("search", inp.value); location.href = items[sel].href; }   // 전체 검색(else)은 통합검색 화면이 센다
      else location.href = `/search.html?q=${encodeURIComponent(inp.value.trim())}`;
    } else if (e.key === "Escape") box.classList.remove("show");
  });
  box.addEventListener("click", e => { const a = e.target.closest("a"); if (a && !a.href.includes("explore.html") && !a.href.includes("search.html")) window.kcStat?.("search", inp.value); });
  document.addEventListener("click", e => { if (!e.target.closest(".gsearch")) box.classList.remove("show"); });
  document.addEventListener("keydown", e => { if (e.key === "/" && document.activeElement.tagName !== "INPUT") { e.preventDefault(); inp.focus(); } });
}

// 연도 막대그래프 (SVG). years: 숫자 배열. opts: {from, to, sel:[a,b], h, onPick}
function histSVG(years, opts = {}) {
  const from = opts.from ?? 1950, to = opts.to ?? 2015, h = opts.h ?? 56, n = to - from + 1;
  const cnt = new Array(n).fill(0);
  years.forEach(y => { if (y >= from && y <= to) cnt[y - from]++; });
  const max = Math.max(1, ...cnt), W = 100 / n, sel = opts.sel;
  const bars = cnt.map((c, i) => {
    const y = from + i, bh = c ? Math.max(1.5, (h - 14) * c / max) : 0;
    const on = sel && y >= sel[0] && y <= sel[1];
    return `<g data-y="${y}"><title>${y}년 · ${c}편</title><rect class="hit" x="${i * W}%" y="0" width="${W}%" height="${h - 12}"></rect>` +
      `<rect class="b${on ? " on" : ""}" x="${i * W + W * 0.12}%" y="${h - 12 - bh}" width="${W * 0.76}%" height="${bh}" rx="1"></rect></g>`;
  }).join("");
  const ticks = [];
  for (let y = Math.ceil(from / 10) * 10; y <= to - 6; y += 10) ticks.push(`<text x="${(y - from) * W}%" y="${h}">${y}</text>`);
  return `<svg class="hist" height="${h}" role="img" aria-label="연도별 분포">${bars}${ticks.join("")}</svg>`;
}
function hbars(rows, opts = {}) {   // rows: [{label, href, v, cls}]
  const max = Math.max(1, ...rows.map(r => r.v));
  return rows.map(r => `<div class="hbar ${r.cls || ""}"><a href="${r.href || "#"}" title="${esc(r.label)}">${esc(r.label)}</a>` +
    `<div class="track"><i style="width:${100 * r.v / max}%"></i></div><span class="v num">${fmt(r.v)}</span></div>`).join("");
}
function download(name, text, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; a.click();
}
