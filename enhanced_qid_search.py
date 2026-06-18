"""
2차 QID 검색 — 1차(suggest_qid_fixes)에서 후보를 못 찾은 인물을 영문명/정확명으로 재검색.

대부분 유명 외국 문인·이론가인데 한글 음역 검색이 실패한 경우다.
각 인물의 알려진 검색어(영문명 또는 정확 한글명)를 주고, 라이브 Wikidata에서
Q5(인간)+문학/학술 직업+이름유사도로 검증하여 QID를 확정한다.

출력: qid_fix_round2.csv (apply_qid_fixes.py 호환 컬럼)
persons.json 은 수정하지 않음.
"""

import json
import re
import csv
import sys
import time
import urllib.request
import urllib.parse
from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding="utf-8")

PERSONS = "persons.json"
OUT = "qid_fix_round2.csv"
UA = {"User-Agent": "kcritic-verify/1.0 (bj3632@gmail.com)"}
API = "https://www.wikidata.org/w/api.php"

# slug -> (검색어, 언어). 모델이 아는 인물명을 검색어로 제공 (QID는 라이브 검증으로 확정)
HINTS = {
    # 수동 24 (외국 문인·이론가 + 김영랑)
    "p-houellebecq":   ("Michel Houellebecq", "en"),
    "p-day-lewis":     ("Cecil Day-Lewis", "en"),
    "p-gourmont":      ("Remy de Gourmont", "en"),
    "p-lamb-charles":  ("Charles Lamb", "en"),
    "p-sainte-beuve":  ("Charles Augustin Sainte-Beuve", "en"),
    "p-verlaine":      ("Paul Verlaine", "en"),
    "p-louise-colet":  ("Louise Colet", "en"),
    "p-taine":         ("Hippolyte Taine", "en"),
    "p-korzybski":     ("Alfred Korzybski", "en"),
    "p-babbitt-irving":("Irving Babbitt", "en"),
    "p-balazs":        ("Etienne Balazs", "en"),
    "p-empson":        ("William Empson", "en"),
    "p-hazlitt":       ("William Hazlitt", "en"),
    "p-herbert-read":  ("Herbert Read", "en"),
    "p-kim-yeongnang": ("김영랑", "ko"),
    "p-levy-bruhl":    ("Lucien Levy-Bruhl", "en"),
    "p-lubbock-percy": ("Percy Lubbock", "en"),
    "p-maugham":       ("Somerset Maugham", "en"),
    "p-stevens":       ("Wallace Stevens", "en"),
    "p-swift":         ("Jonathan Swift", "en"),
    "p-warren":        ("Austin Warren", "en"),
    "p-wellek":        ("Rene Wellek", "en"),
    "p-yeats":         ("William Butler Yeats", "en"),
    "p-lafontaine":    ("Jean de La Fontaine", "en"),
    # 중간 — 제안 미심쩍어 재확정
    "p-stevenson":     ("Robert Louis Stevenson", "en"),
    "p-yoo-jongho":    ("유종호 평론가", "ko"),
}

INTELLECTUAL_KW = [
    "작가", "시인", "소설", "수필", "극작", "평론", "비평", "문학", "저술", "저자",
    "번역", "산문", "철학", "사상", "학자", "교수", "역사", "사회학", "인류학",
    "심리", "정신분석", "언어학", "미학", "신학", "정치학", "경제", "과학",
    "writer", "poet", "novelist", "philosopher", "critic", "essayist", "scholar",
    "historian", "professor", "author", "playwright", "translator", "anthropologist",
    "sociologist", "linguist", "theologian", "logician", "semantic",
]


def api_get(params):
    params = dict(params, format="json")
    url = API + "?" + urllib.parse.urlencode(params)
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.loads(r.read())
        except Exception:
            if a == 3:
                raise
            time.sleep(2 * (a + 1))
    return {}


def chunked(s, n):
    for i in range(0, len(s), n):
        yield s[i:i + n]


def nospace(s):
    return re.sub(r"\s|·|-|\.", "", s or "").lower()


def claim_qids(e, p):
    out = []
    for c in e.get("claims", {}).get(p, []):
        try:
            out.append(c["mainsnak"]["datavalue"]["value"]["id"])
        except (KeyError, TypeError):
            pass
    return out


def fetch_labels(qids):
    out = {}
    for b in chunked(sorted(set(qids)), 50):
        d = api_get({"action": "wbgetentities", "ids": "|".join(b),
                     "props": "labels", "languages": "ko|en"})
        for q, e in d.get("entities", {}).items():
            la = e.get("labels", {})
            out[q] = (la.get("ko") or la.get("en") or {}).get("value", q)
    return out


