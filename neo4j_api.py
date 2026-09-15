"""
kcritic GraphRAG API
실행: py -m uvicorn neo4j_api:app --reload
"""
import os
import re
import json
import uuid
import datetime
import urllib.request
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from neo4j import GraphDatabase
import anthropic

load_dotenv()

def _env(*names, default=""):
    """여러 이름 중 먼저 설정된 값을 쓴다.

    .env.example 은 AURA_* 로 안내하는데 코드는 NEO4J_* 를 읽고 있어
    운영 환경에서 Neo4j 연결이 끊겨 /stats 가 500 이었다(2026-09-07 확인).
    어느 쪽 이름으로 설정돼 있든 동작하도록 둘 다 허용한다.
    """
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return default

NEO4J_URI     = _env("NEO4J_URI", "AURA_URI", default="bolt://127.0.0.1:7687")
NEO4J_USER    = _env("NEO4J_USERNAME", "AURA_USERNAME", default="neo4j")
NEO4J_PWD     = _env("NEO4J_PASSWORD", "AURA_PASSWORD")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_KEY    = os.getenv("GEMINI_API_KEY", "")
ADMIN_TOKEN   = os.getenv("ADMIN_TOKEN", "")
NLK_API_KEY   = os.getenv("NLK_API_KEY", "")
AKS_API_KEY   = os.getenv("AKS_API_KEY", "")

CONTRIB_DIR = Path("/tmp/kcritic_contributions")
CONTRIB_DIR.mkdir(exist_ok=True)
BATCH_THRESHOLD = 10

RATE_LIMIT = 5             # IP당 하루 최대 질문 횟수
CONTRIB_RATE_LIMIT = 10    # IP당 하루 최대 기여 제출 횟수
GLOBAL_DAILY_LIMIT = 300   # 전체 하루 최대 유료 API 호출(비용 상한)
MAX_QUESTION_LEN = 500     # 질문 길이 상한
_rate: dict = {}           # {bucket: {"date": "YYYY-MM-DD", "count": N}}
_global: dict = {"date": "", "count": 0}

# 허용 출처 — CORS 를 "*" 로 열어두면 아무 사이트나 방문자 브라우저로
# /ask 를 호출해 Anthropic 사용료를 전가할 수 있다.
ALLOWED_ORIGINS = [
    "https://kcritic.kr",
    "https://www.kcritic.kr",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
]

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

app = FastAPI(title="kcritic GraphRAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)

def client_ip(request: Request) -> str:
    """프록시(Render) 뒤에서의 클라이언트 IP.

    request.client.host 는 프록시 IP라 모든 사용자가 한 버킷을 공유한다.
    X-Forwarded-For 의 첫 항목이 원 클라이언트지만 이 헤더는 위조 가능하므로,
    이것만으로 비용을 지키지 말고 반드시 check_global_budget() 과 함께 쓸 것.
    """
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_global_budget():
    """전체 일일 상한 — IP 위조로 개별 한도를 우회해도 비용이 무한정 늘지 않게."""
    today = datetime.date.today().isoformat()
    if _global["date"] != today:
        _global["date"], _global["count"] = today, 0
    if _global["count"] >= GLOBAL_DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="오늘 전체 이용 한도에 도달했습니다. 내일 다시 시도해주세요."
        )
    _global["count"] += 1


def check_rate(request_ip: str, limit: int = RATE_LIMIT, scope: str = "ask"):
    today = datetime.date.today().isoformat()
    key = f"{scope}:{request_ip}"
    rec = _rate.get(key)
    if rec and rec["date"] == today:
        if rec["count"] >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"하루 한도({limit}회)를 초과했습니다. 내일 다시 시도해주세요."
            )
        rec["count"] += 1
    else:
        _rate[key] = {"date": today, "count": 1}


# ── Cypher 읽기 전용 강제 ──────────────────────────────
# /ask 는 LLM이 생성한 Cypher 를 실행한다. 프롬프트 인젝션으로
# "MATCH (n) DETACH DELETE n" 같은 쿼리를 만들게 하면 DB 전체가 지워질 수 있다.
# 드라이버의 읽기 전용 세션(아래 run_cypher)과 이 검증을 이중으로 건다.
# 근본 방어는 Neo4j 에서 읽기 전용 계정을 발급해 쓰는 것.
_WRITE_KEYWORDS = (
    "create", "merge", "delete", "detach", "set", "remove", "drop",
    "load csv", "foreach", "call db.", "call apoc", "call dbms",
    "create index", "create constraint", "periodic commit", "use ",
)


