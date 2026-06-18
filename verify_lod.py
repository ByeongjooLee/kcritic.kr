"""
LOD 역검증 스크립트 — persons.json의 Wikidata QID + NLK URI 검증.

기존 검색(wbsearchentities) 방식의 동명이인·미발견 오류를 피하기 위해,
**이미 저장된 QID를 직접 조회(wbgetentities)** 하여 그게 진짜 맞는 인물인지 역검증한다.

검증 항목:
  1. QID 존재 여부 (삭제/리다이렉트 적발)
  2. 이름 일치 — 저장된 한글 이름이 실제 레이블/별칭에 존재하는가
  3. 직업(P106) — 문학·학술 계열 직업이 하나라도 있는가
  4. NLK ↔ Wikidata — 한국 인물의 NLK owl:sameAs QID가 저장 QID와 일치하는가

사용법 (critic-ontology/ 에서):
    py verify_lod.py

출력:
    verify_lod_result.csv   — 검토용 (의심 항목 상단 정렬)
    verify_lod_result.json  — 전체 상세 (재처리용)
"""

import json
import re
import sys
import glob
import os
import time
import urllib.request
import urllib.parse
from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding="utf-8")

PERSONS_JSON = "persons.json"
RDF_DIR = os.path.join("..", "Person_rdf_20260401")
OUT_CSV = "verify_lod_result.csv"
OUT_JSON = "verify_lod_result.json"

UA = {"User-Agent": "kcritic-verify/1.0 (bj3632@gmail.com)"}
API = "https://www.wikidata.org/w/api.php"

# 한국 인물 role (NLK 교차검증 대상)
KOREAN_ROLES = {"critic", "poet", "novelist", "writer", "other"}

# 문학·학술·지식인 계열 직업 키워드 (직업 레이블 한글에 대해 부분일치)
# 비평에 인용되는 이론가는 매우 폭넓음(철학자/과학자/정신분석가 등)이므로 넓게 잡는다.
INTELLECTUAL_KW = [
    "작가", "시인", "소설", "수필", "극작", "평론", "비평", "문학", "저술", "저자",
    "번역", "산문", "편집", "언론", "기자", "출판",
    "철학", "사상", "학자", "교수", "교육", "연구",
    "역사", "사회학", "인류학", "심리", "정신분석", "언어학", "미학", "신학", "종교",
    "정치학", "경제", "법학", "법률",
    "과학", "수학", "물리", "화학", "생물", "천문", "의학", "박물", "박식",
    "예술", "화가", "음악", "작곡", "조각", "미술", "영화", "감독", "건축",
    "성직", "사제", "목사", "승려", "수도",
]


def api_get(params):
    """Wikidata API GET (재시도 포함)."""
    params = dict(params, format="json")
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except Exception as ex:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    return {}


def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def clean_name(label):
    """라벨에서 괄호·한자·로마자 제거 → 순수 한글 이름."""
    s = re.sub(r"[\(（][^)）]*[\)）]", "", label)
    return s.strip()


def fetch_entities(qids):
    """QID 목록 → {qid: entity} (50개씩 배치)."""
    out = {}
    for batch in chunked(qids, 50):
        data = api_get({
            "action": "wbgetentities",
            "ids": "|".join(batch),
            "props": "labels|aliases|descriptions|claims",
            "languages": "ko|en",
        })
        out.update(data.get("entities", {}))
    return out


def fetch_labels(qids):
    """QID 목록 → {qid: 한글or영문 레이블} (직업명 번역용)."""
    out = {}
    uniq = sorted(set(qids))
    for batch in chunked(uniq, 50):
        data = api_get({
            "action": "wbgetentities",
            "ids": "|".join(batch),
            "props": "labels",
            "languages": "ko|en",
        })
        for qid, e in data.get("entities", {}).items():
            labs = e.get("labels", {})
            out[qid] = (labs.get("ko") or labs.get("en") or {}).get("value", qid)
    return out


