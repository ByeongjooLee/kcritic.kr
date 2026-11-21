# -*- coding: utf-8 -*-
"""사이트 투명성 메타데이터 빌드 (2026-11-21)

원본은 site/data/datasets.json 하나다(운영 주체·이용 조건·자료 묶음별 출처·기준일·가공·한계).
이 스크립트는 그 파일을 읽어

  1. 자료 묶음별 규모(counts)와, 데이터 파일에 기준일이 적혀 있는 묶음의 기준일(as_of)을
     실제 공개 파일에서 다시 세어 datasets.json 에 되쓴다 (손으로 적은 숫자를 두지 않는다).
  2. site/data/void.ttl — graph.ttl 등 공개 파일을 VoID/DCAT 로 설명하는 RDF.
     이용 조건이 정해지지 않은 묶음에는 dcterms:license 를 쓰지 않는다(지어내지 않는다).
  3. data.html · index.html 의 JSON-LD 블록(<!-- JSONLD-START --> ~ <!-- JSONLD-END -->)을 다시 쓴다.

실행:  py -X utf8 build_site_meta.py          (build.py → build_site_v2.py 다음, 표준 라이브러리만)
       py -X utf8 build_site_meta.py --check  (파일을 바꾸지 않고, 바뀔 것이 있으면 종료 코드 1)
두 번 돌려도 결과가 같다(결정적). 원문·초록·로컬 경로·메일 주소는 다루지 않는다.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "site" / "data"
CATALOG = DATA / "datasets.json"
VOID = DATA / "void.ttl"
BASE = "https://kcritic.kr"


def load(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _objects(s):
    """한 줄(주어·술어 하나)의 목적어 수 = 따옴표·<> 밖의 쉼표 수 + 1"""
    n, in_q, in_iri, skip = 1, False, False, False
    for ch in s:
        if skip:
            skip = False
        elif in_q:
            if ch == chr(92):
                skip = True
            elif ch == '"':
                in_q = False
        elif in_iri:
            if ch == ">":
                in_iri = False
        elif ch == '"':
            in_q = True
        elif ch == "<":
            in_iri = True
        elif ch == ",":
            n += 1
    return n


def count_triples(rel):
    """build.py 가 쓰는 graph.ttl 꼴(한 줄에 술어 하나, ' ;' 나 ' .' 로 끝남)의 트리플 수.
    같은 트리플이 두 번 적혀 있으면 두 번 센다(rdflib 의 len(graph) 는 한 번)."""
    p = ROOT / rel
    if not p.exists():
        return None
    seen, subj = set(), None
    with open(p, encoding="utf-8") as f:
        for line in f:
            s = line.rstrip()
            if s.startswith("#") or s.startswith("@prefix") or not s:
                continue
            if not (s.endswith(" ;") or s.endswith(" .")):
                continue
            body = s[:-2]
            if not line.startswith(" "):
                subj, _, body = body.partition(" ")
            body = body.strip()
            if _objects(body) == 1:
                seen.add((subj, body))
            else:                       # 목적어가 여럿인 줄 — 쉼표로 나눠 하나씩
                pred, _, rest = body.partition(" ")
                for k in range(_objects(body)):
                    seen.add((subj, pred, k, rest))
    return len(seen)


# ── 묶음별 규모: (이름, 수) 목록. 파일이 없으면 그 줄을 뺀다 ─────────────────────────
def counts_for(did):
    out = []

    def add(label, n):
        if n is not None:
            out.append([label, n])

    essays = load("site/data/v2/essays.json") or []
    if did == "essays-collected":
        own = [e for e in essays if str(e.get("coll", "")).startswith("works-")]
        add("글", len(own))
        add("비평가", len({e.get("critic") for e in own}))
        add("수록 단행본", len({re.sub(r",\s*\d{4}$", "", e.get("venue") or "") for e in own if e.get("venue")}))
    elif did == "essays-mhs":
        mhs = [e for e in essays if e.get("coll") == "mhs"]
        add("글", len(mhs))
        add("필자", len({e.get("critic") for e in mhs}))
        iss = load("site/data/v2/issues.json")
        add("호", len(iss) if iss is not None else None)
        d = DATA / "v2" / "mhs_sum"
        if d.is_dir():
            n = 0
            for p in sorted(d.glob("*.json")):
                j = json.load(open(p, encoding="utf-8"))
                n += len(j)
            add("요약이 붙은 글", n)
    elif did == "essays-changbi":
        iss = load("site/data/v2/issues_cb.json")
        if iss is not None:
            add("호", len(iss))
            add("목차 항목", sum(i.get("n", 0) for i in iss))
            add("비평·산문", sum(i.get("n_crit", 0) for i in iss))
        s = load("site/data/v2/changbi_summaries.json")
        add("검수 통과 해제", len(s) if s is not None else None)
        add("관계망에 넣은 글", len([e for e in essays if e.get("coll") == "cb"]))
    elif did == "persons-authority":
        people = load("site/data/v2/people.json")
        if people is not None:
            add("인물", len(people))
            add("비평가(글을 쓴 사람)", sum(1 for p in people if p.get("wrote")))
            add("외부 전거가 하나라도 있는 인물", sum(1 for p in people if p.get("lod")))
        pj = load("persons.json")
        if pj is not None:
            add("인물 권위 목록", len(pj))
            add("Wikidata 연결", sum(1 for v in pj.values() if v.get("wikidata")))
            add("국립중앙도서관 전거 연결", sum(1 for v in pj.values() if v.get("nlk")))
    elif did == "concepts":
        c2 = load("site/data/v2/concepts.json")
        c1 = load("site/data/concepts.json")
        add("개념어(전체)", len(c1) if c1 is not None else None)
        add("화면에 보이는 개념어(2편 이상)", len(c2) if c2 is not None else None)
    elif did == "graph-rdf":
        g = load("site/data/graph.json")
        if g is not None:
            add("점(노드)", len(g["nodes"]))
            add("선(엣지)", len(g["edges"]))
        add("RDF 트리플(graph.ttl)", count_triples("site/data/graph.ttl"))
    elif did == "quoted-sentences":
        g = load("site/data/interp_game.json")
        add("태도 판정 문장", len(g["items"]) if g else None)
        ex = load("site/data/v2/examples.json")
        add("개념어 예시 문장이 있는 글", sum(1 for v in ex.values() if v) if ex is not None else None)
    elif did == "find-index":
        m = load("site/data/find/meta.json")
        if m:
            add("색인에 든 글", len(m.get("ids") or []))
    elif did == "theses":
        r = load("site/data/research-public.json")
        if r:
            add("박사논문", len(r["theses"]))
            add("뜻 검색·태그 범위(본문 색인)", r.get("corpus_size"))
        c = load("site/data/thesis-citations-public.json")
        add("참고문헌 연결이 있는 논문", len(c["citing_by_thesis"]) if c else None)
    elif did == "lineage":
        g = load("site/data/genealogy-library.json")
        if g:
            s = g["summary"]
            add("교수", s.get("faculty_nodes"))
            add("지도논문이 있는 교수", s.get("faculty_with_advisees"))
            add("지도 관계(논문 단위)", s.get("advisor_thesis_edges"))
            lv = (s.get("identity_levels") or {}).get("edges") or {}
            for k in ("확정", "추론", "미확인"):
                if k in lv:
                    add(f"동일인 판정 {k}", lv[k])
    elif did == "academic-network":
        a = load("site/data/academic-network-public.json")
        if a:
            s = a["summary"]
            add("논문 기록", s.get("thesis_records"))
            add("학위 수여 기관", s.get("normalized_degree_institutions"))
            add("소속을 확인한 교수", s.get("web_reviewed_faculty_profiles"))
            add("관계", len(a.get("relationships") or []))
    elif did == "school-style":
        s = load("site/data/school-style-public.json")
        if s:
            m = s["summary"]
            add("교수(KCI 논문 묶음)", m.get("professors"))
            add("박사논문", m.get("theses"))
            add("계산에 쓴 KCI 논문", m.get("kci_articles"))
            add("계보", m.get("lineages"))
    elif did == "kci-citations":
        k = load("site/data/kci-citations-public.json")
        if k:
            add("논문", k.get("article_count"))
            add("인용 관계", k.get("edges"))
            add("수집 대상 전체 논문", (k.get("coverage") or {}).get("list_articles"))
    elif did == "theses-legacy":
        b = load("site/data/bibliography.json")
        if b is not None:
            add("박사논문", len({r.get("orig_id") for r in b}))
            add("기록(작가별로 나눈 뒤)", len(b))
    elif did == "criticism-2000s":
        c = load("site/data/criticism.json")
        add("기록", len(c["records"]) if c else None)
    return out


# ── 데이터 파일에 기준일이 적혀 있는 묶음 ──────────────────────────────────────────
def as_of_for(did):
    if did == "lineage":
        g = load("site/data/genealogy-library.json")
        return (g or {}).get("as_of")
    if did == "academic-network":
        a = load("site/data/academic-network-public.json")
        return (a or {}).get("updated_at")
    if did == "school-style":
        s = load("site/data/school-style-public.json")
        return (s or {}).get("as_of")
    if did == "kci-citations":
        k = load("site/data/kci-citations-public.json")
        t = ((k or {}).get("coverage") or {}).get("latest_retrieved_at")
        return t[:10] if t else None
    if did == "find-index":
        m = load("site/data/find/meta.json")
        b = (m or {}).get("built")
        return str(b)[:10] if b else None
    return None


def refresh(cat):
    for d in cat["datasets"]:
        d["counts"] = counts_for(d["id"])
        a = as_of_for(d["id"])
        if a:
            d["as_of"] = a
            d["as_of_auto"] = True
    return cat


# ── VoID / DCAT ────────────────────────────────────────────────────────────────
def ttl_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def file_url(f):
    return f"{BASE}/{f}"


def build_void(cat):
    site, lic = cat["site"], cat["licenses"]
    tp = {t["id"]: t for t in cat.get("third_party", [])}
    L = [
        "# kcritic.kr 공개 자료 설명 (VoID · DCAT) — build_site_meta.py 가 site/data/datasets.json 에서 만든다.",
        "# 사람이 읽는 안내: https://kcritic.kr/data.html",
        "# dcterms:license 는 묶음 전체에 한 조건이 적용될 때만 붙인다. 외부 서지가 섞인 묶음은 dcterms:rights 에 글로 적는다(없음 ≠ 자유 이용).",
        "",
        "@prefix dcat:    <http://www.w3.org/ns/dcat#> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        "@prefix foaf:    <http://xmlns.com/foaf/0.1/> .",
        "@prefix void:    <http://rdfs.org/ns/void#> .",
        "@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix kcd:     <https://kcritic.kr/data.html#> .",
        "",
        "<https://kcritic.kr/data.html> a dcat:Catalog ;",
        f"  dcterms:title {ttl_str(site['name'] + ' — 데이터와 출처')}@ko ;",
        f"  foaf:homepage <{site['url']}> ;",
    ]
    if site.get("creator"):
        L.append(f"  dcterms:creator {ttl_str(site['creator']['name'])}@ko ;")
    if site.get("operator"):
        L.append(f"  dcterms:publisher {ttl_str(site['operator'])}@ko ;")
    L.append(f"  dcterms:modified {ttl_str(cat['updated'])}^^xsd:date ;")
    L.append("  dcat:dataset " + ", ".join(f"kcd:{d['id']}" for d in cat["datasets"]) + " .")
    L.append("")
    for d in cat["datasets"]:
        files = [f for f in d.get("files", []) if "*" not in f]
        is_rdf = d["id"] == "graph-rdf"
        L.append(f"kcd:{d['id']} a dcat:Dataset" + (", void:Dataset" if is_rdf else "") + " ;")
        L.append(f"  dcterms:title {ttl_str(d['title'])}@ko ;")
        L.append(f"  dcterms:description {ttl_str(d['what'])}@ko ;")
        if d.get("as_of"):
            L.append(f"  dcterms:modified {ttl_str(d['as_of'])}^^xsd:date ;")
        for s in d.get("sources", []):
            t = tp.get(s.get("ref")) if s.get("ref") else None
            u = (t or {}).get("url") or s.get("url")
            if u:
                L.append(f"  dcterms:source <{u}> ;")
        k = lic.get(d.get("license_key") or "", {})
        if d.get("rights_caveat"):               # 외부 서지가 섞인 묶음 — dcterms:license 를 통째로 붙이지 않는다
            L.append(f"  dcterms:rights {ttl_str(d['rights_caveat'])}@ko ;")
        elif k.get("license_url"):
            L.append(f"  dcterms:license <{k.get('license_uri') or k['license_url']}> ;")
        elif k.get("license"):
            L.append(f"  dcterms:rights {ttl_str(k['license'])}@ko ;")
        if d["id"] == "graph-rdf":
            n = dict(map(tuple, d.get("counts", []))).get("RDF 트리플(graph.ttl)")
            if n:
                L.append(f"  void:triples {n} ;")
            L.append(f"  void:dataDump <{file_url('site/data/graph.ttl')}> ;")
            L.append("  void:uriSpace \"https://kcritic.kr/resource/\" ;")
            L.append("  void:vocabulary <http://kcritic.kr/ontology/critic#>, <http://purl.org/dc/terms/>, <http://xmlns.com/foaf/0.1/>, <http://purl.org/spar/cito/> ;")
        for f in files:
            L.append(f"  dcat:distribution <{file_url(f)}> ;")
        L.append(f"  dcat:landingPage <https://kcritic.kr/data.html#{d['id']}> .")
        L.append("")
    return "\n".join(L)


# ── JSON-LD (schema.org) ───────────────────────────────────────────────────────
def person_or_none(site):
    c = site.get("creator")
    return {"@type": "Person", "name": c["name"], "url": c["page"]} if c else None


def jsonld_catalog(cat):
    site, lic = cat["site"], cat["licenses"]
    creator = person_or_none(site)
    sets = []
    for d in cat["datasets"]:
        o = {
            "@type": "Dataset",
            "@id": f"{BASE}/data.html#{d['id']}",
            "name": f"{d['title']} — kcritic",
            "description": d["what"],
            "url": f"{BASE}/data.html#{d['id']}",
            "inLanguage": "ko",
            "isAccessibleForFree": True,
        }
        if d.get("as_of"):
            o["dateModified"] = d["as_of"]
        if creator:
            o["creator"] = creator
        k = lic.get(d.get("license_key") or "", {})
        if k.get("license_url") and not d.get("rights_caveat"):
            o["license"] = k.get("license_uri") or k["license_url"]          # 정해지지 않았으면 쓰지 않는다
        elif d.get("rights_caveat"):                 # 외부 서지가 섞인 묶음 — 통째로 선언하지 않고 조건을 글로 적는다
            o["usageInfo"] = f"{BASE}/data.html#terms"
            o["conditionsOfAccess"] = d["rights_caveat"]
        files = [f for f in d.get("files", []) if "*" not in f]
        if files:
            o["distribution"] = [{"@type": "DataDownload", "contentUrl": file_url(f),
                                  "encodingFormat": "text/turtle" if f.endswith(".ttl") else "application/rdf+xml" if f.endswith(".rdf") else "application/octet-stream" if f.endswith(".bin") else "application/json"} for f in files]
        src = [s.get("name") or s.get("ref") for s in d.get("sources", [])]
        if src:
            o["isBasedOn"] = [s for s in src if s]
        sets.append(o)
    out = {
        "@context": "https://schema.org",
        "@type": "DataCatalog",
        "@id": f"{BASE}/data.html",
        "name": f"{site['name']} — 데이터와 출처",
        "url": f"{BASE}/data.html",
        "inLanguage": "ko",
        "dateModified": cat["updated"],
        "dataset": sets,
    }
    if creator:
        out["creator"] = creator
    if site.get("operator"):
        out["publisher"] = {"@type": "Organization" if site.get("operator_type") == "organization" else "Person", "name": site["operator"]}
    return out


def jsonld_website(cat):
    site = cat["site"]
    out = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": f"{BASE}/#website",
        "name": site["name"],
        "alternateName": "kcritic",
        "url": f"{BASE}/",
        "inLanguage": "ko",
        "description": "한국 현대 문학비평의 비평가·글·작가·이론가 관계와 현대문학 박사학위논문의 서지·학맥을 연결 데이터로 공개하는 연구 사이트. 원문은 싣지 않는다.",
        "about": f"{BASE}/data.html",
        "potentialAction": {"@type": "SearchAction", "target": f"{BASE}/search.html?q={{search_term_string}}", "query-input": "required name=search_term_string"},
    }
    c = person_or_none(site)
    if c:
        out["creator"] = c
    if site.get("operator"):
        out["publisher"] = {"@type": "Organization" if site.get("operator_type") == "organization" else "Person", "name": site["operator"]}
    return out


MARK = re.compile(r"(<!-- JSONLD-START -->).*?(<!-- JSONLD-END -->)", re.S)


def inject(html, obj):
    block = '<script type="application/ld+json">\n' + json.dumps(obj, ensure_ascii=False, indent=1).replace("</", "<\\/") + "\n</script>"
    if not MARK.search(html):
        raise SystemExit("JSON-LD 자리 표시(<!-- JSONLD-START --> … <!-- JSONLD-END -->)가 없습니다")
    return MARK.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), html, count=1)


def main():
    check = "--check" in sys.argv
    cat = json.load(open(CATALOG, encoding="utf-8"))
    cat = refresh(cat)
    outputs = {
        CATALOG: json.dumps(cat, ensure_ascii=False, indent=2) + "\n",
        VOID: build_void(cat) + "\n",
    }
    for name, obj in (("data.html", jsonld_catalog(cat)), ("index.html", jsonld_website(cat))):
        p = ROOT / name
        if p.exists():
            outputs[p] = inject(p.read_text(encoding="utf-8"), obj)
    blob = "\n".join(outputs.values())
    # 드라이브 경로(C:\ · C:/)만 잡는다 — https:// 의 "s:/" 는 앞 글자가 영문이라 걸리지 않는다
    assert not re.search(r"(?<![A-Za-z])[A-Za-z]:[\\/](?!/)|OneDrive|@gmail|@naver", blob), "로컬 경로나 메일 주소가 섞였습니다"
    changed = []
    for p, text in outputs.items():
        old = p.read_text(encoding="utf-8") if p.exists() else None
        if old != text:
            changed.append(p.relative_to(ROOT).as_posix())
            if not check:
                with open(p, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
    und = [k for k, v in cat["licenses"].items() if v.get("status") == "undecided"]
    und += [k[:-7] for k, v in cat["site"].items() if k.endswith("_status") and v == "undecided"]
    print(("바뀔 파일: " if check else "쓴 파일: ") + (", ".join(changed) or "없음"))
    print("결정 대기: " + (", ".join(und) or "없음"))
    for d in cat["datasets"]:
        print(f"  {d['id']:18s} {d.get('as_of') or '기준일 없음':12s} " + " · ".join(f"{a} {b:,}" for a, b in d["counts"]))
    if check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
