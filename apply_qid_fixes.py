"""
qid_fix_proposals.csv 의 신뢰도 '높음' 항목만 persons.json 에 반영.

- 적용 전 persons.json.bak 백업 생성
- wikidata 필드만 교체 (나머지 필드·키 순서·들여쓰기 보존)
- 변경 내역 콘솔 출력

사용법 (critic-ontology/ 에서):
    py apply_qid_fixes.py            # 신뢰도 '높음'만 적용
    py apply_qid_fixes.py 높음 중간   # 등급 지정 적용
"""

import json
import csv
import sys
import shutil

sys.stdout.reconfigure(encoding="utf-8")

PERSONS_JSON = "persons.json"
PROPOSALS_CSV = "qid_fix_proposals.csv"
BACKUP = "persons.json.bak"

levels = set(sys.argv[1:]) or {"높음"}
print(f"적용 등급: {', '.join(sorted(levels))}")

# 1) 제안 읽기
fixes = []  # (slug, old, new, label, conf)
with open(PROPOSALS_CSV, encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        if row["신뢰도"] in levels and row["제안QID"]:
            fixes.append((row["슬러그"], row["기존QID"], row["제안QID"],
                          row["저장이름"], row["신뢰도"]))

print(f"적용 대상: {len(fixes)}건")

# 2) persons.json 로드
persons = json.load(open(PERSONS_JSON, encoding="utf-8"))

# 3) 백업
shutil.copy2(PERSONS_JSON, BACKUP)
print(f"백업 생성: {BACKUP}")

# 4) 적용
applied, skipped = 0, []
for slug, old, new, label, conf in fixes:
    rec = persons.get(slug)
    if rec is None:
        skipped.append((slug, "슬러그 없음"))
        continue
    cur = rec.get("wikidata")
    if cur != old:
        skipped.append((slug, f"기존 QID 불일치(현재 {cur}, 기대 {old})"))
        continue
    rec["wikidata"] = new
    applied += 1
    print(f"  ✓ {label:20s} {old:11s} → {new}  [{conf}]")

# 5) 저장 (원본 포맷 유지)
with open(PERSONS_JSON, "w", encoding="utf-8") as f:
    json.dump(persons, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"\n적용 완료: {applied}건 / 건너뜀 {len(skipped)}건")
for slug, why in skipped:
    print(f"  - 건너뜀 {slug}: {why}")
print(f"\n검증 재실행: py verify_lod.py")
print(f"되돌리기: copy {BACKUP} {PERSONS_JSON}")
