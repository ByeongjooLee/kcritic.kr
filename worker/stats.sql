-- kcritic 방문 통계 (D1 kcritic-stats). 날짜(한국 시각)·종류·항목별 건수만 쌓는다 — IP·방문자 식별자 없음.
-- 처음 한 번: npx wrangler d1 execute kcritic-stats --remote --file worker/stats.sql   (로컬 시험은 --local)
-- kind: view(페이지) · visit(새 방문, k='') · ref(들어온 사이트) · device · country · search(머리말 검색어) · find(글 찾기 질문)
CREATE TABLE IF NOT EXISTS hits (
  day  TEXT NOT NULL,
  kind TEXT NOT NULL,
  k    TEXT NOT NULL,
  n    INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, kind, k)
);
