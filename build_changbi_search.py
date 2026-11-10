# -*- coding: utf-8 -*-
"""『창작과비평』 낱말 검색 색인 → site/data/v2/cb_search.json (2026-11-10)

입력은 이미 공개한 파일만: site/data/v2/issues_cb.json · issues_cb_items.json · changbi_summaries.json.
창작(c=1)을 뺀 비평·산문 항목마다 한 줄: [웹진 Item 번호, 호 id, 연도, 표제, 필자, 난, 키워드("|" 로 이음), 요지]
— 키워드·요지는 검수 통과한 해제가 있는 글만. 해제·주장 전문은 넣지 않는다(호 화면에서만 읽음).
상단 검색·현장비평 글 찾기·통합검색이 이 파일 하나로 창비 글을 찾는다.

호별 해제 site/data/v2/cb_sum/<호 id>.json {웹진 Item: 해제} — 글 화면·호 화면이 그 호 것만 읽는다(2026-11-10, 전체 1MB 대신).
"""
import json
from pathlib import Path
from build_changbi_toc import write

HERE = Path(__file__).resolve().parent
V2 = HERE / "site" / "data" / "v2"
OUT = V2 / "cb_search.json"


def main():
    try:
        issues = json.loads((V2 / "issues_cb.json").read_text(encoding="utf-8"))
        items = json.loads((V2 / "issues_cb_items.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"창비 목차 파일 없음 — {OUT.name} 유지")
        return
    sp = V2 / "changbi_summaries.json"
    summ = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    rows, per_issue = [], {}
    for iss in issues:
        for it in items.get(iss["id"], []):
            if it.get("c"):
                continue
            s = summ.get(str(it["i"]))
            if s: per_issue.setdefault(iss["id"], {})[str(it["i"])] = s
            rows.append([it["i"], iss["id"], iss["year"], it["t"], it["a"], it["sec"],
                         "|".join(s["kw"]) if s else "", s["s"] if s else ""])
    write(OUT, rows)
    d = V2 / "cb_sum"
    d.mkdir(exist_ok=True)
    for old in d.glob("*.json"):
        if old.stem not in per_issue: old.unlink()   # 해제가 빠진 호의 옛 파일
    for iid, m in per_issue.items():
        write(d / f"{iid}.json", m)
    print(f"창비 검색 색인: {len(rows)}편(해제 있음 {sum(1 for r in rows if r[7])}) → {OUT.relative_to(HERE)} · 호별 해제 {len(per_issue)}개 → cb_sum/")


if __name__ == "__main__":
    main()
