"""
nlk_enrich.py — persons.json의 한국 인물 nlk 필드를 국립중앙도서관 저자정보 API로 자동 채우기
실행: py nlk_enrich.py

API: 공공데이터포털 국립중앙도서관_저자 정보 제공 서비스
엔드포인트: https://apis.data.go.kr/1371029/AuthorInformationService/getAuthorInformationSrch
인증키: .env의 NLK_API_KEY
"""
import json, time, urllib.request, urllib.parse, os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

NLK_API_KEY = os.getenv("NLK_API_KEY", "")
PERSONS_FILE = Path("persons.json")

BASE_URL = "https://apis.data.go.kr/1371029/AuthorInformationService/getAuthorInformationSrch"

# 외국 인물 role — NLK 저자정보는 한국 인물 위주이므로 한국 인물만 조회
KOREAN_ROLES = {"critic", "poet", "novelist", "writer", "other"}

def query_nlk(name: str) -> str | None:
    """저자명으로 NLK API 조회 → 첫 번째 결과의 URI 반환. 없거나 오류면 None."""
    params = urllib.parse.urlencode({
        "serviceKey": NLK_API_KEY,
        "authNm": name,
        "pageNo": 1,
        "numOfRows": 3,
        "type": "json",
    })
    url = f"{BASE_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "kcritic-ontology/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        # 응답 구조: data["response"]["body"]["items"]["item"]
        items = (data.get("response", {})
                     .get("body", {})
                     .get("items", {})
                     .get("item", []))
        if isinstance(items, dict):
            items = [items]  # 결과 1건이면 dict로 옴
        if not items:
            return None
        # 이름 완전 일치 우선
        for item in items:
            if item.get("authNm", "").strip() == name:
                auth_id = item.get("authNo") or item.get("authId") or item.get("id")
                if auth_id:
                    return f"https://lod.nl.go.kr/resource/KAC{str(auth_id).zfill(8)}"
        # 없으면 첫 번째 결과
        first = items[0]
        auth_id = first.get("authNo") or first.get("authId") or first.get("id")
        if auth_id:
            return f"https://lod.nl.go.kr/resource/KAC{str(auth_id).zfill(8)}"
    except Exception as e:
        print(f"  [오류] {name}: {e}")
    return None

def main():
    if not NLK_API_KEY:
        print("[오류] .env에 NLK_API_KEY가 없습니다.")
        sys.exit(1)

    persons = json.loads(PERSONS_FILE.read_text(encoding="utf-8"))

    updated = 0
    skipped = 0
    for pid, p in persons.items():
        # 이미 NLK URI 있으면 건너뜀
        if p.get("nlk"):
            skipped += 1
            continue
        # 외국 인물(foreigner)은 건너뜀
        role = p.get("role", "")
        if role not in KOREAN_ROLES:
            skipped += 1
            continue

        label = p["label"]
        print(f"  조회: {label} ({pid}) ...", end=" ")
        uri = query_nlk(label)
        if uri:
            p["nlk"] = uri
            print(f"-> {uri}")
            updated += 1
        else:
            print("-> 없음")

        time.sleep(0.3)  # API 호출 간격

    PERSONS_FILE.write_text(json.dumps(persons, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n완료: {updated}건 업데이트, {skipped}건 건너뜀")

if __name__ == "__main__":
    main()