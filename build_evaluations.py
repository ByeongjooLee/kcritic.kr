# -*- coding: utf-8 -*-
"""평가 대기열 생성 — (비평문 × 대상작가) 쌍을 판단 항목으로 만든다.

평가(evaluation)는 온톨로지의 다른 데이터와 성격이 다르다.
  · 다른 트리플: 외부 전거로 대조 가능한 사실. 불일치는 오류다.
  · 평가 트리플: 외부에 정답이 없는 해석. 불일치는 데이터다.
따라서 평가는 본체 그래프에 덮어쓰지 않고 판단자·일시와 함께 누적한다.

출력
  site/data/evaluations.json   판단 대기열 + 기존 판단 (웹 UI가 적재)
  ../평가작업목록.xlsx          연구자가 내려받아 채우는 작업 파일

주의: 지침 §1에 따라 원문 본문은 어떤 출력에도 포함하지 않는다.
      판단 화면은 서지 정보와 비평문 페이지 링크만 제공한다.
"""
import json, os, io, re, sys, glob, collections
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "site", "data")
OUT_JSON = os.path.join(DATA, "evaluations.json")
OUT_XLSX = os.path.join(os.path.dirname(HERE), "평가작업목록.xlsx")

VALUES = [
    ("affirmative", "긍정", "비평가가 대상을 옹호·상찬하는 태도"),
    ("neutral",     "중립", "가치 판단을 유보하거나 기술에 머무는 태도"),
    ("critical",    "비판", "비평가가 대상의 한계를 지적하는 태도"),
    ("mixed",       "양가", "긍정과 비판이 함께 나타나는 태도"),
]

# ── 그래프에서 (비평문, 작가) 쌍 수집 ─────────────────
graph = json.load(open(os.path.join(DATA, "graph.json"), encoding="utf-8"))
nodes = {n["id"]: n for n in graph["nodes"]}
author_of = {e["target"]: e["source"] for e in graph["edges"] if e["type"] == "wrote"}

pairs = []
for e in graph["edges"]:
    if e["type"] != "subject_of":
        continue
    stem, wid = e["source"], e["target"]
    cid = author_of.get(stem)
    if not cid:
        continue
    pairs.append({
        "id": f"{stem}::{wid}",
        "essay": stem,
        "essay_title": nodes[stem].get("label", ""),
        "year": nodes[stem].get("year", ""),
        "critic_id": cid,
        "critic": nodes[cid].get("label", ""),
        "writer_id": wid,
        "writer": nodes[wid].get("label", ""),
        "essay_url": f"/site/essays/{stem}.html",
    })
pairs.sort(key=lambda p: (p["critic"], p["year"], p["essay"], p["writer"]))

# ── 기존 TEI stance 마크업이 있는 비평문 표시 ──────────
# 문장 단위 판단이므로 그대로 항목 값이 되지는 않는다.
# "연구자가 이미 태도를 표시한 비평문"이라는 단서로만 쓴다.
STANCE = re.compile(r'ana="#(?:st-)?(affirmative|critical|neutral)"')
marked = collections.Counter()
for f in glob.glob(os.path.join(HERE, "essays", "*.xml")):
    stem = os.path.basename(f)[:-4]
    hits = STANCE.findall(io.open(f, encoding="utf-8").read())
    if hits:
        marked[stem] = len(hits)
for p in pairs:
    p["tei_marks"] = marked.get(p["essay"], 0)

# ── 기존 판단 보존 (재생성해도 사라지지 않게) ──────────
prev = {}
if os.path.exists(OUT_JSON):
    old = json.load(open(OUT_JSON, encoding="utf-8"))
    prev = {j["item"]: j for j in old.get("judgements", [])}

payload = {
    "generated": date.today().isoformat(),
    "unit": "essay×writer",
    "values": [{"key": k, "label": l, "desc": d} for k, l, d in VALUES],
    "note": ("평가는 외부 전거로 대조할 수 없는 해석이다. "
             "같은 항목에 복수의 판단이 쌓이면 덮어쓰지 않고 모두 보존한다."),
    "items": pairs,
    "judgements": list(prev.values()),
}
os.makedirs(DATA, exist_ok=True)
io.open(OUT_JSON, "w", encoding="utf-8", newline="\n").write(
    json.dumps(payload, ensure_ascii=False, indent=1))

# ── 연구자 작업용 xlsx ─────────────────────────────────
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "평가작업"
    cols = ["항목ID", "비평가", "연도", "비평문", "대상 작가",
            "판단", "확신도(1-5)", "근거 메모", "판단자", "TEI 표시"]
    ws.append(cols)
    for c in range(1, len(cols) + 1):
        ws.cell(1, c).font = Font(bold=True, color="FFFFFF")
        ws.cell(1, c).fill = PatternFill("solid", fgColor="1A237E")
    for p in pairs:
        ws.append([p["id"], p["critic"], p["year"], p["essay_title"], p["writer"],
                   "", "", "", "", p["tei_marks"] or ""])
    dv = DataValidation(type="list",
                        formula1='"' + ",".join(l for _, l, _ in VALUES) + ',판단보류"',
                        allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"F2:F{len(pairs)+1}")
    for i, w in enumerate([34, 9, 7, 44, 12, 11, 13, 30, 12, 10], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=True)

    gd = wb.create_sheet("판단 기준")
    gd.append(["값", "라벨", "설명"])
    for c in range(1, 4):
        gd.cell(1, c).font = Font(bold=True, color="FFFFFF")
        gd.cell(1, c).fill = PatternFill("solid", fgColor="1A237E")
    for k, l, d in VALUES:
        gd.append([k, l, d])
    gd.append(["", "판단보류", "비평문을 읽지 못했거나 태도를 특정할 수 없는 경우"])
    for i, w in enumerate([16, 12, 60], 1):
        gd.column_dimensions[get_column_letter(i)].width = w

    wb.save(OUT_XLSX)
    xlsx_ok = True
except ImportError:
    xlsx_ok = False

print(f"평가 항목 {len(pairs):,}개")
print(f"  기존 판단 보존 {len(prev)}건")
print(f"  TEI 태도 마크업이 있는 비평문의 항목 {sum(1 for p in pairs if p['tei_marks']):,}개")
c = collections.Counter(p["critic"] for p in pairs)
print("  비평가별:", " · ".join(f"{k} {v:,}" for k, v in c.most_common()))
print(f"JSON : {OUT_JSON}")
if xlsx_ok:
    print(f"XLSX : {OUT_XLSX}")
