# -*- coding: utf-8 -*-
"""『문학과사회』 글의 창비형 해제·요지·주장 → site/data/v2/mhs_sum/<호 id>.json (2026-11-14)

『창작과비평』 글 화면(cb_sum)과 같은 꼴로 『문학과사회』 글에도 요지·해제·주장·근거 구조를 붙인다.
입력: ../문학과사회/site_prep/mhs_summary/<stem>.json (save_mhs_summary.py 가 점검 통과분만 씀 — TEI 구조화 요약에서 작성)
  + site/data/v2/essays.json(build_site_v2.py 다음에 실행) 의 『문학과사회』 공개 글.
공개 필드는 창비와 같다: u t a y l s h kw c — kw 는 TEI 개념어(앞 7개). 원문은 싣지 않는다.
공개 전 다시 점검: 지금 XML 의 sha = 작성 때 sha(인코딩이 바뀌면 빠짐), 원문(TXT)과 공백·부호 빼고 20자 이상 일치 없음.
../문학과사회 폴더가 없으면(다른 PC) 기존 파일을 그대로 둔다.
사용: py build_mhs_summaries.py
"""
import hashlib
import json
import re
from pathlib import Path
from build_changbi_toc import write

HERE = Path(__file__).resolve().parent
V2 = HERE / "site" / "data" / "v2"
OUT = V2 / "mhs_sum"
MHS = HERE.parent / "문학과사회"
SRC = MHS / "site_prep" / "mhs_summary"
LABELS = {"주장", "논거", "비판", "제언"}


def norm(s):
    return re.sub(r"[\W_]+", "", s)


def verbatim(texts, body, n=20):
    b = norm(body)
    grams = {b[i:i + n] for i in range(len(b) - n + 1)}
    return [t for t in texts if any(norm(t)[i:i + n] in grams for i in range(len(norm(t)) - n + 1))]


def main():
    if not SRC.exists():
        print(f"{SRC} 없음 — mhs_sum/ 유지")
        return
    essays = [e for e in json.loads((V2 / "essays.json").read_text(encoding="utf-8")) if e.get("coll") == "mhs"]
    per_issue, skipped = {}, []
    for e in essays:
        p = SRC / f"{e['id']}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        xml = MHS / "essays" / f"{e['id']}.xml"
        if not xml.exists() or hashlib.sha1(xml.read_bytes()).hexdigest()[:12] != d["sha"]:
            skipped.append((e["id"], "인코딩이 바뀜 — 다시 작성"))
            continue
        texts = [d["s"], d["h"]] + [c[0] for c in d["c"]]
        if not all(isinstance(x, str) and x.strip() for x in texts) or any(c[1] not in LABELS for c in d["c"]):
            skipped.append((e["id"], "형식 오류"))
            continue
        txt = MHS / "essays" / f"{e['id']}.txt"
        if txt.exists() and verbatim(texts, txt.read_text(encoding="utf-8")):
            skipped.append((e["id"], "원문 20자 이상 일치"))
            continue
        if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|[A-Za-z]:[\\/]|file://|〔인용〕", " ".join(texts)):
            skipped.append((e["id"], "전자우편/경로/인용 표지"))
            continue
        iid = f"{e['issue']:03d}"
        per_issue.setdefault(iid, {})[e["id"]] = {
            "u": e["id"], "t": e["title"], "a": e["critic_name"], "y": int(str(e["year"])[:4]),
            "l": f"《문학과사회》 {e['issue']}호" + (f", {e['pages']}면" if e.get("pages") else ""),
            "s": d["s"], "h": d["h"], "kw": e["concepts"][:7], "c": d["c"]}
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.json"):
        if old.stem not in per_issue:
            old.unlink()
    for iid, m in sorted(per_issue.items()):
        write(OUT / f"{iid}.json", dict(sorted(m.items())))
    n = sum(len(m) for m in per_issue.values())
    print(f"『문학과사회』 해제: {n}/{len(essays)}편 → mhs_sum/ 호 {len(per_issue)}개" + (f" · 뺀 것 {len(skipped)}: {skipped[:5]}" if skipped else ""))


if __name__ == "__main__":
    main()
