// kcritic Worker — 정적 사이트는 assets 가 그대로 내보내고, /api/* 만 이 코드가 받는다 (wrangler.jsonc run_worker_first).
//
// GET /api/find?q=질문&w=낱말,낱말
//   → { v: [1024 실수] (bge-m3 질문 벡터, 정규화), body: { 낱말: [글 번호…] } }
//   글 찾기 점수 계산은 브라우저(kc-find.js)가 공개 벡터(site/data/find/)로 한다. 여기서는
//   ① 질문 임베딩(Workers AI)과 ② 본문 희귀어 역색인 조회만 한다. 역색인은 원문에서 만든 것이라
//   공개 파일로 두지 않고 이 Worker 번들 안에만 둔다(worker/private/, git·자산 제외).
//   응답에는 질문에 들어 있던 낱말과 글 번호만 담긴다 — 원문 문장은 없다.
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
const json = (obj, status = 200, extra = {}) => new Response(JSON.stringify(obj), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra } });

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
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