def claim_qids(entity, prop):
    """엔티티의 특정 프로퍼티에서 대상 QID 목록 추출."""
    res = []
    for c in entity.get("claims", {}).get(prop, []):
        try:
            dv = c["mainsnak"]["datavalue"]["value"]
            res.append(dv["id"])
        except (KeyError, TypeError):
            pass
    return res


def claim_time_year(entity, prop):
    """P569/P570 등 시간 프로퍼티에서 연도 추출."""
    for c in entity.get("claims", {}).get(prop, []):
        try:
            t = c["mainsnak"]["datavalue"]["value"]["time"]  # +1749-08-28T00:00:00Z
            m = re.search(r"([+-]?\d{1,5})-", t)
            if m:
                return str(int(m.group(1)))
        except (KeyError, TypeError):
            pass
    return ""


def build_nlk_index(target_uris):
    """RDF 파일에서 지정된 NLK URI들의 owl:sameAs Wikidata QID 추출."""
    if not target_uris:
        return {}
    want = set(target_uris)
    index = {}
    files = sorted(glob.glob(os.path.join(RDF_DIR, "*.rdf")))
    if not files:
        print(f"  [경고] NLK RDF 파일 없음: {RDF_DIR} — NLK 교차검증 건너뜀")
        return {}
    for path in files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for uri, block in re.findall(
            r'<nlon:Author rdf:about="([^"]+)">(.*?)</nlon:Author>',
            text, re.DOTALL,
        ):
            if uri not in want:
                continue
            qid = None
            for m in re.finditer(r'wikidata\.org/entity/(Q\d+)', block):
                qid = m.group(1)
            index[uri] = qid
        if len(index) >= len(want):
            break
    return index


