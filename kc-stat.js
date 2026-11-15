// kcritic 방문 통계 알림 — 화면을 열 때와 머리말 검색을 할 때 /api/hit 에 한 줄을 보낸다(worker/index.js).
// 보내는 것: 화면 이름(경로), 이 탭에서 처음 연 화면인지, 들어온 사이트 이름, 휴대폰 여부, 검색어.
// 방문자 식별자·IP 는 쓰지 않는다. 관리자 브라우저는 '나'로 따로 센다 — 아무 화면이나 ?nostat=1 로 한 번 열면
// 그 브라우저에 표시가 남고(a:1, ?nostat=0 이면 지움), /api/admin 에 토큰으로 들어간 브라우저는 Worker 가 관리자 쿠키로 알아본다.
// 통계 화면(/api/admin)은 공개 화면에서 링크하지 않는다.
// kc.js shell() 과 kc-shell.js(예전 화면)가 이 파일을 불러온다.
(function () {
  if (window.kcStat) return;
  let admin = false, first = false;
  try {
    const ns = new URLSearchParams(location.search).get("nostat");
    if (ns === "1") localStorage.setItem("kc-nostat", "1"); else if (ns === "0") localStorage.removeItem("kc-nostat");
    admin = !!localStorage.getItem("kc-nostat");
  } catch (e) {}
  try { first = !sessionStorage.getItem("kc-v"); sessionStorage.setItem("kc-v", "1"); } catch (e) {}
  window.KC_NOSTAT = admin;
  const send = o => {
    if (location.hostname === "localhost" && !/[?&]stat=1/.test(location.search)) return;
    if (admin) o.a = 1;
    const body = JSON.stringify(o);
    try { if (navigator.sendBeacon && navigator.sendBeacon("/api/hit", body)) return; } catch (e) {}
    fetch("/api/hit", { method: "POST", body, keepalive: true }).catch(() => {});
  };
  window.kcStat = (t, k) => { k = String(k || "").trim(); if (k) send({ t, k }); };

  // 화면 이름: 개체 화면은 종류·id, 탐색 화면은 탭, 나머지는 경로(.html 없이)
  const q = new URLSearchParams(location.search);
  let k = location.pathname.replace(/\.html$/, "").replace(/\/index$/, "/") || "/";
  if (/^\/entity$/.test(k) && q.get("t") && q.get("id")) k = `entity:${q.get("t")}:${q.get("id")}`;
  else if (/^\/explore$/.test(k)) k = `explore:${q.get("p") || "essays"}`;
  let r = "";
  try { const h = new URL(document.referrer).hostname; if (h && h !== location.hostname) r = h; } catch (e) {}
  send({ t: "view", k, v: first ? 1 : 0, r, m: matchMedia("(max-width: 760px)").matches ? 1 : 0 });
  if (q.get("q") && /^\/explore$/.test(location.pathname.replace(/\.html$/, ""))) window.kcStat("search", q.get("q"));
})();
