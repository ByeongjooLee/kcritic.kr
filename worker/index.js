// kcritic Worker — 정적 사이트는 assets 가 그대로 내보내고, /api/* 만 이 코드가 받는다 (wrangler.jsonc run_worker_first).
//
// GET /api/find?q=질문&w=낱말,낱말
//   → { v: [1024 실수] (bge-m3 질문 벡터, 정규화), body: { 낱말: [글 번호…] } }
//   글 찾기 점수 계산은 브라우저(kc-find.js)가 공개 벡터(site/data/find/)로 한다. 여기서는
//   ① 질문 임베딩(Workers AI)과 ② 본문 희귀어 역색인 조회만 한다. 역색인은 원문에서 만든 것이라
//   공개 파일로 두지 않고 이 Worker 번들 안에만 둔다(worker/private/, git·자산 제외).
//   응답에는 질문에 들어 있던 낱말과 글 번호만 담긴다 — 원문 문장은 없다.
//
// POST /api/hit   방문 통계 알림(kc-stat.js 가 sendBeacon 으로 보냄) → D1 hits 표의 날짜·항목별 건수 +1
// GET  /api/stats 관리자 통계 — Authorization: Bearer <STATS_TOKEN 비밀값> 이 맞을 때만. 통계 화면은 사이트에 올리지 않고
//   관리자 컴퓨터의 HTML 파일(저장소 밖)에서 부른다 → CORS 허용(토큰이 있어야 답하므로 출처는 묻지 않는다)
//   IP·방문자 식별자는 저장하지 않는다. IP 는 아래 분당 요청 상한을 셀 때 메모리에서만 잠깐 쓴다.
import SHARDS from "./private/shards.js";

const MODEL = "@cf/baai/bge-m3";
const MAX_Q = 200, MAX_WORDS = 40, MAX_W_LEN = 30;
const RATE = 30;                       // 같은 IP 분당 요청 (Worker 인스턴스별, 느슨한 상한)
const hits = new Map();

