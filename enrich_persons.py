"""
enrich_persons.py — persons.json 외부 식별자 자동 채우기
실행: py enrich_persons.py [--nlk] [--aks] [--all]

채우는 필드:
  nlk        국립중앙도서관 LOD URI  (한국 인물만)
  encykorea  한국민족문화대백과사전 항목 URL  (한국 인물만)
  wikidata   Wikidata Q번호  (현재는 수동 관리)
  isni       ISNI 식별자  (현재는 수동 관리)
"""
import json, time, urllib.request, urllib.parse, os, sys, argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

NLK_API_KEY = os.getenv("NLK_API_KEY", "")
AKS_API_KEY = os.getenv("AKS_API_KEY", "")
PERSONS_FILE = Path("persons.json")

NLK_URL = "https://apis.data.go.kr/1371029/AuthorInformationService/getAuthorInformationSrch"
AKS_URL = "https://devin.aks.ac.kr:8080/api/articles/search"

# 한국 인물 role (외국 인물 제외)
KOREAN_ROLES = {"critic", "poet", "novelist", "writer", "other"}


# ── NLK ────────────────────────────────────────────────────────

def query_nlk(name: str) -> str | None:
    """저자명 → NLK LOD URI. 완전 일치 우선, 없으면 첫 결과."""
    if not NLK_API_KEY:
        return None
    params = urllib.parse.urlencode({
        "serviceKey": NLK_API_KEY,
        "authNm": name,
        "pageNo": 1,
        "numOfRows": 5,
        "type": "json",
    })
    try:
        req = urllib.request.Request(
            f"{NLK_URL}?{params}",
            headers={"User-Agent": "kcritic-ontology/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        items = (data.get("response", {})
                     .get("body", {})
                     .get("items", {})
                     .get("item", []))
        if isinstance(items, dict):
            items = [items]
        if not items:
            return None
        for item in items:
            if item.get("authNm", "").strip() == name:
                aid = item.get("authNo") or item.get("authId") or item.get("id")
                if aid:
                    return f"https://lod.nl.go.kr/resource/KAC{str(aid).zfill(8)}"
        first = items[0]
        aid = first.get("authNo") or first.get("authId") or first.get("id")
        return f"https://lod.nl.go.kr/resource/KAC{str(aid).zfill(8)}" if aid else None
    except Exception as e:
        print(f"    [NLK 오류] {e}")
        return None


# ── AKS (한국민족문화대백과사전) ────────────────────────────────

def query_aks(name: str) -> str | None:
    """저자명 → 민족문화대백과사전 항목 URL. 인물 항목 완전 일치 우선."""
    if not AKS_API_KEY:
        return None
    params = urllib.parse.urlencode({"q": name, "p": 1, "ps": 5})
    try:
        req = urllib.request.Request(
            f"{AKS_URL}?{params}",
            headers={
                "X-API-Key": AKS_API_KEY,
                "User-Agent": "kcritic-ontology/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        items = data.get("items", [])
        if not items:
            return None
        # 인물 항목 + 이름 완전 일치 우선
        for item in items:
            hw = item.get("headword", "").strip()
            ptype = item.get("primaryTypePartA", "")
            if hw == name and ptype == "인물":
                return item["url"]
        # 완전 일치 없으면 인물 항목 중 첫 번째
        for item in items:
            if item.get("primaryTypePartA") == "인물":
                return item["url"]
        return None
    except Exception as e:
        print(f"    [AKS 오류] {e}")
        return None


# ── 메인 ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="persons.json 외부 식별자 자동 채우기")
    parser.add_argument("--nlk", action="store_true", help="NLK LOD URI 채우기")
    parser.add_argument("--aks", action="store_true", help="민족문화대백과 URL 채우기")
    parser.add_argument("--all", action="store_true", help="NLK + AKS 모두")
    args = parser.parse_args()

    do_nlk = args.nlk or args.all
    do_aks = args.aks or args.all

    if not do_nlk and not do_aks:
        parser.print_help()
        print("\n예) py enrich_persons.py --all")
        sys.exit(0)

    persons = json.loads(PERSONS_FILE.read_text(encoding="utf-8"))

    nlk_updated = aks_updated = skipped = 0

    for pid, p in persons.items():
        role = p.get("role", "")
        label = p["label"]

        if role not in KOREAN_ROLES:
            skipped += 1
            continue

        print(f"\n{label} ({pid})")

        if do_nlk and not p.get("nlk"):
            uri = query_nlk(label)
            if uri:
                p["nlk"] = uri
                print(f"  NLK  -> {uri}")
                nlk_updated += 1
            else:
                print("  NLK  -> 없음")
            time.sleep(0.3)

        if do_aks and not p.get("encykorea"):
            uri = query_aks(label)
            if uri:
                p["encykorea"] = uri
                print(f"  AKS  -> {uri}")
                aks_updated += 1
            else:
                print("  AKS  -> 없음")
            time.sleep(0.3)

    PERSONS_FILE.write_text(json.dumps(persons, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n완료 — NLK {nlk_updated}건, AKS {aks_updated}건 업데이트, {skipped}건 건너뜀(외국 인물)")


if __name__ == "__main__":
    main()
