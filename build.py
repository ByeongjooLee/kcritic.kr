"""
TEI XML -> 메타데이터 HTML 변환 스크립트
원문 텍스트는 일절 포함하지 않음.
추출 대상: 비평가, 대상 인물, 활용 이론가, 인용 작품, 개념어, 서지정보
"""

import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import defaultdict

TEI_NS = "http://www.w3.org/XML/1998/namespace"
T = "http://www.tei-c.org/ns/1.0"
ESSAYS_DIR = Path("essays")
OUTPUT_DIR = Path("site/essays")
DATA_DIR = Path("site/data")

def tns(tag):
    return f"{{{T}}}{tag}"

# ── 메타데이터 추출 ──────────────────────────────────────────

def get_attr_id(elem):
    return elem.get(f"{{{TEI_NS}}}id", "")

def collect_persons(root):
    """모든 persName 요소에서 인물 정보 수집."""
    persons = {}
    for pn in root.iter(tns("persName")):
        xml_id = get_attr_id(pn)
        ref = pn.get("ref", "")
        role = pn.get("role", "")
        name = "".join(pn.itertext()).strip()
        if xml_id:
            # 최초 정의 (xml:id 있음)
            persons[xml_id] = {
                "id": xml_id,
                "name": name,
                "role": role,
                "ref": ref,
            }
        elif ref and ref.startswith("#"):
            # 이후 참조 — 기존 항목에 이름 변형 추가
            target = ref[1:]
            if target in persons and name not in persons[target]["name"]:
                pass  # 이미 수집됨
    return persons

def classify_role(role):
    """role 문자열에서 인물 유형 분류."""
    if not role:
        return "other"
    if "critic" in role:
        return "critic"
    if "poet" in role or "novelist" in role or "writer" in role:
        return "writer"
    if "scholar" in role or "foreigner" in role:
        return "theorist"
    return "other"

def collect_interp_persons(root, persons):
    """interp 요소 주변 persName ref로 '비평 대상' 추출."""
    # interp를 포함하는 s 요소 안의 persName ref들
    subjects = set()
    for s_elem in root.iter(tns("s")):
        has_interp = s_elem.find(tns("interp")) is not None
        if not has_interp:
            continue
        for pn in s_elem.iter(tns("persName")):
            ref = pn.get("ref", "")
            xml_id = get_attr_id(pn)
            pid = xml_id if xml_id else (ref[1:] if ref.startswith("#") else "")
            if pid and pid in persons:
                role = persons[pid].get("role", "")
                if "poet" in role or "novelist" in role or "writer" in role:
                    subjects.add(pid)
    return subjects

def collect_quotes(root):
    """quote 요소에서 출처/장르 수집 (본문 텍스트 제외)."""
    quotes = []
    for q in root.iter(tns("quote")):
        source = q.get("source", "")
        genre = q.get("genre", "")
        q_type = q.get("type", "")
        if source:
            quotes.append({"source": source, "genre": genre, "type": q_type})
    return quotes

def collect_titles(root):
    """title 요소에서 작품 정보 수집."""
    titles = {}
    for t in root.iter(tns("title")):
        xml_id = get_attr_id(t)
        if not xml_id:
            continue
        ref = t.get("ref", "")
        level = t.get("level", "")
        t_type = t.get("type", "")
        name = "".join(t.itertext()).strip()
        titles[xml_id] = {
            "id": xml_id,
            "name": name,
            "level": level,
            "type": t_type,
            "author_ref": ref[1:] if ref.startswith("#") else "",
        }
    return titles

def collect_terms(root):
    """term 요소에서 개념어 수집."""
    seen = set()
    terms = []
    for t in root.iter(tns("term")):
        xml_id = get_attr_id(t)
        name = "".join(t.itertext()).strip()
        key = xml_id or name
        if key and key not in seen:
            seen.add(key)
            terms.append({"id": xml_id, "name": name})
    return terms