def main():
    persons = json.load(open(PERSONS_JSON, encoding="utf-8"))
    print(f"persons.json: {len(persons)}명")

    with_qid = [(s, r) for s, r in persons.items() if r.get("wikidata")]
    print(f"Wikidata QID 보유: {len(with_qid)}명 — 역조회 중...")

    qids = [r["wikidata"] for _, r in with_qid]
    entities = fetch_entities(qids)

    # 직업 QID → 한글 레이블 번역 테이블 구축
    occ_qids = []
    for e in entities.values():
        occ_qids += claim_qids(e, "P106")
    print(f"직업(P106) 종류 {len(set(occ_qids))}개 레이블 조회 중...")
    occ_labels = fetch_labels(occ_qids)

    # NLK 교차검증 인덱스
    nlk_uris = [r["nlk"] for _, r in persons.items() if r.get("nlk")]
    print(f"NLK URI 보유: {len(nlk_uris)}명 — RDF 교차검증 인덱스 구축 중...")
    nlk_index = build_nlk_index(nlk_uris)

    results = []
    for slug, rec in with_qid:
        qid = rec["wikidata"]
        label = rec["label"]
        kname = clean_name(label)
        e = entities.get(qid)

        rdata = {
            "slug": slug, "label": label, "role": rec.get("role", ""),
            "qid": qid, "ko_label": "", "en_label": "", "desc": "",
            "occupations": "", "birth": "", "death": "",
            "nlk": rec.get("nlk") or "", "nlk_qid": "", "flags": [],
        }

        if e is None or "missing" in e:
            rdata["flags"].append("NOT_FOUND")
            results.append(rdata)
            continue

        labs = e.get("labels", {})
        ko_label = (labs.get("ko") or {}).get("value", "")
        en_label = (labs.get("en") or {}).get("value", "")
        ko_aliases = [a["value"] for a in e.get("aliases", {}).get("ko", [])]
        descs = e.get("descriptions", {})
        desc = (descs.get("ko") or descs.get("en") or {}).get("value", "")
        occs = [occ_labels.get(q, q) for q in claim_qids(e, "P106")]
        instance_of = claim_qids(e, "P31")

        rdata.update({
            "ko_label": ko_label, "en_label": en_label, "desc": desc,
            "occupations": ", ".join(occs),
            "birth": claim_time_year(e, "P569"),
            "death": claim_time_year(e, "P570"),
        })

        # --- 1) 인간(Q5) 여부 ---
        if instance_of and "Q5" not in instance_of:
            rdata["flags"].append("NOT_HUMAN")

        # --- 2) 이름 일치 ---
        name_pool = [ko_label] + ko_aliases
        nospace = lambda s: re.sub(r"\s|·|-", "", s or "")
        ks = nospace(kname)
        # (a) 부분일치 (공백·중점·하이픈 무시)
        name_hit = any(ks and (ks in nospace(n) or nospace(n) in ks)
                       for n in name_pool if n)
        # (b) 유사도 — 음역 변이(줄리아/쥘리아, 로런스/로렌스) 구제
        best_ratio = max(
            (SequenceMatcher(None, ks, nospace(n)).ratio()
             for n in name_pool if n), default=0.0)
        rdata["name_ratio"] = round(best_ratio, 2)
        if not name_hit:
            if not ko_label:
                rdata["flags"].append("NO_KO_LABEL")     # 외국인, ko 레이블 없음
            elif best_ratio >= 0.5:
                rdata["flags"].append("NAME_VARIANT")     # 음역 변이 추정 (대체로 정상)
            else:
                rdata["flags"].append("NAME_MISMATCH")    # 진짜 불일치

        # --- 3) 직업 ---
        occ_text = " ".join(occs) + " " + desc
        has_intellectual = any(kw in occ_text for kw in INTELLECTUAL_KW)
        if occs and not has_intellectual:
            rdata["flags"].append("OCCUPATION_REVIEW")
        elif not occs and not desc:
            rdata["flags"].append("NO_OCCUPATION")

        # --- 4) NLK ↔ Wikidata ---
        if rec.get("nlk"):
            nlk_qid = nlk_index.get(rec["nlk"])
            rdata["nlk_qid"] = nlk_qid or ""
            if nlk_qid and nlk_qid != qid:
                rdata["flags"].append("NLK_QID_CONFLICT")
            elif rec["nlk"] not in nlk_index:
                rdata["flags"].append("NLK_URI_NOT_IN_RDF")

        results.append(rdata)

    # 의심 항목 상단 정렬: 플래그 많은 순
    severity = {
        "NOT_FOUND": 100, "NAME_MISMATCH": 90, "NLK_QID_CONFLICT": 80,
        "NOT_HUMAN": 70, "OCCUPATION_REVIEW": 50, "NLK_URI_NOT_IN_RDF": 30,
        "NAME_VARIANT": 25, "NO_KO_LABEL": 20, "NO_OCCUPATION": 15,
    }
    results.sort(key=lambda r: -sum(severity.get(f, 10) for f in r["flags"]))

    # CSV 출력 (Excel용 BOM)
    import csv
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["상태", "슬러그", "저장이름", "role", "QID",
                    "한글레이블", "영문레이블", "직업", "생", "몰",
                    "설명", "NLK_QID", "링크"])
        for r in results:
            w.writerow([
                "; ".join(r["flags"]) or "OK",
                r["slug"], r["label"], r["role"], r["qid"],
                r["ko_label"], r["en_label"], r["occupations"],
                r["birth"], r["death"], r["desc"], r["nlk_qid"],
                f"https://www.wikidata.org/wiki/{r['qid']}",
            ])

    json.dump(results, open(OUT_JSON, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # 요약
    from collections import Counter
    flag_count = Counter()
    ok = 0
    for r in results:
        if not r["flags"]:
            ok += 1
        for fl in r["flags"]:
            flag_count[fl] += 1
    print("\n=== 검증 요약 ===")
    print(f"정상(OK): {ok} / {len(results)}")
    for fl, c in flag_count.most_common():
        print(f"  {fl}: {c}건")
    print(f"\n검토용 CSV: {OUT_CSV}")
    print(f"상세 JSON:  {OUT_JSON}")

    # 가장 의심스러운 상위 15건 콘솔 출력
    print("\n=== 의심 상위 15건 ===")
    for r in results[:15]:
        if not r["flags"]:
            break
        print(f"  [{'; '.join(r['flags'])}] {r['label']} ({r['qid']}) "
              f"→ {r['ko_label'] or r['en_label']} | {r['occupations'][:40]} | {r['desc'][:40]}")


if __name__ == "__main__":
    main()
