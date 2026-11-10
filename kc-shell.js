// kcritic 2판 머리글·바닥글 — 예전 화면(style.css)용 독립판.
// kc.js 의 shell()·globalSearch() 와 같은 모양을 만들되, 전역 이름을 남기지 않는다(IIFE)
// → 예전 화면의 자체 스크립트와 이름이 부딪히지 않는다. 경로는 모두 사이트 뿌리 기준(/).
(function () {
  const R = "/";
  const NAV = [
  ["search", "통합검색", "/search.html"],
  ["find", "현장비평", "/explore.html?p=find"],
  ["theses", "학술연구", "/theses/"],
];
  const TYPE = { essay: ["글", "t-essay"], critic: ["비평가", "t-critic"], writer: ["작가", "t-writer"], theorist: ["이론가", "t-theorist"], concept: ["개념어", "t-concept"] };
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const role = p => p.wrote ? "critic" : (p.discussed >= p.cited ? "writer" : "theorist");
  const ent = (t, id) => `${R}entity.html?t=${t}&id=${encodeURIComponent(id)}`;

  function build() {
    document.body.classList.add("kcs");
    document.body.insertAdjacentHTML("afterbegin", `
  <header class="hd"><div class="wrap">
    <a class="brand" href="${R}index.html"><b>kcritic<i>.</i></b><span>한국 비평사 온톨로지</span></a>
    <nav class="nav" id="kcs-nav">${NAV.map(([, l, h]) => `<a href="${h}">${l}</a>`).join("")}</nav>
    <div class="hd-right">
      <div class="gsearch"><input id="kcs-q" type="search" placeholder="글·인물·개념어·박사논문 찾기" autocomplete="off" aria-label="글·인물·개념어·박사논문 찾기"><div class="suggest" id="kcs-s"></div></div>
      <a class="btn dark" href="${R}ask.html">질문하기</a>
      <button class="btn menu-btn" id="kcs-menu" type="button">메뉴</button>
    </div>
  </div></header>`);
    document.body.insertAdjacentHTML("beforeend", `
  <footer class="ft"><div class="wrap cols">
    <div><b style="color:var(--kc-ink);font-size:15px">kcritic.</b><p style="margin-top:6px;max-width:360px">한국 현대 문학비평을 TEI XML로 인코딩해 비평가·작가·이론가·개념어의 관계를 연결 데이터로 공개합니다. 원문은 제공하지 않습니다.</p></div>
    <div><h6>분석</h6><a href="${R}ask.html">질문하기 · SPARQL</a><a href="${R}evaluate.html">태도 평가</a><a href="${R}graph.html">관계망</a></div>
    <div><h6>참고 데이터</h6><a href="${R}theses/">학술연구 · 박사논문 검색</a><a href="${R}criticism.html">2000년대 시 비평 목록</a></div>
    <div><h6>프로젝트</h6><a href="${R}about.html">소개 · 방법</a><a href="${R}maker.html">만든 사람</a><a href="${R}contribute.html">참여하기</a><a href="${R}site/data/graph.ttl">데이터 내려받기 (TTL)</a><a href="${R}critic_v8_schema.rdf">온톨로지 (OWL)</a><a href="${R}list.html">전체 목록 (예전 화면)</a></div>
  </div></footer>`);
    const nav = document.getElementById("kcs-nav");
    document.getElementById("kcs-menu").onclick = () => nav.classList.toggle("show");
    const q = document.getElementById("kcs-q"), box = document.getElementById("kcs-s"), narrow = matchMedia("(max-width: 1180px)");
    const ph = () => { q.placeholder = narrow.matches ? "이름·논문 찾기" : "글·인물·개념어·박사논문 찾기"; };
    narrow.addEventListener("change", ph); ph();
    search(q, box);
    const st = document.createElement("script"); st.src = "/kc-stat.js"; st.defer = true; document.head.appendChild(st);   // 방문 통계(IP 없음)
  }

  function search(inp, box) {
    // kc.js globalSearch() 와 같은 동작(2026-11-02): 현장비평 이름 찾기 + 박사논문 제목·저자 + 입력이 멈추면 학술연구 뜻 검색, Enter 는 통합검색
    let D = null, RS = null, sel = -1, gen = 0, timer = null; const sem = new Map();
    const load = () => D ??= Promise.all(["essays", "people", "concepts"].map(n => fetch(`${R}site/data/v2/${n}.json`).then(r => r.json()))
      .concat(fetch(`${R}site/data/v2/cb_search.json`).then(r => r.json()).catch(() => [])))
      .then(([essays, people, concepts, cb]) => ({ essays, people, concepts, cb }));
    // 『창작과비평』 글(kc.js cbSearch 와 같은 규칙, 2026-11-10): [Item, 호 id, 연도, 표제, 필자, 난, 키워드, 요지] — 띄어쓰기 무시, 표제 > 키워드 > 필자 > 요지·난
    const cbNorm = s => String(s || "").toLowerCase().replace(/\s+/g, "");
    const cbFind = (q, rows) => { const w = cbNorm(q); if (!w) return []; rows._n ??= rows.map(r => r.map(cbNorm));
      const out = []; rows._n.forEach((r, k) => { const sc = Math.max(0, ...[[3, 4], [6, 3], [4, 2], [7, 1], [5, 1]].map(([f, wt]) => r[f].includes(w) ? wt : 0)); if (sc) out.push([sc, rows[k]]); });
      return out.sort((a, b) => b[0] - a[0] || (b[1][7] ? 1 : 0) - (a[1][7] ? 1 : 0) || b[1][2] - a[1][2]).slice(0, 5).map(x => x[1]); };
    const cbLink = r => r[7] ? ent("essay", `cb${r[0]}`) : `https://magazine.changbi.com/MCQuarterly/Item/${r[0]}`;
    const thesisId = u => { try { return new URL(u).searchParams.get("control_no") || ""; } catch (e) { return ""; } };
    const thesisHref = (id, q) => `${R}study.html?type=thesis&id=${encodeURIComponent(id)}&q=${encodeURIComponent(q.slice(0, 160))}`;
    const loadResearch = () => RS ??= fetch(`${R}site/data/research-public.json`).then(r => r.json())
      .then(d => d.theses.map(t => ({ id: thesisId(t.riss_url), title: t.title, author: t.author, year: t.year, advisor: t.advisor })).filter(t => t.id)).catch(() => (RS = null, []));
    inp.addEventListener("focus", () => { load(); loadResearch(); });
    const render = async (v, g) => {
      const d = await load(), th = (await loadResearch()).filter(t => (t.title || "").includes(v) || (t.author || "").includes(v) || (t.advisor || "").includes(v)).slice(0, 4);   // 제목·저자·지도교수 이름
      if (g !== gen) return;
      const has = s => (s || "").includes(v), s = sem.get(v) || [];
      const grp = (h, items) => items.length ? `<h6>${h}</h6>` + items.join("") : "";
      box.innerHTML =
        grp("인물", d.people.filter(p => has(p.name) || has(p.en)).slice(0, 5).map(p => { const t = TYPE[role(p)];
          return `<a href="${ent("person", p.id)}"><span class="dot ${t[1]}"></span>${esc(p.name)}<small>${t[0]}</small></a>`; })) +
        grp("글", d.essays.filter(e => has(e.title)).slice(0, 5).map(e => `<a href="${ent("essay", e.id)}"><span class="dot t-essay"></span>${esc(e.title)}<small>${esc(e.critic_name)} ${esc(e.year)}</small></a>`)) +
        grp("『창작과비평』 글", cbFind(v, d.cb).map(r => `<a href="${cbLink(r)}"${r[7] ? "" : ' target="_blank" rel="noopener"'}><span class="dot t-essay"></span>${esc(r[3])}<small>${esc(`${r[4]} · ${r[2]} · 『창작과비평』 ${r[1].replace(/^cb0*/, "")}호${r[7] ? " · 해제" : " · 창비 웹진"}`)}</small></a>`)) +
        grp("개념어", d.concepts.filter(c => has(c.name)).slice(0, 5).map(c => `<a href="${ent("concept", c.name)}"><span class="dot t-concept"></span>${esc(c.name)}<small>${c.n}편</small></a>`)) +
        grp("박사논문 (학술연구)", th.map(t => `<a href="${thesisHref(t.id, v)}"><span class="dot t-venue"></span>${esc(t.title)}<small>${esc(t.author)} ${esc(t.year)}${t.advisor ? ' · 지도 ' + esc(t.advisor) : ''}</small></a>`)) +
        grp("학술연구 · 뜻으로 찾은 논문", s.map(t => `<a href="${thesisHref(t.id, v)}"><span class="dot t-venue"></span>${esc(t.title)}<small>${esc(t.author)} ${esc(t.year)}</small></a>`)) +
        `<h6>전체 검색</h6><a href="${R}search.html?q=${encodeURIComponent(v)}">“${esc(v)}” 통합검색 — 현장비평·학술연구를 뜻으로 찾기 →</a><a href="${R}explore.html?p=essays&q=${encodeURIComponent(v)}">“${esc(v)}” 현장비평 글에서만 찾기 →</a>`;
      box.classList.add("show"); sel = -1;
    };
    const semantic = async (v, g) => {
      if (v.length < 2 || sem.has(v)) return;
      try {
        const r = await fetch(`${R}theses/api/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: v }), signal: AbortSignal.timeout(12000) });
        if (!r.ok) return;
        const d = await r.json();
        sem.set(v, (d.results || []).map(t => ({ id: thesisId(t.riss_url), title: t.title, author: t.author, year: t.year })).filter(t => t.id).slice(0, 4));
      } catch (e) { return; }
      if (g === gen && inp.value.trim() === v) render(v, g);
    };
    inp.addEventListener("input", () => {
      const v = inp.value.trim(), g = ++gen; clearTimeout(timer);
      if (!v) { box.classList.remove("show"); return; }
      render(v, g); timer = setTimeout(() => semantic(v, g), 600);
    });
    inp.addEventListener("keydown", e => {
      const items = [...box.querySelectorAll("a")];
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); sel = Math.max(0, Math.min(items.length - 1, sel + (e.key === "ArrowDown" ? 1 : -1)));
        items.forEach((a, i) => a.classList.toggle("sel", i === sel));
      } else if (e.key === "Enter") {
        if (items[sel]) window.kcStat?.("search", inp.value);   // 전체 검색은 통합검색 화면이 센다
        location.href = items[sel] ? items[sel].href : `${R}search.html?q=${encodeURIComponent(inp.value.trim())}`;
      } else if (e.key === "Escape") box.classList.remove("show");
    });
    box.addEventListener("click", e => { const a = e.target.closest("a"); if (a && !a.href.includes("explore.html") && !a.href.includes("search.html")) window.kcStat?.("search", inp.value); });
    document.addEventListener("click", e => { if (!e.target.closest(".hd .gsearch")) box.classList.remove("show"); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build); else build();
})();