def extract_sources(root):
    """sourceDesc에서 서지 정보 추출."""
    sources = []
    for biblstruct in root.findall(f".//{tns('sourceDesc')}/{tns('biblStruct')}"):
        btype = biblstruct.get("type", "")
        monogr = biblstruct.find(tns("monogr"))
        if monogr is None:
            continue
        title_el = monogr.find(tns("title"))
        pub_el = monogr.find(f"{tns('imprint')}/{tns('publisher')}")
        date_el = monogr.find(f"{tns('imprint')}/{tns('date')}")
        place_el = monogr.find(f"{tns('imprint')}/{tns('pubPlace')}")
        sources.append({
            "type": btype,
            "journal_or_book": (title_el.text or "").strip() if title_el is not None else "",
            "publisher": (pub_el.text or "").strip() if pub_el is not None else "",
            "date": (date_el.text or "").strip() if date_el is not None else "",
            "when": date_el.get("when", "") if date_el is not None else "",
            "place": (place_el.text or "").strip() if place_el is not None else "",
        })
    return sources

def extract_essay_meta(root):
    title_el = root.find(f".//{tns('titleStmt')}/{tns('title')}")
    title = (title_el.text or "").strip() if title_el is not None else ""
    return title

def get_pub_year(sources):
    for s in sources:
        when = s.get("when", "")
        if when and len(when) >= 4:
            return when[:4]
    return ""

# ── HTML 생성 ────────────────────────────────────────────────

ROLE_LABEL = {
    "critic": "비평가",
    "writer": "작가 / 시인",
    "theorist": "이론가 / 사상가",
    "other": "기타",
}

ROLE_CLASS = {
    "critic": "role-critic",
    "writer": "role-writer",
    "theorist": "role-theorist",
    "other": "role-other",
}

def person_chip(p, role_type=None):
    role = role_type or classify_role(p.get("role", ""))
    cls = ROLE_CLASS.get(role, "role-other")
    ref = p.get("ref", "")
    wikidata = ""
    if ref and "wikidata" in ref:
        # ref에 복수 URI 있을 수 있음
        for uri in ref.split():
            if "wikidata" in uri:
                wikidata = uri
                break
    name = p.get("name", "")
    pid = p.get("id", "")
    chip = f'<span class="chip {cls}" data-id="{pid}">{name}</span>'
    if wikidata:
        chip = f'<a href="{wikidata}" target="_blank" class="chip {cls} chip-linked" data-id="{pid}" title="Wikidata">{name} <span class="chip-ext">↗</span></a>'
    return chip

def source_html(sources):
    if not sources:
        return ""
    items = []
    for s in sources:
        label = {"journal": "저널", "publication": "단행본"}.get(s["type"], s["type"])
        items.append(
            f'<li><span class="source-badge">{label}</span> '
            f'<strong>{s["journal_or_book"]}</strong>'
            f'{", " + s["publisher"] if s["publisher"] else ""}'
            f'{", " + s["date"] if s["date"] else ""}</li>'
        )
    return '<ul class="source-list">' + "\n".join(items) + "</ul>"

