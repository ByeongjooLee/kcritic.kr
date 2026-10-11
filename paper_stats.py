# -*- coding: utf-8 -*-
"""논문 수치 재현 스크립트 — 발행 RDF(site/data/graph.ttl)에서 논문의 표·질의 결과를 다시 계산한다.

    py -m pip install rdflib
    py paper_stats.py            # 표준 출력
    py paper_stats.py --json     # site/data/paper_stats.json 으로도 저장

논문 「현대문학비평 온톨로지 구축과 활용 방안」의 <표 2>·<표 4>·<표 5>·<표 8>과
Ⅳ장 질의 1~5의 결과 건수는 모두 이 스크립트의 출력과 같은 시점의 graph.ttl 기준이다.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import rdflib

TTL = Path("site/data/graph.ttl")
PREFIX = """
PREFIX critic:  <http://kcritic.kr/ontology/critic#>
PREFIX cito:    <http://purl.org/spar/cito/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX foaf:    <http://xmlns.com/foaf/0.1/>
PREFIX owl:     <http://www.w3.org/2002/07/owl#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema:  <https://schema.org/>
"""

# 논문 Ⅳ장에 실린 질의 원문 그대로
QUERIES = {
    "q1_common_theorists_kimuchang_yujongho": """SELECT DISTINCT ?name WHERE {
  ?c1 foaf:name "김우창"@ko . ?c2 foaf:name "유종호"@ko .
  ?e1 dcterms:creator ?c1 ; cito:citesAsAuthority ?t .
  ?e2 dcterms:creator ?c2 ; cito:citesAsAuthority ?t .
  ?t foaf:name ?name . }""",
    "q2_heidegger_critic_writer_pairs": """SELECT DISTINCT ?criticName ?writerName WHERE {
  ?t foaf:name "하이데거"@ko .
  ?e cito:citesAsAuthority ?t ; dcterms:creator ?c ; cito:discusses ?w .
  ?c foaf:name ?criticName . ?w foaf:name ?writerName . }""",
    "q3_theorists_in_yundongju_essays": """SELECT ?name (COUNT(?e) AS ?n) WHERE {
  ?w foaf:name "윤동주"@ko .
  ?e cito:discusses ?w ; cito:citesAsAuthority ?t .
  ?t foaf:name ?name . } GROUP BY ?name ORDER BY DESC(?n) ?name""",
    "q4_concepts_shared_by_2plus_critics": """SELECT ?concept (COUNT(DISTINCT ?c) AS ?critics) WHERE {
  ?e dcterms:subject ?concept ; dcterms:creator ?c .
} GROUP BY ?concept HAVING (COUNT(DISTINCT ?c) >= 2)""",
    "q5_discussed_and_cited": """SELECT DISTINCT ?name WHERE {
  ?e1 cito:discusses ?p . ?e2 cito:citesAsAuthority ?p . ?p foaf:name ?name . }""",
}


def main():
    g = rdflib.Graph()
    g.parse(TTL, format="turtle")

    def q(s):
        return list(g.query(PREFIX + s))

    def count(s):
        return int(q(s)[0][0])

    out = {"source": str(TTL), "triples": len(g)}

    out["classes"] = {c: count(f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s a {c} }}")
                      for c in ("critic:Critic", "critic:Writer", "critic:Thinker",
                                "critic:CriticalEssay", "foaf:Person")}
    out["properties"] = {p: count(f"SELECT (COUNT(*) AS ?n) WHERE {{ ?s {p} ?o }}")
                         for p in ("critic:analyzes", "dcterms:creator", "foaf:made",
                                   "cito:discusses", "cito:citesAsAuthority", "dcterms:subject",
                                   "dcterms:title", "dcterms:date", "schema:isPartOf",
                                   "foaf:name", "rdfs:label", "schema:url")}

    def by_host(pred):
        rows = q(f"SELECT ?o WHERE {{ ?s {pred} ?o }}")
        return dict(sorted(Counter(str(r[0]).split("/")[2] for r in rows).items(),
                           key=lambda x: (-x[1], x[0])))
    out["owl:sameAs"] = by_host("owl:sameAs")
    out["rdfs:seeAlso"] = by_host("rdfs:seeAlso")

    linked = {}
    for c in ("foaf:Person", "critic:Critic", "critic:Thinker", "critic:Writer"):
        total = count(f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s a {c} }}")
        n = count(f"SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s a {c} ; owl:sameAs|rdfs:seeAlso ?o }}")
        linked[c] = {"linked": n, "total": total, "pct": round(100 * n / total, 1) if total else 0}
    out["authority_linked"] = linked

    res = {}
    for k, s in QUERIES.items():
        rows = q(s)
        res[k] = {"count": len(rows), "rows": [[str(v) for v in r] for r in rows]}
    out["queries"] = res

    # 질의 3 보조: 윤동주 비평문의 이론가를 인용 비평가 수로 (세 비평가 교차점 확인)
    cross = q("""SELECT ?name (COUNT(DISTINCT ?c) AS ?nc) (COUNT(DISTINCT ?e) AS ?n) WHERE {
      ?w foaf:name "윤동주"@ko . ?e cito:discusses ?w ; cito:citesAsAuthority ?t ; dcterms:creator ?c .
      ?t foaf:name ?name } GROUP BY ?name HAVING (COUNT(DISTINCT ?c) >= 3)""")
    out["q3_cited_by_3plus_critics"] = [[str(a), int(b), int(c)] for a, b, c in cross]

    pairs = {}
    for a, b in (("김현", "김우창"), ("김현", "유종호"), ("김우창", "유종호")):
        pairs[f"{a}-{b}"] = count(f"""SELECT (COUNT(DISTINCT ?w) AS ?n) WHERE {{
          ?c1 foaf:name "{a}"@ko . ?c2 foaf:name "{b}"@ko .
          ?e1 dcterms:creator ?c1 ; cito:discusses ?w . ?e2 dcterms:creator ?c2 ; cito:discusses ?w . }}""")
    out["common_writers_by_critic_pair"] = pairs

    concepts = q("SELECT DISTINCT ?c WHERE { ?e dcterms:subject ?c }")
    out["distinct_concepts"] = len(concepts)

    if "--json" in sys.argv:
        Path("site/data/paper_stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {k: v for k, v in out.items() if k != "queries"}
    summary["query_counts"] = {k: v["count"] for k, v in out["queries"].items()}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("q3 top:", out["queries"]["q3_theorists_in_yundongju_essays"]["rows"][:6])
    print("q5:", [r[0] for r in out["queries"]["q5_discussed_and_cited"]["rows"]])
    print("q4 shared by 3+:", sorted(r[0] for r in out["queries"]["q4_concepts_shared_by_2plus_critics"]["rows"] if int(r[1]) >= 3))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
