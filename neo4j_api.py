"""
kcritic GraphRAG API
실행: py -m uvicorn neo4j_api:app --reload
"""
import os
import json
import uuid
import datetime
import urllib.request
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from neo4j import GraphDatabase
import anthropic

load_dotenv()

NEO4J_URI     = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER    = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PWD     = os.getenv("NEO4J_PASSWORD", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_KEY    = os.getenv("GEMINI_API_KEY", "")
ADMIN_TOKEN   = os.getenv("ADMIN_TOKEN", "")
NLK_API_KEY   = os.getenv("NLK_API_KEY", "")
AKS_API_KEY   = os.getenv("AKS_API_KEY", "")

NLK_SRCH_URL  = "https://apis.data.go.kr/1371029/AuthorInformationService/getAuthorInformationSrch"
AKS_SRCH_URL  = "https://devin.aks.ac.kr:8080/api/articles/search"

CONTRIB_DIR = Path("/tmp/kcritic_contributions")
CONTRIB_DIR.mkdir(exist_ok=True)
BATCH_THRESHOLD = 10

RATE_LIMIT = 5           # IP당 하루 최대 질문 횟수
_rate: dict = {}         # {ip: {"date": "YYYY-MM-DD", "count": N}}

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

app = FastAPI(title="kcritic GraphRAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def check_rate(request_ip: str):
    today = datetime.date.today().isoformat()
    rec = _rate.get(request_ip)
    if rec and rec["date"] == today:
        if rec["count"] >= RATE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=f"하루 질문 한도({RATE_LIMIT}회)를 초과했습니다. 내일 다시 시도해주세요."
            )
        rec["count"] += 1
    else:
        _rate[request_ip] = {"date": today, "count": 1}

# ──────────────────────────────────────────
# GraphRAG (기존)
# ──────────────────────────────────────────

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
    cypher_resp = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"다음 질문에 답하기 위한 Cypher 쿼리만 작성하세요.\n쿼리만 출력하고 설명은 하지 마세요. 코드블록 없이 순수 Cypher만.\n\n질문: {question}"}]
    )
    cypher = cypher_resp.content[0].text.strip().replace("```cypher", "").replace("```", "").strip()

    try:
        rows = run_cypher(cypher)
        cypher_error = None
    except Exception as e:
        rows = []
        cypher_error = str(e)

    context = json.dumps(rows, ensure_ascii=False, indent=2) if rows else "조회 결과 없음"
    answer_resp = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"질문: {question}\n\nNeo4j 조회 결과:\n{context}\n\n위 데이터를 바탕으로 질문에 학술적으로 답해주세요."}]
    )
    return {
        "question": question,
        "cypher": cypher,
        "cypher_error": cypher_error,
        "rows": rows,
        "answer": answer_resp.content[0].text.strip(),
    }

@app.get("/")
def root():
    return {"status": "ok", "service": "kcritic GraphRAG API"}

@app.post("/ask")
def ask(q: Question, request: Request):
    ip = request.client.host
    check_rate(ip)
    return ask_claude(q.question)

@app.get("/stats")
def stats():
    nodes = run_cypher("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY cnt DESC")
    edges = run_cypher("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt ORDER BY cnt DESC")
    return {"nodes": nodes, "edges": edges}


# ──────────────────────────────────────────
# NLK 저자정보 조회
# ──────────────────────────────────────────

def _nlk_search(name: str) -> list[dict]:
    """국립중앙도서관 저자정보 API 조회. 결과 item 목록 반환."""
    if not NLK_API_KEY:
        return []
    params = urllib.parse.urlencode({
        "serviceKey": NLK_API_KEY,
        "authNm": name,
        "pageNo": 1,
        "numOfRows": 5,
        "type": "json",
    })
    url = f"{NLK_SRCH_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "kcritic-ontology/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        items = (data.get("response", {})
                     .get("body", {})
                     .get("items", {})
                     .get("item", []))
        if isinstance(items, dict):
            items = [items]
        return items or []
    except Exception as e:
        return []


