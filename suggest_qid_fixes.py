"""
깨진 Wikidata QID에 대한 올바른 QID 후보 제안.

verify_lod_result.json 에서 NOT_HUMAN / NOT_FOUND / NAME_MISMATCH 로 분류된
항목만 대상으로, 엄격한 필터를 걸어 올바른 QID를 재검색한다.

엄격 필터 (동명이인 차단):
  1. instance_of(P31) 에 Q5(인간) 포함 — 사람만
  2. 직업(P106) 또는 설명이 문학·학술 키워드와 일치
  3. 이름 유사도 (한글 레이블 / 별칭 / 음역)

사용법 (critic-ontology/ 에서):
    py suggest_qid_fixes.py

출력:
    qid_fix_proposals.csv  — 검토용 (적용 전 사람이 확인)
persons.json 은 수정하지 않는다. 승인 후 별도 적용.
"""

import json
import re
import sys
import time
import urllib.request
import urllib.parse
from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding="utf-8")

VERIFY_JSON = "verify_lod_result.json"
PERSONS_JSON = "persons.json"
OUT_CSV = "qid_fix_proposals.csv"

UA = {"User-Agent": "kcritic-verify/1.0 (bj3632@gmail.com)"}
API = "https://www.wikidata.org/w/api.php"

TARGET_FLAGS = {"NOT_HUMAN", "NOT_FOUND", "NAME_MISMATCH"}

INTELLECTUAL_KW = [
    "작가", "시인", "소설", "수필", "극작", "평론", "비평", "문학", "저술", "저자",
    "번역", "산문", "편집", "언론", "기자", "출판",
    "철학", "사상", "학자", "교수", "교육", "연구",
    "역사", "사회학", "인류학", "심리", "정신분석", "언어학", "미학", "신학", "종교",
    "정치학", "경제", "법학", "법률",
    "과학", "수학", "물리", "화학", "생물", "천문", "의학", "박물", "박식",
    "예술", "화가", "음악", "작곡", "조각", "미술", "영화", "감독", "건축",
    "성직", "사제", "목사", "승려", "수도",
    "writer", "poet", "novelist", "philosopher", "critic", "essayist",
    "scholar", "historian", "professor", "author", "playwright", "translator",
    "sociologist", "anthropologist", "psycho", "linguist", "theologian",
    "painter", "artist", "composer", "director", "scientist", "academic",
]


def api_get(params):
    params = dict(params, format="json")
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    return {}


def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def nospace(s):
    return re.sub(r"\s|·|-|\.", "", s or "")


def split_label(label):
    """'프랜시스 퐁주(Francis Ponge)' → ('프랜시스 퐁주', 'Francis Ponge')."""
    m = re.search(r"[\(（]([^)）]*)[\)）]", label)
    paren = m.group(1).strip() if m else ""
    korean = re.sub(r"[\(（][^)）]*[\)）]", "", label).strip()
    # 괄호 안이 로마자면 영문 검색어로 사용
    roman = paren if re.search(r"[A-Za-z]", paren) else ""
    return korean, roman


def search(term, lang):
    data = api_get({
        "action": "wbsearchentities", "search": term, "language": lang,
        "uselang": lang, "limit": 10, "type": "item",
    })
    return [(h["id"], h.get("label", ""), h.get("description", ""))
            for h in data.get("search", [])]


def fetch_entities(qids):
    out = {}
    for batch in chunked(sorted(set(qids)), 50):
        data = api_get({
            "action": "wbgetentities", "ids": "|".join(batch),
            "props": "labels|aliases|descriptions|claims|sitelinks",
            "languages": "ko|en",
        })
        out.update(data.get("entities", {}))
    return out


# persons.json role → 기대 직업 키워드 (동명이인 판별 핵심)
ROLE_KW = {
    "poet": ["시인", "poet"],
    "novelist": ["소설", "작가", "novelist"],
    "critic": ["평론", "비평", "critic"],
    "writer": ["작가", "시인", "소설", "수필", "극작", "writer", "essayist"],
    "scholar": ["철학", "학자", "교수", "사회학", "인류학", "심리", "정신분석",
                "언어학", "역사", "신학", "미학", "사상", "과학", "수학", "이론",
                "philosopher", "scholar", "professor", "scientist"],
    "theorist": ["철학", "학자", "이론", "사상", "사회학", "비평", "philosopher"],
    "director": ["감독", "영화", "director"],
}


