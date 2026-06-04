# kcritic — 한국 비평사 온톨로지

비평가 · 작가 · 이론가 · 비평글의 관계망을 TEI XML로 인코딩하고 정적 웹사이트로 발행하는 인문학 데이터 프로젝트.

**사이트**: https://kcritic.kr  
**API**: https://kcritic-api.onrender.com

---

## 현재 수록 규모 (2026-06)

| 항목 | 수량 |
|---|---|
| 비평글 (TEI XML 인코딩) | 47편 |
| 비평가 | 2명 (김우창 30편, 유종호 17편) |
| 작가 노드 | 39명 |
| 이론가 노드 | 143명 |
| 그래프 엣지 | 288개 |
| 선행연구 (박사논문) | 1,528건 |

---

## 핵심 질문

이 온톨로지로 탐색하는 것:

- 윤동주를 비평한 비평가들은 각각 어떤 이론적 도구를 썼는가?
- 하버마스 개념을 가장 적극적으로 활용한 한국 비평가는 누구인가?
- 특정 작가에 대한 비평 방식이 시기별로 어떻게 변화했는가?
- 어떤 이론가들이 함께 인용되는 경향이 있는가?
- 지도교수-제자 네트워크가 비평의 계보와 어떻게 연결되는가?

---

## 탭 구성

| 탭 | URL | 내용 |
|---|---|---|
| 비평글 | `/index.html` | 수록 비평글 카드 목록 |
| 비평가 | `/critics.html` | 비평가 프로필 · 에세이 목록 |
| 작가 | `/writers.html` | 비평 대상 작가 목록 |
| 관계망 | `/site/graph.html` | Cytoscape.js 인터랙티브 네트워크 |
| 개념어 | `/concepts.html` | 비평 개념어 색인 (17개 공유 개념) |
| 선행연구 | `/research.html` | 박사논문 1,528건 — 작가별 · 지도교수별 탐색 |
| 2000년대 비평 | `/criticism.html` | 2000년대 시 문학 비평 136건 |
| 질문하기 | `/ask.html` | Neo4j GraphRAG — 자연어 질문 → 학술 답변 |
| 기여하기 | `/contribute.html` | 크라우드소싱 기여 신청 폼 |

---

## 폴더 구조

```
critic-ontology/
├── essays/                  ← 로컬 전용 (gitignored, 저작권 보호)
│   ├── *.xml                ← TEI XML 원문 인코딩
│   └── *.txt                ← 원문 텍스트
├── schema/
│   └── korean-critique-schema.xsd
├── site/
│   ├── essays/              ← build.py 출력: 메타데이터 HTML
│   ├── critics/             ← build.py 출력: 비평가 프로필 HTML
│   ├── data/
│   │   ├── graph.json       ← 관계망 데이터 (231 노드, 288 엣지)
│   │   ├── critics.json     ← 비평가 목록
│   │   ├── concepts.json    ← 개념어 색인 (514개)
│   │   ├── graph.ttl        ← RDF Turtle LOD 직렬화
│   │   └── bibliography.json ← 선행연구 데이터 (1,528건)
│   └── graph.html           ← Cytoscape.js 관계망 시각화
├── index.html               ← 비평글 목록
├── critics.html
├── writers.html
├── concepts.html
├── research.html            ← 박사논문 작가별·지도교수별 탐색
├── criticism.html           ← 2000년대 시 비평 136건
├── ask.html                 ← GraphRAG 질문 UI
├── contribute.html          ← 크라우드소싱 기여 폼
├── admin.html               ← 관리자 기여 검토 대시보드 (토큰 인증)
├── style.css
├── build.py                 ← TEI XML → HTML + JSON + Neo4j 빌드
├── neo4j_api.py             ← FastAPI GraphRAG + 크라우드소싱 API
├── convert_phd.py           ← 박사논문 xlsx → bibliography.json
└── CLAUDE.md                ← AI 어시스턴트 작업 지침
```

---

## 빌드 워크플로우

### TEI XML → 사이트 빌드

```powershell
cd critic-ontology
py build.py
```

