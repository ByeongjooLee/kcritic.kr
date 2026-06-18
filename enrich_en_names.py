"""
persons.json 인물의 Wikidata 영문 레이블을 받아, 외국 인물에 한해 `en` 필드 추가.

분류: P27(국적)이 한국계가 아니면 외국 → en 표시. 한국계/한국 인물은 en 미표시.
  - 한국 판정: P27 레이블에 Korea/조선/한국/고려/대한/Joseon/Goryeo 포함, 또는 (P27 없고 NLK 보유)
미리보기만 출력(--apply 주면 persons.json에 en 필드 기록).

사용법:
    py enrich_en_names.py            # 미리보기
    py enrich_en_names.py --apply    # persons.json에 en 기록 (persons.json.bak 백업)
"""

import json
import sys
import time
import urllib.request
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")

PERSONS = "persons.json"
UA = {"User-Agent": "kcritic-verify/1.0 (bj3632@gmail.com)"}
API = "https://www.wikidata.org/w/api.php"
APPLY = "--apply" in sys.argv

KOREA_KW = ["korea", "조선", "한국", "고려", "대한", "joseon", "goryeo", "silla", "신라", "백제", "고구려"]


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


def claim_qids(e, p):
    out = []
    for c in e.get("claims", {}).get(p, []):
        try:
            out.append(c["mainsnak"]["datavalue"]["value"]["id"])
        except (KeyError, TypeError):
            pass
    return out


def main():
    persons = json.load(open(PERSONS, encoding="utf-8"))
    with_qid = [(s, r) for s, r in persons.items() if r.get("wikidata")]
    qids = [r["wikidata"] for _, r in with_qid]
    print(f"QID 보유 인물: {len(with_qid)}명 — 영문 레이블·국적 조회 중...")

    ents = {}
    for b in chunked(qids, 50):
        d = api_get({"action": "wbgetentities", "ids": "|".join(b),
                     "props": "labels|claims", "languages": "ko|en"})
        ents.update(d.get("entities", {}))
        time.sleep(0.3)

    # P27 국적 QID → 레이블
    cqids = sorted({q for e in ents.values() for q in claim_qids(e, "P27")})
    clabel = {}
    for b in chunked(cqids, 50):
        d = api_get({"action": "wbgetentities", "ids": "|".join(b),
                     "props": "labels", "languages": "ko|en"})
        for q, e in d.get("entities", {}).items():
            la = e.get("labels", {})
            clabel[q] = (la.get("en") or la.get("ko") or {}).get("value", q)
        time.sleep(0.3)

    foreign, korean, no_data = [], [], []
    updates = {}
    for slug, rec in with_qid:
        e = ents.get(rec["wikidata"], {})
        labs = e.get("labels", {})
        en = (labs.get("en") or {}).get("value", "")
        ko = (labs.get("ko") or {}).get("value", "")
        citiz = [clabel.get(q, "") for q in claim_qids(e, "P27")]
        is_korean = any(any(kw in c.lower() for kw in KOREA_KW) for c in citiz)
        if not citiz and rec.get("nlk"):
            is_korean = True  # 국적 미상 + NLK 보유 → 한국인 추정

        if is_korean:
            korean.append((slug, rec["label"], en, citiz))
        elif not en:
            no_data.append((slug, rec["label"]))
        else:
            foreign.append((slug, rec["label"], en, citiz))
            updates[slug] = en

    print(f"\n분류: 외국(en 표시) {len(foreign)} / 한국(미표시) {len(korean)} / 데이터없음 {len(no_data)}")
    print("\n=== 외국 인물 영문 병기 미리보기 (상위 30) ===")
    for slug, label, en, citiz in foreign[:30]:
        print(f"  {label}  ({en})   [{', '.join(citiz[:2])}]")
    print(f"  ... 외 {max(0, len(foreign)-30)}명")
    print("\n=== 한국 인물로 분류 (영문 미표시) 샘플 10 ===")
    for slug, label, en, citiz in korean[:10]:
        print(f"  {label}  (en={en})  [{', '.join(citiz[:2]) or 'NLK기반'}]")

    if APPLY:
        import shutil
        shutil.copy2(PERSONS, PERSONS + ".bak")
        for slug, en in updates.items():
            persons[slug]["en"] = en
        json.dump(persons, open(PERSONS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        open(PERSONS, "a", encoding="utf-8").write("\n")
        print(f"\n적용 완료: {len(updates)}명에 en 필드 기록 (백업 persons.json.bak)")
    else:
        print("\n(미리보기 모드 — 적용하려면 --apply)")


if __name__ == "__main__":
    main()