def _aks_search(name: str) -> list[dict]:
    """민족문화대백과사전 항목 검색. 인물 항목만 필터링."""
    if not AKS_API_KEY:
        return []
    params = urllib.parse.urlencode({"q": name, "p": 1, "ps": 5})
    try:
        req = urllib.request.Request(
            f"{AKS_SRCH_URL}?{params}",
            headers={"X-API-Key": AKS_API_KEY, "User-Agent": "kcritic-ontology/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        return [item for item in data.get("items", [])
                if item.get("primaryTypePartA") == "인물"]
    except Exception:
        return []


@app.get("/person-lookup")
def person_lookup(name: str):
    """저자명으로 NLK + 민족문화대백과 동시 조회 — 사이트 기여/검색 연동용."""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="name 파라미터 필요")
    name = name.strip()

    nlk_items = _nlk_search(name)
    aks_items = _aks_search(name)

    nlk_results = []
    for item in nlk_items:
        auth_id = item.get("authNo") or item.get("authId") or item.get("id")
        nlk_uri = f"https://lod.nl.go.kr/resource/KAC{str(auth_id).zfill(8)}" if auth_id else None
        nlk_results.append({
            "name": item.get("authNm", ""),
            "birth": item.get("birthYear", ""),
            "death": item.get("deathYear", ""),
            "occupation": item.get("occpNm", ""),
            "nlk_uri": nlk_uri,
        })

    aks_results = []
    for item in aks_items:
        aks_results.append({
            "headword": item.get("headword", ""),
            "definition": item.get("definition", ""),
            "era": item.get("era", ""),
            "field": item.get("field", ""),
            "url": item.get("url", ""),
            "eid": item.get("eid", ""),
        })

    return {
        "query": name,
        "nlk": {"count": len(nlk_results), "results": nlk_results},
        "encykorea": {"count": len(aks_results), "results": aks_results},
    }


# ──────────────────────────────────────────
# 크라우드소싱 기여 시스템
# ──────────────────────────────────────────

class Contribution(BaseModel):
    type: str           # "new_essay" | "fix_person" | "fix_essay" | "new_person" | "other"
    name: str           # 기여자 이름 (공개 표시용)
    email: str          # 기여자 이메일 (비공개, 승인 알림용)
    affiliation: Optional[str] = None   # 소속 기관
    summary: str        # 제안 요약 (1~2문장)
    detail: str         # 상세 내용 (TEI XML 스니펫, 서지 정보 등)
    source: Optional[str] = None        # 출처 URL 또는 문헌 정보

def _pending_files():
    return sorted(CONTRIB_DIR.glob("pending_*.json"))