def assert_read_only(cypher: str) -> str:
    """쓰기·관리 조작이 섞인 Cypher 를 거부한다."""
    if not cypher or not cypher.strip():
        raise HTTPException(status_code=400, detail="빈 쿼리")
    # 문자열 리터럴을 지운 뒤 검사 — 작품 제목 안의 'delete' 같은 단어 오탐 방지
    stripped = re.sub(r"'[^']*'|\"[^\"]*\"", "''", cypher).lower()
    for kw in _WRITE_KEYWORDS:
        if kw in stripped:
            raise HTTPException(
                status_code=400,
                detail="읽기 전용 질의만 허용됩니다. 조회 형태로 다시 질문해주세요."
            )
    if ";" in stripped.rstrip().rstrip(";"):
        raise HTTPException(status_code=400, detail="다중 구문 질의는 허용되지 않습니다.")
    if not re.match(r"^\s*(match|with|return|unwind|call\s*\{|profile\s+match|explain\s+match)\b",
                    stripped):
        raise HTTPException(status_code=400, detail="조회(MATCH/RETURN) 형태의 질의만 허용됩니다.")
    return cypher

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

def run_cypher(query: str, params: dict = {}, read_only: bool = True) -> list:
    # default_access_mode=READ_ACCESS 로 드라이버 수준에서도 쓰기를 막는다
    # (assert_read_only 검증과 이중 방어).
    from neo4j import READ_ACCESS
    kwargs = {"default_access_mode": READ_ACCESS} if read_only else {}
    with driver.session(**kwargs) as s:
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
        assert_read_only(cypher)          # 쓰기·다중구문 질의 거부
        rows = run_cypher(cypher)
        cypher_error = None
    except HTTPException as e:
        rows = []
        cypher_error = e.detail
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
    if len(q.question) > MAX_QUESTION_LEN:
        raise HTTPException(status_code=413, detail=f"질문은 {MAX_QUESTION_LEN}자 이내로 입력해주세요.")
    check_rate(client_ip(request), RATE_LIMIT, "ask")
    check_global_budget()                 # 유료 API 호출 전 전체 상한 확인
    return ask_claude(q.question)

@app.get("/stats")
def stats():
    nodes = run_cypher("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY cnt DESC")
    edges = run_cypher("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt ORDER BY cnt DESC")
    return {"nodes": nodes, "edges": edges}


# ──────────────────────────────────────────
# 크라우드소싱 기여 시스템
# ──────────────────────────────────────────

class Contribution(BaseModel):
    # 길이 상한 없이 받으면 대용량 페이로드로 디스크를 채울 수 있어 전 필드 제한.
    type: str = Field(max_length=32)     # "new_essay" | "fix_person" | "fix_essay" | "new_person" | "other"
    name: str = Field(max_length=100)    # 기여자 이름 (공개 표시용)
    email: str = Field(max_length=254)   # 기여자 이메일 (비공개, 승인 알림용)
    affiliation: Optional[str] = Field(default=None, max_length=200)   # 소속 기관
    summary: str = Field(max_length=1000)   # 제안 요약 (1~2문장)
    detail: str = Field(max_length=20000)   # 상세 내용 (TEI XML 스니펫, 서지 정보 등)
    source: Optional[str] = Field(default=None, max_length=1000)       # 출처 URL 또는 문헌 정보

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
def contribute(c: Contribution, request: Request):
    # 레이트리밋이 없으면 자동 제출로 디스크를 채우고,
    # 10건마다 도는 Gemini 배치 검증까지 무한히 유발해 비용이 증폭된다.
    check_rate(client_ip(request), CONTRIB_RATE_LIMIT, "contribute")
    # EmailStr(email-validator 의존) 대신 의존성 없는 최소 형식 검증
    if not re.match(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$", c.email):
        raise HTTPException(status_code=422, detail="이메일 형식이 올바르지 않습니다.")
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
    if len(pending) >= BATCH_THRESHOLD and _global["count"] < GLOBAL_DAILY_LIMIT:
        check_global_budget()             # Gemini 호출도 전체 예산에 포함
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
