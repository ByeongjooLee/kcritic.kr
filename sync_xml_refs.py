"""
essays/*.xml 의 persName ref Wikidata QID를 persons.json 교정값에 동기화.

xml:id → 슬러그(직접 또는 id_map 숫자→슬러그) 로 해석하여,
적용 대상 슬러그(qid_fix_proposals.csv 신뢰도='높음')의 persName 정의에 박힌
Wikidata QID를 교정 QID로 일괄 치환한다. (한 인물이 여러 잘못된 QID로 인코딩돼도 모두 교정)

- 실행 전 essays 를 essays_backup_qidfix/ 로 백업 (없을 때만 생성)
- wikidata.org URI 의 Q번호만 치환, ISNI·VIAF 등 다른 URI 는 보존
- ref="#p-xxx" 앵커 참조는 건드리지 않음 (wikidata 없음)

사용법 (critic-ontology/ 에서):
    py sync_xml_refs.py
"""

import json
import re
import csv
import glob
import os
import sys
import shutil

sys.stdout.reconfigure(encoding="utf-8")

ESSAYS = "essays"
BACKUP = "essays_backup_qidfix"
ID_MAP = os.path.join("..", "id_map.json")
PERSONS = "persons.json"
PROPOSALS = "qid_fix_proposals.csv"

# 1) 매핑 로드
idmap = json.load(open(ID_MAP, encoding="utf-8"))         # slug -> numeric
num2slug = {v: k for k, v in idmap.items()}
persons = json.load(open(PERSONS, encoding="utf-8"))
fixes = {r["슬러그"]: r["제안QID"]
         for r in csv.DictReader(open(PROPOSALS, encoding="utf-8-sig"))
         if r["신뢰도"] == "높음" and r["제안QID"]}
print(f"동기화 대상 슬러그: {len(fixes)}개")

# 2) 백업
if not os.path.isdir(BACKUP):
    os.makedirs(BACKUP)
    for f in glob.glob(os.path.join(ESSAYS, "*.xml")):
        shutil.copy2(f, os.path.join(BACKUP, os.path.basename(f)))
    print(f"백업 생성: {BACKUP}/ ({len(os.listdir(BACKUP))} files)")
else:
    print(f"백업 폴더 이미 존재: {BACKUP}/ (재백업 생략)")

PERSNAME = re.compile(r'<persName\b[^>]*?>.*?</persName>', re.S)
WIKIQ = re.compile(r'(wikidata\.org/(?:wiki|entity)/)(Q\d+)')


def resolve_slug(xid):
    if xid in persons:
        return xid
    return num2slug.get(xid)


total_changes = 0
changed_files = 0
detail = []

for path in sorted(glob.glob(os.path.join(ESSAYS, "*.xml"))):
    text = open(path, encoding="utf-8").read()
    file_changes = 0

    def repl_persname(m):
        global file_changes
        block = m.group(0)
        xid_m = re.search(r'xml:id="([^"]+)"', block)
        ref_m = re.search(r'ref="([^"]*wikidata[^"]*)"', block)
        if not xid_m or not ref_m:
            return block
        slug = resolve_slug(xid_m.group(1))
        if slug not in fixes:
            return block
        new_qid = fixes[slug]
        ref_val = ref_m.group(1)

        def fix_q(qm):
            global file_changes
            if qm.group(2) != new_qid:
                file_changes += 1
                detail.append((os.path.basename(path), slug,
                               qm.group(2), new_qid))
            return qm.group(1) + new_qid

        new_ref = WIKIQ.sub(fix_q, ref_val)
        return block.replace(ref_val, new_ref)

    new_text = PERSNAME.sub(repl_persname, text)
    if file_changes:
        open(path, "w", encoding="utf-8").write(new_text)
        changed_files += 1
        total_changes += file_changes

print(f"\n치환: {total_changes}건 / 변경 파일: {changed_files}개")
for fn, slug, old, new in detail:
    print(f"  {fn:46s} {slug:16s} {old} → {new}")
print(f"\n되돌리기: {BACKUP}/ 의 파일을 essays/ 로 복사")
print("다음: py build.py 로 사이트 재생성")