function fnv(s) {                      // find/build_find.py 의 fnv() 와 같아야 한다 (UTF-16 코드 단위)
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
  return h >>> 0;
}
function lookup(word) {
  const shard = SHARDS[fnv(word) % SHARDS.length];
  const key = "\n" + word + "\t";
  const at = shard.indexOf(key);
  if (at < 0) return null;
  const end = shard.indexOf("\n", at + key.length);
  return shard.slice(at + key.length, end < 0 ? undefined : end).split(",").map(Number);
}
function limited(ip) {
  const now = Date.now(), win = 60000;
  const arr = (hits.get(ip) || []).filter(t => now - t < win);
  arr.push(now); hits.set(ip, arr);
  if (hits.size > 5000) hits.clear();
  return arr.length > RATE;
}
// ── 방문 통계 ──
const DAY = (ms = Date.now()) => new Date(ms + 9 * 3600e3).toISOString().slice(0, 10);   // 한국 날짜
const BOT = /bot|crawl|spider|slurp|preview|headless|lighthouse|monitor|python|curl|wget/i;
const clean = (s, n) => String(s ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, n);
const VIEW_KEY = /^(\/[\w\-./%가-힣]{0,120}|entity:(essay|person|concept|issue):[^\s]{1,100}|explore:[a-z]{1,20})$/;
const HOST = /^[a-z0-9.-]{3,80}$/;
function bump(env, ctx, rows) {           // rows: [[kind, k], …] — 오늘 날짜의 건수를 1씩 올린다
  if (!env.DB || !rows.length) return;
  const d = DAY(), st = env.DB.prepare("INSERT INTO hits (day, kind, k, n) VALUES (?1, ?2, ?3, 1) ON CONFLICT (day, kind, k) DO UPDATE SET n = n + 1");
  ctx.waitUntil(env.DB.batch(rows.map(([kind, k]) => st.bind(d, kind, k))).catch(() => {}));
}
async function handleHit(request, env, ctx) {
  if (request.method !== "POST") return new Response(null, { status: 405 });
  if (BOT.test(request.headers.get("user-agent") || "")) return new Response(null, { status: 204 });
  if (limited(request.headers.get("cf-connecting-ip") || "?")) return new Response(null, { status: 204 });
  let b;
  try { const t = await request.text(); if (t.length > 2000) throw 0; b = JSON.parse(t); } catch { return new Response(null, { status: 400 }); }
  const rows = [];
  if (b.t === "view") {
    const k = clean(b.k, 160);
    if (!VIEW_KEY.test(k)) return new Response(null, { status: 400 });
    rows.push(["view", k]);
    if (b.v) {                            // 이 탭에서 처음 연 화면 = 새 방문
      rows.push(["visit", ""], ["device", b.m ? "휴대폰" : "PC"], ["country", clean(request.cf?.country || "?", 4)]);
      const r = clean(b.r, 80).toLowerCase().replace(/^www\./, "");
      if (r && HOST.test(r) && !r.endsWith("kcritic.kr")) rows.push(["ref", r]);
    }
  } else if (b.t === "search") {
    const k = clean(b.k, 60);
    if (!k) return new Response(null, { status: 400 });
    rows.push(["search", k]);
  } else return new Response(null, { status: 400 });
  bump(env, ctx, rows);
  return new Response(null, { status: 204 });
}
const CORS = { "access-control-allow-origin": "*", "access-control-allow-headers": "authorization", "access-control-allow-methods": "GET, OPTIONS", "access-control-max-age": "86400" };
async function pageNames(env, origin, keys) {   // 통계 키 → 사람이 읽는 이름(인물 이름·글 제목)
  const get = async p => { try { const r = await env.ASSETS.fetch(new Request(origin + p)); return r.ok ? await r.json() : []; } catch { return []; } };
  const [people, essays] = await Promise.all([get("/site/data/v2/people.json"), get("/site/data/v2/essays.json")]);
  const P = new Map(people.map(x => [x.id, x.name])), E = new Map(essays.map(x => [x.id, x.title]));
  const out = {};
  for (const k of keys) {
    let m = k.match(/^entity:(person|essay):(.+)$/);
    if (m) { const v = m[1] === "person" ? P.get(m[2]) : E.get(m[2]); if (v) out[k] = v; continue; }
    m = k.match(/^\/site\/(critics|writers|thinkers|essays)\/(.+)$/);
    if (m) { let id = m[2]; try { id = decodeURIComponent(id); } catch {} const v = P.get(id) || E.get(id); if (v) out[k] = v; }
  }
  return out;
}
function sameToken(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  let x = 0; for (let i = 0; i < a.length; i++) x |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return x === 0;
}
async function handleStats(request, env, ctx, url) {
  const tok = (request.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  if (!sameToken(tok, env.STATS_TOKEN)) return json({ error: "관리자 토큰이 맞지 않습니다" }, 401, CORS);
  if (!env.DB) return json({ error: "통계 저장소(D1)가 연결되어 있지 않습니다" }, 500, CORS);
  const days = Math.max(1, Math.min(400, parseInt(url.searchParams.get("days") || "30", 10) || 30));
  const since = DAY(Date.now() - (days - 1) * 86400e3);
  const [daily, tops] = await Promise.all([
    env.DB.prepare("SELECT day, kind, SUM(n) AS n FROM hits WHERE day >= ?1 AND kind IN ('view','visit') GROUP BY day, kind ORDER BY day").bind(since).all(),
    env.DB.prepare("SELECT kind, k, SUM(n) AS n FROM hits WHERE day >= ?1 AND kind <> 'visit' GROUP BY kind, k ORDER BY n DESC").bind(since).all(),
  ]);
  const top = {};
  for (const r of tops.results) (top[r.kind] ||= []).length < 60 && top[r.kind].push([r.k, r.n]);
  ctx.waitUntil(env.DB.prepare("DELETE FROM hits WHERE day < ?1").bind(DAY(Date.now() - 430 * 86400e3)).run().catch(() => {}));   // 14개월 넘은 기록은 지운다
  const names = await pageNames(env, url.origin, (top.view || []).map(([k]) => k));
  return json({ since, today: DAY(), days, daily: daily.results, top, names }, 200, CORS);
}

const json = (obj, status = 200, extra = {}) => new Response(JSON.stringify(obj), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra } });

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/api/hit") return handleHit(request, env, ctx);
    if (url.pathname === "/api/stats") return request.method === "OPTIONS" ? new Response(null, { status: 204, headers: CORS }) : handleStats(request, env, ctx, url);
    if (url.pathname !== "/api/find") {
      return env.ASSETS ? env.ASSETS.fetch(request) : new Response("not found", { status: 404 });
    }
    if (request.method !== "GET") return json({ error: "GET only" }, 405);
    const q = (url.searchParams.get("q") || "").trim();
    if (!q || q.length > MAX_Q) return json({ error: `질문은 1~${MAX_Q}자` }, 400);
    const words = [...new Set((url.searchParams.get("w") || "").split(",").map(s => s.trim())
      .filter(s => s.length >= 2 && s.length <= MAX_W_LEN))].slice(0, MAX_WORDS);
    const ip = request.headers.get("cf-connecting-ip") || "?";
    if (limited(ip)) return json({ error: "잠시 후 다시 시도해 주세요" }, 429, { "retry-after": "30" });
    if (!url.searchParams.has("ns") && !BOT.test(request.headers.get("user-agent") || "")) bump(env, ctx, [["find", clean(q, 80)]]);   // ns: 관리자 브라우저

    const cacheKey = new Request(`https://kcritic.kr/api/find?q=${encodeURIComponent(q)}&w=${encodeURIComponent(words.join(","))}`);
    const cache = caches.default;
    const hit = await cache.match(cacheKey);
    if (hit) return hit;

    const body = {};
    for (const w of words) { const d = lookup(w); if (d) body[w] = d; }
    let v = null, error = null;
    try {
      const r = await env.AI.run(MODEL, { text: [q] });
      const x = r && r.data && r.data[0];
      if (x) { let s = 0; for (const a of x) s += a * a; s = Math.sqrt(s) || 1; v = x.map(a => Math.round(a / s * 1e5) / 1e5); }
    } catch (e) { error = "embedding unavailable"; }      // Workers AI 한도·장애: 브라우저가 낱말·관계망만으로 계속한다
    const res = json({ v, body, error }, 200, { "cache-control": "public, max-age=86400" });
    if (v) ctx.waitUntil(cache.put(cacheKey, res.clone()));
    return res;
  },
};