출력: `site/essays/`, `site/critics/`, `site/data/graph.json`, `site/data/critics.json`, `site/data/concepts.json`, `site/data/graph.ttl`

Neo4j Desktop이 실행 중이면 자동 동기화. 꺼져 있으면 건너뜀 (빌드 실패 아님).

### 박사논문 데이터 변환

```powershell
cd ..   # 온톨로지/ 디렉터리에서
py convert_phd.py
```

- 입력: `200805_현대문학_박사논문.xlsx` (1,528건)
- 출력: `critic-ontology/site/data/bibliography.json`

### GraphRAG API 서버 (로컬)

```powershell
cd critic-ontology
py -m uvicorn neo4j_api:app --reload
```

- 포트 8000. Neo4j Desktop + `.env` 파일 필요
- `.env` 필수 항목: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `ANTHROPIC_API_KEY`
- 크라우드소싱 기능 추가 항목: `GEMINI_API_KEY`, `ADMIN_TOKEN`

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/` | 헬스체크 |
| POST | `/ask` | GraphRAG 자연어 질문 |
| GET | `/stats` | 그래프 노드·엣지 통계 |
| POST | `/contribute` | 기여 제안 제출 |
| GET | `/admin/contributions` | 기여 목록 조회 (토큰 인증) |
| POST | `/admin/approve/{id}` | 개별 승인 (토큰 인증) |
| POST | `/admin/reject/{id}` | 개별 거절 (토큰 인증) |
| POST | `/admin/run-batch` | 수동 AI 검증 트리거 (토큰 인증) |

---

## 크라우드소싱 시스템

`contribute.html` 폼으로 4가지 유형의 기여 제안을 받습니다:

1. 새 비평글 추가
2. 비평글 정보 수정
3. 새 인물 추가
4. 인물 정보 수정

**검증 파이프라인**: 제안 10건 누적 → Gemini 1.5 Flash로 TEI 서식 자동 정규화 + 국립중앙도서관 LOD SPARQL 서지 검증 → `admin.html` 관리자 최종 검토 → 승인 시 사이트 반영

---

## 기술 스택

| 영역 | 도구 |
|---|---|
| 인코딩 | VS Code + Red Hat XML + XSD 스키마 |
| 빌드 | Python (`build.py`) |
| 관계망 시각화 | Cytoscape.js 3.28 |
| 그래프 DB | Neo4j (로컬: Desktop, 배포: Aura) |
| GraphRAG API | FastAPI + Anthropic Claude (`claude-sonnet-4-6`) |
| AI 검증 | Gemini 1.5 Flash (크라우드소싱 서식 정규화) |
| 호스팅 | Cloudflare Workers (정적) + Render (API) |
| LOD 연결 | Wikidata · 국립중앙도서관 LOD · ISNI |

---

## 외부 LOD 연결

각 인물은 Wikidata `@ref` URI로 글로벌 연결됩니다:

```xml
<persName xml:id="p-habermas"
          ref="https://www.wikidata.org/wiki/Q76357"
          role="foreigner scholar">위르겐 하버마스</persName>
```

- **비평가·작가**: 국립중앙도서관 LOD (https://lod.nl.go.kr) 우선
- **외국 이론가**: Wikidata (https://wikidata.org) 우선

---

## 보안 규칙

- `essays/*.xml`, `essays/*.txt` — gitignored (저작권 원문, 절대 커밋 금지)
- `.env` — gitignored (크레덴셜, 절대 커밋 금지)
- 빌드 결과물(`site/essays/*.html`)은 메타데이터만 포함, 원문 텍스트 없음

---

## 다음 단계 (Phase 1)

학술적 비교 분석을 위해 비평가를 3명 이상으로 확장하는 것이 목표입니다.

- 김윤식 에세이 인코딩 (반-김우창 입장 — 비교 분석 가능)
- `critic:respondsTo` 프로퍼티 추가 (에세이 간 논쟁 관계)
- KCI 논문 데이터 통합 (`bibliography.json`에 `type: "kci"` 레코드 추가)
- GitHub API 연동으로 승인된 기여 자동 PR 생성 (크라우드소싱 2단계)
