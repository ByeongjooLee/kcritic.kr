// kcritic 사이트 2판 — 공통 머리글·바닥글·데이터·작은 시각화 (build_site_v2.py 가 site/data/v2/ 를 만든다)
const KC = "";                                  // 사이트 뿌리 기준 (현행 프로필·관계망·질문하기 등)
const TYPE = {
  essay:    { label: "글", cls: "t-essay" },
  critic:   { label: "비평가", cls: "t-critic" },
  writer:   { label: "작가",   cls: "t-writer" },
  theorist: { label: "이론가", cls: "t-theorist" },
  concept:  { label: "개념어", cls: "t-concept" },
  venue:    { label: "지면",   cls: "t-venue" },
};
// 주 메뉴는 '관점' 다섯 개뿐. 분석·참여·참고 자료는 오른쪽 버튼과 바닥글로.
const NAV = [
  ["find", "글 찾기", "explore.html?p=find"],
  ["essays", "글", "explore.html?p=essays"],
  ["people", "인물", "explore.html?p=people"],
  ["concepts", "개념어", "explore.html?p=concepts"],
  ["venues", "지면", "explore.html?p=venues"],
  ["graph", "관계망", KC + "graph.html"],
];

const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = n => Number(n || 0).toLocaleString("ko-KR");
const ko = (a, b) => String(a).localeCompare(String(b), "ko");
const qs = new URLSearchParams(location.search);

const _cache = {};
const load = name => (_cache[name] ??= fetch(`site/data/v2/${name}.json`).then(r => r.json()));
async function db() {
  const [essays, people, concepts, issues] = await Promise.all(["essays", "people", "concepts", "issues"].map(load));
  const E = new Map(essays.map(e => [e.id, e])), P = new Map(people.map(p => [p.id, p]));
  return { essays, people, concepts, issues, E, P };
}
const href = {
  essay: id => `entity.html?t=essay&id=${encodeURIComponent(id)}`,
  person: id => `entity.html?t=person&id=${encodeURIComponent(id)}`,
  concept: n => `entity.html?t=concept&id=${encodeURIComponent(n)}`,
  issue: id => `entity.html?t=issue&id=${encodeURIComponent(id)}`,
};
// 잡지 원문 안내 (build.py JOURNAL_LINKS 와 같게) — 원문 대신 발행처 공식 페이지로 연결
const VENUE_LINK = { mhs: { url: "https://moonji.com/literatureAndSociety/intro", label: "문학과지성사 『문학과사회』 소개·구독" } };
const LODN = { "W": "Wikidata", "NLK": "국중 LOD", "한": "민족문화대백과", "한(작품)": "민족문화대백과(작품)", "문학": "현대문학대사전" };
const lodName = b => LODN[b.label] || b.full || b.label;
const mainRole = p => p.wrote ? "critic" : (p.discussed >= p.cited ? "writer" : "theorist");

function shell(current) {
  document.body.insertAdjacentHTML("afterbegin", `
  <header class="hd"><div class="wrap">
    <a class="brand" href="index.html"><b>kcritic<i>.</i></b><span>한국 비평사 온톨로지</span></a>
    <nav class="nav">${NAV.map(([k, l, h]) => `<a href="${h}"${k === current ? ' class="on"' : ""}>${l}</a>`).join("")}</nav>
    <div class="hd-right">
      <div class="gsearch"><input id="gq" type="search" placeholder="글·인물·개념어 이름으로 찾기" autocomplete="off"><div class="suggest" id="gs"></div></div>
      <a class="btn dark" href="${KC}ask.html">질문하기</a>
      <button class="btn menu-btn" id="menu">메뉴</button>
    </div>
  </div></header>`);
  document.body.insertAdjacentHTML("beforeend", `
  <footer class="ft"><div class="wrap cols">
    <div><b style="color:var(--ink);font-size:15px">kcritic.</b><p style="margin-top:6px;max-width:360px">한국 현대 문학비평을 TEI XML로 인코딩해 비평가·작가·이론가·개념어의 관계를 연결 데이터로 공개합니다. 원문은 제공하지 않습니다.</p></div>
    <div><h6>분석</h6><a href="${KC}ask.html">질문하기 · SPARQL</a><a href="${KC}evaluate.html">태도 평가</a><a href="${KC}graph.html">관계망</a></div>
    <div><h6>참고 데이터</h6><a href="${KC}research.html">선행연구 (박사논문)</a><a href="${KC}criticism.html">2000년대 시 비평 목록</a></div>
    <div><h6>프로젝트</h6><a href="${KC}about.html">소개 · 방법</a><a href="${KC}maker.html">만든 사람</a><a href="${KC}contribute.html">참여하기</a><a href="${KC}site/data/graph.ttl">데이터 내려받기 (TTL)</a><a href="${KC}critic_v8_schema.rdf">온톨로지 (OWL)</a><a href="${KC}list.html">전체 목록 (예전 화면)</a></div>
  </div></footer>`);
  document.getElementById("menu").onclick = () => document.querySelector(".nav").classList.toggle("show");
  const gq = document.getElementById("gq"), narrowQ = matchMedia("(max-width: 980px)");   // 좁은 화면: 안내 글이 잘리지 않게 짧게
  const ph = () => { gq.placeholder = narrowQ.matches ? "이름으로 찾기" : "글·인물·개념어 이름으로 찾기"; };
  narrowQ.addEventListener("change", ph); ph();
  globalSearch();
}

function globalSearch() {
  const inp = document.getElementById("gq"), box = document.getElementById("gs");
  let D = null, sel = -1;
  inp.addEventListener("focus", async () => { D ??= await db(); });
  inp.addEventListener("input", async () => {
    D ??= await db();
    const q = inp.value.trim();
    if (!q) { box.classList.remove("show"); return; }
    const has = s => (s || "").includes(q);
    const ess = D.essays.filter(e => has(e.title)).slice(0, 5);
    const ppl = D.people.filter(p => has(p.name) || has(p.en)).slice(0, 5);
    const con = D.concepts.filter(c => has(c.name)).slice(0, 5);
    const grp = (h, items) => items.length ? `<h6>${h}</h6>` + items.join("") : "";
    box.innerHTML =
      grp("인물", ppl.map(p => `<a href="${href.person(p.id)}"><span class="dot ${TYPE[mainRole(p)].cls}"></span>${esc(p.name)}<small>${TYPE[mainRole(p)].label}</small></a>`)) +
      grp("글", ess.map(e => `<a href="${href.essay(e.id)}"><span class="dot t-essay"></span>${esc(e.title)}<small>${esc(e.critic_name)} ${e.year}</small></a>`)) +
      grp("개념어", con.map(c => `<a href="${href.concept(c.name)}"><span class="dot t-concept"></span>${esc(c.name)}<small>${c.n}편</small></a>`)) +
      `<h6>전체 검색</h6><a href="explore.html?p=essays&q=${encodeURIComponent(q)}">“${esc(q)}” 글 전체에서 찾기 →</a>`;
    box.classList.add("show"); sel = -1;
  });
  inp.addEventListener("keydown", e => {
    const items = [...box.querySelectorAll("a")];
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault(); sel = Math.max(0, Math.min(items.length - 1, sel + (e.key === "ArrowDown" ? 1 : -1)));
      items.forEach((a, i) => a.classList.toggle("sel", i === sel));
    } else if (e.key === "Enter") {
      if (items[sel]) location.href = items[sel].href;
      else location.href = `explore.html?p=essays&q=${encodeURIComponent(inp.value.trim())}`;
    } else if (e.key === "Escape") box.classList.remove("show");
  });
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