def build_essay_html(stem, title, year, persons, subjects, theorists, quotes, titles, terms, sources, author_id):
    author = persons.get(author_id, {})
    author_name = author.get("name", "")
    author_ref = author.get("ref", "")

    # 비평 대상 작가
    subjects_html = ""
    if subjects:
        chips = " ".join(person_chip(persons[pid], "writer") for pid in sorted(subjects) if pid in persons)
        subjects_html = f"""
    <section class="meta-section">
      <h2 class="meta-label">비평 대상</h2>
      <div class="chip-group">{chips}</div>
    </section>"""

    # 활용 이론가
    th_ids = sorted(theorists)
    theorists_html = ""
    if th_ids:
        chips = " ".join(person_chip(persons[pid], "theorist") for pid in th_ids if pid in persons)
        theorists_html = f"""
    <section class="meta-section">
      <h2 class="meta-label">활용된 이론가 / 사상가</h2>
      <div class="chip-group">{chips}</div>
    </section>"""

    # 언급 작품
    works_html = ""
    work_items = [t for t in titles.values() if t["level"] in ("a", "m")]
    if work_items:
        def work_label(w):
            lbr = {"a": "「」", "m": "『』", "j": "《》"}.get(w["level"], "")
            open_b = lbr[0] if lbr else ""
            close_b = lbr[1] if len(lbr) > 1 else ""
            author_name_w = persons.get(w["author_ref"], {}).get("name", "")
            suffix = f' <span class="work-author">— {author_name_w}</span>' if author_name_w else ""
            return f'<span class="work-item">{open_b}{w["name"]}{close_b}{suffix}</span>'
        items_html = "\n".join(work_label(w) for w in work_items)
        works_html = f"""
    <section class="meta-section">
      <h2 class="meta-label">언급된 작품</h2>
      <div class="work-list">{items_html}</div>
    </section>"""

    # 핵심 개념
    terms_html = ""
    if terms:
        chips = " ".join(f'<span class="chip chip-term">{t["name"]}</span>' for t in terms)
        terms_html = f"""
    <section class="meta-section">
      <h2 class="meta-label">핵심 개념어</h2>
      <div class="chip-group">{chips}</div>
    </section>"""

    # 인용 출처 목록 (본문 텍스트 없이 출처만)
    quotes_html = ""
    if quotes:
        q_items = []
        seen_src = set()
        for q in quotes:
            src = q["source"]
            if src and src not in seen_src:
                seen_src.add(src)
                genre_label = {"poet": "시", "foreign": "외국어 텍스트", "prose": "산문"}.get(q["genre"], "")
                badge = f'<span class="source-badge">{genre_label}</span> ' if genre_label else ""
                q_items.append(f"<li>{badge}{src}</li>")
        if q_items:
            quotes_html = f"""
    <section class="meta-section">
      <h2 class="meta-label">인용 출처</h2>
      <ul class="quote-source-list">{"".join(q_items)}</ul>
    </section>"""

    author_link = f'<a href="{author_ref}" target="_blank">{author_name}</a>' if author_ref and "wikidata" in author_ref else author_name

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — 한국 비평사 온톨로지</title>
  <link rel="preconnect" href="https://cdn.jsdelivr.net">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
  <link rel="stylesheet" href="../../style.css">
</head>
<body>
  <header class="site-header">
    <div class="container">
      <a href="../../index.html" class="site-title">한국 비평사 온톨로지</a>
      <nav class="site-nav">
        <a href="../../index.html">비평글</a>
      </nav>
    </div>
  </header>

  <main class="container essay-main">
    <article class="essay-article">

      <header class="essay-header">
        <div class="essay-byline">
          <span class="chip role-critic">{author_link}</span>
          <span class="essay-year">{year}</span>
        </div>
        <h1 class="essay-title">{title}</h1>
        {source_html(sources)}
      </header>

      <div class="essay-meta-body">
        {subjects_html}
        {theorists_html}
        {works_html}
        {terms_html}
        {quotes_html}
      </div>

      <div class="essay-notice">
        <p>이 페이지는 비평글의 구조화 데이터(관계망)만 표시합니다. 원문은 저작권 보호에 따라 제공하지 않습니다.</p>
      </div>

    </article>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>비평 온톨로지 프로젝트 · TEI XML 기반 디지털 아카이브</p>
    </div>
  </footer>
