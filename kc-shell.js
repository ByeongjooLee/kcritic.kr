// kcritic 2판 머리글·바닥글 — 예전 화면(style.css)용 독립판.
// kc.js 의 shell()·globalSearch() 와 같은 모양을 만들되, 전역 이름을 남기지 않는다(IIFE)
// → 예전 화면의 자체 스크립트와 이름이 부딪히지 않는다. 경로는 모두 사이트 뿌리 기준(/).
(function () {
  const R = "/";
  const NAV = [
    ["find", "글 찾기", R + "explore.html?p=find"], ["essays", "글", R + "explore.html?p=essays"],
    ["people", "인물", R + "explore.html?p=people"], ["concepts", "개념어", R + "explore.html?p=concepts"],
    ["venues", "지면", R + "explore.html?p=venues"], ["graph", "관계망", R + "graph.html"],
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
      <div class="gsearch"><input id="kcs-q" type="search" placeholder="글·인물·개념어 이름으로 찾기" autocomplete="off" aria-label="글·인물·개념어 찾기"><div class="suggest" id="kcs-s"></div></div>
      <a class="btn dark" href="${R}ask.html">질문하기</a>
      <button class="btn menu-btn" id="kcs-menu" type="button">메뉴</button>
    </div>
  </div></header>`);
    document.body.insertAdjacentHTML("beforeend", `
  <footer class="ft"><div class="wrap cols">
    <div><b style="color:var(--kc-ink);font-size:15px">kcritic.</b><p style="margin-top:6px;max-width:360px">한국 현대 문학비평을 TEI XML로 인코딩해 비평가·작가·이론가·개념어의 관계를 연결 데이터로 공개합니다. 원문은 제공하지 않습니다.</p></div>
    <div><h6>분석</h6><a href="${R}ask.html">질문하기 · SPARQL</a><a href="${R}evaluate.html">태도 평가</a><a href="${R}graph.html">관계망</a></div>
    <div><h6>참고 데이터</h6><a href="${R}research.html">선행연구 (박사논문)</a><a href="${R}criticism.html">2000년대 시 비평 목록</a></div>
    <div><h6>프로젝트</h6><a href="${R}about.html">소개 · 방법</a><a href="${R}maker.html">만든 사람</a><a href="${R}contribute.html">참여하기</a><a href="${R}site/data/graph.ttl">데이터 내려받기 (TTL)</a><a href="${R}critic_v8_schema.rdf">온톨로지 (OWL)</a><a href="${R}list.html">전체 목록 (예전 화면)</a></div>
  </div></footer>`);
    const nav = document.getElementById("kcs-nav");
    document.getElementById("kcs-menu").onclick = () => nav.classList.toggle("show");
    const q = document.getElementById("kcs-q"), box = document.getElementById("kcs-s"), narrow = matchMedia("(max-width: 980px)");
    const ph = () => { q.placeholder = narrow.matches ? "이름으로 찾기" : "글·인물·개념어 이름으로 찾기"; };
    narrow.addEventListener("change", ph); ph();
    search(q, box);
  }

  function search(inp, box) {
    let D = null, sel = -1;
    const load = () => D ??= Promise.all(["essays", "people", "concepts"].map(n => fetch(`${R}site/data/v2/${n}.json`).then(r => r.json())))
      .then(([essays, people, concepts]) => ({ essays, people, concepts }));
    inp.addEventListener("focus", load);
    inp.addEventListener("input", async () => {
      const d = await load(), v = inp.value.trim();
      if (!v) { box.classList.remove("show"); return; }
      const has = s => (s || "").includes(v);
      const grp = (h, items) => items.length ? `<h6>${h}</h6>` + items.join("") : "";
      box.innerHTML =
        grp("인물", d.people.filter(p => has(p.name) || has(p.en)).slice(0, 5).map(p => { const t = TYPE[role(p)];
          return `<a href="${ent("person", p.id)}"><span class="dot ${t[1]}"></span>${esc(p.name)}<small>${t[0]}</small></a>`; })) +
        grp("글", d.essays.filter(e => has(e.title)).slice(0, 5).map(e => `<a href="${ent("essay", e.id)}"><span class="dot t-essay"></span>${esc(e.title)}<small>${esc(e.critic_name)} ${esc(e.year)}</small></a>`)) +
        grp("개념어", d.concepts.filter(c => has(c.name)).slice(0, 5).map(c => `<a href="${ent("concept", c.name)}"><span class="dot t-concept"></span>${esc(c.name)}<small>${c.n}편</small></a>`)) +
        `<h6>전체 검색</h6><a href="${R}explore.html?p=essays&q=${encodeURIComponent(v)}">“${esc(v)}” 글 전체에서 찾기 →</a>`;
      box.classList.add("show"); sel = -1;
    });
    inp.addEventListener("keydown", e => {
      const items = [...box.querySelectorAll("a")];
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); sel = Math.max(0, Math.min(items.length - 1, sel + (e.key === "ArrowDown" ? 1 : -1)));
        items.forEach((a, i) => a.classList.toggle("sel", i === sel));
      } else if (e.key === "Enter") {
        location.href = items[sel] ? items[sel].href : `${R}explore.html?p=essays&q=${encodeURIComponent(inp.value.trim())}`;
      } else if (e.key === "Escape") box.classList.remove("show");
    });
    document.addEventListener("click", e => { if (!e.target.closest(".hd .gsearch")) box.classList.remove("show"); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build); else build();
})();
