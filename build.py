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
WRITERS_DIR = Path("site/writers")
THINKERS_DIR = Path("site/thinkers")
DATA_DIR = Path("site/data")
PERSONS_FILE = Path("persons.json")

# persons.json 권위 소스 로드 (없으면 빈 dict)
_PERSONS_REGISTRY: dict = {}
# Wikidata Q번호 → persons.json 슬러그 역방향 인덱스
_WIKIDATA_TO_SLUG: dict = {}
if PERSONS_FILE.exists():
    _PERSONS_REGISTRY = json.loads(PERSONS_FILE.read_text(encoding="utf-8"))
    for _slug, _p in _PERSONS_REGISTRY.items():
        if _p.get("wikidata"):
            _WIKIDATA_TO_SLUG[_p["wikidata"]] = _slug
        for _alias in (_p.get("wikidata_aliases") or []):
            if _alias not in _WIKIDATA_TO_SLUG:
                _WIKIDATA_TO_SLUG[_alias] = _slug

# id_map.json (슬러그 → 숫자ID) 로드 → 숫자ID → 슬러그 역인덱스.
# 에세이 XML이 숫자 xml:id(p-00117 등)로 인물을 참조해도 persons.json 권위 레코드로 연결.
_NUM_TO_SLUG: dict = {}
_ID_MAP_FILE = Path("..") / "id_map.json"
if _ID_MAP_FILE.exists():
    try:
        for _slug, _num in json.loads(_ID_MAP_FILE.read_text(encoding="utf-8")).items():
            _NUM_TO_SLUG.setdefault(_num, _slug)
    except Exception:
        pass

# ── LOD 외부 식별자 단일 레지스트리 ───────────────────────────────
# 새 LOD 소스 추가 = 여기 한 줄 + persons.json 필드. 모든 표시 위치(프로필/칩/카드)가 이 정의를 따른다.
#   field : persons.json 키
#   url   : 값 → 전체 URL
#   full  : 프로필 배지 라벨 / chip : 에세이 칩 짧은 라벨(None이면 칩 미표시) / card : 카드 라벨(None이면 카드 미표시)
#   bg/fg : 카드 배지 색(None이면 기본) / work : 작품 배지 여부(추가 클래스) / title : 툴팁
LOD_SOURCES = [
    {"field": "encykorea",      "url": lambda v: v, "full": "한국민족문화대백과",        "chip": "한",   "card": "한",       "bg": "#e8f0e8", "fg": "#2a5a2a", "work": False, "title": "한국민족문화대백과"},
    {"field": "encykorea_work", "url": lambda v: v, "full": "한국민족문화대백과 (작품)", "chip": "한*",  "card": "한(작품)", "bg": "#f0ede8", "fg": "#5a3a2a", "work": True,  "title": "한국민족문화대백과 (작품)"},
    {"field": "naver_munhak",   "url": lambda v: v, "full": "한국현대문학대사전",        "chip": "문",   "card": "문학",     "bg": "#f3ead6", "fg": "#6a4e16", "work": False, "title": "네이버 지식백과 · 한국현대문학대사전"},
    {"field": "nlk",            "url": lambda v: v, "full": "NLK LOD",                 "chip": "NLK",  "card": "NLK",      "bg": "#e8eef5", "fg": "#1a3a5a", "work": False, "title": "국립중앙도서관 LOD"},
    {"field": "wikidata",       "url": lambda v: f"https://www.wikidata.org/wiki/{v}", "full": "Wikidata", "chip": "W",  "card": "W",        "bg": None,      "fg": None,      "work": False, "title": "Wikidata"},
    {"field": "isni",           "url": lambda v: f"https://isni.org/isni/{v}",         "full": "ISNI",     "chip": None, "card": None,       "bg": None,      "fg": None,      "work": False, "title": "ISNI"},
    {"field": "viaf",           "url": lambda v: v, "full": "VIAF",                    "chip": None,   "card": None,       "bg": None,      "fg": None,      "work": False, "title": "VIAF"},
]


def _lod_record(xml_id, fallback_ref=""):
    """persons.json 권위 레코드 + (wikidata 누락 시) fallback_ref에서 Q번호 보완."""
    rec = dict(_persons_record(xml_id, fallback_ref))
    if not rec.get("wikidata"):
        for uri in fallback_ref.split():
            if "wikidata.org/wiki/" in uri:
                rec["wikidata"] = uri.rstrip("/").split("/")[-1]
                break
    return rec


def _en_of(xml_id, fallback_ref=""):
    """외국 인물의 Wikidata 영문 레이블 (한국 인물은 빈 문자열)."""
    return (_persons_record(xml_id, fallback_ref) or {}).get("en", "") or ""


def _name_en_html(name, en):
    """이름 + 외국인이면 영문 괄호 병기 HTML. name은 호출부에서 _strip_parens 처리 권장."""
    return f'{name} <span class="name-en">({en})</span>' if en else name


def _canonical_label(xml_id, fallback_ref, xml_name):
    """표시용 정식 이름: persons.json 라벨 우선(없으면 XML 이름), 괄호(한자/영문) 제거.
    카드·그래프 노드·프로필 heading 등 '대표 이름'에 사용 (소월→김소월, 정희성（鄭喜成）→정희성)."""
    rec = _persons_record(xml_id, fallback_ref)
    return _strip_parens(rec.get("label") or xml_name)


def _lod_card_badges(rec):
    """카드용 LOD 배지 데이터 리스트 (JSON에 담아 JS가 그대로 렌더)."""
    out = []
    for s in LOD_SOURCES:
        if s["card"] is None:
            continue
        v = rec.get(s["field"])
        if v:
            out.append({"href": s["url"](v), "label": s["card"], "full": s["full"],
                        "bg": s["bg"] or "", "fg": s["fg"] or ""})
    return out

def _strip_parens(name: str) -> str:
    """이름에서 괄호(전각·반각) 안 한자/영문 표기 제거. 예: 김수영（金洙暎） → 김수영"""
    import re
    return re.sub(r'[\s]*[（(][^）)]+[）)]', '', name).strip()