def _load_contrib(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _contrib_count_pending() -> int:
    return len(_pending_files())

# ── Gemini로 서식 정규화 ──
def gemini_normalize(contributions: list[dict]) -> list[dict]:
    if not GEMINI_KEY:
        return contributions

    prompt = f"""다음은 한국 비평사 온톨로지 기여 제안 목록입니다.
각 항목의 detail 필드를 TEI XML 서식 규칙에 맞게 정규화해주세요.
- persName에는 xml:id와 role 속성 포함
- 연도는 4자리 숫자
- 한국어 이름 표기 통일
- 원래 의미를 바꾸지 말 것

입력 JSON:
{json.dumps(contributions, ensure_ascii=False, indent=2)}

정규화된 JSON만 출력하세요. 설명 없이."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.load(r)
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return contributions   # 실패 시 원본 반환

# ── NLK LOD 서지 검증 ──
def nlk_verify(name: str) -> Optional[str]:
    """인명으로 NLK LOD SPARQL 조회 → URI 반환."""
    query = f"""
    SELECT ?s WHERE {{
      ?s <http://www.w3.org/2000/01/rdf-schema#label> "{name}"@ko .
    }} LIMIT 1
    """
    url = "https://lod.nl.go.kr/sparql?" + urllib.parse.urlencode({"query": query, "format": "json"})
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "kcritic-ontology/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        bindings = data.get("results", {}).get("bindings", [])
        return bindings[0]["s"]["value"] if bindings else None
    except Exception:
        return None

# ── 배치 검증 실행 ──
def run_batch_validation(files: list[Path]):
    contribs = [_load_contrib(f) for f in files]

    # 1. Gemini 서식 정규화
    normalized = gemini_normalize(contribs)

    # 2. NLK 서지 검증 (이름 언급된 항목)
    for item in normalized:
        names = []
        # detail에서 한글 이름 추출 (간단 휴리스틱)
        import re
        names = re.findall(r'[가-힣]{2,4}(?=</persName>|<|,|\s|")', item.get("detail", ""))
        verifications = {}
        for name in set(names[:5]):   # 최대 5개
            uri = nlk_verify(name)
            if uri:
                verifications[name] = uri
        item["nlk_verified"] = verifications
        item["gemini_normalized"] = True

    # 3. 검증된 항목 저장 (pending → validated)
    for f, item in zip(files, normalized):
        validated_path = CONTRIB_DIR / f.name.replace("pending_", "validated_")
        validated_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        f.unlink()   # pending 삭제


# ── 제안 제출 ──
@app.post("/contribute")
def contribute(c: Contribution):
    contrib_id = str(uuid.uuid4())[:8]
    now = datetime.datetime.utcnow().isoformat()

    record = {
        "id": contrib_id,
        "submitted_at": now,
        "status": "pending",
        "type": c.type,
        "name": c.name,
        "email": c.email,
        "affiliation": c.affiliation,
        "summary": c.summary,
        "detail": c.detail,
        "source": c.source,
    }

    path = CONTRIB_DIR / f"pending_{now[:10]}_{contrib_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    # 10건 누적 시 배치 검증 자동 실행
    pending = _pending_files()
    batch_msg = None
    if len(pending) >= BATCH_THRESHOLD:
        run_batch_validation(pending[:BATCH_THRESHOLD])
        batch_msg = f"{BATCH_THRESHOLD}건 누적 — Gemini 서식 검증 완료, 관리자 검토 대기 중"

    return {
        "id": contrib_id,
        "status": "received",
        "pending_count": _contrib_count_pending(),
        "batch_message": batch_msg,
    }


# ── 관리자: 제안 목록 조회 ──
def _check_admin(token: Optional[str]):
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="관리자 인증 필요")

@app.get("/admin/contributions")
def admin_list(x_admin_token: Optional[str] = Header(None)):
    _check_admin(x_admin_token)
    result = {"pending": [], "validated": [], "approved": [], "rejected": []}
    for f in CONTRIB_DIR.glob("*.json"):
        item = _load_contrib(f)
        status = item.get("status", "pending")
        if f.name.startswith("pending_"):
            result["pending"].append(item)
        elif f.name.startswith("validated_"):
            result["validated"].append(item)
        elif f.name.startswith("approved_"):
            result["approved"].append(item)
        elif f.name.startswith("rejected_"):
            result["rejected"].append(item)
    # 최신순 정렬
    for k in result:
        result[k].sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
    result["counts"] = {k: len(v) for k, v in result.items() if k != "counts"}
    return result


# ── 관리자: 개별 승인 ──
@app.post("/admin/approve/{contrib_id}")
def admin_approve(contrib_id: str, x_admin_token: Optional[str] = Header(None)):
    _check_admin(x_admin_token)
    for prefix in ("pending_", "validated_"):
        matches = list(CONTRIB_DIR.glob(f"{prefix}*{contrib_id}*.json"))
        if matches:
            f = matches[0]
            item = _load_contrib(f)
            item["status"] = "approved"
            item["reviewed_at"] = datetime.datetime.utcnow().isoformat()
            new_path = CONTRIB_DIR / f.name.replace(prefix, "approved_")
            new_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
            f.unlink()
            return {"status": "approved", "id": contrib_id}
    raise HTTPException(status_code=404, detail="제안을 찾을 수 없음")


# ── 관리자: 개별 거절 ──
@app.post("/admin/reject/{contrib_id}")
def admin_reject(contrib_id: str, reason: str = "", x_admin_token: Optional[str] = Header(None)):
    _check_admin(x_admin_token)
    for prefix in ("pending_", "validated_"):
        matches = list(CONTRIB_DIR.glob(f"{prefix}*{contrib_id}*.json"))
        if matches:
            f = matches[0]
            item = _load_contrib(f)
            item["status"] = "rejected"
            item["reject_reason"] = reason
            item["reviewed_at"] = datetime.datetime.utcnow().isoformat()
            new_path = CONTRIB_DIR / f.name.replace(prefix, "rejected_")
            new_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
            f.unlink()
            return {"status": "rejected", "id": contrib_id}
    raise HTTPException(status_code=404, detail="제안을 찾을 수 없음")


# ── 관리자: 수동 배치 검증 트리거 ──
@app.post("/admin/run-batch")
def admin_run_batch(x_admin_token: Optional[str] = Header(None)):
    _check_admin(x_admin_token)
    pending = _pending_files()
    if not pending:
        return {"message": "대기 중인 제안 없음"}
    run_batch_validation(pending)
    return {"message": f"{len(pending)}건 검증 완료"}
