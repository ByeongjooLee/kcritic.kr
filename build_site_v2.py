# -*- coding: utf-8 -*-
"""사이트 2판(탐색·개체 페이지·글 찾기) 데이터 — build.py 다음에 실행 (표준 라이브러리만)

  site/data/v2/essays.json    글: 제목·연도·필자·컬렉션·지면(호·쪽·난)·개념어·다룬 작가 id·인용 이론가 id
  site/data/v2/people.json    인물: 이름·영문·LOD 배지·역할별 편수(씀/다룸/인용)·등장 연도
  site/data/v2/concepts.json  개념어(2편 이상): 이름·편수·글 id
  site/data/v2/examples.json  글마다 개념어 하나에 예시 문장 하나 {글 id: {개념어: 문장}} — 개념어 화면에서만 읽는다
  site/data/v2/issues.json    『문학과사회』 호별 목차 — ../문학과사회/encode_ledger.json 이 있을 때만 다시 만든다(목차 서지만, 본문 없음)

원문 본문은 쓰지 않는다. 예외는 examples.json 의 개념어 예시 문장(개념어마다 한 문장, 연구자 결정 2026-10-23). 글 찾기 벡터(site/data/find/)는 find/build_find.py(GPU)로 따로 만든다.
"""
import json, os, sys, re, collections
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
os.chdir(HERE)
import build  # noqa: E402  (main() 은 __main__ 일 때만)

OUT = HERE / "site" / "data" / "v2"
OUT.mkdir(parents=True, exist_ok=True)
MHS = HERE.parent / "문학과사회"
WORKS = {"p-kim-hyon": "김현 전집", "p-00246": "유종호 전집", "p-00117": "김우창 전집", "p-hwang-hyonsan": "황현산 비평집"}


def fmt_pages(p):
    """쪽 표기 통일: 1308-1309,1317-1329 → 1308–1309·1317–1329"""
    p = re.sub(r"\s*[-~–]\s*", "–", str(p or "").strip())
    return re.sub(r"\s*[,·]\s*", "·", p)


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    ledger = {}
    lp = MHS / "encode_ledger.json"
    if lp.exists():
        ledger = json.loads(lp.read_text(encoding="utf-8"))
    section_of = {v["stem"]: v.get("section", "") for v in ledger.values() if v.get("stem")}

    essays, examples = [], {}
    for xml_path in sorted(Path("essays").glob("*.xml")):
        d = build.process(xml_path)
        # 개념어 화면: 글마다 개념어 하나에 그 개념어가 든 예시 문장 하나 (연구자 결정 2026-10-23)
        examples[d["stem"]] = {c["name"]: c["excerpt"] for c in d.get("concepts", [])[:12] if c.get("excerpt")}
        src = d["sources"][0] if d["sources"] else {}
        is_mhs = src.get("type") == "journal" and src.get("journal_or_book") == "문학과사회"
        aid = d["author_id"]
        essays.append({
            "id": d["stem"], "title": d["title"], "year": d["display_year"] or d["year"],
            "critic": aid, "critic_name": build._strip_parens(d["persons"].get(aid, {}).get("name", "")),
            "coll": "mhs" if is_mhs else "works-" + aid,
            "coll_name": "『문학과사회』" if is_mhs else WORKS.get(aid, "기타"),
            "venue": build._source_short(d["sources"]),
            "issue": int(src["issue"]) if is_mhs and str(src.get("issue", "")).isdigit() else None,
            "pages": fmt_pages(src.get("pages", "")) if is_mhs else "",
            "section": section_of.get(d["stem"], "") if is_mhs else "",
            "concepts": [c["name"] for c in d.get("concepts", [])][:12],
            "subjects": sorted(d["subjects"]), "theorists": sorted(d["theorists"]),
        })
    dump("essays.json", essays)
    dump("examples.json", examples)

    info = {}
    for f in ("critics", "writers", "thinkers"):
        for p in json.loads((HERE / "site" / "data" / (f + ".json")).read_text(encoding="utf-8")):
            r = info.setdefault(p["id"], {"id": p["id"], "name": p["name"], "en": p.get("en", ""), "lod": p.get("lod", [])})
            r["lod"] = r["lod"] or p.get("lod", [])
    roles = collections.defaultdict(lambda: {"wrote": 0, "discussed": 0, "cited": 0, "years": []})
    for e in essays:
        y = int(e["year"]) if str(e["year"]).isdigit() else None
        for pid, k in [(e["critic"], "wrote")] + [(p, "discussed") for p in e["subjects"]] + [(p, "cited") for p in e["theorists"]]:
            if pid and pid in info:
                roles[pid][k] += 1
                if y: roles[pid]["years"].append(y)
    people = []
    for pid, r in roles.items():
        ys = r.pop("years")
        people.append({**info[pid], **r, "from": min(ys) if ys else None, "to": max(ys) if ys else None})
    people.sort(key=lambda p: (-(p["wrote"] + p["discussed"] + p["cited"]), p["name"]))
    dump("people.json", people)

    cmap = collections.defaultdict(list)
    for e in essays:
        for c in set(e["concepts"]): cmap[c].append(e["id"])
    concepts = sorted(({"name": k, "n": len(v), "essays": sorted(v)} for k, v in cmap.items() if len(v) >= 2), key=lambda c: (-c["n"], c["name"]))
    dump("concepts.json", concepts)

    if ledger:
        inv = {}
        ip = MHS / "issues.json"
        if ip.exists():
            inv = {x["id"]: x for x in json.loads(ip.read_text(encoding="utf-8"))}
        published = {e["id"]: e for e in essays if e["coll"] == "mhs"}
        by_issue = collections.defaultdict(list)
        for v in ledger.values():
            if v.get("status") != "skipped": by_issue[v["issue"]].append(v)
        state = {"done": "인코딩 완료·미공개", "held": "검토 보류", "queued": "인코딩 예정", "encoding": "인코딩 중"}
        issues = []
        for iid in sorted(by_issue):
            meta = inv.get(iid, {})
            items = []
            for v in by_issue[iid]:
                e = published.get(v.get("stem"))
                pg = re.match(r"(\d+)", str(v.get("pages", "")))
                items.append({"author": v.get("author", ""), "title": v.get("title", ""), "section": v.get("section", ""),
                              "pages": e["pages"] if e else fmt_pages(v.get("pages", "")), "first": int(pg.group(1)) if pg else 0,
                              "stem": v["stem"] if e else None, "state": "공개" if e else state.get(v["status"], v["status"])})
            items.sort(key=lambda x: x["first"])
            issues.append({"id": iid, "no": meta.get("no", int(iid[:3])), "year": meta.get("year"), "season": meta.get("season"),
                           "n_public": sum(1 for x in items if x["stem"]), "items": items})
        dump("issues.json", issues)
    print(f"v2 data: 글 {len(essays)} · 인물 {len(people)} · 개념어 {len(concepts)}" + (f" · 호 {len(issues)}" if ledger else " · 호 목차는 기존 파일 유지"))


if __name__ == "__main__":
    main()