def main():
    persons = json.load(open(PERSONS, encoding="utf-8"))

    # 1) 검색 → 후보 수집
    cand = {}
    for slug, (term, lang) in HINTS.items():
        d = api_get({"action": "wbsearchentities", "search": term,
                     "language": lang, "uselang": lang, "limit": 8, "type": "item"})
        cand[slug] = [h["id"] for h in d.get("search", [])]

    # 2) 후보 엔티티 일괄 조회
    allq = [q for cs in cand.values() for q in cs]
    ents = {}
    for b in chunked(sorted(set(allq)), 50):
        d = api_get({"action": "wbgetentities", "ids": "|".join(b),
                     "props": "labels|aliases|descriptions|claims|sitelinks",
                     "languages": "ko|en"})
        ents.update(d.get("entities", {}))
    occ_labels = fetch_labels([q for e in ents.values() for q in claim_qids(e, "P106")])

    # 3) 채점
    rows = []
    for slug, (term, lang) in HINTS.items():
        kname = nospace(re.sub(r"[\(（][^)）]*[\)）]", "", persons.get(slug, {}).get("label", "")))
        tname = nospace(term)
        best = None
        for q in cand.get(slug, []):
            e = ents.get(q)
            if not e or "Q5" not in claim_qids(e, "P31"):
                continue
            labs = e.get("labels", {})
            ko_l = (labs.get("ko") or {}).get("value", "")
            en_l = (labs.get("en") or {}).get("value", "")
            aliases = [a["value"] for a in e.get("aliases", {}).get("en", [])] + \
                      [a["value"] for a in e.get("aliases", {}).get("ko", [])]
            desc = (e.get("descriptions", {}).get("ko") or
                    e.get("descriptions", {}).get("en") or {}).get("value", "")
            occs = [occ_labels.get(x, x) for x in claim_qids(e, "P106")]
            sl = len(e.get("sitelinks", {}))
            # 이름 유사도: 검색어(영/한) 및 한글라벨 대비
            ns = 0.0
            for n in [en_l, ko_l] + aliases:
                if not n:
                    continue
                ns = max(ns, SequenceMatcher(None, tname, nospace(n)).ratio())
                if kname:
                    ns = max(ns, SequenceMatcher(None, kname, nospace(n)).ratio())
            occ_text = " ".join(occs).lower() + " " + desc.lower()
            occ_hit = any(k.lower() in occ_text for k in INTELLECTUAL_KW)
            score = ns + (0.5 if occ_hit else 0) + min(sl, 60) / 60 * 0.5
            c = (score, ns, occ_hit, q, ko_l, en_l, ", ".join(occs), desc, sl)
            if best is None or c[0] > best[0]:
                best = c
        cur = persons.get(slug, {}).get("wikidata", "")
        if best and best[1] >= 0.55 and best[2]:
            conf = "높음" if best[1] >= 0.85 else "중간"
            rows.append([conf, slug, persons[slug]["label"], "round2",
                         cur, "", best[3], best[4], best[5], best[6], best[7],
                         round(best[1], 2), best[2], best[8],
                         f"https://www.wikidata.org/wiki/{best[3]}"])
        else:
            rows.append(["수동", slug, persons.get(slug, {}).get("label", ""), "round2",
                         cur, "", "", "", "", "", "", "", "", "", ""])

    order = {"높음": 0, "중간": 1, "수동": 2}
    rows.sort(key=lambda r: order.get(r[0], 9))
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["신뢰도", "슬러그", "저장이름", "기존플래그", "기존QID", "기존가리킴",
                    "제안QID", "제안한글", "제안영문", "제안직업", "제안설명",
                    "이름유사도", "직업적합", "언어판수", "제안링크"])
        w.writerows(rows)

    from collections import Counter
    cc = Counter(r[0] for r in rows)
    print("=== 2차 검색 결과 ===")
    for c in ["높음", "중간", "수동"]:
        print(f"  {c}: {cc.get(c,0)}건")
    print(f"\n출력: {OUT}\n")
    for r in rows:
        if r[0] in ("높음", "중간"):
            print(f"  [{r[0]}] {r[2]:16s} {r[4]:11s} → {r[6]:11s} "
                  f"{r[7] or r[8]} | {r[9][:32]} (유사도{r[11]}, 언어판{r[13]})")
    print("\n  --- 수동(여전히 못 찾음) ---")
    for r in rows:
        if r[0] == "수동":
            print(f"    {r[2]}  (현재 {r[4]})")


if __name__ == "__main__":
    main()
