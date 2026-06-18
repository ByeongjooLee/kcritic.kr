"""
encykorea(한국민족문화대백과) 링크를 Wikidata P9475로 교차검증·교정.

검증된 QID에서 Wikidata P9475(Encyclopedia of Korean Culture ID)를 가져오면
그 인물의 정확한 encykorea E번호가 나온다(동명이인 불가). 이를 권위 소스로 삼아
persons.json의 encykorea와 대조.

분류:
  MISMATCH  : 저장값 ≠ Wikidata → 교정 필요 (자동 적용 대상)
  MISSING   : 저장값 없음, Wikidata 있음 → 추가 후보
  NO_WIKIDATA: 저장값 있음, Wikidata에 P9475 없음 → 수동 확인
  OK        : 일치

사용법:
    py verify_encykorea.py            # 미리보기
    py verify_encykorea.py --apply    # MISMATCH 교정 + MISSING 추가 (persons.json.bak 백업)
"""

import json
import re
import sys
import time
import urllib.request
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")

PERSONS = "persons.json"
UA = {"User-Agent": "kcritic-verify/1.0 (bj3632@gmail.com)"}
API = "https://www.wikidata.org/w/api.php"
APPLY = "--apply" in sys.argv
ENCY = "https://encykorea.aks.ac.kr/Article/"


def api_get(params):
    params = dict(params, format="json")
    url = API + "?" + urllib.parse.urlencode(params)
    for a in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.loads(r.read())
        except Exception:
            if a == 4:
                raise
            time.sleep(5 * (a + 1))
    return {}


def chunked(s, n):
    for i in range(0, len(s), n):
        yield s[i:i + n]


def p9475(entity):
    for c in entity.get("claims", {}).get("P9475", []):
        try:
            return c["mainsnak"]["datavalue"]["value"]
        except (KeyError, TypeError):
            pass
    return None


def e_num(url):
    m = re.search(r"(E\d+)", url or "")
    return m.group(1) if m else None


def main():
    persons = json.load(open(PERSONS, encoding="utf-8"))
    with_qid = [(s, r) for s, r in persons.items() if r.get("wikidata")]
    qids = [r["wikidata"] for _, r in with_qid]
    print(f"QID 보유 {len(with_qid)}명 — Wikidata P9475(한국민족문화대백과 ID) 조회 중...")

    ents = {}
    for b in chunked(qids, 50):
        d = api_get({"action": "wbgetentities", "ids": "|".join(b),
                     "props": "claims"})
        ents.update(d.get("entities", {}))
        time.sleep(0.3)

    mismatch, missing, no_wiki, ok = [], [], [], 0
    for slug, rec in with_qid:
        wiki_e = p9475(ents.get(rec["wikidata"], {}))
        stored_e = e_num(rec.get("encykorea"))
        if stored_e and wiki_e:
            if stored_e == wiki_e:
                ok += 1
            else:
                mismatch.append((slug, rec["label"], stored_e, wiki_e))
        elif stored_e and not wiki_e:
            no_wiki.append((slug, rec["label"], stored_e))
        elif not stored_e and wiki_e:
            missing.append((slug, rec["label"], wiki_e))

    print(f"\n=== 결과 ===  일치 {ok} / 불일치 {len(mismatch)} / 누락(추가가능) {len(missing)} / Wikidata無 {len(no_wiki)}")
    print(f"\n[MISMATCH — 저장값이 틀림, 교정 필요] {len(mismatch)}건")
    for slug, label, st, wk in mismatch:
        print(f"  {label:14s} 저장 {st} → Wikidata {wk}   (https://encykorea.aks.ac.kr/Article/{wk})")
    print(f"\n[MISSING — encykorea 없는데 Wikidata에 있음, 추가 가능] {len(missing)}건")
    for slug, label, wk in missing[:20]:
        print(f"  {label:14s} + {wk}")
    if len(missing) > 20:
        print(f"  ... 외 {len(missing)-20}건")
    print(f"\n[NO_WIKIDATA — 저장값 있으나 Wikidata에 P9475 없음, 수동 확인] {len(no_wiki)}건")
    for slug, label, st in no_wiki[:15]:
        print(f"  {label:14s} {st}")

    if APPLY:
        import shutil
        shutil.copy2(PERSONS, PERSONS + ".bak")
        n_fix = n_add = 0
        for slug, label, st, wk in mismatch:
            persons[slug]["encykorea"] = ENCY + wk
            n_fix += 1
        for slug, label, wk in missing:
            persons[slug]["encykorea"] = ENCY + wk
            n_add += 1
        json.dump(persons, open(PERSONS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        open(PERSONS, "a", encoding="utf-8").write("\n")
        print(f"\n적용: 교정 {n_fix}건 + 추가 {n_add}건 (백업 persons.json.bak)")
    else:
        print("\n(미리보기 — 적용: py verify_encykorea.py --apply)")


if __name__ == "__main__":
    main()
