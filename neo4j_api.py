"""
kcritic GraphRAG API
실행: py -m uvicorn neo4j_api:app --reload
"""
import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from neo4j import GraphDatabase
import anthropic

load_dotenv()

NEO4J_URI  = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PWD  = os.getenv("NEO4J_PASSWORD", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

app = FastAPI(title="kcritic GraphRAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SCHEMA = """
Neo4j 그래프 스키마 (한국 비평사 온톨로지):

노드 레이블:
  - Critic   : 비평가 (label: 이름)
  - Writer   : 작가·비평 대상 (label: 이름)
  - Theorist : 이론가·사상가 (label: 이름)
  - Essay    : 비평 에세이 (label: 제목, year: 연도)

관계:
  - (Critic)-[:WROTE]->(Essay)          비평가가 에세이를 씀
  - (Essay)-[:SUBJECT_OF]->(Writer)     에세이가 작가를 다룸
  - (Essay)-[:USES_THEORY]->(Theorist)  에세이가 이론가를 인용

주요 인물:
  - 비평가: 김우창, 유종호
  - 작가: 윤동주, 한용운, 김수영, 서정주, 정현종 등
  - 이론가: 하버마스, 헤겔, 프로이트, 하이데거, 칸트, 사르트르 등
"""

SYSTEM_PROMPT = f"""당신은 한국 비평사 온톨로지 전문 어시스턴트입니다.
사용자의 자연어 질문을 받아 두 단계로 답합니다:

1. 질문에 맞는 Cypher 쿼리를 작성해 Neo4j에서 데이터를 조회합니다.
2. 조회 결과를 바탕으로 한국어로 학술적 답변을 생성합니다.

{SCHEMA}

규칙:
- 노드 속성은 .label (이름), .year (연도), .ref (Wikidata URI) 사용
- 결과는 항상 LIMIT 20 이하로
- 답변은 간결하고 학술적으로
"""

class Question(BaseModel):
    question: str

def run_cypher(query: str, params: dict = {}) -> list:
    with driver.session() as s:
        result = s.run(query, **params)
        return [dict(r) for r in result]

def ask_claude(question: str) -> dict:
    # 1단계: Cypher 생성
    cypher_resp = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""다음 질문에 답하기 위한 Cypher 쿼리만 작성하세요.
쿼리만 출력하고 설명은 하지 마세요. 코드블록 없이 순수 Cypher만.

질문: {question}"""
        }]
    )
    cypher = cypher_resp.content[0].text.strip()
    # 코드블록 제거
    cypher = cypher.replace("```cypher", "").replace("```", "").strip()

    # 2단계: Neo4j 조회
    try:
        rows = run_cypher(cypher)
    except Exception as e:
        rows = []
        cypher_error = str(e)
    else:
        cypher_error = None

    # 3단계: 답변 생성
    context = json.dumps(rows, ensure_ascii=False, indent=2) if rows else "조회 결과 없음"
    answer_resp = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""질문: {question}

Neo4j 조회 결과:
{context}

위 데이터를 바탕으로 질문에 학술적으로 답해주세요."""
        }]
    )
    answer = answer_resp.content[0].text.strip()

    return {
        "question": question,
        "cypher": cypher,
        "cypher_error": cypher_error,
        "rows": rows,
        "answer": answer,
    }

@app.get("/")
def root():
    return {"status": "ok", "service": "kcritic GraphRAG API"}

@app.post("/ask")
def ask(q: Question):
    return ask_claude(q.question)

@app.get("/stats")
def stats():
    nodes = run_cypher("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY cnt DESC")
    edges = run_cypher("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt ORDER BY cnt DESC")
    return {"nodes": nodes, "edges": edges}