def _persons_record(xml_id: str, fallback_ref: str = "") -> dict:
    """persons.json 레코드 반환. xml_id 직접 조회 → Wikidata Q번호로 역방향 조회 순으로 시도."""
    if xml_id in _PERSONS_REGISTRY:
        return _PERSONS_REGISTRY[xml_id]
    # 숫자 xml:id → 슬러그 (id_map) 로 persons.json 권위 레코드 조회
    _slug = _NUM_TO_SLUG.get(xml_id)
    if _slug and _slug in _PERSONS_REGISTRY:
        return _PERSONS_REGISTRY[_slug]
    # fallback_ref의 Wikidata URI에서 Q번호 추출해 역방향 조회
    for uri in fallback_ref.split():
        if "wikidata.org/wiki/" in uri:
            qid = uri.rstrip("/").split("/")[-1]
            slug = _WIKIDATA_TO_SLUG.get(qid)
            if slug:
                return _PERSONS_REGISTRY[slug]
    return {}

def _registry_ref(xml_id: str) -> str:
    """persons.json에서 xml_id의 외부 식별자 URI 문자열을 조합해 반환.
    wikidata > encykorea > nlk > isni > viaf 순으로 있는 것만 포함."""
    p = _PERSONS_REGISTRY.get(xml_id) or _PERSONS_REGISTRY.get(_NUM_TO_SLUG.get(xml_id, ""), {})
    uris = []
    if p.get("wikidata"):
        uris.append(f"https://www.wikidata.org/wiki/{p['wikidata']}")
    if p.get("encykorea"):
        uris.append(p["encykorea"])
    if p.get("nlk"):
        uris.append(p["nlk"])
    if p.get("isni"):
        uris.append(f"https://isni.org/isni/{p['isni']}")
    if p.get("viaf"):
        uris.append(p["viaf"])
    return " ".join(uris)

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


def collect_theorist_contexts(root, persons, theorists, stem, essay_title):
    """이론가별로 해당 인물이 등장하는 문장 컨텍스트 수집.
    <s> 우선, 없으면 부모 <p> 전체를 fallback으로 사용.
    ref가 외부 URI(Wikidata 등)인 경우 persons dict에서 역조회.
    반환: {pid: [{"essay_stem": ..., "essay_title": ..., "sentence": ...}, ...]}"""
    parent_map = {child: parent for parent in root.iter() for child in parent}

    # 외부 URI → pid 역방향 인덱스 (persons에 등록된 이론가만)
    uri_to_pid = {}
    for pid in theorists:
        p = persons.get(pid, {})
        ref_str = p.get("ref", "")
        # persons.json 권위 소스도 확인
        reg_ref = _registry_ref(pid)
        for uri in (ref_str + " " + reg_ref).split():
            if uri:
                uri_to_pid[uri] = pid

    def nearest_sentence_elem(elem):
        """elem 위로 올라가며 가장 가까운 <s> 또는 <p> 반환."""
        node = parent_map.get(elem)
        while node is not None:
            local = node.tag.split("}")[-1] if "}" in node.tag else node.tag
            if local in ("s", "p"):
                return node
            node = parent_map.get(node)
        return None

    ctx = defaultdict(list)
    seen = set()

    for pn in root.iter(tns("persName")):
        xml_id = get_attr_id(pn)
        ref = pn.get("ref", "")
        # 1순위: xml:id로 직접 매핑
        if xml_id and xml_id in theorists:
            pid = xml_id
        # 2순위: ref="#p-xxx" 형태
        elif ref.startswith("#") and ref[1:] in theorists:
            pid = ref[1:]
        # 3순위: ref가 외부 URI → 역조회
        elif ref and not ref.startswith("#") and ref in uri_to_pid:
            pid = uri_to_pid[ref]
        else:
            continue
        container = nearest_sentence_elem(pn)
        if container is None:
            continue
        key = (id(container), pid)
        if key in seen:
            continue
        seen.add(key)
        raw = " ".join("".join(container.itertext()).split()).strip()
        if not raw:
            continue
        sentence = raw[:300] + ("…" if len(raw) > 300 else "")
        ctx[pid].append({"essay_stem": stem, "essay_title": essay_title, "sentence": sentence})
    return ctx


def collect_interp_concepts(root):
    """interp[type='concept'] 요소에서 핵심 개념어 수집 (중복 제거).
    본문 <body> 안의 interp를 우선 순회해 excerpt를 추출하고,
    teiHeader 선언부(interpGrp)는 excerpt 없이 보완용으로만 사용."""
    parent_map = {child: parent for parent in root.iter() for child in parent}

    def find_excerpt(el):
        node = el
        while node is not None:
            node = parent_map.get(node)
            if node is None:
                break
            local = node.tag.split("}")[-1] if "}" in node.tag else node.tag
            if local in ("p", "s"):
                raw = " ".join("".join(node.itertext()).split()).strip()
                return raw[:150] + ("…" if len(raw) > 150 else "")
        return ""

    # 1단계: 본문 <body> 안의 interp — excerpt 있음
    seen = set()
    concepts = []
    body = root.find(f".//{tns('body')}")
    if body is not None:
        for el in body.iter(tns("interp")):
            if el.get("type") != "concept":
                continue
            name = "".join(el.itertext()).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            slug = re.sub(r"[^\w가-힣]", "-", name)[:40].strip("-")
            concepts.append({"name": name, "slug": slug, "excerpt": find_excerpt(el)})

    # 2단계: teiHeader interpGrp 선언 — 본문에 없는 것만 보완 (excerpt 없음)
    for el in root.iter(tns("interp")):
        if el.get("type") != "concept":
            continue
        name = "".join(el.itertext()).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        slug = re.sub(r"[^\w가-힣]", "-", name)[:40].strip("-")
        concepts.append({"name": name, "slug": slug, "excerpt": ""})

    return concepts

