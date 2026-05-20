"""
TEI XML → 정적 HTML 변환 스크립트
로컬에서만 실행. essays/*.xml 읽어서 site/essays/*.html 생성.
원문 XML은 절대 GitHub에 올라가지 않음.
"""

import os
import re
from pathlib import Path
from xml.etree import ElementTree as ET

TEI_NS = "http://www.tei-c.org/ns/1.0"
ESSAYS_DIR = Path("essays")
OUTPUT_DIR = Path("site/essays")

def ns(tag):
    return f"{{{TEI_NS}}}{tag}"

def get_text(elem, tag):
    el = elem.find(f".//{ns(tag)}")
    return el.text.strip() if el is not None and el.text else ""

def render_inline(elem):
    """TEI 인라인 요소를 HTML span으로 변환."""
    tag = elem.tag.replace(f"{{{TEI_NS}}}", "")
    text = elem.text or ""
    tail = elem.tail or ""

    children_html = "".join(render_inline(c) for c in elem)

    if tag == "s":
        return f'<span class="tei-s">{text}{children_html}</span>{tail}'
    elif tag == "persName":
        ref = elem.get("ref", "")
        role = elem.get("role", "")
        xml_id = elem.get("{http://www.w3.org/XML/1998/namespace}id", "")
        attrs = f' class="tei-persname" data-role="{role}"'
        if ref and ref.startswith("http"):
            attrs += f' title="{ref}"'
        if xml_id:
            attrs += f' id="{xml_id}"'
        return f'<span{attrs}>{text}{children_html}</span>{tail}'
    elif tag == "title":
        level = elem.get("level", "")
        # 작품 제목 표기: a레벨은 「」, m레벨은 『』
        if level == "a":
            return f'<cite class="tei-title tei-title-a">「{text}{children_html}」</cite>{tail}'
        elif level == "m":
            return f'<cite class="tei-title tei-title-m">『{text}{children_html}』</cite>{tail}'
        else:
            return f'<cite class="tei-title">{text}{children_html}</cite>{tail}'
    elif tag == "quote":
        q_type = elem.get("type", "")
        source = elem.get("source", "")
        genre = elem.get("genre", "")
        attrs = f' class="tei-quote tei-quote-{q_type}" data-genre="{genre}"'
        source_html = f'<footer class="quote-source">{source}</footer>' if source else ""
        return f'<blockquote{attrs}><p>{text}{children_html}</p>{source_html}</blockquote>{tail}'
    elif tag == "interp":
        value = elem.get("value", "")
        return f'<mark class="tei-interp tei-interp-{value}" data-value="{value}">{text}{children_html}</mark>{tail}'
    elif tag == "term":
        return f'<span class="tei-term">{text}{children_html}</span>{tail}'
    elif tag == "lb":
        return f'<br>{tail}'
    elif tag == "note":
        return f'<span class="tei-note">{text}{children_html}</span>{tail}'
    elif tag == "head":
        return ""  # div head는 상위에서 처리
    else:
        return f'{text}{children_html}{tail}'

def render_p(p_elem):
    content = (p_elem.text or "") + "".join(render_inline(c) for c in p_elem)
    return f'<p>{content}</p>'

def render_div(div_elem, depth=1):
    div_type = div_elem.get("type", "section")
    xml_id = div_elem.get("{http://www.w3.org/XML/1998/namespace}id", "")
    id_attr = f' id="{xml_id}"' if xml_id else ""

    head_el = div_elem.find(ns("head"))
    head_html = ""
    if head_el is not None and head_el.text:
        htag = f"h{min(depth + 1, 6)}"
        head_html = f'<{htag} class="section-head">{head_el.text.strip()}</{htag}>'

    paragraphs = "".join(render_p(p) for p in div_elem.findall(ns("p")))

    nested = "".join(render_div(d, depth + 1) for d in div_elem.findall(ns("div")))

    return f'<section class="tei-div tei-div-{div_type}"{id_attr}>{head_html}{paragraphs}{nested}</section>'

def extract_meta(root):
    """teiHeader에서 메타데이터 추출."""
    title = ""
    author = ""
    pub_year = ""
    sources = []

    title_el = root.find(f".//{ns('titleStmt')}/{ns('title')}")
    if title_el is not None:
        title = (title_el.text or "").strip()

    author_el = root.find(f".//{ns('titleStmt')}/{ns('author')}/{ns('persName')}")
    if author_el is not None:
        author = (author_el.text or "").strip()

    for biblstruct in root.findall(f".//{ns('sourceDesc')}/{ns('biblStruct')}"):
        btype = biblstruct.get("type", "")
        monogr = biblstruct.find(ns("monogr"))
        if monogr is None:
            continue
        monogr_title_el = monogr.find(ns("title"))
        pub_el = monogr.find(f"{ns('imprint')}/{ns('publisher')}")
        date_el = monogr.find(f"{ns('imprint')}/{ns('date')}")
        monogr_title = (monogr_title_el.text or "").strip() if monogr_title_el is not None else ""
        pub = (pub_el.text or "").strip() if pub_el is not None else ""
        date_text = (date_el.text or "").strip() if date_el is not None else ""
        when = date_el.get("when", "") if date_el is not None else ""
        if when and len(when) >= 4:
            pub_year = when[:4]
        sources.append({"type": btype, "title": monogr_title, "pub": pub, "date": date_text})

    return {"title": title, "author": author, "year": pub_year, "sources": sources}

def make_source_html(sources):
    if not sources:
        return ""
    items = []
    for s in sources:
        label = "저널" if s["type"] == "journal" else "단행본"
        items.append(f'<li><span class="source-type">{label}</span> {s["title"]}, {s["pub"]}, {s["date"]}</li>')
    return '<ul class="source-list">' + "".join(items) + "</ul>"

def convert(xml_path: Path, output_path: Path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    meta = extract_meta(root)

    body = root.find(f".//{ns('body')}")
    if body is None:
        print(f"  [경고] <body> 없음: {xml_path.name}")
        return

    sections_html = "".join(render_div(d) for d in body.findall(ns("div")))
    source_html = make_source_html(meta["sources"])

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{meta['title']} — 한국 비평사 온톨로지</title>
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
          <span class="essay-author">{meta['author']}</span>
          <span class="essay-year">{meta['year']}</span>
        </div>
        <h1 class="essay-title">{meta['title']}</h1>
        {source_html}
      </header>

      <div class="essay-body">
        {sections_html}
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"  OK {xml_path.name} -> {output_path}")

def main():
    print("TEI XML → HTML 변환 시작")
    xml_files = list(ESSAYS_DIR.glob("*.xml"))
    if not xml_files:
        print(f"  [오류] {ESSAYS_DIR}/ 에 XML 파일이 없습니다.")
        return
    for xml_path in sorted(xml_files):
        stem = xml_path.stem
        out = OUTPUT_DIR / f"{stem}.html"
        try:
            convert(xml_path, out)
        except Exception as e:
            print(f"  [오류] {xml_path.name}: {e}")
    print(f"\n완료. {OUTPUT_DIR}/ 폴더 확인하세요.")

if __name__ == "__main__":
    main()