</body>
</html>"""


# ── 전체 그래프 데이터 생성 ──────────────────────────────────

def build_graph_data(all_essays):
    """모든 비평글에서 노드/엣지 추출. 엣지 weight = 같은 source→target 쌍 등장 횟수."""
    nodes = {}
    raw_edges = []

    for essay in all_essays:
        stem = essay["stem"]
        title = essay["title"]
        year = essay["year"]
        persons = essay["persons"]
        subjects = essay["subjects"]
        theorists = essay["theorists"]
        author_id = essay["author_id"]

        # 비평글 노드
        nodes[stem] = {"id": stem, "label": title, "type": "essay", "year": year}

        # 비평가 노드
        if author_id and author_id in persons:
            p = persons[author_id]
            nodes[author_id] = {"id": author_id, "label": p["name"], "type": "critic", "ref": p.get("ref", "")}
            raw_edges.append((author_id, stem, "wrote"))

        # 대상 작가 노드
        for pid in subjects:
            if pid in persons:
                p = persons[pid]
                if pid not in nodes:
                    nodes[pid] = {"id": pid, "label": p["name"], "type": "writer", "ref": p.get("ref", "")}
                raw_edges.append((stem, pid, "subject_of"))

        # 이론가 노드
        for pid in theorists:
            if pid in persons:
                p = persons[pid]
                if pid not in nodes:
                    nodes[pid] = {"id": pid, "label": p["name"], "type": "theorist", "ref": p.get("ref", "")}
                raw_edges.append((stem, pid, "uses_theory"))

    # 엣지 weight 집계 (같은 source→target→type 쌍이 여러 비평글에서 반복될 때 가중치 증가)
    edge_counts = defaultdict(int)
    for src, tgt, etype in raw_edges:
        edge_counts[(src, tgt, etype)] += 1

    edges = [
        {"source": src, "target": tgt, "type": etype, "weight": cnt}
        for (src, tgt, etype), cnt in edge_counts.items()
    ]

    # 노드 degree (연결된 엣지 수 합산, weight 반영)
    degree = defaultdict(int)
    for (src, tgt, etype), cnt in edge_counts.items():
        degree[src] += cnt
        degree[tgt] += cnt

    node_list = []
    for nid, n in nodes.items():
        n["degree"] = degree.get(nid, 0)
        node_list.append(n)

    return {"nodes": node_list, "edges": edges}


# ── 메인 ─────────────────────────────────────────────────────

def process(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    title = extract_essay_meta(root)
    sources = extract_sources(root)
    year = get_pub_year(sources)
    persons = collect_persons(root)
    subjects = collect_interp_persons(root, persons)
    quotes = collect_quotes(root)
    titles_map = collect_titles(root)
    terms = collect_terms(root)

    # 비평가 = 첫 번째 xml:id 있는 persName with role=critic
    author_id = ""
    for pid, p in persons.items():
        if "critic" in p.get("role", ""):
            author_id = pid
            break

    # 이론가 = scholar 또는 foreigner scholar — 비평 대상 작가 제외
    theorists = set()
    for pid, p in persons.items():
        role = p.get("role", "")
        if ("scholar" in role) and pid not in subjects and pid != author_id:
            theorists.add(pid)

    return {
        "stem": xml_path.stem,
        "title": title,
        "year": year,
        "persons": persons,
        "subjects": subjects,
        "theorists": theorists,
        "quotes": quotes,
        "titles": titles_map,
        "terms": terms,
        "sources": sources,
        "author_id": author_id,
    }


def main():
    print("TEI XML -> 메타데이터 HTML 변환 시작")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    xml_files = sorted(ESSAYS_DIR.glob("*.xml"))
    if not xml_files:
        print(f"  [오류] {ESSAYS_DIR}/ 에 XML 파일 없음")
        return

    all_essays = []
    for xml_path in xml_files:
        try:
            data = process(xml_path)
            all_essays.append(data)

            html = build_essay_html(
                stem=data["stem"],
                title=data["title"],
                year=data["year"],
                persons=data["persons"],
                subjects=data["subjects"],
                theorists=data["theorists"],
                quotes=data["quotes"],
                titles=data["titles"],
                terms=data["terms"],
                sources=data["sources"],
                author_id=data["author_id"],
            )
            out = OUTPUT_DIR / f"{xml_path.stem}.html"
            out.write_text(html, encoding="utf-8")
            print(f"  OK {xml_path.name} -> {out}")
        except Exception as e:
            print(f"  [오류] {xml_path.name}: {e}")

    # 그래프 데이터 JSON
    graph = build_graph_data(all_essays)
    graph_path = DATA_DIR / "graph.json"
    graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  OK graph.json -> {graph_path} ({len(graph['nodes'])} nodes, {len(graph['edges'])} edges)")

    print("\n완료.")


if __name__ == "__main__":
    main()