def extract_sources(root):
    """sourceDesc에서 서지 정보 추출. biblStruct 및 bibl 모두 처리."""
    sources = []

    # biblStruct (기존 구조)
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

    # bibl (단순 구조 — 최근 추가된 XML들)
    if not sources:
        for bibl in root.findall(f".//{tns('sourceDesc')}/{tns('bibl')}"):
            title_el = bibl.find(tns("title"))
            date_el = bibl.find(tns("date"))
            note_el = bibl.find(tns("note"))
            sources.append({
                "type": "bibl",
                "journal_or_book": (title_el.text or "").strip() if title_el is not None else "",
                "publisher": "",
                "date": (date_el.text or "").strip() if date_el is not None else "",
                "when": date_el.get("when", "") if date_el is not None else "",
                "place": "",
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
    name = p.get("name", "")
    pid = p.get("id", "")

    # persons.json 우선, 없으면 XML ref에서 추출
    reg_ref = _registry_ref(pid) if pid else ""
    xml_ref = p.get("ref", "")
    combined_ref = reg_ref if reg_ref else xml_ref

    # 칩 LOD 배지 — 레지스트리 순회 (숫자 xml:id도 id_map/wikidata로 슬러그 해석)
    rec = _lod_record(pid, combined_ref) if pid else {}
    badges = ""
    for s in LOD_SOURCES:
        if s["chip"] is None:
            continue
        v = rec.get(s["field"])
        if v:
            extra = " chip-ext-work" if s["work"] else ""
            badges += (f' <a href="{s["url"](v)}" target="_blank" '
                       f'class="chip-ext-link{extra}" title="{s["title"]}">{s["chip"]}</a>')

    if badges:
        chip = f'<span class="chip {cls}" data-id="{pid}">{name}{badges}</span>'
    else:
        chip = f'<span class="chip {cls}" data-id="{pid}">{name}</span>'
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
    # persons.json 권위 ref 우선 (숫자 xml:id도 id_map으로 해석), 없으면 XML ref
    author_ref = _registry_ref(author_id) or author.get("ref", "")

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

    # author_ref는 여러 URI(wikidata/encykorea/...)가 공백으로 이어진 문자열이므로 wikidata URI만 추출
    _author_wiki = next((u for u in author_ref.split() if "wikidata" in u), "")
    author_link = f'<a href="{_author_wiki}" target="_blank">{author_name}</a>' if _author_wiki else author_name

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
        <a href="../../writers.html">작가</a>
        <a href="../../thinkers.html">이론가</a>
        <a href="../graph.html">관계망</a>
        <a href="../../concepts.html">개념어</a>
        <a href="../../research.html">선행연구</a>
        <a href="../../criticism.html">2000년대 비평</a>
        <a href="../../ask.html">질문하기</a>
        <a href="../../about.html">소개</a>
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
      <p>kcritic — 한국 비평사 온톨로지 파일럿 · TEI XML 기반 LOD 아카이브</p>
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

        # 비평글 노드 (graph.json에는 display_year 사용 — 원발표연도 우선)
        display_year = essay.get("display_year") or year
        nodes[stem] = {"id": stem, "label": title, "type": "essay", "year": display_year}

        # 비평가 노드 (persons.json 권위 소스 우선, 없으면 XML ref)
        if author_id and author_id in persons:
            p = persons[author_id]
            reg_ref = _registry_ref(author_id)
            xml_ref = p.get("ref", "")
            nodes[author_id] = {
                "id": author_id,
                "label": _canonical_label(author_id, reg_ref if reg_ref else xml_ref, p["name"]),
                "type": "critic",
                "ref": reg_ref if reg_ref else xml_ref,
            }
            raw_edges.append((author_id, stem, "wrote"))

        # 대상 작가 노드
        for pid in subjects:
            if pid in persons:
                p = persons[pid]
                if pid not in nodes:
                    reg_ref = _registry_ref(pid)
                    nodes[pid] = {"id": pid,
                                  "label": _canonical_label(pid, reg_ref if reg_ref else p.get("ref", ""), p["name"]),
                                  "type": "writer",
                                  "ref": reg_ref if reg_ref else p.get("ref", "")}
                raw_edges.append((stem, pid, "subject_of"))

        # 이론가 노드
        for pid in theorists:
            if pid in persons:
                p = persons[pid]
                if pid not in nodes:
                    reg_ref = _registry_ref(pid)
                    nodes[pid] = {"id": pid,
                                  "label": _canonical_label(pid, reg_ref if reg_ref else p.get("ref", ""), p["name"]),
                                  "type": "theorist",
                                  "ref": reg_ref if reg_ref else p.get("ref", "")}
                raw_edges.append((stem, pid, "uses_theory"))

    # 엣지 weight 집계 (같은 source→target→type 쌍이 여러 비평글에서 반복될 때 가중치 증가)
    edge_counts = defaultdict(int)
    for src, tgt, etype in raw_edges:
        edge_counts[(src, tgt, etype)] += 1

    edges = [
        {"source": src, "target": tgt, "type": etype, "weight": cnt}
        for (src, tgt, etype), cnt in sorted(edge_counts.items())
    ]

    # 노드 degree (연결된 엣지 수 합산, weight 반영)
    degree = defaultdict(int)
    for (src, tgt, etype), cnt in edge_counts.items():
        degree[src] += cnt
        degree[tgt] += cnt

    _PERSON_TYPES = {"critic", "writer", "theorist"}
    node_list = []
    for nid, n in sorted(nodes.items()):
        n["degree"] = degree.get(nid, 0)
        if n.get("type") in _PERSON_TYPES:
            n["lod"] = _lod_card_badges(_lod_record(nid, n.get("ref", "")))
            n["en"] = _en_of(nid, n.get("ref", ""))
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


def _lod_links_html(xml_id, fallback_ref=""):
    """persons.json에서 LOD 외부 링크 뱃지 HTML 생성. 순서: encykorea → NLK → Wikidata → ISNI → VIAF
    persons.json에 없으면 fallback_ref(공백 구분 URI 문자열)에서 Wikidata 배지만 생성."""
    p = _lod_record(xml_id, fallback_ref)
    badges = []
    for s in LOD_SOURCES:
        v = p.get(s["field"])
        if v:
            cls = "lod-badge lod-badge-work" if s["work"] else "lod-badge"
            badges.append(f'<a href="{s["url"](v)}" target="_blank" class="{cls}" '
                          f'title="{s["title"]}">{s["full"]} ↗</a>')
    # persons.json 미스 시 fallback_ref의 Wikidata URI로 배지 생성
    if not badges and fallback_ref:
        for uri in fallback_ref.split():
            if "wikidata" in uri:
                badges.append(f'<a href="{uri}" target="_blank" class="lod-badge" title="Wikidata">Wikidata ↗</a>')
            elif "lod.nl.go.kr" in uri:
                badges.append(f'<a href="{uri}" target="_blank" class="lod-badge" title="국립중앙도서관 LOD">NLK LOD ↗</a>')
            elif "encykorea" in uri:
                badges.append(f'<a href="{uri}" target="_blank" class="lod-badge" title="한국민족문화대백과">한국민족문화대백과 ↗</a>')
    if not badges:
        return ""
    return '<div class="lod-links">' + " ".join(badges) + '</div>'


def build_critic_profile(critic_id, critic_info, essays, graph_data=None):
    """비평가 한 명의 프로필 페이지 생성. essays = 해당 비평가의 비평글 데이터 목록."""
    name = critic_info["name"]
    reg_ref = _registry_ref(critic_id)
    xml_ref = critic_info.get("ref", "")
    ref = reg_ref if reg_ref else xml_ref
    heading_name = _name_en_html(name, _en_of(critic_id, ref))
    wikidata_link = ""
    if ref and "wikidata" in ref:
        for uri in ref.split():
            if "wikidata" in uri:
                wikidata_link = f'<a href="{uri}" target="_blank" class="chip role-critic chip-linked">{name} <span class="chip-ext">↗</span></a>'
                break
    if not wikidata_link:
        wikidata_link = f'<span class="chip role-critic">{name}</span>'
    lod_links = _lod_links_html(critic_id, ref)

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
    top_theorists = sorted(theorist_count.items(), key=lambda x: (-x[1], x[0]))
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
    top_subjects = sorted(subject_count.items(), key=lambda x: (-x[1], x[0]))
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
        <a href="../../writers.html">작가</a>
        <a href="../../thinkers.html">이론가</a>
        <a href="../graph.html">관계망</a>
        <a href="../../concepts.html">개념어</a>
        <a href="../../research.html">선행연구</a>
        <a href="../../criticism.html">2000년대 비평</a>
        <a href="../../ask.html">질문하기</a>
        <a href="../../about.html">소개</a>
      </nav>
    </div>
  </header>

  <main class="container index-main">
    <section class="critic-profile-hero">
      <div class="critic-profile-byline">{wikidata_link}</div>
      <h1 class="index-heading">{heading_name}</h1>
      {lod_links}
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
      <p>kcritic — 한국 비평사 온톨로지 파일럿 · TEI XML 기반 LOD 아카이브</p>
    </div>
  </footer>
</body>
</html>"""


def build_writer_profile(writer_id, writer_info, essays_about):
    """작가 한 명의 프로필 페이지. essays_about = 이 작가를 비평 대상으로 다룬 에세이 목록."""
    name = writer_info["name"]
    reg_ref = _registry_ref(writer_id)
    xml_ref = writer_info.get("ref", "")
    ref = reg_ref if reg_ref else xml_ref
    heading_name = _name_en_html(name, _en_of(writer_id, ref))

    wikidata_uri = ""
    for uri in ref.split():
        if "wikidata" in uri:
            wikidata_uri = uri
            break

    if wikidata_uri:
        name_chip = f'<a href="{wikidata_uri}" target="_blank" class="chip role-writer chip-linked">{name} <span class="chip-ext">↗</span></a>'
    else:
        name_chip = f'<span class="chip role-writer">{name}</span>'
    lod_links = _lod_links_html(writer_id, fallback_ref=ref)

    # 비평가 집계 — 이 작가를 다룬 비평가
    critic_count = defaultdict(int)
    critic_names = {}
    for e in essays_about:
        aid = e["author_id"]
        if aid:
            critic_count[aid] += 1
            critic_names[aid] = e["persons"].get(aid, {}).get("name", aid)

    critics_chips_html = " ".join(
        f'<a href="../critics/{cid}.html" class="chip role-critic chip-linked">{critic_names[cid]} ({cnt}편)<span class="chip-ext"> →</span></a>'
        for cid, cnt in sorted(critic_count.items(), key=lambda x: (-x[1], x[0]))
    ) if critic_count else '<span class="muted">—</span>'

    # 비평글 카드 목록
    essay_cards = []
    for e in sorted(essays_about, key=lambda x: x.get("display_year") or x["year"]):
        aid = e["author_id"]
        critic_name = e["persons"].get(aid, {}).get("name", "") if aid else ""
        card_year = e.get("display_year") or e["year"]
        essay_cards.append(f"""
      <article class="essay-card">
        <div class="essay-card-meta">
          <span class="essay-card-year">{card_year}</span>
          {f'<a href="../critics/{aid}.html" class="chip role-critic chip-linked" style="font-size:0.8rem;padding:2px 8px;">{critic_name}</a>' if aid else ''}
        </div>
        <h3 class="essay-card-title">
          <a href="../essays/{e["stem"]}.html">{e["title"]}</a>
        </h3>
        <p class="essay-card-source">{_source_short(e["sources"])}</p>
      </article>""")

    essay_count = len(essays_about)

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
        <a href="../../critics.html">비평가</a>
        <a href="../../writers.html" class="active">작가</a>
        <a href="../../thinkers.html">이론가</a>
        <a href="../graph.html">관계망</a>
        <a href="../../concepts.html">개념어</a>
        <a href="../../research.html">선행연구</a>
        <a href="../../criticism.html">2000년대 비평</a>
        <a href="../../ask.html">질문하기</a>
        <a href="../../about.html">소개</a>
      </nav>
    </div>
  </header>

  <main class="container index-main">
    <section class="critic-profile-hero">
      <div class="critic-profile-byline">{name_chip}</div>
      <h1 class="index-heading">{heading_name}</h1>
      {lod_links}
      <div class="stat-row">
        <div class="stat"><span class="stat-num">{essay_count}</span><span class="stat-label">관련 비평글</span></div>
        <div class="stat"><span class="stat-num">{len(critic_count)}</span><span class="stat-label">비평한 비평가</span></div>
      </div>
    </section>

    <section class="critic-profile-meta">
      <div class="meta-section">
        <h2 class="meta-label">이 작가를 비평한 비평가</h2>
        <div class="chip-group">{critics_chips_html}</div>
      </div>
    </section>

    <section class="essay-grid">
      <h2 class="section-label">관련 비평글 ({essay_count}편)</h2>
      {"".join(essay_cards)}
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>kcritic — 한국 비평사 온톨로지 파일럿 · TEI XML 기반 LOD 아카이브</p>
    </div>
  </footer>
</body>
</html>"""


def build_thinker_profile(thinker_id, thinker_info):
    """이론가 한 명의 프로필 페이지.
    thinker_info = {name, ref, essay_count, essays:[{stem,title,year,critic_id,critic_name}], contexts:[{essay_stem,essay_title,sentence}]}"""
    name = thinker_info["name"]
    reg_ref = _registry_ref(thinker_id)
    xml_ref = thinker_info.get("ref", "")
    ref = reg_ref if reg_ref else xml_ref
    heading_name = _name_en_html(name, _en_of(thinker_id, ref))
    lod_links = _lod_links_html(thinker_id, fallback_ref=ref)

    wikidata_uri = ""
    for uri in ref.split():
        if "wikidata" in uri:
            wikidata_uri = uri
            break

    if wikidata_uri:
        name_chip = f'<a href="{wikidata_uri}" target="_blank" class="chip role-theorist chip-linked">{name} <span class="chip-ext">↗</span></a>'
    else:
        name_chip = f'<span class="chip role-theorist">{name}</span>'

    # 이 이론가를 인용한 비평가 집계
    critic_count = defaultdict(int)
    critic_names = {}
    for e in thinker_info["essays"]:
        cid = e["critic_id"]
        if cid:
            critic_count[cid] += 1
            critic_names[cid] = e["critic_name"]

    critics_chips_html = " ".join(
        f'<a href="../critics/{cid}.html" class="chip role-critic chip-linked">{critic_names[cid]} ({cnt}편)<span class="chip-ext"> →</span></a>'
        for cid, cnt in sorted(critic_count.items(), key=lambda x: (-x[1], x[0]))
    ) if critic_count else '<span class="muted">—</span>'

    # 인용 비평글 카드 목록 (중복 제거, 연도순)
    seen_stems = set()
    essay_cards = []
    for e in sorted(thinker_info["essays"], key=lambda x: x.get("year") or ""):
        stem = e["stem"]
        if stem in seen_stems:
            continue
        seen_stems.add(stem)
        cid = e["critic_id"]
        cname = e["critic_name"]
        essay_cards.append(f"""
      <article class="essay-card">
        <div class="essay-card-meta">
          <span class="essay-card-year">{e.get("year", "")}</span>
          {f'<a href="../critics/{cid}.html" class="chip role-critic chip-linked" style="font-size:0.8rem;padding:2px 8px;">{cname}</a>' if cid else ''}
        </div>
        <h3 class="essay-card-title">
          <a href="../essays/{stem}.html">{e["title"]}</a>
        </h3>
      </article>""")

    # 인용 문맥 섹션
    contexts = thinker_info.get("contexts", [])
    context_items = []
    for ctx in contexts:
        essay_link = f'<a href="../essays/{ctx["essay_stem"]}.html" class="ctx-essay-link">{ctx["essay_title"]}</a>'
        cid = ctx.get("critic_id", "")
        cname = ctx.get("critic_name", "")
        critic_part = f'<a href="../critics/{cid}.html" class="ctx-critic-link">{cname}</a> · ' if cid and cname else ""
        context_items.append(f"""
        <li class="context-item">
          <div class="context-sentence">"{ctx["sentence"]}"</div>
          <div class="context-source">— {critic_part}{essay_link}</div>
        </li>""")
    contexts_html = f"""
    <section class="critic-profile-meta">
      <div class="meta-section">
        <h2 class="meta-label">인용 문맥 ({len(contexts)}건)</h2>
        <ul class="context-list">{"".join(context_items)}</ul>
      </div>
    </section>""" if context_items else ""

    essay_count = len(seen_stems)

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
        <a href="../../critics.html">비평가</a>
        <a href="../../writers.html">작가</a>
        <a href="../../thinkers.html" class="active">이론가</a>
        <a href="../graph.html">관계망</a>
        <a href="../../concepts.html">개념어</a>
        <a href="../../research.html">선행연구</a>
        <a href="../../criticism.html">2000년대 비평</a>
        <a href="../../ask.html">질문하기</a>
        <a href="../../about.html">소개</a>
      </nav>
    </div>
  </header>

  <main class="container index-main">
    <section class="critic-profile-hero">
      <div class="critic-profile-byline">{name_chip}</div>
      <h1 class="index-heading">{heading_name}</h1>
      {lod_links}
      <div class="stat-row">
        <div class="stat"><span class="stat-num">{essay_count}</span><span class="stat-label">인용 비평글</span></div>
        <div class="stat"><span class="stat-num">{len(critic_count)}</span><span class="stat-label">인용한 비평가</span></div>
        <div class="stat"><span class="stat-num">{len(contexts)}</span><span class="stat-label">인용 문맥</span></div>
      </div>
    </section>

    <section class="critic-profile-meta">
      <div class="meta-section">
        <h2 class="meta-label">이 이론가를 인용한 비평가</h2>
        <div class="chip-group">{critics_chips_html}</div>
      </div>
    </section>

    {contexts_html}

    <section class="essay-grid">
      <h2 class="section-label">인용된 비평글 ({essay_count}편)</h2>
      {"".join(essay_cards)}
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>kcritic — 한국 비평사 온톨로지 파일럿 · TEI XML 기반 LOD 아카이브</p>
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
            reg_ref = _registry_ref(aid)
            critics[aid] = {"id": aid, "name": _strip_parens(p.get("name", aid)), "ref": reg_ref if reg_ref else p.get("ref", ""), "essays": []}
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

    # 비평가 = titleStmt > author > persName 에서 추출 (TEI 표준)
    # xml:id 있으면 그대로 사용, ref="#p-xxx" 형태면 p-xxx 추출
    author_id = ""
    auth_pn = root.find(f".//{tns('titleStmt')}/{tns('author')}/{tns('persName')}")
    if auth_pn is not None:
        pid = get_attr_id(auth_pn)
        ref = auth_pn.get("ref", "")
        role = auth_pn.get("role", "")
        name = "".join(auth_pn.itertext()).strip()
        if pid:
            author_id = pid
        elif ref.startswith("#"):
            author_id = ref[1:]
        # persons dict에 없으면 추가 (ref-only 참조라 collect_persons가 못 잡은 경우)
        if author_id and author_id not in persons:
            persons[author_id] = {"id": author_id, "name": name, "role": role, "ref": ""}

    # 이론가 = scholar 또는 foreigner scholar — 비평 대상 작가 제외
    theorists = set()
    for pid, p in persons.items():
        role = p.get("role", "")
        if ("scholar" in role) and pid not in subjects and pid != author_id:
            theorists.add(pid)

    theorist_contexts = collect_theorist_contexts(root, persons, theorists, xml_path.stem, title)

    original_year = get_original_year(sources)
    # display_year: 원발표연도 > note 추출연도 > 파일명 suffix > sources 연도
    stem_year_match = re.search(r"_(\d{4})$", xml_path.stem)
    stem_year = stem_year_match.group(1) if stem_year_match else ""
    display_year = original_year or stem_year or year
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
        "theorist_contexts": theorist_contexts,
    }


def main():
    print("TEI XML -> 메타데이터 HTML 변환 시작")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CRITICS_DIR.mkdir(parents=True, exist_ok=True)
    WRITERS_DIR.mkdir(parents=True, exist_ok=True)
    THINKERS_DIR.mkdir(parents=True, exist_ok=True)
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

    # 개념어 JSON (concepts.html에서 사용)
    concept_map = defaultdict(list)  # concept_name -> [essay 정보]
    for e in all_essays:
        for c in e.get("concepts", []):
            concept_map[c["name"]].append({
                "stem": e["stem"],
                "title": e["title"],
                "critic": _strip_parens(e["persons"].get(e.get("author_id"), {}).get("name", "")),
                "year": e.get("display_year") or e["year"],
                "excerpt": c.get("excerpt", ""),
            })
    concepts_json = [
        {
            "name": name,
            "slug": re.sub(r"[^\w가-힣]", "-", name)[:40].strip("-"),
            "essay_count": len(essays),
            "essays": essays,
        }
        for name, essays in sorted(concept_map.items(), key=lambda x: -len(x[1]))
    ]
    concepts_path = DATA_DIR / "concepts.json"
    concepts_path.write_text(json.dumps(concepts_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  OK concepts.json -> {concepts_path} ({len(concepts_json)} concepts)")

    # 비평가 목록 JSON (critics.html에서 사용)
    critics_json = [
        {
            "id": cid,
            "name": cinfo["name"],
            "ref": cinfo["ref"],
            "lod": _lod_card_badges(_lod_record(cid, cinfo["ref"])),
            "essay_count": len(cinfo["essays"]),
            "subjects": sorted({pid for e in cinfo["essays"] for pid in e["subjects"]}),
            "theorists": sorted({pid for e in cinfo["essays"] for pid in e["theorists"]}),
        }
        for cid, cinfo in critics.items()
    ]
    critics_path = DATA_DIR / "critics.json"
    critics_path.write_text(json.dumps(critics_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  OK critics.json -> {critics_path} ({len(critics_json)} critics)")

    # 작가 프로필 페이지 + 작가 목록 JSON
    # writer_id -> {info, essays[]} 수집
    writers_map = {}
    for e in all_essays:
        for pid in e["subjects"]:
            p = e["persons"].get(pid, {})
            if not p:
                continue
            if pid not in writers_map:
                reg_ref = _registry_ref(pid)
                writers_map[pid] = {"id": pid, "name": _canonical_label(pid, reg_ref if reg_ref else p.get("ref", ""), p.get("name", pid)), "ref": reg_ref if reg_ref else p.get("ref", ""), "essays": []}
            writers_map[pid]["essays"].append(e)

    for wid, winfo in writers_map.items():
        html = build_writer_profile(wid, winfo, winfo["essays"])
        out = WRITERS_DIR / f"{wid}.html"
        out.write_text(html, encoding="utf-8")
        print(f"  OK writer profile -> {out}")

    writers_json = [
        {
            "id": wid,
            "name": winfo["name"],
            "en": _en_of(wid, winfo["ref"]),
            "ref": winfo["ref"],
            "lod": _lod_card_badges(_lod_record(wid, winfo["ref"])),
            "essay_count": len(winfo["essays"]),
            "critics": sorted({e["author_id"] for e in winfo["essays"] if e["author_id"]}),
        }
        for wid, winfo in sorted(writers_map.items(), key=lambda x: (-len(x[1]["essays"]), x[0]))
    ]
    writers_path = DATA_DIR / "writers.json"
    writers_path.write_text(json.dumps(writers_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  OK writers.json -> {writers_path} ({len(writers_json)} writers)")

    # 이론가 프로필 페이지 + 이론가 목록 JSON
    # thinker_id -> {id, name, ref, essays:[{stem,title,year,critic_id,critic_name}], contexts:[...]}
    thinkers_map = {}
    for e in all_essays:
        cid = e["author_id"]
        cname = e["persons"].get(cid, {}).get("name", "") if cid else ""
        eyear = e.get("display_year") or e["year"]
        for pid in e["theorists"]:
            p = e["persons"].get(pid, {})
            if not p:
                continue
            if pid not in thinkers_map:
                reg_ref = _registry_ref(pid)
                thinkers_map[pid] = {
                    "id": pid,
                    "name": _canonical_label(pid, reg_ref if reg_ref else p.get("ref", ""), p.get("name", pid)),
                    "ref": reg_ref if reg_ref else p.get("ref", ""),
                    "essays": [],
                    "contexts": [],
                }
            thinkers_map[pid]["essays"].append({
                "stem": e["stem"],
                "title": e["title"],
                "year": eyear,
                "critic_id": cid,
                "critic_name": cname,
            })
        # 인용 문맥 병합 — 비평가 정보도 함께 추가
        for pid, ctx_list in e.get("theorist_contexts", {}).items():
            if pid in thinkers_map:
                for ctx in ctx_list:
                    thinkers_map[pid]["contexts"].append({
                        **ctx,
                        "critic_id": cid,
                        "critic_name": cname,
                    })

    for tid, tinfo in thinkers_map.items():
        html = build_thinker_profile(tid, tinfo)
        out = THINKERS_DIR / f"{tid}.html"
        out.write_text(html, encoding="utf-8")
        print(f"  OK thinker profile -> {out}")

    thinkers_json = [
        {
            "id": tid,
            "name": tinfo["name"],
            "en": _en_of(tid, tinfo["ref"]),
            "ref": tinfo["ref"],
            "lod": _lod_card_badges(_lod_record(tid, tinfo["ref"])),
            "essay_count": len({e["stem"] for e in tinfo["essays"]}),
            "critics": sorted({e["critic_id"] for e in tinfo["essays"] if e["critic_id"]}),
            "context_count": len(tinfo["contexts"]),
        }
        for tid, tinfo in sorted(thinkers_map.items(), key=lambda x: (-len({e["stem"] for e in x[1]["essays"]}), x[0]))
    ]
    thinkers_path = DATA_DIR / "thinkers.json"
    thinkers_path.write_text(json.dumps(thinkers_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  OK thinkers.json -> {thinkers_path} ({len(thinkers_json)} thinkers)")

    # RDF Turtle 발행
    ttl = build_turtle(all_essays, graph)
    ttl_path = DATA_DIR / "graph.ttl"
    ttl_path.write_text(ttl, encoding="utf-8")
    triple_count = ttl.count(" .\n")
    print(f"  OK graph.ttl -> {ttl_path} (~{triple_count} triples)")

    print("\n완료.")


# ── RDF Turtle 생성 ──────────────────────────────────────────
# critic_v5_kcritic.rdf 온톨로지 (http://kcritic.kr/ontology/critic#) 준거:
#   클래스: critic:Critic, critic:CriticalEssay, foaf:Person
#   프로퍼티: critic:analyzes (비평가→인물), dcterms:creator (에세이→비평가),
#             cito:discusses (에세이→인물), foaf:name, dcterms:title, dcterms:date

BASE_URI = "https://kcritic.kr/resource/"
ESSAY_PAGE_BASE = "https://kcritic.kr/site/essays/"

# TEI ref에 Wikidata URI가 없는 인물의 보완 매핑 (이름 → Wikidata URI)
_WIKIDATA_FALLBACK = {
    "김우창":  "http://www.wikidata.org/entity/Q17129594",
    "김윤식":  "http://www.wikidata.org/entity/Q12594764",
    "김종길":  "http://www.wikidata.org/entity/Q12594791",
    "유종호":  "http://www.wikidata.org/entity/Q12607768",
    "김소월":  "http://www.wikidata.org/entity/Q484063",
    "김수영":  "http://www.wikidata.org/entity/Q12594637",
    "김현승":  "http://www.wikidata.org/entity/Q12594919",
    "박두진":  "http://www.wikidata.org/entity/Q12598972",
    "박목월":  "http://www.wikidata.org/entity/Q12598974",
    "서정주":  "http://www.wikidata.org/entity/Q487022",
    "신동엽":  "http://www.wikidata.org/entity/Q12600842",
    "안수길":  "http://www.wikidata.org/entity/Q12604192",
    "윤동주":  "http://www.wikidata.org/entity/Q493297",
    "정지용":  "http://www.wikidata.org/entity/Q12617484",
    "정현종":  "http://www.wikidata.org/entity/Q12617486",
    "조지훈":  "http://www.wikidata.org/entity/Q12610858",
    "주요한":  "http://www.wikidata.org/entity/Q12614972",
    "천상병":  "http://www.wikidata.org/entity/Q12612988",
    "최남선":  "http://www.wikidata.org/entity/Q484710",
    "최인훈":  "http://www.wikidata.org/entity/Q491597",
    "피천득":  "http://www.wikidata.org/entity/Q12619274",
    "하버마스": "http://www.wikidata.org/entity/Q76357",
    "한용운":  "http://www.wikidata.org/entity/Q484383",
}

def _ttl_str(s):
    """Turtle 문자열 이스케이프."""
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

def _ttl_uri(s):
    return f"<{s}>"

def build_turtle(all_essays, graph):
    lines = [
        "# 한국 비평사 온톨로지 — RDF Turtle 직렬화",
        "# 온톨로지 준거: http://kcritic.kr/ontology/critic# (critic_v7_kcritic.rdf)",
        "",
        "@prefix kc:      <https://kcritic.kr/resource/> .",
        "@prefix kce:     <https://kcritic.kr/resource/essay/> .",
        "@prefix critic:  <http://kcritic.kr/ontology/critic#> .",
        "@prefix foaf:    <http://xmlns.com/foaf/0.1/> .",
        "@prefix cito:    <http://purl.org/spar/cito/> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        "@prefix owl:     <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix schema:  <https://schema.org/> .",
        "@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .",
        "",
        "# ── 인물 노드 ────────────────────────────────────────────",
    ]

    # 인물 노드 수집 (모든 에세이의 persons 병합, 중복 제거)
    all_persons = {}
    for essay in all_essays:
        for pid, p in essay["persons"].items():
            if pid not in all_persons:
                all_persons[pid] = p
            elif not all_persons[pid].get("ref") and p.get("ref"):
                all_persons[pid]["ref"] = p["ref"]

    # 인물 타입 수집 (graph.json nodes에서)
    node_type_map = {n["id"]: n["type"] for n in graph["nodes"]}

    # critic:analyzes 집계 (비평가 → 비평 대상 인물 직접 관계)
    analyzes_map = defaultdict(set)  # critic_id -> {writer_id, ...}

    for pid, p in sorted(all_persons.items()):
        ntype = node_type_map.get(pid, "")
        # critic:Critic / foaf:Person 클래스 매핑 (온톨로지 준거)
        cls_map = {
            "critic":   "critic:Critic",
            "writer":   "foaf:Person",
            "theorist": "foaf:Person",
        }
        cls = cls_map.get(ntype)
        if not cls:
            continue
        name = p.get("name", "")
        ref = _registry_ref(pid) or p.get("ref", "")

        triples = [f"kc:{pid} a {cls} ;"]
        triples.append(f'  foaf:name {_ttl_str(name)}@ko ;')
        triples.append(f'  rdfs:label {_ttl_str(name)}@ko ;')

        # Wikidata sameAs: TEI ref 우선, 없으면 fallback 딕셔너리에서 보완
        wikidata_uri = ""
        for uri in ref.split():
            if "wikidata" in uri:
                wikidata_uri = uri
                break
        if not wikidata_uri and name in _WIKIDATA_FALLBACK:
            wikidata_uri = _WIKIDATA_FALLBACK[name]
        if wikidata_uri:
            triples.append(f'  owl:sameAs {_ttl_uri(wikidata_uri)} ;')

        triples.append(f'  schema:url {_ttl_uri(BASE_URI + pid)} .')
        lines.extend(triples)
        lines.append("")

    lines.append("# ── 비평글 노드 ─────────────────────────────────────────")

    for essay in all_essays:
        stem = essay["stem"]
        title = essay["title"]
        display_year = essay.get("display_year") or essay["year"]
        author_id = essay["author_id"]
        sources = essay["sources"]
        concepts = essay.get("concepts", [])

        pub_info = ""
        if sources:
            s = sources[0]
            pub_info = s.get("journal_or_book", "")

        # critic:CriticalEssay 클래스 사용 (온톨로지 준거)
        triples = [f"kce:{stem} a critic:CriticalEssay ;"]
        triples.append(f'  dcterms:title {_ttl_str(title)}@ko ;')
        triples.append(f'  rdfs:label {_ttl_str(title)}@ko ;')
        if display_year:
            triples.append(f'  dcterms:date "{display_year}"^^xsd:gYear ;')
        if pub_info:
            triples.append(f'  schema:isPartOf {_ttl_str(pub_info)} ;')
        triples.append(f'  schema:url {_ttl_uri(ESSAY_PAGE_BASE + stem + ".html")} ;')
        if author_id:
            # dcterms:creator (온톨로지 준거)
            triples.append(f'  dcterms:creator kc:{author_id} ;')
        # cito:discusses — 비평 대상 작가 (비평적 분석의 직접 대상)
        for pid in sorted(essay["subjects"]):
            triples.append(f'  cito:discusses kc:{pid} ;')
            if author_id:
                analyzes_map[author_id].add(pid)
        # cito:citesAsAuthority — 이론가 (권위로 인용, 비평 대상과 구별)
        for pid in sorted(essay["theorists"]):
            triples.append(f'  cito:citesAsAuthority kc:{pid} ;')
        # 개념어
        for c in concepts:
            triples.append(f'  dcterms:subject {_ttl_str(c["name"])}@ko ;')
        # 마지막 세미콜론을 마침표로
        if triples[-1].endswith(" ;"):
            triples[-1] = triples[-1][:-2] + " ."
        else:
            triples.append("  .")
        lines.extend(triples)
        lines.append("")

    # 비평가 → 에세이 wrote + critic:analyzes (온톨로지 핵심 관계)
    lines.append("# ── 비평가 관계 (wrote / critic:analyzes) ───────────────")
    wrote_by_critic = defaultdict(list)
    for essay in all_essays:
        if essay["author_id"]:
            wrote_by_critic[essay["author_id"]].append(essay["stem"])

    for cid, stems in sorted(wrote_by_critic.items()):
        for stem in stems:
            lines.append(f"kc:{cid} dcterms:creator kce:{stem} .")
        # critic:analyzes (비평가 → 비평 대상 직접 관계, 온톨로지 핵심 관계)
        for target_pid in sorted(analyzes_map.get(cid, set())):
            lines.append(f"kc:{cid} critic:analyzes kc:{target_pid} .")
        lines.append("")

    return "\n".join(lines)


def sync_neo4j(graph: dict):
    """graph.json 데이터를 Neo4j에 동기화."""
    try:
        from neo4j import GraphDatabase
        from dotenv import load_dotenv
        import os
        load_dotenv()
        uri  = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        pwd  = os.getenv("NEO4J_PASSWORD", "")
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        driver.verify_connectivity()
    except Exception as e:
        print(f"  Neo4j 연결 실패 (건너뜀): {e}")
        return

    nodes = graph["nodes"]
    edges = graph["edges"]
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
        for n in nodes:
            label = n.get("type", "node").capitalize()
            s.run(
                f"MERGE (n:{label} {{id: $id}}) "
                "SET n.label=$label, n.type=$type, n.year=$year, n.ref=$ref, n.degree=$degree",
                id=n["id"], label=n.get("label",""), type=n.get("type",""),
                year=n.get("year",""), ref=n.get("ref",""), degree=n.get("degree",0),
            )
        for e in edges:
            rel = e.get("type","related").upper().replace("-","_")
            s.run(
                f"MATCH (a {{id:$src}}),(b {{id:$tgt}}) MERGE (a)-[r:{rel}]->(b) SET r.weight=$w",
                src=e["source"], tgt=e["target"], w=e.get("weight",1),
            )
    driver.close()
    print(f"  Neo4j 동기화 완료: 노드 {len(nodes)}개, 엣지 {len(edges)}개")


if __name__ == "__main__":
    main()
    # Neo4j 동기화 (Neo4j가 실행 중일 때만 작동, 꺼져있으면 자동 건너뜀)
    print("\nNeo4j 동기화 시도 중...")
    graph_path = DATA_DIR / "graph.json"
    if graph_path.exists():
        with open(graph_path, encoding="utf-8") as f:
            graph_data = json.load(f)
        sync_neo4j(graph_data)
    else:
        print("  graph.json 없음, 동기화 건너뜀")
