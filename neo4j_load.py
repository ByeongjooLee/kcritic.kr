"""
graph.json → Neo4j 적재 스크립트
실행: py neo4j_load.py
"""
import json
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI      = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
USER     = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "")

GRAPH_JSON = "site/data/graph.json"

def load_graph(driver, graph):
    nodes = graph["nodes"]
    edges = graph["edges"]

    with driver.session() as s:
        # 기존 데이터 초기화
        s.run("MATCH (n) DETACH DELETE n")
        print("기존 데이터 삭제 완료")

        # 노드 적재
        for n in nodes:
            label = n.get("type", "Node").capitalize()
            s.run(
                f"MERGE (n:{label} {{id: $id}}) "
                "SET n.label = $label, n.type = $type, "
                "n.year = $year, n.ref = $ref, n.degree = $degree",
                id=n["id"],
                label=n.get("label", ""),
                type=n.get("type", ""),
                year=n.get("year", ""),
                ref=n.get("ref", ""),
                degree=n.get("degree", 0),
            )
        print(f"노드 {len(nodes)}개 적재 완료")

        # 엣지 적재
        for e in edges:
            rel = e.get("type", "RELATED").upper().replace("-", "_")
            s.run(
                f"MATCH (a {{id: $src}}), (b {{id: $tgt}}) "
                f"MERGE (a)-[r:{rel}]->(b) "
                "SET r.weight = $weight",
                src=e["source"],
                tgt=e["target"],
                weight=e.get("weight", 1),
            )
        print(f"엣지 {len(edges)}개 적재 완료")

    print("\n완료. Neo4j Browser에서 확인:")
    print("  MATCH (n) RETURN labels(n), count(*) ORDER BY count(*) DESC")


if __name__ == "__main__":
    with open(GRAPH_JSON, encoding="utf-8") as f:
        graph = json.load(f)

    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    try:
        driver.verify_connectivity()
        print(f"Neo4j 연결 성공: {URI}")
        load_graph(driver, graph)
    except Exception as e:
        print(f"오류: {e}")
    finally:
        driver.close()