def claim_qids(entity, prop):
    res = []
    for c in entity.get("claims", {}).get(prop, []):
        try:
            res.append(c["mainsnak"]["datavalue"]["value"]["id"])
        except (KeyError, TypeError):
            pass
    return res


def fetch_labels(qids):
    out = {}
    for batch in chunked(sorted(set(qids)), 50):
        data = api_get({
            "action": "wbgetentities", "ids": "|".join(batch),
            "props": "labels", "languages": "ko|en",
        })
        for q, e in data.get("entities", {}).items():
            labs = e.get("labels", {})
            out[q] = (labs.get("ko") or labs.get("en") or {}).get("value", q)
    return out


def main():
    verify = json.load(open(VERIFY_JSON, encoding="utf-8"))
    persons = json.load(open(PERSONS_JSON, encoding="utf-8"))

    broken = [r for r in verify if set(r["flags"]) & TARGET_FLAGS]
    print(f"수정 대상(깨진 QID): {len(broken)}명 — 후보 검색 중...")

    # 1단계: 각 인물별 후보 QID 수집
    cand_map = {}      # slug -> [candidate qids]
    for r in broken:
        slug = r["slug"]
        korean, roman = split_label(r["label"])
        cands = []
        seen = set()
        queries = [(korean, "ko")]
        if roman:
            queries.append((roman, "en"))
        for term, lang in queries:
            if not term:
                continue
            for qid, lab, desc in search(term, lang):
                if qid not in seen:
                    seen.add(qid)
                    cands.append(qid)
        cand_map[slug] = cands

    # 2단계: 모든 후보 엔티티 한 번에 조회
    all_qids = [q for cs in cand_map.values() for q in cs]
    print(f"후보 엔티티 {len(set(all_qids))}개 조회 중...")
    ents = fetch_entities(all_qids)
    occ_qids = []
    for e in ents.values():
        occ_qids += claim_qids(e, "P106")
    occ_labels = fetch_labels(occ_qids)

    # 3단계: 채점
    rows = []
    for r in broken:
        slug = r["slug"]
        role = r.get("role", "")
        role_kw = ROLE_KW.get(role, [])
        korean, roman = split_label(r["label"])
        kpool = [nospace(korean)]
        rpool = nospace(roman).lower() if roman else ""

        best = None  # (score, name_score, occ_hit, role_hit, qid, ko, en, occ, desc, sl)
        for qid in cand_map.get(slug, []):
            e = ents.get(qid)
            if not e or "missing" in e:
                continue
            p31 = claim_qids(e, "P31")
            if "Q5" not in p31:            # 사람만
                continue
            labs = e.get("labels", {})
            ko_l = (labs.get("ko") or {}).get("value", "")
            en_l = (labs.get("en") or {}).get("value", "")
            aliases = ([a["value"] for a in e.get("aliases", {}).get("ko", [])] +
                       [a["value"] for a in e.get("aliases", {}).get("en", [])])
            descs = e.get("descriptions", {})
            desc = (descs.get("ko") or descs.get("en") or {}).get("value", "")
            occs = [occ_labels.get(q, q) for q in claim_qids(e, "P106")]
            sitelinks = len(e.get("sitelinks", {}))     # 유명도 prior

            # 이름 점수
            namepool = [ko_l, en_l] + aliases
            name_score = 0.0
            for n in namepool:
                if not n:
                    continue
                nn = nospace(n)
                name_score = max(name_score,
                                 SequenceMatcher(None, kpool[0], nn).ratio())
                if rpool and re.search(r"[A-Za-z]", n):
                    name_score = max(name_score,
                                     SequenceMatcher(None, rpool, nn.lower()).ratio())
            # 직업 점수
            occ_text = " ".join(occs).lower() + " " + desc.lower()
            occ_hit = any(kw.lower() in occ_text for kw in INTELLECTUAL_KW)
            role_hit = bool(role_kw) and any(kw.lower() in occ_text for kw in role_kw)

            # 종합: 이름 + 직업 + role일치(동명이인 판별) + 유명도
            score = (name_score
                     + (0.4 if occ_hit else 0)
                     + (1.2 if role_hit else 0)           # role 일치가 가장 강함
                     + min(sitelinks, 40) / 40 * 0.4)     # 유명도 prior
            cand = (score, name_score, occ_hit, role_hit, qid, ko_l, en_l,
                    ", ".join(occs), desc, sitelinks)
            if best is None or cand[0] > best[0]:
                best = cand

        if best and best[1] >= 0.45:      # 이름 유사도 최소 기준
            name_sim, occ_hit, role_hit, sl = best[1], best[2], best[3], best[9]
            # role 일치 + 이름 높으면 높음, role 불일치면 신뢰도 낮춤(동명이인 의심)
            if role_kw and not role_hit:
                conf = "중간" if name_sim >= 0.7 else "낮음"
            elif name_sim >= 0.7 and (occ_hit or not INTELLECTUAL_KW):
                conf = "높음"
            elif name_sim >= 0.55:
                conf = "중간"
            else:
                conf = "낮음"
            rows.append({
                "slug": slug, "label": r["label"], "flags": "; ".join(r["flags"]),
                "old_qid": r["qid"], "old_target": r["ko_label"] or r["en_label"],
                "new_qid": best[4], "new_ko": best[5], "new_en": best[6],
                "new_occ": best[7], "new_desc": best[8],
                "name_sim": round(name_sim, 2), "occ_ok": occ_hit,
                "role_ok": role_hit, "sitelinks": sl, "conf": conf,
            })
        else:
            rows.append({
                "slug": slug, "label": r["label"], "flags": "; ".join(r["flags"]),
                "old_qid": r["qid"], "old_target": r["ko_label"] or r["en_label"],
                "new_qid": "", "new_ko": "", "new_en": "", "new_occ": "",
                "new_desc": "", "name_sim": "", "occ_ok": "", "role_ok": "",
                "sitelinks": "", "conf": "수동",
            })

    # 신뢰도 정렬: 높음 → 중간 → 낮음 → 수동
    order = {"높음": 0, "중간": 1, "낮음": 2, "수동": 3}
    rows.sort(key=lambda x: order.get(x["conf"], 9))

    import csv
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["신뢰도", "슬러그", "저장이름", "기존플래그",
                    "기존QID", "기존가리킴", "제안QID", "제안한글", "제안영문",
                    "제안직업", "제안설명", "이름유사도", "직업적합", "role일치",
                    "언어판수", "제안링크"])
        for x in rows:
            w.writerow([
                x["conf"], x["slug"], x["label"], x["flags"],
                x["old_qid"], x["old_target"], x["new_qid"], x["new_ko"], x["new_en"],
                x["new_occ"], x["new_desc"], x["name_sim"], x["occ_ok"],
                x["role_ok"], x["sitelinks"],
                f"https://www.wikidata.org/wiki/{x['new_qid']}" if x["new_qid"] else "",
            ])

    from collections import Counter
    conf_c = Counter(x["conf"] for x in rows)
    print("\n=== 제안 요약 ===")
    for c in ["높음", "중간", "낮음", "수동"]:
        print(f"  {c}: {conf_c.get(c,0)}건")
    print(f"\n제안 CSV: {OUT_CSV}")

    print("\n=== 신뢰도 '높음' 제안 (적용 후보) ===")
    for x in rows:
        if x["conf"] != "높음":
            continue
        print(f"  {x['label']:20s} {x['old_qid']:11s}({x['old_target'][:8]}) "
              f"→ {x['new_qid']:11s} {x['new_ko'] or x['new_en']} | {x['new_occ'][:28]} "
              f"(언어판{x['sitelinks']})")
    print("\n=== 신뢰도 '중간' (role 불일치 등 — 동명이인 주의) ===")
    for x in rows:
        if x["conf"] != "중간":
            continue
        print(f"  {x['label']:20s} → {x['new_qid']:11s} {x['new_ko'] or x['new_en']} "
              f"| {x['new_occ'][:28]} (role일치={x['role_ok']}, 언어판{x['sitelinks']})")


if __name__ == "__main__":
    main()
