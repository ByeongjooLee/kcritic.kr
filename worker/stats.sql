-- kcritic 방문 통계 (D1 kcritic-stats). 날짜(한국 시각)·누구·종류·항목별 건수만 쌓는다 — IP·방문자 식별자 없음.
-- 처음 한 번: npx wrangler d1 execute kcritic-stats --remote --config wrangler.jsonc --file worker/stats.sql   (로컬 시험은 --local)
-- who : me(관리자 쿠키 또는 ?nostat=1 표시가 있는 브라우저) · bot(User-Agent 로 알아본 봇·크롤러·자동화 도구) · user(일반 접속자)
-- kind: view(화면) · visit(새 방문, k='') · ref(들어온 사이트) · engine(검색엔진·AI 유입) · device · country
--       search(머리말 검색어) · usearch(통합검색 search.html) · find(글 찾기 질문) · agent(봇 이름, who='bot' 만)
-- 예전 hits 표(누구 구분 없음)는 원격에 만들어진 적이 없다(2026-11-15 확인) — 옮길 기록이 없다.
CREATE TABLE IF NOT EXISTS tally (
  day  TEXT NOT NULL,
  who  TEXT NOT NULL,
  kind TEXT NOT NULL,
  k    TEXT NOT NULL,
  n    INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, who, kind, k)
);
