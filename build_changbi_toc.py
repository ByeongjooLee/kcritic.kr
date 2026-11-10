# -*- coding: utf-8 -*-
"""『창작과비평』 호별 목차 → site/data/v2/issues_cb.json (표준 라이브러리만, 2026-11-09)

입력: ../문학과사회/changbi_corpus/data/{issues,toc}.jsonl (창비 웹진 목차 수집본)
      ../문학과사회/changbi_corpus/summary/plan.json (기사별 범위 판정 — 창작 여부)
출력: 목차 서지만(표제·필자·난·창비 웹진 기사 번호). 본문·요약은 싣지 않는다.
  site/data/v2/issues_cb.json       호 목록 [{id:"cb001", no:통권, label, year, season, list:웹진 호 번호, n:항목 수, n_crit:비평·산문 수}]
  site/data/v2/issues_cb_items.json 호별 항목 {"cb001": [{s:순서, sec:난, t:표제, a:필자, i:웹진 Item 번호, c:1(시·소설·희곡 등 창작)}]}
입력 폴더가 없으면 기존 파일을 그대로 둔다(빌드 체인에서 실패하지 않게).
"""
import json, os, sys, tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
CB = HERE.parent / "문학과사회" / "changbi_corpus"
OUT = HERE / "site" / "data" / "v2" / "issues_cb.json"
OUT_ITEMS = HERE / "site" / "data" / "v2" / "issues_cb_items.json"


def main():
    if not (CB / "data" / "toc.jsonl").exists():
        print(f"창비 목차 입력 없음({CB}) — {OUT.name} 유지")
        return
    rd = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    iss = {r["issue_id"]: r for r in rd(CB / "data" / "issues.jsonl")}
    creative = {}
    plan = CB / "summary" / "plan.json"
    if plan.exists():
        for x in json.loads(plan.read_text(encoding="utf-8"))["items"]:
            creative[str(x["item_id"])] = 0 if x["in_scope"] else 1
    rows = {}
    for r in rd(CB / "data" / "toc.jsonl"):
        it = {"s": int(r["sequence"]), "sec": (r["category"] or "").strip(), "t": (r["title"] or "").strip(),
              "a": (r["author"] or "").strip(), "i": int(r["item_id"])}
        if creative.get(str(r["item_id"])): it["c"] = 1
        rows.setdefault(r["issue_id"], []).append(it)
    out = []
    for iid in sorted(iss, key=lambda k: iss[k]["volume"]):
        i = iss[iid]
        items = sorted(rows.get(iid, []), key=lambda x: x["s"])
        label = i["label"].split("] ", 1)[-1]
        out.append({"id": f"cb{i['volume']:03d}", "no": i["volume"], "label": label, "year": i["year"],
                    "season": i["season"] or "부정기간", "list": int(iid), "n": len(items),
                    "n_crit": sum(1 for x in items if not x.get("c")), "items": items})
    # 호 목록(가벼움, 모든 탐색 화면이 읽음)과 항목(호 화면에서만 읽음)을 나눠 쓴다
    write(OUT_ITEMS, {x["id"]: x.pop("items") for x in out})
    write(OUT, out)
    import build_changbi_search; build_changbi_search.main()   # 검색 색인(cb_search.json)도 같이 갱신
    print(f"창비 목차: 호 {len(out)} · 항목 {sum(x['n'] for x in out)} · 비평·산문 {sum(x['n_crit'] for x in out)} → {OUT.relative_to(HERE)}, {OUT_ITEMS.name}")


def write(path, obj):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


if __name__ == "__main__":
    main()
