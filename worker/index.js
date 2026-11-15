// kcritic Worker — 정적 사이트는 assets 가 그대로 내보내고, /api/* 만 이 코드가 받는다 (wrangler.jsonc run_worker_first).
//
// GET /api/find?q=질문&w=낱말,낱말
//   → { v: [1024 실수] (bge-m3 질문 벡터, 정규화), body: { 낱말: [글 번호…] } }
//   글 찾기 점수 계산은 브라우저(kc-find.js)가 공개 벡터(site/data/find/)로 한다. 여기서는
//   ① 질문 임베딩(Workers AI)과 ② 본문 희귀어 역색인 조회만 한다. 역색인은 원문에서 만든 것이라
//   공개 파일로 두지 않고 이 Worker 번들 안에만 둔다(worker/private/, git·자산 제외).
//   응답에는 질문에 들어 있던 낱말과 글 번호만 담긴다 — 원문 문장은 없다.
//
// POST /api/hit   방문 통계 알림(kc-stat.js 가 sendBeacon 으로 보냄) → D1 tally 표의 날짜·누구·항목별 건수 +1
// 화면(HTML) 요청   봇·크롤러는 화면 스크립트를 돌리지 않는 일이 많아, Worker 가 화면 요청을 먼저 받아 User-Agent 로 센다
//   (wrangler.jsonc run_worker_first 의 화면 경로들). 사람의 화면 요청은 세지 않고 그대로 넘긴다(사람은 /api/hit 로 센다).
// GET  /api/admin  관리자 통계 화면(공개 화면에서 링크하지 않음, 검색엔진 색인 금지). 토큰으로 들어가면 이 브라우저에
//   관리자 쿠키(HttpOnly)가 붙고, 그 뒤로 이 브라우저의 방문은 '나'로 따로 센다.
// GET  /api/stats  통계 숫자 — 관리자 쿠키 또는 Authorization: Bearer <STATS_TOKEN> 이 맞을 때만.
//   관리자 컴퓨터의 HTML 파일(저장소 밖)에서도 부를 수 있게 CORS 허용(토큰이 있어야 답하므로 출처는 묻지 않는다)
// 누구 구분: me = 관리자 쿠키 또는 ?nostat=1 로 표시한 브라우저(kc-stat.js) · bot = User-Agent · user = 나머지. IP 로 추측하지 않는다.
//   IP·방문자 식별자는 저장하지 않는다. IP 는 아래 분당 요청 상한을 셀 때 메모리에서만 잠깐 쓴다.
import ADMIN_HTML from "./admin.html";
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
// 봇 이름표: [User-Agent 패턴, 이름, 갈래]. 위에서부터 맞춰 본다. 사람 브라우저의 앱 표시(KAKAOTALK, NAVER(inapp))는 봇이 아니다.
const BOTS = [
  [/googlebot|google-inspectiontool|googleother|adsbot-google|mediapartners-google|storebot-google|google-extended|feedfetcher-google|apis-google/i, "Googlebot", "검색엔진"],
  [/bingbot|bingpreview|msnbot|adidxbot/i, "Bingbot", "검색엔진"],
  [/\byeti\b/i, "네이버 Yeti", "검색엔진"],
  [/daumoa|daum-?bot/i, "다음 Daumoa", "검색엔진"],
  [/applebot/i, "Applebot", "검색엔진"],
  [/duckduckbot|duckassistbot/i, "DuckDuckBot", "검색엔진"],
  [/baiduspider/i, "Baidu", "검색엔진"],
  [/yandex/i, "Yandex", "검색엔진"],
  [/seznambot|sogou|360spider|qwantbot|mojeekbot|coccocbot|petalbot/i, "기타 검색엔진", "검색엔진"],
  [/gptbot|chatgpt-user|oai-searchbot/i, "OpenAI", "AI"],
  [/claudebot|claude-user|claude-searchbot|anthropic-ai/i, "Anthropic", "AI"],
  [/perplexitybot|perplexity-user/i, "Perplexity", "AI"],
  [/bytespider/i, "ByteDance", "AI"],
  [/ccbot/i, "Common Crawl", "AI"],
  [/amazonbot/i, "Amazonbot", "AI"],
  [/meta-externalagent|meta-externalfetcher|facebookbot/i, "Meta AI", "AI"],
  [/elevenlabs/i, "ElevenLabs", "AI"],
  [/deepseekbot/i, "DeepSeek", "AI"],
  [/cohere-ai|diffbot|youbot|ai2bot|timpibot|imagesiftbot|omgili|keenablebot|shapbot|mistralai|novellum/i, "기타 AI 수집기", "AI"],
  [/facebookexternalhit|twitterbot|kakaotalk-scrap|slackbot|discordbot|telegrambot|linkedinbot|whatsapp|pinterest|line-poker|skypeuripreview|embedly|prefetch proxy/i, "링크 미리보기·미리 받기", "미리보기"],
  [/ahrefsbot|semrushbot|mj12bot|dotbot|dataforseobot|blexbot|serpstatbot|barkrowler|seokicks|zoominfobot/i, "SEO 수집기", "SEO 도구"],
  [/uptimerobot|pingdom|statuscake|site24x7|monitor|lighthouse|pagespeed|gtmetrix|paloaltonetworks|censys|expanse|zgrab|masscan|nmap|internet-measurement/i, "점검·보안 스캐너", "점검"],
  [/headless|phantomjs|puppeteer|playwright|selenium|python|curl|wget|go-http-client|okhttp|axios|node-fetch|undici|java\/|libwww|httpclient|scrapy|ruby|php\/|^node$/i, "스크립트·자동화 도구", "자동화"],
  [/bot\b|bot\/|crawl|spider|slurp|scraper|fetcher|preview/i, "기타 봇", "기타"],
];
function botOf(ua) {
  if (!ua) return ["User-Agent 없음", "자동화"];
  for (const [re, name, cat] of BOTS) if (re.test(ua)) return [name, cat];
  if (!/mozilla|opera/i.test(ua)) return ["기타 봇", "기타"];   // 브라우저라면 거의 모두 Mozilla/… 로 시작한다
  return null;
}
// 들어온 곳 → 검색엔진·AI 유입 이름(나머지는 ref 로만 센다)
const ENGINES = [
  [/^scholar\.google\./, "검색엔진", "Google 학술검색"], [/^gemini\.google\.com$/, "AI", "Gemini"],
  [/^(google\.[a-z.]+|com\.google\.android\.googlequicksearchbox)$/, "검색엔진", "Google"],
  [/(^|\.)search\.naver\.com$/, "검색엔진", "네이버"], [/(^|\.)search\.daum\.net$/, "검색엔진", "다음"],
  [/(^|\.)bing\.com$/, "검색엔진", "Bing"], [/(^|\.)duckduckgo\.com$/, "검색엔진", "DuckDuckGo"],
  [/(^|\.)search\.yahoo\.|^yahoo\./, "검색엔진", "Yahoo"], [/(^|\.)baidu\.com$/, "검색엔진", "Baidu"],
  [/(^|\.)yandex\./, "검색엔진", "Yandex"], [/(^|\.)ecosia\.org$/, "검색엔진", "Ecosia"],
  [/(^|\.)search\.nate\.com$/, "검색엔진", "네이트"], [/(^|\.)search\.zum\.com$/, "검색엔진", "ZUM"],
  [/(^|\.)(chatgpt\.com|chat\.openai\.com)$/, "AI", "ChatGPT"], [/(^|\.)perplexity\.ai$/, "AI", "Perplexity"],
  [/^claude\.ai$/, "AI", "Claude"], [/^copilot\.microsoft\.com$/, "AI", "Copilot"],
];
const clean = (s, n) => String(s ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, n);
const VIEW_KEY = /^(\/[\w\-./%가-힣]{0,120}|entity:[a-z]{2,12}:[^\s]{1,100}|explore:[a-z]{1,20})$/;
const HOST = /^[a-z0-9.-]{3,80}$/;
function viewKey(url) {                 // kc-stat.js 의 화면 이름과 같은 규칙
  const q = url.searchParams;
  let k = url.pathname.replace(/\.html$/, "").replace(/\/index$/, "/") || "/";
  if (k === "/entity" && q.get("t") && q.get("id")) k = `entity:${q.get("t")}:${q.get("id")}`;
  else if (k === "/explore") k = `explore:${q.get("p") || "essays"}`;
  k = clean(k, 160);
  return VIEW_KEY.test(k) ? k : null;
}
function bump(env, ctx, who, rows) {      // rows: [[kind, k], …] — 오늘 날짜의 건수를 1씩 올린다
  if (!env.DB || !rows.length) return;
  const d = DAY(), st = env.DB.prepare("INSERT INTO tally (day, who, kind, k, n) VALUES (?1, ?2, ?3, ?4, 1) ON CONFLICT (day, who, kind, k) DO UPDATE SET n = n + 1");
  ctx.waitUntil(env.DB.batch(rows.map(([kind, k]) => st.bind(d, who, kind, k))).catch(e => console.log("stats write failed", String(e))));
}
// 관리자 쿠키 — 값은 토큰 자체가 아니라 토큰에서 만든 해시(토큰을 바꾸면 예전 쿠키는 저절로 무효)
const COOKIE = "kc_admin";
let adminHash = null, adminHashOf = null;
async function adminValue(env) {
  if (!env.STATS_TOKEN) return null;
  if (adminHashOf !== env.STATS_TOKEN) {
    const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("kcritic-admin:" + env.STATS_TOKEN));
    adminHash = [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join(""); adminHashOf = env.STATS_TOKEN;
  }
  return adminHash;
}
async function isAdmin(request, env) {
  const m = (request.headers.get("cookie") || "").match(/(?:^|;\s*)kc_admin=([0-9a-f]{64})/);
  return !!m && sameToken(m[1], await adminValue(env));
}
async function handleHit(request, env, ctx) {
  if (request.method !== "POST") return new Response(null, { status: 405 });
  if (botOf(request.headers.get("user-agent") || "")) return new Response(null, { status: 204 });   // 봇은 화면 요청에서 이미 셌다
  if (limited(request.headers.get("cf-connecting-ip") || "?")) return new Response(null, { status: 204 });
  let b;
  try { const t = await request.text(); if (t.length > 2000) throw 0; b = JSON.parse(t); } catch { return new Response(null, { status: 400 }); }
  const who = b.a || await isAdmin(request, env) ? "me" : "user";
  const rows = [];
  if (b.t === "view") {
    const k = clean(b.k, 160);
    if (!VIEW_KEY.test(k)) return new Response(null, { status: 400 });
    rows.push(["view", k]);
    if (b.v) {                            // 이 탭에서 처음 연 화면 = 새 방문
      rows.push(["visit", ""], ["device", b.m ? "휴대폰" : "PC"], ["country", clean(request.cf?.country || "?", 4)]);
      const r = clean(b.r, 80).toLowerCase().replace(/^www\./, "");
      if (r && HOST.test(r) && !r.endsWith("kcritic.kr")) {
        rows.push(["ref", r]);
        const e = ENGINES.find(([re]) => re.test(r));
        rows.push(["engine", e ? `${e[1]}:${e[2]}` : "기타:다른 사이트"]);
      } else rows.push(["engine", "기타:직접 입력·북마크·알 수 없음"]);
    }
  } else if (b.t === "search") {
    const k = clean(b.k, 60);
    if (!k) return new Response(null, { status: 400 });
    rows.push(["search", k]);
  } else return new Response(null, { status: 400 });
  bump(env, ctx, who, rows);
  return new Response(null, { status: 204 });
}
function countPage(request, env, ctx, url) {   // 화면 요청: 봇만 센다
  if (request.method !== "GET" && request.method !== "HEAD") return;
  const bot = botOf(request.headers.get("user-agent") || "");
  if (!bot) return;
  const k = url.pathname === "/robots.txt" ? "/robots.txt" : viewKey(url);
  bump(env, ctx, "bot", [["agent", `${bot[1]}:${bot[0]}`], ...(k ? [["view", k]] : [])]);
}
const CORS = { "access-control-allow-origin": "*", "access-control-allow-headers": "authorization", "access-control-allow-methods": "GET, OPTIONS", "access-control-max-age": "86400" };
async function pageNames(env, origin, keys) {   // 통계 키 → 사람이 읽는 이름(인물 이름·글 제목)
  if (!keys.some(k => /^entity:(person|essay):|^\/site\//.test(k))) return {};
  const get = async p => { try { const r = await env.ASSETS.fetch(new Request(origin + p)); return r.ok ? await r.json() : []; } catch { return []; } };
  const [people, essays] = await Promise.all([get("/site/data/v2/people.json"), get("/site/data/v2/essays.json")]);
  const P = new Map(people.map(x => [x.id, x.name])), E = new Map(essays.map(x => [x.id, x.title]));
  const out = {};
  for (const k of keys) {
    let m = k.match(/^entity:(person|essay):(.+)$/);
    if (m) { let id = m[2]; try { id = decodeURIComponent(id); } catch {} const v = m[1] === "person" ? P.get(id) : E.get(id); if (v) out[k] = v; continue; }
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
  const viaCookie = await isAdmin(request, env);
  if (!viaCookie && !sameToken(tok, env.STATS_TOKEN)) return json({ error: "관리자 토큰이 맞지 않습니다" }, 401, CORS);
  if (!env.DB) return json({ error: "통계 저장소(D1)가 연결되어 있지 않습니다" }, 500, CORS);
  const days = Math.max(1, Math.min(400, parseInt(url.searchParams.get("days") || "30", 10) || 30));
  const since = DAY(Date.now() - (days - 1) * 86400e3);
  let daily, tops;
  try {
    [daily, tops] = await Promise.all([
      env.DB.prepare("SELECT day, who, kind, SUM(n) AS n FROM tally WHERE day >= ?1 AND kind IN ('view','visit','agent') GROUP BY day, who, kind ORDER BY day").bind(since).all(),
      env.DB.prepare("SELECT who, kind, k, SUM(n) AS n FROM tally WHERE day >= ?1 AND kind <> 'visit' GROUP BY who, kind, k ORDER BY n DESC").bind(since).all(),
    ]);
  } catch (e) {
    return json({ error: "통계 표(tally)를 읽지 못했습니다 — worker/stats.sql 을 D1 에 한 번 실행했는지 확인해 주세요", detail: String(e).slice(0, 200) }, 500, CORS);
  }
  const top = {};                         // top[who][kind] = [[k, n], …] (종류마다 많은 순 200개)
  for (const r of tops.results) { const w = (top[r.who] ||= {}); (w[r.kind] ||= []).length < 200 && w[r.kind].push([r.k, r.n]); }
  ctx.waitUntil(env.DB.prepare("DELETE FROM tally WHERE day < ?1").bind(DAY(Date.now() - 430 * 86400e3)).run().catch(() => {}));   // 14개월 넘은 기록은 지운다
  const keys = new Set(); for (const w of Object.values(top)) for (const [k] of w.view || []) keys.add(k);
  const names = await pageNames(env, url.origin, [...keys]);
  return json({ since, today: DAY(), days, me: viaCookie, daily: daily.results, top, names }, 200, CORS);
}
// 관리자 화면 — 껍데기 HTML 만 내보내고(숫자 없음), 숫자는 화면이 /api/stats 로 읽는다
const ADMIN_HEADERS = { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "x-robots-tag": "noindex, nofollow", "referrer-policy": "no-referrer", "x-frame-options": "DENY" };
async function handleAdmin(request, env, url) {
  const secure = url.protocol === "https:" ? "; Secure" : "";
  if (url.pathname === "/api/admin/login" && request.method === "POST") {
    if (limited(request.headers.get("cf-connecting-ip") || "?")) return new Response("잠시 후 다시 시도해 주세요", { status: 429 });
    let tok = "";
    try { tok = String((await request.formData()).get("token") || "").trim(); } catch {}
    if (!sameToken(tok, env.STATS_TOKEN)) return new Response(null, { status: 303, headers: { location: "/api/admin?e=1", "cache-control": "no-store" } });
    return new Response(null, { status: 303, headers: { location: "/api/admin", "cache-control": "no-store",
      "set-cookie": `${COOKIE}=${await adminValue(env)}; Path=/api; Max-Age=34560000; HttpOnly; SameSite=Strict${secure}` } });
  }
  if (url.pathname === "/api/admin/logout" && request.method === "POST")
    return new Response(null, { status: 303, headers: { location: "/api/admin", "cache-control": "no-store", "set-cookie": `${COOKIE}=; Path=/api; Max-Age=0; HttpOnly; SameSite=Strict${secure}` } });
  if (url.pathname === "/api/admin" && (request.method === "GET" || request.method === "HEAD")) return new Response(ADMIN_HTML, { headers: ADMIN_HEADERS });
  return new Response("not found", { status: 404 });
}

const json = (obj, status = 200, extra = {}) => new Response(JSON.stringify(obj), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra } });

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/api/hit") return handleHit(request, env, ctx);
    if (url.pathname === "/api/stats") return request.method === "OPTIONS" ? new Response(null, { status: 204, headers: CORS }) : handleStats(request, env, ctx, url);
    if (url.pathname === "/api/admin" || url.pathname.startsWith("/api/admin/")) return handleAdmin(request, env, url);
    if (url.pathname !== "/api/find") {
      if (!env.ASSETS) return new Response("not found", { status: 404 });
      const res = await env.ASSETS.fetch(request);
      if (!url.pathname.startsWith("/api/") && (res.status < 300 || res.status === 404)) countPage(request, env, ctx, url);   // 화면 요청(run_worker_first): 봇만 센다. .html→깨끗한 주소 넘김(307)은 한 번만 세려고 뺀다
      return res;
    }
    if (request.method !== "GET") return json({ error: "GET only" }, 405);
    const q = (url.searchParams.get("q") || "").trim();
    if (!q || q.length > MAX_Q) return json({ error: `질문은 1~${MAX_Q}자` }, 400);
    const words = [...new Set((url.searchParams.get("w") || "").split(",").map(s => s.trim())
      .filter(s => s.length >= 2 && s.length <= MAX_W_LEN))].slice(0, MAX_WORDS);
    const ip = request.headers.get("cf-connecting-ip") || "?";
    if (limited(ip)) return json({ error: "잠시 후 다시 시도해 주세요" }, 429, { "retry-after": "30" });
    if (!botOf(request.headers.get("user-agent") || "")) {   // 통합검색(search.html)과 글 찾기(explore)를 나눠 센다. ns=1: ?nostat=1 표시 브라우저
      let from = ""; try { from = new URL(request.headers.get("referer") || "").pathname; } catch {}
      bump(env, ctx, url.searchParams.has("ns") || await isAdmin(request, env) ? "me" : "user", [[/^\/search(\.html)?$/.test(from) ? "usearch" : "find", clean(q, 80)]]);
    }

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
