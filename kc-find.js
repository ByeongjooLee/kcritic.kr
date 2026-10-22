// 글 찾기 — 브라우저 엔진 (find/engine 2판을 옮긴 것, DeepSeek 없음)
// 점수 = 뜻(임베딩) 0.62 + 낱말 0.23 + 인물 관계 0.15
//   뜻: bge-m3 — 글 전체 벡터 0.55 + 칸별(제목·개념어·인물) 최고값 0.45   (공개 벡터 site/data/find/vec.bin)
//   낱말: 개념어·인물 정확 일치(idf) + 제목·개념어 부분 일치 + 글자 2-gram BM25 + 본문 희귀어(Worker 가 조회) + 아주 드문 말 가산
//   인물 관계: 질문 속 인물이 쓴 글·다룬 글·인용한 글 + 함께 자주 나오는 인물
// 질문 벡터와 본문 희귀어 조회는 /api/find (worker/index.js). 나머지 계산은 모두 여기서 한다.
const FIND = (() => {
  const PARTS = ["으로서", "으로", "에서", "에게", "에는", "에서의", "이라는", "라는", "과의", "와의", "이란", "란", "은", "는", "이", "가",
    "을", "를", "의", "과", "와", "도", "로", "에", "만", "들", "이다", "이며", "하는", "하고", "했다", "한다", "에서는", "으로는",
    "이나", "나", "께서", "처럼", "보다", "부터", "까지"].sort((a, b) => b.length - a.length);
  const STOP = new Set(["글", "글들", "비평", "비평글", "관한", "대한", "관련", "논의", "읽고", "싶어", "싶다", "찾아", "줘", "있는", "다룬", "어떤", "무엇",
    "보여", "알려", "년대", "년", "호", "작품", "쓴", "나오는", "어떻게", "읽을까", "살핀", "그린", "논한", "통해", "본", "같은", "위한",
    "문제", "의미", "시", "소설"]);
  const W_EMB = 0.62, W_LEX = 0.23, W_GRAPH = 0.15, LAYER = [0.55, 0.45];
  const VOCAB_FLOOR = 0.68, VOCAB_W = 0.35, BODYLEX_W = 0.8, RARE_BONUS = 0.2, BM25_W = 0.15;
  const DIM = 1024;

  const strip = w => { for (const p of PARTS) if (w.endsWith(p) && w.length - p.length >= 2) return w.slice(0, -p.length); return w; };
  const norm = s => (s || "").replace(/[\s·\-—‘’'"“”「」『』《》()（）]/g, "");
  const bigrams = s => { s = norm(s); const o = []; for (let i = 0; i < s.length - 1; i++) o.push(s.slice(i, i + 2)); return o; };
  const minmax = a => { let lo = Infinity, hi = -Infinity; for (const x of a) { if (x < lo) lo = x; if (x > hi) hi = x; } const r = (hi - lo) || 1; return a.map(x => (x - lo) / r); };
  const counter = arr => { const m = new Map(); for (const x of arr) m.set(x, (m.get(x) || 0) + 1); return m; };

  let S = null;
  function decode(buf, rows) {             // int8 행렬 + float32 행별 배율 → Float32Array (행 우선)
    const q = new Int8Array(buf, 0, rows * DIM), sc = new Float32Array(buf.slice(rows * DIM, rows * DIM + rows * 4));
    const out = new Float32Array(rows * DIM);
    for (let r = 0; r < rows; r++) { const s = sc[r], o = r * DIM; for (let j = 0; j < DIM; j++) out[o + j] = q[o + j] * s; }
    return out;
  }
  const dot = (M, row, v) => { let s = 0; const o = row * DIM; for (let j = 0; j < DIM; j++) s += M[o + j] * v[j]; return s; };

  async function init(D) {
    if (S) return S;
    const base = "site/data/find/";
    const [meta, vb, wb] = await Promise.all([
      fetch(base + "meta.json").then(r => r.json()),
      fetch(base + "vec.bin").then(r => r.arrayBuffer()),
      fetch(base + "vocab.bin").then(r => r.arrayBuffer())]);
    const N = meta.ids.length, V = meta.vocab.terms.length;
    const VEC = decode(vb, N * 4), VOC = decode(wb, V);
    const row = new Map(meta.ids.map((id, i) => [id, i]));
    const essays = D.essays, n = essays.length;
    const nm = pid => (D.P.get(pid) || {}).name || "";
    const kw = new Map(), head = [], conc = [], bg = [];
    essays.forEach((e, i) => {
      const add = (k) => { k = norm(k); if (!k) return; if (!kw.has(k)) kw.set(k, new Set()); kw.get(k).add(i); };
      e.concepts.forEach(add);
      [...e.subjects, ...e.theorists, e.critic].forEach(p => nm(p) && add(nm(p)));
      head.push(norm(e.title + (e.section || "")));
      conc.push(norm(e.concepts.join(" ")));
      bg.push(counter(bigrams(e.title + " " + e.concepts.join(" ") + " " + [...e.subjects, ...e.theorists].map(nm).join(" "))));
    });
    const dfg = new Map(); bg.forEach(c => c.forEach((_, g) => dfg.set(g, (dfg.get(g) || 0) + 1)));
    const bgIdf = new Map([...dfg].map(([g, d]) => [g, Math.log(1 + (n - d + 0.5) / (d + 0.5))]));
    const bgAvg = bg.reduce((s, c) => s + [...c.values()].reduce((a, b) => a + b, 0), 0) / n;
    const personArts = new Map(), artPersons = [];
    essays.forEach((e, i) => {
      const rels = [[e.critic, "필자"], ...e.subjects.map(p => [p, "대상"]), ...e.theorists.map(p => [p, "이론"])];
      artPersons.push(rels);
      for (const [p, r] of rels) if (p) { if (!personArts.has(p)) personArts.set(p, []); personArts.get(p).push([i, r]); }
    });
    const byName = new Map();
    for (const p of D.people) if (p.name.length >= 2 && personArts.has(p.id)) { if (!byName.has(p.name)) byName.set(p.name, []); byName.get(p.name).push(p.id); }
    const name2pid = new Map([...byName].map(([k, v]) => [k, v.reduce((a, b) => personArts.get(b).length > personArts.get(a).length ? b : a)]));
    const names = [...name2pid.keys()].sort((a, b) => b.length - a.length);
    S = { meta, N, V, VEC, VOC, row, essays, n, kw, head, conc, bg, bgIdf, bgAvg, personArts, artPersons, name2pid, names, D };
    return S;
  }

  function parse(q) {
    const f = {};
    let m = q.match(/(19|20)(\d)0\s*년대/);
    if (m) { const d = +(m[1] + m[2] + "0"); f.years = [d, d + 9]; }
    else if ((m = q.match(/(?<!\d)(\d)0\s*년대/))) { const d = 1900 + (+m[1]) * 10; f.years = [d, d + 9]; }
    else if ((m = q.match(/(19\d\d|20\d\d)\s*년/))) f.years = [+m[1], +m[1]];
    if (/문학과\s*사회/.test(q)) f.coll = "mhs";
    const persons = []; let role = null; const used = new Set();
    for (const name of S.names) {
      let at = q.indexOf(name);
      while (at >= 0) {
        const a = at, b = at + name.length;
        let ok = ![...Array(b - a).keys()].some(x => used.has(a + x));
        if (ok) {
          const tail = q.slice(b, b + 4), tw = (tail.match(/^[가-힣]*/) || [""])[0];
          ok = name.length >= 3 || !/^[가-힣]/.test(tail) || strip(name + tw) === name;
          if (a > 0 && /[가-힣]/.test(q[a - 1])) ok = false;
        }
        if (ok) {
          const pid = S.name2pid.get(name); persons.push(pid); for (let x = a; x < b; x++) used.add(x);
          const rest = q.slice(b);
          if (/^\s*(이|가)\s*쓴|^의\s*(글|비평|평론)/.test(rest)) role = role || "필자";
          else if (/^\s*(을|를)?\s*(인용|원용|빌려|끌어)|^의\s*(이론|개념|사상)/.test(rest)) role = role || "이론";
          else if (/^\s*(론|을\s*다룬|를\s*다룬|에\s*관한|에\s*대한|을\s*논한|를\s*논한)/.test(rest)) role = role || "대상";
          break;
        }
        at = q.indexOf(name, at + 1);
      }
    }
    const words = [], raw = [];
    for (let w of q.match(/[가-힣A-Za-z0-9·]+/g) || []) {
      w = w.replace(/^·+|·+$/g, ""); const w2 = strip(w);
      if (w2.length >= 2 && !STOP.has(w2) && !/^\d+년?대?$/.test(w2)) { words.push(w2); if (w !== w2 && !STOP.has(w)) raw.push(w); }
    }
    if (role === "필자" && persons.length && (S.D.P.get(persons[0]) || {}).wrote) f.critic = persons[0];
    return { filters: f, persons, role, words: [...new Set(words)], raw: [...new Set(raw)] };
  }

  function lexScores(words, { raw = [], body = {}, skip = new Set(), useBody = true } = {}) {
    const n = S.n, sc = new Float64Array(n), hits = new Map(), rare = new Map();
    const H = (i, k, v) => { if (!hits.has(i)) hits.set(i, {}); const h = hits.get(i); (h[k] = h[k] || []).push(v); };
    for (const t of words) {
      const tn = norm(t); if (tn.length < 2) continue;
      const exact = S.kw.get(tn) || new Set(), idf = Math.log(1 + n / (1 + exact.size));
      for (const i of exact) { sc[i] += idf; H(i, "exact", t); }
      for (let i = 0; i < n; i++) {
        if (S.head[i].includes(tn)) { sc[i] += 0.6 * idf; H(i, "title", t); }
        else if (S.conc[i].includes(tn) && !exact.has(i)) { sc[i] += 0.35 * idf; H(i, "concept_part", t); }
      }
    }
    const qg = counter(words.flatMap(bigrams));
    if (qg.size && BM25_W) {
      const k1 = 1.2, b = 0.75;
      S.bg.forEach((c, i) => {
        let dl = 0; c.forEach(v => dl += v); dl = dl || 1; let acc = 0;
        qg.forEach((_, g) => { const fq = c.get(g) || 0; if (fq) acc += (S.bgIdf.get(g) || 0) * fq * (k1 + 1) / (fq + k1 * (1 - b + b * dl / S.bgAvg)); });
        sc[i] += BM25_W * acc;
      });
    }
    if (useBody) {
      const seen = new Set();
      for (const w of [...raw, ...words]) {
        if (skip.has(w) || skip.has(strip(w)) || seen.has(w) || raw.some(r => r !== w && r.startsWith(w) && body[r])) continue;
        seen.add(w);
        const docs = body[w]; if (!docs) continue;
        const idf = Math.log(1 + n / docs.length);
        for (const r of docs) {
          const i = S.rowToEssay[r]; if (i == null) continue;
          sc[i] += BODYLEX_W * idf;
          if (docs.length <= 20) { const sw = strip(w); H(i, "body", ["만", "가", "도", "이", ""].includes(w.slice(sw.length)) ? w : sw); }
          if (docs.length <= 3 && w.length >= 3) rare.set(i, Math.min(RARE_BONUS, (rare.get(i) || 0) + RARE_BONUS / 2));
        }
      }
    }
    let mx = 0; for (const x of sc) if (x > mx) mx = x; mx = mx || 1;
    return { lex: Array.from(sc, x => x / mx), hits, rare };
  }

  function graphScores(persons, role) {
    const sc = new Float64Array(S.n);
    for (const pid of persons) {
      for (const [i, rel] of S.personArts.get(pid) || []) {
        let w;
        if (role === "필자") w = rel === "필자" ? 1 : 0.3;
        else if (role === "이론") w = rel === "이론" ? 1 : 0.5;
        else if (role === "대상") w = rel === "대상" ? 1 : 0.5;
        else w = (rel === "대상" || rel === "이론") ? 1 : 0.8;
        sc[i] += w;
      }
      const co = new Map();
      for (const [i] of S.personArts.get(pid) || []) for (const [p2] of S.artPersons[i]) if (p2 !== pid) co.set(p2, (co.get(p2) || 0) + 1);
      [...co].sort((a, b) => b[1] - a[1]).slice(0, 5).forEach(([p2]) => (S.personArts.get(p2) || []).forEach(([i]) => sc[i] += 0.08));
    }
    let mx = 0; for (const x of sc) if (x > mx) mx = x; mx = mx || 1;
    return Array.from(sc, x => x / mx);
  }

  async function api(q, words) {
    try {
      const r = await fetch(`/api/find?q=${encodeURIComponent(q)}&w=${encodeURIComponent(words.join(","))}`);
      if (!r.ok) return { v: null, body: {}, error: r.status === 429 ? "잠시 뒤 다시 시도해 주세요" : "검색 서버 응답 없음" };
      return await r.json();
    } catch (e) { return { v: null, body: {}, error: "검색 서버에 연결하지 못했습니다" }; }
  }

  async function find(q, D, k = 24, apiFn = api) {
    await init(D);
    const t0 = performance.now();
    q = q.trim().slice(0, 200);
    const P = parse(q);
    const pnames = P.persons.map(p => S.D.P.get(p).name);
    const A = await apiFn(q, [...new Set([...P.raw, ...P.words])]);
    // Worker 응답의 글 번호는 meta.ids 순서 → 화면 글 순서로
    if (!S.rowToEssay) { S.rowToEssay = S.meta.ids.map(id => { const i = S.essays.findIndex(e => e.id === id); return i < 0 ? null : i; }); }
    const n = S.n;
    let emb = new Array(n).fill(0), related = [], strong = [];
    if (A.v) {
      const qv = Float32Array.from(A.v);
      const doc = new Array(n).fill(-1), fld = new Array(n).fill(-1);
      S.essays.forEach((e, i) => {
        const r = S.row.get(e.id); if (r == null) return;
        doc[i] = dot(S.VEC, r, qv);
        fld[i] = Math.max(dot(S.VEC, S.N + r, qv), dot(S.VEC, 2 * S.N + r, qv), dot(S.VEC, 3 * S.N + r, qv));
      });
      const md = minmax(doc), mf = minmax(fld);
      emb = minmax(md.map((x, i) => LAYER[0] * x + LAYER[1] * mf[i]));
      const ws = new Float64Array(S.V); for (let r = 0; r < S.V; r++) ws[r] = dot(S.VOC, r, qv);
      const order = [...ws.keys()].sort((a, b) => ws[b] - ws[a]).slice(0, 60);
      const nq = norm(q);
      for (const r of order) {
        const t = S.meta.vocab.terms[r]; if (nq.includes(norm(t))) continue;
        const kind = S.meta.vocab.kinds[r];
        related.push({ t, s: Math.round(ws[r] * 1000) / 1000, n: S.meta.vocab.df[r], kind: kind === "c" ? "concept" : "person", id: kind.startsWith("p:") ? kind.slice(2) : null });
        if (ws[r] >= VOCAB_FLOOR && strong.length < 4) strong.push(t);
        if (related.length >= 10) break;
      }
    }
    let { lex, hits, rare } = lexScores([...P.words, ...pnames], { raw: P.raw, body: A.body || {}, skip: new Set(pnames) });
    if (strong.length) {
      const L2 = lexScores(strong, { useBody: false });
      lex = lex.map((x, i) => x + VOCAB_W * L2.lex[i]); const mx = Math.max(...lex) || 1; lex = lex.map(x => x / mx);
      L2.hits.forEach((h, i) => { if (!hits.has(i)) hits.set(i, {}); const t = hits.get(i); t.vocab = [...(t.vocab || []), ...Object.values(h).flat()]; });
    }
    const gr = graphScores(P.persons, P.role);
    let we = W_EMB, wl = W_LEX, wg = W_GRAPH;
    if (!A.v) { we = 0; wl = 0.75; wg = 0.25; }
    if (!P.persons.length) { we += wg * 0.6; wl += wg * 0.4; wg = 0; }
    else if (P.role === "필자") { we = A.v ? 0.25 : 0; wl = 0.15; wg = 0.60; }
    else if (P.role === "이론" || P.role === "대상") { we = A.v ? 0.45 : 0; wl = 0.20; wg = 0.35; }
    const total = emb.map((x, i) => we * x + wl * lex[i] + wg * gr[i] + (rare.get(i) || 0));
    const f = P.filters;
    const ok = (i, useYears = true) => {
      const e = S.essays[i], y = +e.year || 0;
      if (useYears && f.years && !(f.years[0] <= y && y <= f.years[1])) return false;
      if (f.coll && e.coll !== f.coll) return false;
      if (f.critic && e.critic !== f.critic) return false;
      return true;
    };
    const order = [...total.keys()].sort((a, b) => total[b] - total[a]);
    let picked = order.filter(i => ok(i));
    if (picked.length < 5 && f.years) picked = order.filter(i => ok(i, false));
    picked = picked.slice(0, k);
    const top = picked.length ? total[picked[0]] : 1;
    const results = picked.map(i => {
      const h = hits.get(i) || {}, e = S.essays[i], why = [];
      const ex = [...new Set(h.exact || [])], cps = ex.filter(x => S.conc[i].includes(norm(x))), pps = ex.filter(x => !cps.includes(x));
      if (cps.length) why.push("개념어 " + cps.join(", "));
      if (h.concept_part) why.push("개념어에 " + [...new Set(h.concept_part)].join("·"));
      const rels = P.persons.flatMap(p => S.artPersons[i].filter(([pp]) => pp === p).map(([, r]) => [S.D.P.get(p).name, r]));
      if (rels.length) why.push(rels.map(([nmv, r]) => `${nmv} ${r === "필자" ? "필자" : r === "대상" ? "다룸" : "인용"}`).join(" · "));
      else if (pps.length) why.push("인물 " + pps.join(", "));
      if (h.title) why.push("제목에 " + [...new Set(h.title)].join("·"));
      if (h.vocab) why.push("관련 어휘 " + [...new Set(h.vocab)].slice(0, 3).join("·"));
      if (h.body) why.push("본문에 「" + [...new Set(h.body)].slice(0, 3).join("·") + "」");
      if (!why.length) why.push("주제 유사");
      return { id: e.id, score: total[i], rel: Math.round(100 * total[i] / top), layers: { emb: emb[i], lex: lex[i], graph: gr[i] }, why };
    });
    return { q, filters: f, persons: P.persons.map(p => ({ id: p, name: S.D.P.get(p).name })), role: P.role, words: P.words,
      expanded: strong, related, weights: { emb: we, lex: wl, graph: wg }, results, n_candidates: picked.length ? [...total.keys()].filter(i => ok(i)).length : 0,
      ms: Math.round(performance.now() - t0), error: A.error || null };
  }
  return { init, find, parse, _state: () => S };
})();
if (typeof module !== "undefined") module.exports = FIND;
