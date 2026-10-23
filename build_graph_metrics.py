"""관계망 2판용 구조 지표 — site/data/v2/{essays,people}.json → site/data/v2/graph_metrics.json

사람끼리의 관계망(비평가 → 다룬 작가·활용한 이론가, 글은 선 안으로 접음, 무게 = 글 수)에서
- 연결 중심성: 이어진 사람 수와 그 순위
- 매개 중심성: 거리 = 1/무게 로 잰 최단 경로 위에 놓이는 정도와 그 순위
- 군집: Louvain (무게 사용, seed 고정 → 다시 돌려도 같은 결과)
- 참여 계수: 이어진 무게가 여러 군집에 고루 퍼진 정도(0 = 한 군집 안, 1에 가까울수록 군집 사이를 잇는다)
build_site_v2.py 다음에 돌린다. 원문은 쓰지 않는다(메타데이터 JSON만 읽음).
"""
import json, time
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
from networkx.algorithms.community import louvain_communities

V2 = Path(__file__).parent / "site" / "data" / "v2"
essays = json.loads((V2 / "essays.json").read_text(encoding="utf-8"))
people = {p["id"]: p for p in json.loads((V2 / "people.json").read_text(encoding="utf-8"))}

w = Counter()
for e in essays:
    for x in set(e.get("subjects", [])) | set(e.get("theorists", [])):
        if x != e["critic"]:
            w[tuple(sorted((e["critic"], x)))] += 1

G = nx.Graph()
for (a, b), n in w.items():
    G.add_edge(a, b, weight=n, dist=1 / n)

t0 = time.time()
btw = nx.betweenness_centrality(G, weight="dist", normalized=True)
comms = sorted(louvain_communities(G, weight="weight", seed=42), key=len, reverse=True)
cid = {n: i for i, c in enumerate(comms) for n in c}

strength = dict(G.degree(weight="weight"))
def rank(score):                                  # 1 = 가장 높음 (같은 값은 같은 순위)
    order = sorted(score, key=lambda n: -score[n])
    out, prev, r = {}, None, 0
    for i, n in enumerate(order, 1):
        if score[n] != prev: r, prev = i, score[n]
        out[n] = r
    return out
deg = dict(G.degree())
deg_rank, btw_rank = rank(deg), rank(btw)

def participation(n):
    k = strength[n]
    per = Counter()
    for m, d in G[n].items(): per[cid[m]] += d["weight"]
    return 1 - sum((v / k) ** 2 for v in per.values())

name = lambda n: people.get(n, {}).get("name", n)
comm_out = []
for i, c in enumerate(comms):
    top = sorted(c, key=lambda n: -strength[n])[:5]
    critics = [n for n in sorted(c, key=lambda n: -strength[n]) if people.get(n, {}).get("wrote")][:3]
    comm_out.append({"id": i, "size": len(c), "label": " · ".join(name(n) for n in top[:3]), "top": top, "critics": critics})

nodes = {n: [deg[n], deg_rank[n], round(btw[n], 5), btw_rank[n], cid[n], round(participation(n), 3)] for n in G}
out = {
    "meta": {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "communities": len(comms),
             "fields": ["이어진 사람 수", "연결 순위", "매개 중심성", "매개 순위", "군집", "참여 계수"],
             "method": "사람-사람 투영(비평가→다룬 작가·활용한 이론가, 무게=글 수), 매개=거리 1/무게, Louvain seed 42",
             "built": time.strftime("%Y-%m-%d")},
    "comms": comm_out,
    "nodes": nodes,
}
(V2 / "graph_metrics.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"노드 {G.number_of_nodes()} · 엣지 {G.number_of_edges()} · 군집 {len(comms)} · {time.time() - t0:.1f}초")
for c in comm_out[:8]: print(f"  군집 {c['id']} ({c['size']}명): {c['label']}")
