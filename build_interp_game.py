# -*- coding: utf-8 -*-
"""태도 판정 게임 데이터 생성 — TEI 태도 표시(<interp>·<quote> 의 @ana) 문장 추출

출력: site/data/interp_game.json

※ 원문 공개 예외 (2026-09-15 연구자 결정)
   지침 §1은 원문 본문의 사이트 게재를 금지한다. 이 스크립트는 그 예외로,
   태도 표시가 붙은 문장만 판정 게임용으로 공개한다. 각 문장에는 비평문 제목과
   수록 단행본을 출처로 함께 싣는다. 대상을 넓히려면 연구자의 명시적 결정이 필요하다.

항목 ID는 (비평문, 표시 범위, 문장) 해시로 만들어 XML 안의 순서가 바뀌어도 유지된다.
"""
import hashlib, io, json, os, re, sys, glob, collections
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "site", "data", "interp_game.json")
VAL = re.compile(r"#(?:st-)?(affirmative|critical|neutral)\b")
LABEL = {"affirmative": "긍정", "neutral": "중립", "critical": "비판"}

graph = json.load(open(os.path.join(HERE, "site", "data", "graph.json"), encoding="utf-8"))
nodes = {n["id"]: n for n in graph["nodes"]}
author = {e["target"]: nodes[e["source"]]["label"] for e in graph["edges"] if e["type"] == "wrote"}


def tag(e):
    return e.tag.split("}")[-1]


def clean(t):
    return re.sub(r"\s+", " ", t or "").strip()


def prose_text(el):
    """요소의 원문 텍스트. 줄 단위로 따로 달린 개념어 꼬리표는 원문이 아니므로 뺀다.

    <s>
      <interp value="affirmative" ana="#st-affirmative"/>      ← 점 표시(텍스트 없음)
      <interp type="concept">저항적 의지</interp>             ← 줄 단위 꼬리표: 제외
      조태일이 … <interp type="concept">되풀이</interp>되면서도 …  ← 인라인 개념어: 원문, 유지
    </s>
    """
    out = [el.text or ""]
    for ch in el:
        label = (tag(ch) == "interp" and ch.get("type") == "concept"
                 and (ch.tail or "").startswith(chr(10)))
        if not label:
            out.append(prose_text(ch))
        out.append(ch.tail or "")
    return "".join(out)


def source_of(raw):
    """sourceDesc 에서 수록 단행본(마지막 『』)을 뽑는다."""
    sd = re.search(r"<sourceDesc>(.*?)</sourceDesc>", raw, re.S)
    if not sd:
        return ""
    body = clean(re.sub(r"<[^>]+>", " ", sd.group(1)))
    c = re.findall(r"『([^』]+)』\s*[,(]?\s*([가-힣A-Za-z]+(?:사|원|다|방))?\s*,?\s*(\d{4})", body)
    if not c:
        return ""
    t, p, y = c[-1]
    return f"『{t.strip()}』" + (f", {p}" if p else "") + f", {y}"


items, seen = [], set()
for f in sorted(glob.glob(os.path.join(HERE, "essays", "*.xml"))):
    raw = io.open(f, encoding="utf-8").read()
    if not VAL.search(raw):
        continue
    stem = os.path.basename(f)[:-4]
    root = ET.fromstring(raw)
    parent = {c: p for p in root.iter() for c in p}
    src = source_of(raw)
    for e in root.iter():
        m = VAL.search(e.get("ana") or "")
        if not m or tag(e) not in ("interp", "quote"):
            continue
        span = clean(prose_text(e))
        p, hops = parent.get(e), 0
        while p is not None and tag(p) not in ("s", "p", "l") and hops < 5:
            p, hops = parent.get(p), hops + 1
        sentence = clean(prose_text(p)) if p is not None else span
        if not sentence:
            continue
        # 점 표시(텍스트 없는 <interp …/>)는 그 문장 전체의 태도를 나타낸다
        whole = not span
        if whole:
            span = sentence
        hid = hashlib.sha1(f"{stem}|{span}|{sentence}".encode("utf-8")).hexdigest()[:10]
        iid = f"{stem}#{hid}"
        if iid in seen:
            continue
        seen.add(iid)
        start = sentence.find(span)
        items.append({
            "id": iid,
            "essay": stem,
            "essay_title": nodes.get(stem, {}).get("label", ""),
            "year": nodes.get(stem, {}).get("year", ""),
            "critic": author.get(stem, ""),
            "source": src,
            "sentence": sentence,
            "span": span,
            "span_start": start,
            "element": tag(e),
            "whole_sentence": whole,
            "encoder_value": m.group(1),
        })

payload = {
    "generated": __import__("datetime").date.today().isoformat(),
    "unit": "sentence",
    "note": ("비평 태도에는 외부에 정답이 없다. 1편 인코딩의 표시는 한 연구자의 판정일 뿐이며, "
             "참여자의 판정은 덮어쓰지 않고 모두 보존한다."),
    "copyright": ("아래 문장은 연구·비평 목적의 인용이며, 저작권은 각 필자와 수록 단행본의 권리자에게 있다."),
    "values": [
        {"key": "affirmative", "label": "긍정", "desc": "대상을 옹호·상찬한다"},
        {"key": "neutral", "label": "중립", "desc": "판단을 유보하거나 기술에 머문다"},
        {"key": "critical", "label": "비판", "desc": "대상의 한계를 지적한다"},
        {"key": "mixed", "label": "양가", "desc": "긍정과 비판이 함께 나타난다"},
        {"key": "unsure", "label": "판단보류", "desc": "태도를 특정할 수 없다"},
    ],
    "items": items,
}
io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(payload, ensure_ascii=False, indent=1))

c = collections.Counter(i["encoder_value"] for i in items)
print(f"판정 문장 {len(items)}개 · 비평문 {len({i['essay'] for i in items})}편")
print("  1편 인코딩 표시:", " · ".join(f"{LABEL[k]} {v}" for k, v in c.most_common()))
print(f"  문장 전체 표시(점 표시) {sum(1 for i in items if i['whole_sentence'])}개 · 부분 표시 {sum(1 for i in items if not i['whole_sentence'])}개")
print(f"  표시 범위를 문장 안에서 찾지 못한 항목 {sum(1 for i in items if i['span_start'] < 0)}개")
print(f"  출처(수록 단행본)가 없는 항목 {sum(1 for i in items if not i['source'])}개")
print(f"  출력: {OUT}  ({os.path.getsize(OUT)//1024} KB)")
