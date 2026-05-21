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
CRITICS_DIR = Path("site/critics")
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


def collect_interp_concepts(root):
    """interp[type='concept'] 요소에서 핵심 개념어 수집 (중복 제거)."""
    seen = set()
    concepts = []
    for el in root.iter(tns("interp")):
        if el.get("type") != "concept":
            continue
        name = "".join(el.itertext()).strip()
        if name and name not in seen:
            seen.add(name)
            # slug: 첫 16자 ASCII+숫자, 나머지는 한글 그대로 허용
            slug = re.sub(r"[^\w가-힣]", "-", name)[:40].strip("-")
            concepts.append({"name": name, "slug": slug})
    return concepts

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
        note_el = biblstruct.find(tns("note"))
        sources.append({
            "type": btype,
            "journal_or_book": (title_el.text or "").strip() if title_el is not None else "",
            "publisher": (pub_el.text or "").strip() if pub_el is not None else "",
            "date": (date_el.text or "").strip() if date_el is not None else "",
            "when": date_el.get("when", "") if date_el is not None else "",
            "place": (place_el.text or "").strip() if place_el is not None else "",
            "note": (note_el.text or "").strip() if note_el is not None else "",
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

def get_original_year(sources):
    """<note>에서 '원 발표: YYYY년' 형태의 원 발표 연도 추출."""
    import re
    for s in sources:
        note = s.get("note", "")
        if note:
            m = re.search(r"(\d{4})년", note)
            if m:
                return m.group(1)
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

def build_essay_html(stem, title, year, display_year, persons, subjects, theorists, quotes, titles, terms, sources, author_id):
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
        <a href="../../critics.html">비평가</a>
        <a href="../graph.html">관계망</a>
        <a href="../../research.html">선행연구</a>
      </nav>
    </div>
  </header>

  <main class="container essay-main">
    <article class="essay-article">

      <header class="essay-header">
        <div class="essay-byline">
          <span class="chip role-critic">{author_link}</span>
          <span class="essay-year">{display_year}</span>
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

        # 개념 노드 (interp[type='concept'])
        for concept in essay.get("concepts", []):
            cid = f"concept-{concept['slug']}"
            label = concept["name"]
            if cid not in nodes:
                nodes[cid] = {"id": cid, "label": label, "type": "concept"}
            raw_edges.append((stem, cid, "uses_concept"))

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


# ── 비평가 프로필 HTML 생성 ──────────────────────────────────

def build_critic_mini_graph(critic_id, graph_data):
    """비평가 관련 노드/엣지만 추출해 Cytoscape.js 임베드용 JSON 반환."""
    # critic 노드와 직접 연결된 노드/엣지만 수집
    connected_ids = {critic_id}
    relevant_edges = []
    for e in graph_data["edges"]:
        if e["source"] == critic_id or e["target"] == critic_id:
            connected_ids.add(e["source"])
            connected_ids.add(e["target"])
            relevant_edges.append(e)
    # essay 노드들과 연결된 작가/이론가 엣지도 포함
    essay_ids = {e["source"] for e in relevant_edges if e["type"] == "wrote"} | \
                {e["target"] for e in relevant_edges if e["type"] == "wrote"}
    for e in graph_data["edges"]:
        if (e["source"] in essay_ids or e["target"] in essay_ids) and \
           e not in relevant_edges:
            connected_ids.add(e["source"])
            connected_ids.add(e["target"])
            relevant_edges.append(e)

    relevant_nodes = [n for n in graph_data["nodes"] if n["id"] in connected_ids]
    return {"nodes": relevant_nodes, "edges": relevant_edges}


def build_critic_profile(critic_id, critic_info, essays, graph_data=None):
    """비평가 한 명의 프로필 페이지 생성. essays = 해당 비평가의 비평글 데이터 목록."""
    name = critic_info["name"]
    ref = critic_info.get("ref", "")
    wikidata_link = ""
    if ref and "wikidata" in ref:
        for uri in ref.split():
            if "wikidata" in uri:
                wikidata_link = f'<a href="{uri}" target="_blank" class="chip role-critic chip-linked">{name} <span class="chip-ext">↗</span></a>'
                break
    if not wikidata_link:
        wikidata_link = f'<span class="chip role-critic">{name}</span>'

    # 비평글 카드 목록
    essay_cards = []
    for e in sorted(essays, key=lambda x: x.get("display_year") or x["year"]):
        tags_html = ""
        # 비평 대상 작가 chip
        subject_chips = " ".join(
            f'<span class="tag">{essays_persons_name(e, pid)}</span>'
            for pid in sorted(e["subjects"])
        )
        # 활용 이론가 chip
        theorist_chips = " ".join(
            f'<span class="tag">{essays_persons_name(e, pid)}</span>'
            for pid in sorted(e["theorists"])
        )
        tags_html = subject_chips + theorist_chips
        card_year = e.get("display_year") or e["year"]

        essay_cards.append(f"""
      <article class="essay-card">
        <div class="essay-card-meta">
          <span class="essay-card-year">{card_year}</span>
        </div>
        <h3 class="essay-card-title">
          <a href="../essays/{e["stem"]}.html">{e["title"]}</a>
        </h3>
        <p class="essay-card-source">{_source_short(e["sources"])}</p>
        <div class="essay-card-tags">{tags_html}</div>
      </article>""")

    # 자주 활용한 이론가 집계
    theorist_count = defaultdict(int)
    theorist_names = {}
    for e in essays:
        for pid in e["theorists"]:
            theorist_count[pid] += 1
            theorist_names[pid] = essays_persons_name(e, pid)
    top_theorists = sorted(theorist_count.items(), key=lambda x: -x[1])
    theorist_chips_html = " ".join(
        f'<span class="chip chip-term">{theorist_names[pid]} ({cnt})</span>'
        for pid, cnt in top_theorists
    ) if top_theorists else '<span class="muted">—</span>'

    # 비평 대상 작가 집계
    subject_count = defaultdict(int)
    subject_names = {}
    for e in essays:
        for pid in e["subjects"]:
            subject_count[pid] += 1
            subject_names[pid] = essays_persons_name(e, pid)
    top_subjects = sorted(subject_count.items(), key=lambda x: -x[1])
    subject_chips_html = " ".join(
        f'<span class="chip role-writer">{subject_names[pid]}</span>'
        for pid, _ in top_subjects
    ) if top_subjects else '<span class="muted">—</span>'

    essay_count = len(essays)

    # 미니 그래프 섹션
    mini_graph_html = ""
    if graph_data:
        subgraph = build_critic_mini_graph(critic_id, graph_data)
        graph_json = json.dumps(subgraph, ensure_ascii=False)
        mini_graph_html = f"""
    <section class="critic-mini-graph-section">
      <h2 class="section-label">관계망</h2>
      <div id="critic-mini-graph" class="critic-mini-graph"></div>
      <div class="mini-graph-legend">
        <span class="mini-legend-item"><span class="mini-dot dot-critic"></span>비평가</span>
        <span class="mini-legend-item"><span class="mini-dot dot-essay"></span>비평글</span>
        <span class="mini-legend-item"><span class="mini-dot dot-writer"></span>작가</span>
        <span class="mini-legend-item"><span class="mini-dot dot-theorist"></span>이론가</span>
      </div>
    </section>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
    <script>
    (function() {{
      var graphData = {graph_json};
      var elements = [];
      graphData.nodes.forEach(function(n) {{
        elements.push({{ data: {{ id: n.id, label: n.label, type: n.type, degree: n.degree || 1 }} }});
      }});
      graphData.edges.forEach(function(e) {{
        elements.push({{ data: {{ source: e.source, target: e.target, type: e.type, weight: e.weight || 1 }} }});
      }});

      var TYPE_COLOR = {{
        critic: '#c9986a',
        writer: '#6a9bc9',
        theorist: '#9a7ac9',
        essay: '#c8c8a8'
      }};
      var TYPE_TEXT_COLOR = {{
        critic: '#4a2400',
        writer: '#0e2d4a',
        theorist: '#2d1050',
        essay: '#3a3a2a'
      }};

      var cy = cytoscape({{
        container: document.getElementById('critic-mini-graph'),
        elements: elements,
        style: [
          {{
            selector: 'node',
            style: {{
              'background-color': function(ele) {{ return TYPE_COLOR[ele.data('type')] || '#aaa'; }},
              'label': 'data(label)',
              'font-family': 'Pretendard, sans-serif',
              'font-size': function(ele) {{ return ele.data('type') === 'essay' ? '10px' : '12px'; }},
              'color': function(ele) {{ return TYPE_TEXT_COLOR[ele.data('type')] || '#333'; }},
              'text-valign': 'bottom',
              'text-halign': 'center',
              'text-margin-y': '4px',
              'text-wrap': 'wrap',
              'text-max-width': '90px',
              'width': function(ele) {{
                if (ele.data('type') === 'essay') return 60;
                var d = ele.data('degree') || 1;
                return Math.min(Math.max(40 + d * 6, 40), 90);
              }},
              'height': function(ele) {{
                if (ele.data('type') === 'essay') return 30;
                var d = ele.data('degree') || 1;
                return Math.min(Math.max(40 + d * 6, 40), 90);
              }},
              'shape': function(ele) {{ return ele.data('type') === 'essay' ? 'round-rectangle' : 'ellipse'; }},
              'border-width': 1.5,
              'border-color': 'rgba(0,0,0,0.15)',
              'transition-property': 'opacity',
              'transition-duration': '0.15s',
            }}
          }},
          {{
            selector: 'edge',
            style: {{
              'width': function(ele) {{ return Math.min(Math.max((ele.data('weight') || 1) * 1.5, 1.5), 5); }},
              'line-color': '#c9c7bf',
              'target-arrow-color': '#c9c7bf',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'opacity': 0.7,
            }}
          }},
          {{
            selector: 'node.faded',
            style: {{ 'opacity': 0.15 }}
          }},
          {{
            selector: 'edge.faded',
            style: {{ 'opacity': 0.05 }}
          }},
          {{
            selector: 'node.highlighted',
            style: {{ 'border-width': 3, 'border-color': '#6b3e26' }}
          }}
        ],
        layout: {{
          name: 'cose',
          animate: false,
          randomize: false,
          nodeRepulsion: 8000,
          idealEdgeLength: 100,
          edgeElasticity: 200,
          gravity: 0.8,
          numIter: 1000,
        }},
        userZoomingEnabled: true,
        userPanningEnabled: true,
        boxSelectionEnabled: false,
      }});

      // hover 강조
      cy.on('mouseover', 'node', function(e) {{
        var node = e.target;
        cy.elements().addClass('faded');
        node.removeClass('faded').addClass('highlighted');
        node.neighborhood().removeClass('faded');
      }});
      cy.on('mouseout', 'node', function() {{
        cy.elements().removeClass('faded highlighted');
      }});
    }})();
    </script>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} — 한국 비평사 온톨로지</title>
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
        <a href="../../critics.html" class="active">비평가</a>
        <a href="../graph.html">관계망</a>
        <a href="../../research.html">선행연구</a>
      </nav>
    </div>
  </header>

  <main class="container index-main">
    <section class="critic-profile-hero">
      <div class="critic-profile-byline">{wikidata_link}</div>
      <h1 class="index-heading">{name}</h1>
      <div class="stat-row">
        <div class="stat"><span class="stat-num">{essay_count}</span><span class="stat-label">수록 비평글</span></div>
        <div class="stat"><span class="stat-num">{len(top_subjects)}</span><span class="stat-label">비평 대상 작가</span></div>
        <div class="stat"><span class="stat-num">{len(top_theorists)}</span><span class="stat-label">활용 이론가</span></div>
      </div>
    </section>

    <section class="critic-profile-meta">
      <div class="meta-section">
        <h2 class="meta-label">주요 비평 대상</h2>
        <div class="chip-group">{subject_chips_html}</div>
      </div>
      <div class="meta-section">
        <h2 class="meta-label">자주 활용한 이론가</h2>
        <div class="chip-group">{theorist_chips_html}</div>
      </div>
    </section>
    {mini_graph_html}
    <section class="essay-grid">
      <h2 class="section-label">수록 비평글 ({essay_count}편)</h2>
      {"".join(essay_cards)}
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>비평 온톨로지 프로젝트 · TEI XML 기반 디지털 아카이브</p>
    </div>
  </footer>
</body>
</html>"""


def essays_persons_name(essay_data, pid):
    """essay 데이터에서 인물 이름 반환."""
    return essay_data["persons"].get(pid, {}).get("name", pid)


def _source_short(sources):
    """서지 정보 한 줄 요약 — 짧게 (간행처·연도만)."""
    if not sources:
        return ""
    s = sources[0]
    title = s["journal_or_book"]
    # 전집/총서 부제 괄호 이전만 사용 (예: "시인의 보석 — 현대 문학..." → "시인의 보석")
    short_title = title.split(" — ")[0].split("（")[0].split("(")[0].strip()
    parts = [short_title]
    if s["publisher"]:
        parts.append(s["publisher"])
    year = s["when"][:4] if s.get("when") and len(s["when"]) >= 4 else ""
    if year:
        parts.append(year)
    return ", ".join(parts)


def build_critics_data(all_essays):
    """비평가별로 비평글 묶기. {critic_id: {info, essays[]}} 반환."""
    critics = {}
    for e in all_essays:
        aid = e["author_id"]
        if not aid:
            continue
        p = e["persons"].get(aid, {})
        if aid not in critics:
            critics[aid] = {"id": aid, "name": p.get("name", aid), "ref": p.get("ref", ""), "essays": []}
        critics[aid]["essays"].append(e)
    return critics


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

    original_year = get_original_year(sources)
    display_year = original_year if original_year else year
    concepts = collect_interp_concepts(root)

    return {
        "stem": xml_path.stem,
        "title": title,
        "year": year,
        "display_year": display_year,
        "persons": persons,
        "subjects": subjects,
        "theorists": theorists,
        "quotes": quotes,
        "titles": titles_map,
        "terms": terms,
        "concepts": concepts,
        "sources": sources,
        "author_id": author_id,
    }


def main():
    print("TEI XML -> 메타데이터 HTML 변환 시작")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CRITICS_DIR.mkdir(parents=True, exist_ok=True)
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
                display_year=data["display_year"],
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

    # 비평가 프로필 페이지
    critics = build_critics_data(all_essays)
    for cid, cinfo in critics.items():
        html = build_critic_profile(cid, cinfo, cinfo["essays"], graph_data=graph)
        out = CRITICS_DIR / f"{cid}.html"
        out.write_text(html, encoding="utf-8")
        print(f"  OK critic profile -> {out}")

    # 비평가 목록 JSON (critics.html에서 사용)
    critics_json = [
        {
            "id": cid,
            "name": cinfo["name"],
            "ref": cinfo["ref"],
            "essay_count": len(cinfo["essays"]),
            "subjects": list({pid for e in cinfo["essays"] for pid in e["subjects"]}),
            "theorists": list({pid for e in cinfo["essays"] for pid in e["theorists"]}),
        }
        for cid, cinfo in critics.items()
    ]
    critics_path = DATA_DIR / "critics.json"
    critics_path.write_text(json.dumps(critics_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  OK critics.json -> {critics_path} ({len(critics_json)} critics)")

    print("\n완료.")


if __name__ == "__main__":
    main()
