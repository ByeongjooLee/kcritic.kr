# CLAUDE.md — 한국 비평사 온톨로지 프로젝트 지침

AI 어시스턴트가 이 프로젝트에서 작업할 때 따를 규칙. 새로운 결정이 생기면 즉시 이 파일을 업데이트할 것.

---

## 0. 프로젝트 목표

한국 비평사를 노드-엣지 네트워크로 구축. "김우창이 윤동주를 비평할 때 하버마스를 활용했다"는 관계를 TEI XML로 인코딩하고, 웹 시각화로 탐색 가능하게 만든다.

핵심 관계: **비평가 → 비평글 → 작가(비평 대상) / 이론가(개념 활용)**

---

## 1. 보안 규칙 (절대 위반 금지)

- `essays/*.xml` 및 `essays/*.txt` 는 `.gitignore` 에 등록 — **절대 Git 커밋/푸시 금지**
- 저작권 보호 원문. OneDrive/로컬에만 존재
- `site/essays/*.html` 은 메타데이터만 담으며 GitHub에 올라감 (원문 텍스트 없음)
- `build.py` 는 원문 본문을 HTML에 포함시키지 않음. 위반 시 즉시 수정

---

## 2. 실제 폴더 구조

```
critic-ontology/
├── essays/                  ← 로컬 전용 (gitignored)
│   ├── *.xml                ← TEI XML 원문 인코딩
│   └── *.txt                ← 원문 텍스트 (XML 작업 전 저장)
├── schema/
│   └── korean-critique-schema.xsd
├── site/
│   ├── essays/              ← build.py 출력: 메타데이터 HTML (GitHub 포함)
│   │   └── *.html
│   ├── critics/             ← build.py 출력: 비평가 프로필 HTML (GitHub 포함)
│   │   └── {critic-id}.html
│   ├── writers/             ← build.py 출력: 작가 프로필 HTML (GitHub 포함)
│   │   └── {person-id}.html
│   ├── thinkers/            ← build.py 출력: 이론가 프로필 HTML (GitHub 포함)
│   │   └── {person-id}.html
│   ├── data/
│   │   ├── graph.json       ← build.py 출력: 관계망 데이터
│   │   ├── critics.json     ← build.py 출력: 비평가 목록 데이터
│   │   ├── writers.json     ← build.py 출력: 작가 목록 데이터
│   │   ├── thinkers.json    ← build.py 출력: 이론가 목록 데이터
│   │   ├── concepts.json    ← build.py 출력: 개념어 색인
│   │   ├── graph.ttl        ← build.py 출력: RDF Turtle LOD 직렬화
│   │   └── bibliography.json ← convert_phd.py 출력: 선행연구 데이터
│   └── graph.html           ← Cytoscape.js 관계망 시각화
├── index.html               ← 비평글 목록 (메인)
├── critics.html             ← 비평가 목록 탭
├── writers.html             ← 작가 목록 탭
├── thinkers.html            ← 이론가 목록 탭
├── concepts.html            ← 개념어 탭
├── research.html            ← 선행연구 탭
├── criticism.html           ← 2000년대 비평 탭
├── ask.html                 ← 질문하기 탭 (Neo4j GraphRAG UI)
├── sparql.html              ← SPARQL 탭 (숨김 상태 — ask.html 내 SPARQL 탭으로 대체)
├── style.css                ← 공유 스타일 (반응형 포함)
├── build.py                 ← TEI XML → HTML + JSON + Neo4j 동기화 빌드 스크립트
├── persons.json             ← 인물 권위 소스 (LOD URI, Wikidata 등) — 슬러그 키
├── neo4j_api.py             ← FastAPI GraphRAG 서버 (포트 8000)
├── neo4j_load.py            ← graph.json → Neo4j 단독 로드 스크립트
├── convert_phd.py           ← 박사논문 xlsx → bibliography.json 변환
├── .env                     ← Neo4j/Anthropic 크레덴셜 (gitignored, 절대 커밋 금지)
├── wrangler.jsonc           ← Cloudflare Workers 배포 설정
├── .gitignore
└── CLAUDE.md                ← 이 파일
```

---

## 3. 사이트 구조 (탭 9개)

| 탭 | 파일 | 설명 |
|---|---|---|
| 비평글 | `index.html` | 수록 비평글 카드 목록 |
| 비평가 | `critics.html` | 비평가 카드 그리드 → 클릭 시 프로필 페이지 |
| 작가 | `writers.html` | 비평 대상 작가 목록 → 클릭 시 프로필 페이지 |
| 이론가 | `thinkers.html` | 비평에서 인용된 이론가 목록 → 클릭 시 프로필 페이지 (인용 문맥 포함) |
| 관계망 | `site/graph.html` | Cytoscape.js 네트워크 시각화 |
| 개념어 | `concepts.html` | 개념어 색인 + 사용 에세이 목록 (좌우 분할 UI) |
| 선행연구 | `research.html` | 박사·KCI 논문 작가 중심 검색 |
| 2000년대 비평 | `criticism.html` | 2000년대 시 문학 비평 136건, 연대/대상/주제/논쟁 필터 |
| 질문하기 | `ask.html` | Neo4j GraphRAG — 자연어 질문 → Cypher 자동 생성 → 학술 답변 |

### 네비게이션 경로 (파일 위치별)
- 루트 페이지(`index.html`, `critics.html`, `writers.html`, `thinkers.html` 등): `비평글`, `비평가`, `작가`, `이론가`, `관계망`, `개념어`, `선행연구`, `2000년대 비평`, `질문하기`
- `site/essays/*.html`: `../../index.html`, `../../critics.html`, `../../writers.html`, `../../thinkers.html`, `../graph.html`, `../../concepts.html`, `../../research.html`
- `site/critics/*.html`: `../../index.html`, `../../critics.html`, `../../writers.html`, `../../thinkers.html`, `../graph.html`, `../../concepts.html`, `../../research.html`
- `site/writers/*.html`: `../../index.html`, `../../critics.html`, `../../writers.html`, `../../thinkers.html`, `../graph.html`, `../../concepts.html`, `../../research.html`
- `site/thinkers/*.html`: `../../index.html`, `../../critics.html`, `../../writers.html`, `../../thinkers.html`, `../graph.html`, `../../concepts.html`, `../../research.html`
- `site/graph.html`: `../index.html`, `../critics.html`, `../writers.html`, `../thinkers.html`, `graph.html`, `../concepts.html`, `../research.html`, `../criticism.html`, `../ask.html`

---

## 4. 빌드 워크플로우

### TEI XML → 사이트

```powershell
cd critic-ontology
py build.py
```

build.py 출력:
- `site/essays/{stem}.html` — 메타데이터 HTML (원문 없음, 저작권 고지 포함)
- `site/critics/{critic-id}.html` — 비평가 프로필 HTML
- `site/writers/{person-id}.html` — 작가 프로필 HTML
- `site/thinkers/{person-id}.html` — 이론가 프로필 HTML (인용 문맥 포함)
- `site/data/graph.json` — 관계망 노드/엣지 데이터
- `site/data/critics.json` — 비평가 목록 데이터
- `site/data/writers.json` — 작가 목록 데이터 (encykorea, nlk, ref 포함)
- `site/data/thinkers.json` — 이론가 목록 데이터 (context_count 포함)

### 박사논문 데이터 변환

```powershell
cd ..   # 온톨로지/ 디렉터리에서
py convert_phd.py
```

- 입력: `200805_현대문학_박사논문.xlsx` (1,528건)
- 출력: `critic-ontology/site/data/bibliography.json`
- `WRITER_NODE_MAP` 에 작가명 → 노드 ID 매핑 추가하면 노드 연결 확장

### 2000년대 비평 데이터 변환

```powershell
cd ..   # 온톨로지/ 디렉터리에서
py convert_criticism.py
```

- 입력: `2000-2020년대 시 문학 진단 비평(목록) (1).xlsx` (3 시트, 총 136건)
- 출력: `critic-ontology/site/data/criticism.json`
- 엑셀에 subject(대상), topic(주제), debate(논쟁) 컬럼 추가 후 재실행하면 필터 UI에 자동 반영
- COL 인덱스: no=0, year=1, title=2, author=3, journal=4, pages=5, note=6, subject=7, topic=8, debate=9

### Neo4j 동기화 (자동)

`py build.py` 실행 시 끝에 Neo4j 자동 동기화 시도. Neo4j Desktop이 실행 중이면 graph.json을 Neo4j에 반영. 꺼져 있으면 경고 출력 후 건너뜀 (빌드 실패 아님).

수동 로드가 필요할 때:
```powershell
cd critic-ontology
py neo4j_load.py
```

### GraphRAG API 서버 실행

```powershell
cd critic-ontology
py -m uvicorn neo4j_api:app --reload
```

- 포트: 8000. ask.html이 `http://127.0.0.1:8000/ask`에 POST 요청
- Neo4j Desktop이 실행 중이어야 함
- `.env` 파일에 `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `ANTHROPIC_API_KEY` 필요
- 엔드포인트: `GET /` (헬스체크), `POST /ask` (GraphRAG 질의), `GET /stats`

### 새 비평가 추가 절차

비평집·전집을 새로 인코딩하기 전에 반드시 먼저 수행.

1. **NLK Person RDF 조회** (`온톨로지/Person_rdf_20260401/*.rdf`)
   - 이름 검색 → `schema:jobTitle` / `nlon:fieldOfActivity` 로 문학 관련 항목 필터
   - 해당 블록의 `rdf:about` → NLK URI 추출
   - `owl:sameAs` 에서 Wikidata QID, VIAF, ISNI 추출
2. **persons.json 등록** — 슬러그 키(`p-{slug}`)로 추가:
   ```json
   "p-hwang-hyonsan": {
     "label": "황현산",
     "role": "critic",
     "wikidata": "Q12625944",
     "encykorea": null,
     "nlk": "http://lod.nl.go.kr/resource/KAC201208718",
     "isni": "000000004542828X",
     "viaf": "http://viaf.org/viaf/12101125",
     "encykorea_work": null
   }
   ```
3. **Git commit** — persons.json만 단독 커밋 후 push
4. 이후 TEI XML에서 `ref="#p-{slug}"` 로 참조 → build.py가 자동으로 LOD 링크 연결

> 작가(writer)·이론가(theorist) 신규 등록도 동일한 절차. 외국 인물은 NLK RDF 대신 Wikidata API 사용 (섹션 13 참조).

### 새 비평글 추가 절차

1. 원문 텍스트를 `essays/{stem}.txt` 저장
2. `essays/{stem}.xml` 생성 및 TEI 인코딩
3. `py build.py` 실행 (사이트 + Neo4j 동시 갱신)
4. build 결과 확인: graph.json 노드·엣지, concepts.json 개념어·excerpt
5. `index.html` 에 essay-card 추가
6. Git diff 확인 (essays/, .env 제외) → push

### 파일명 규칙

`{비평가-슬러그}_{대상-슬러그}_{연도}.xml`

- 특정 작가 없는 에세이(시평·사회비평 등): `{비평가-슬러그}_{주제-슬러그}_{연도}.xml`
  예: `yu-jongho_freedom-name_1960.xml`

### sourceDesc 출처 기재 규칙

**초출지 있는 경우:**
```xml
<bibl>
  <title>에세이 제목</title>
  <date when="1960">1960</date>
  <note>《현대문학》, 1960년 9월호. 수록: 『비순수의 선언 — 유종호 전집 1』, 민음사, 1995</note>
</bibl>
```

**초출지 미상인 경우:**
```xml
<bibl>
  <title>에세이 제목</title>
  <date when="1960">1960</date>
  <note>초출지 미상 (1960). 수록: 『비순수의 선언 — 유종호 전집 1』, 민음사, 1995</note>
</bibl>
```

**전집 수록 시 대체·편집 사항은 note에 추가:**
```
전집 편집 시 「원래 글 제목」을 대체하여 수록.
```

### 특정 작가 없는 에세이 처리

정치·사회 시평, 문학론, 비평론 등 비평 대상 작가가 없는 에세이:
- `subject` 없이 비평가 단독 에세이로 처리
- 이론가로 인용된 인물은 `role="foreigner scholar"` 또는 `role="scholar"`로 마크업 → `uses_theory` 엣지 생성
- graph.json에서 `wrote` 엣지만 생성 (subject_of 없음)

---

## 5. graph.json 형식

```json
{
  "nodes": [
    { "id": "p-kim-uchang", "label": "김우창", "type": "critic",
      "ref": "https://www.wikidata.org/wiki/Q17129594", "degree": 4 },
    { "id": "kim-uchang_yun-dongju_1985", "label": "윤동주의 시와 근대적 자아",
      "type": "essay", "year": "1985", "degree": 3 },
    { "id": "concept-슬픔차로운-양심", "label": "괴로운 양심", "type": "concept", "degree": 2 }
  ],
  "edges": [
    { "source": "p-kim-uchang", "target": "kim-uchang_yun-dongju_1985",
      "type": "wrote", "weight": 1 },
    { "source": "kim-uchang_yun-dongju_1985", "target": "concept-괴로운-양심",
      "type": "uses_concept", "weight": 1 }
  ]
}
```

- `node.degree` — 연결 엣지 수 합산 (weight 반영). 노드 크기에 반영
- `edge.weight` — 같은 source→target 쌍 반복 횟수. 엣지 굵기에 반영
- `node.type`: `critic` | `writer` | `theorist` | `essay` | `concept`
- `edge.type`: `wrote` | `subject_of` | `uses_theory` | `uses_concept`
- concept 노드: `interp[type='concept']` 텍스트에서 자동 추출. ID = `concept-{slug}` (40자 이내)
- 같은 개념 텍스트가 여러 에세이에 반복 출현 시 weight 증가 → 에세이 간 공유 개념을 시각적으로 강조

---

## 6. concepts.json 형식

```json
[
  {
    "name": "인간모멸",
    "slug": "인간모멸",
    "essay_count": 2,
    "essays": [
      { "stem": "yu-jongho_son-changsub_1959", "title": "모멸과 연민 — 손창섭론", "year": "1959",
        "excerpt": "손창섭의 작업은 인간의 추태를 집요하게 폭로하는..." },
      { "stem": "yu-jongho_confession_1961", "title": "고백이라는 것", "year": "1961",
        "excerpt": "이상이나 꿈을 치몽으로 부정하는 작가에게..." }
    ]
  }
]
```

- `concepts.html`에서 fetch해 좌측 목록 / 우측 에세이 상세 UI로 표시
- 빈도(essay_count) 내림차순 정렬
- `interp[type='concept']` 텍스트가 그대로 `name`. 같은 개념이 여러 에세이에 반복 출현 시 essay_count 증가
- `excerpt`: build.py가 해당 interp의 부모 `<p>`/`<s>` 텍스트에서 자동 추출 (최대 150자)
- **concepts.html 표시 기준: `essay_count >= 2`인 개념어만 공개** — 1편만 등장한 개념어는 JSON에는 있지만 UI에서 숨김

## 6-1. writers.json / thinkers.json 형식

```json
[
  {
    "id": "p-00247",
    "name": "윤동주",
    "ref": "https://www.wikidata.org/wiki/Q625089",
    "encykorea": "https://encykorea.aks.ac.kr/Article/E0042294",
    "encykorea_work": null,
    "nlk": "http://lod.nl.go.kr/resource/KAC201110203",
    "essay_count": 3,
    "critics": ["p-00117", "p-00246"]
  }
]
```

thinkers.json 추가 필드:
- `context_count`: 인용 문맥(sentence) 개수
- 인용 문맥 출처 표기 순서: `— 비평가 · 에세이 제목`

---

## 7. bibliography.json 형식

```json
{
  "id": 1,
  "type": "phd",
  "title": "윤동주 시의 자아 연구",
  "title_full": "윤동주 시의 자아 연구 = A Study on...",
  "author": "김용주",
  "institution": "국민대학교",
  "year": 2004,
  "genre": "시",
  "subject1": "시인론",
  "subject2": null,
  "major": "작가론",
  "period": "일제강점기",
  "writer": "윤동주",
  "writer_node_id": "p-yun-dongju",
  "keywords": ["자아", "저항", "식민지"]
}
```

- `type`: `"phd"` | `"kci"` — KCI 논문 추가 시 같은 구조로 합류
- `writer_node_id`: 온톨로지 노드와 연결점. `convert_phd.py`의 `WRITER_NODE_MAP` 에서 관리

---

## 7. 시각화 (site/graph.html)

Cytoscape.js 3.28 기반.

- 노드 크기: `degree` 비례 (56~120px). essay 노드 고정 110×56. concept 노드 다이아몬드 52×52
- 엣지 굵기: `weight` 비례 (1.5~6px)
- 노드 클릭: 사이드패널 (데스크탑) / 하단 드로어 슬라이드업 (모바일 768px 이하)
- 비평가 노드 클릭 시 → "비평가 프로필 보기" 링크 포함
- 에세이 노드 클릭 시 → "구조화 데이터 페이지 보기" 링크 포함
- 개념 노드 클릭 시 → "이 개념이 사용된 비평글" 목록
- 노드 hover: 연결 강조, 나머지 페이드
- 필터: 비평가/작가/이론가/비평글/개념어 유형별 토글
- 검색: 왼쪽 상단 검색창 — 한글 포함 노드 이름 실시간 검색, 클릭 시 해당 노드로 줌·포커스
- URL hash: `site/graph.html#essay-stem` 형태로 진입 시 해당 노드 자동 포커스 (index.html "관계망에서 보기" 버튼 연동)

### 색상 시스템
| 유형 | 색상 | 모양 |
|---|---|---|
| 비평가 (critic) | #c9986a | 원 |
| 작가 (writer) | #6a9bc9 | 원 |
| 이론가 (theorist) | #9a7ac9 | 원 |
| 비평글 (essay) | #c8c8a8 | 둥근 직사각형 |
| 개념어 (concept) | #7ac9a0 | 다이아몬드 |

---

## 8. 선행연구 탭 (research.html)

- 데이터: `site/data/bibliography.json` fetch
- 작가 중심 검색: 좌측 목록에서 작가 클릭 → 우측에 논문 목록
- 연도별 막대 차트 (클릭 시 해당 연도 필터)
- 장르 필터 (시/소설/비평/희곡 등)
- ● 표시 = 관계망 노드와 연결된 작가
- KCI 논문 추가 시: `type: "kci"` 레코드를 bibliography.json에 추가하면 자동 포함

---

## 9. 반응형 (768px 기준)

- 768px 이하: 모바일 레이아웃 자동 전환
- graph.html: 사이드패널 숨김 → 하단 드로어
- index/essay: 여백·폰트 축소
- critics.html: 카드 그리드 1열
- research.html: 좌우 분할 → 상하 분할

---

## 10. 배포

Cloudflare Workers (무료 티어). `wrangler.jsonc`의 `assets.directory = "."`.

```
py build.py → git push → Cloudflare Workers 자동 서빙
```

---

## 11. TEI XML 인코딩 패턴

### 파일명 규칙
`비평가-슬러그_대상-슬러그_연도.xml` (동일 이름 `.txt` 병행)

예: `kim-uchang_yun-dongju_1985.xml` + `kim-uchang_yun-dongju_1985.txt`

### 인물 최초 정의
```xml
<persName xml:id="p-habermas"
          ref="https://www.wikidata.org/wiki/Q76509"
          role="foreigner scholar">위르겐 하버마스</persName>
```

### 이후 참조
```xml
<persName ref="#p-habermas">하버마스</persName>
```

### role 속성 → build.py 분류
| role 값 | 분류 |
|---|---|
| `critic` | 비평가 (비평글 저자) |
| `poet`, `novelist`, `writer` | 작가 (비평 대상) |
| `scholar`, `foreigner scholar` | 이론가 (이론 활용) |

### build.py 이론가 추출 로직
`role`에 `scholar` 포함 + 비평 대상(`subjects`)에 없음 + 비평가 본인 아님 → `theorist`

### 개념어 인코딩

**개념어는 teiHeader의 `<interpGrp type="concept">` 블록에 선언하고, 본문 `<p>`/`<s>` 안에서 `<interp type="concept">핵심어</interp>` 로 직접 텍스트를 포함한다.**

```xml
<!-- teiHeader > encodingDesc > interpGrp (선언부) -->
<interpGrp type="concept">
  <interp xml:id="c-slug" type="concept">핵심어</interp>
</interpGrp>

<!-- 본문: 핵심어를 텍스트로 직접 포함 (excerpt 자동 추출) -->
<interp type="concept">핵심어</interp>
```

- `interp[type='concept']` **텍스트**가 graph.json의 `concept` 노드로 자동 추출
- 노드 ID: `concept-{slug}` (slug = 특수문자 제거 후 최대 40자)
- 에세이 → 개념 엣지 유형: `uses_concept`
- 같은 개념이 여러 에세이에 반복 출현하면 edge weight 증가 → 비평 언어의 공유·전파 추적 가능

**금지 패턴 — 개념어가 추출되지 않음:**
- `<interp type="concept" corresp="#c-slug"/>` — 텍스트 없이 corresp 속성만 사용하면 build.py가 빈 문자열을 읽어 무시함
- `classDecl > taxonomy > category` 구조 — build.py가 처리하지 않음

**interpGrp type 구분:**
- `type="concept"` — 개념어용 (build.py가 concept 노드로 추출)
- `type="stance"` — 인용 태도 분류용 (긍정/비판/중립). build.py에서 무시됨. 현재 사용 중단 권장

**개념어 추출 기준 (엄수)**
- 에세이당 **8~12개** 이내
- 포함: 반복 등장하는 비평 핵심어, 이론가에게서 차용한 이론 개념, 논지의 중심이 되는 해석 개념
- 제외: 요약 문장, 서술적 단언, 결론 진술, 특정 작품 묘사에만 쓰이는 표현
- 표기: **짧은 명사구** (2~8자 내외). 문장 전체를 개념어로 쓰지 말 것
  - 나쁜 예: "손창섭의 작업은 인간의 추태를 집요하게 폭로하는 인간존재에 대한 근본적 모멸이다."
  - 좋은 예: "인간모멸"

---

## 12. AI 행동 규칙

- **원문 텍스트를 HTML에 포함하는 코드 작성 금지**
- **essays/*.xml, *.txt 를 git staging에 추가하는 명령 실행 금지**
- **`.env` 파일을 git staging에 추가하는 명령 실행 금지** (크레덴셜 포함)
- 인물 xml:id 는 한 번 정해지면 변경 금지
- Wikidata ref 추측 채우기 금지 — 모르면 빈값
- build.py 수정 후 반드시 `py build.py` 테스트
- convert_phd.py 수정 후 반드시 `py convert_phd.py` 테스트
- PowerShell에서 한글 포함 git commit 메시지는 here-string 파싱 오류 발생 → ASCII 메시지 사용
- Neo4j URI는 반드시 `bolt://127.0.0.1:7687` 사용 — `neo4j://` 프로토콜은 라우팅 오류 발생

---

## 13. 외부 연결 데이터 (LOD)

- 한국 인물: 국립중앙도서관 LOD (https://lod.nl.go.kr) → Wikidata → ISNI
- 외국 이론가: Wikidata (https://wikidata.org) 우선
- `ref` 속성에 전체 URI. 여러 URI는 공백 구분

### persons.json — 인물 권위 소스

`persons.json` 파일이 LOD 링크의 권위 소스. 키는 **슬러그 형식** (`p-yun-dongju`), XML의 숫자 ID(`p-00247`)와 다름.

```json
"p-yun-dongju": {
  "label": "윤동주",
  "role": "poet",
  "wikidata": "Q625089",
  "wikidata_aliases": ["Q다른Q번호"],
  "encykorea": "https://encykorea.aks.ac.kr/Article/E0042294",
  "nlk": "http://lod.nl.go.kr/resource/KAC201110203",
  "isni": "0000000081384480",
  "viaf": "http://viaf.org/viaf/59228311",
  "encykorea_work": null
}
```

**build.py 연결 메커니즘:**
- `_WIKIDATA_TO_SLUG`: Wikidata Q번호 → 슬러그 역방향 인덱스 (빌드 시 자동 구축)
- `wikidata_aliases`: 같은 인물이 에세이마다 다른 Q번호로 정의된 경우 별칭 등록
- `_persons_record(xml_id, fallback_ref)`: xml_id 직접 조회 → XML ref의 Q번호로 역방향 조회 순

**LOD 배지 표시 우선순위:** encykorea → encykorea_work → 한국현대문학대사전(naver_munhak) → NLK → Wikidata → ISNI → VIAF

**`naver_munhak` 필드:** 네이버 지식백과 「한국현대문학대사전」 항목의 전체 URL (terms.naver.com/entry.naver?docId=...&cid=41708&...). 2000년대 이후 활동 비평가(김우창·유종호·황현산 등)에 추가. 프로필 페이지 배지("한국현대문학대사전 ↗") + essay 칩 배지("문")로 렌더링.

**숫자 xml:id → persons.json 연결 (id_map):** build.py는 `../id_map.json`(슬러그→숫자)을 역인덱스(`_NUM_TO_SLUG`)로 로드. 에세이가 숫자 xml:id(p-00117 등)로 인물을 참조해도 `_persons_record`/`_registry_ref`가 슬러그로 해석해 persons.json 권위 레코드(올바른 wikidata·encykorea·naver_munhak 등)를 사용. author_ref·TTL 노드 ref도 이 경로로 persons.json 우선. → XML ref가 낡아도 persons.json만 고치면 사이트 전체에 반영됨.

**persons.json 수정 시 주의:**
- encykorea URL은 반드시 실제 해당 인물 항목인지 확인 (동명이인 오류 빈번)
  - 서정주: `E0028180`(무형문화재 동명) → 올바른 `E0071543`(시인)
  - 심훈: `E0033978`(조선 승려 동명) → 올바른 `E0033979`(소설가)
- 같은 인물이 에세이마다 Q번호가 다르면 `wikidata_aliases`에 추가
- 인물 이름 표시: `_strip_parens()` 함수가 `（漢字）` `(English)` 괄호 표기 자동 제거 → XML에 한자 병기해도 카드/페이지에는 한글만 표시됨

### 신규 인물 추가 시 Wikidata 검증 절차

persons.json에 새 인물을 추가하거나 기존 Q번호가 의심될 때 반드시 검증.

#### 한국 인물 — NLK Person RDF 우선 (권장)

**비평가(critic)·작가(writer) 구분 없이 한국 인물은 모두 이 절차를 따른다.**

국립중앙도서관 LOD RDF 파일(`온톨로지/Person_rdf_20260401/*.rdf`, 744,496건)에는
이미 검증된 `owl:sameAs → Wikidata QID`가 포함되어 있다.
이 데이터를 먼저 조회하면 동명이인 오류를 크게 줄일 수 있다.

**흐름:**
1. 이름으로 RDF 인덱스 검색 → 문학 관련 `nlon:fieldOfActivity` / `schema:jobTitle` 항목 필터
2. 해당 항목의 `owl:sameAs` Wikidata URL에서 QID 추출
3. QID가 없거나 외국 인물이면 아래 Wikidata API 방식으로 진행

**문학 관련 fieldOfActivity 키워드 (필터 기준):**
`한국 문학`, `한국 소설`, `한국 시`, `한국 희곡`, `한국 수필`, `문학(예술)`, `아동 문학`,
`한국 현대 문학`, `비교 문학`, `영미 문학`, `프랑스 문학`, `철학(사상)`, `미학`, `언어학` 등

**문학 관련 jobTitle 키워드 (필터 기준):**
`시인`, `소설가`, `작가`, `수필가`, `극작가`, `문학비평가`, `평론가`, `철학자`, `번역가` 등

**주의사항:**
- 동명이인 처리: 같은 이름에 QID가 다른 항목 여러 개 → 필드/직업 기준 수동 선택
- NLK에 없는 경우(외국 인물 다수): Wikidata API 방식으로 전환
- 일괄 매칭이 필요하면 Claude에게 `match_from_nlk_rdf.py` 재생성 요청

```python
# match_from_nlk_rdf.py — 온톨로지/ 디렉터리에서 실행
# NLK RDF 전체 파싱(약 30초) → persons.json 자동 업데이트
# (스크립트가 없으면 Claude에게 재생성 요청)
```

#### 외국 인물 — Wikidata API 검색

NLK RDF에 한글 이름이 없는 외국 인물에 한해 Wikidata API를 사용한다.

**1. Wikidata API로 후보 확인**

```python
import urllib.request, urllib.parse, json

def search_wikidata(name, lang='ko'):
    params = {'action':'wbsearchentities','search':name,'language':lang,
              'limit':5,'type':'item','format':'json'}
    url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent':'kcritic/1.0'})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['search']

# 사용: search_wikidata('하이데거') 또는 search_wikidata('Heidegger', 'en')
```

**2. 직업(P106) 우선순위 — 문학·철학 관련 항목 선택**

| 우선순위 | 직업 QID 예시 |
|---|---|
| 높음 ✅ | Q4964182(철학자), Q36180(작가), Q49757(시인), Q6625963(소설가), Q4853732(문학비평가) |
| 중간 | Q201788(역사학자), Q2306091(사회학자), Q2478141(사상가) |
| 낮음 ❌ | Q937857(축구선수), Q82955(정치인) — 동명이인 오류 |

**판단 기준:**
- 현재 QID보다 명확히 높은 직업 점수의 후보 있음 → 교체
- 모든 후보의 직업 불명확(Wikidata에 P106 미등록) → 기존 QID 유지 (변경 근거 없음)
- 기존 QID 자체가 존재하지 않거나 무관한 항목 → 교체 필수

**3. Q번호 확정 후 검증**

`https://www.wikidata.org/wiki/{Q번호}` 직접 접속해서 한글 레이블·직업·설명 확인.

**4. encykorea 동명이인 확인**

`https://encykorea.aks.ac.kr/Article/{E번호}` 접속 → 페이지 상단 인물 설명이 해당 인물인지 직접 확인. 동명이인이 많으므로 생년·직업 반드시 대조.

---

## 14. 스택 요약

| 목적 | 도구 |
|---|---|
| 인코딩 | VS Code + Red Hat XML + `korean-critique-schema.xsd` |
| 빌드 | `build.py` (Python 표준 라이브러리만 + neo4j driver 선택적) |
| 데이터 변환 | `convert_phd.py` (openpyxl), `convert_criticism.py` (openpyxl) |
| 관계망 시각화 | Cytoscape.js 3.28 |
| 그래프 DB | Neo4j Desktop (로컬, bolt://127.0.0.1:7687, APOC 플러그인) |
| GraphRAG API | FastAPI + uvicorn (`neo4j_api.py`, 포트 8000) |
| AI 답변 | Anthropic Claude API (`claude-sonnet-4-6`) — Cypher 생성 + 학술 답변 |
| SPARQL | Comunica + N3 로컬 번들 (site/sparql-bundle.js, ask.html SPARQL 탭에 통합) |
| 호스팅 | Cloudflare Workers (무료) |
| 비용 | 도메인 갱신비 + Anthropic API 사용료 |
| LOD | Wikidata + 국립중앙도서관 LOD |

---

## 15. 공식 OWL 온톨로지 (critic_v7_kcritic.rdf)

- v5 파일: `c:\onedrive\문서\대학원 공부\박사이후 논문 투고\온톨로지\critic_v5_kcritic.rdf`
- v6 파일: `c:\onedrive\문서\대학원 공부\박사이후 논문 투고\온톨로지\critic_v6_kcritic.rdf`
  - v5 대비 추가: `critic:Thinker` 클래스, `cito:citesAsAuthority` 프로퍼티, 이론가 68명, 에세이 48편 인용관계
- **v7 파일 (최신)**: `c:\onedrive\문서\대학원 공부\박사이후 논문 투고\온톨로지\critic_v7_kcritic.rdf`
  - v6 대비 추가: `critic:Writer` 클래스, 한국 작가 40명 NamedIndividual + owl:sameAs (Wikidata/encykorea/NLK LOD/ISNI/VIAF) 177트리플
  - 비평가 owl:sameAs: 김우창(encykorea), 유종호(NLK LOD)

`build.py`의 `build_turtle()`은 이 온톨로지를 준거로 삼아 RDF Turtle을 생성함.

### 온톨로지 URI
- Base: `http://kcritic.kr/ontology/`
- 접두사: `critic: <http://kcritic.kr/ontology/critic#>`

### 클래스 매핑
| build.py 내부 타입 | TTL 클래스 | 온톨로지 클래스 |
|---|---|---|
| `critic` | `critic:Critic` | `http://kcritic.kr/ontology/critic#Critic` |
| `writer` / `theorist` | `foaf:Person` | `http://xmlns.com/foaf/0.1/Person` |
| essay | `critic:CriticalEssay` | `http://kcritic.kr/ontology/critic#CriticalEssay` |

### 핵심 프로퍼티 매핑 (2026-05-22 수정)
| 관계 | TTL 프로퍼티 | 온톨로지 준거 | 비고 |
|---|---|---|---|
| 에세이 저자 | `dcterms:creator` | Dublin Core | |
| 비평 대상 (작가) | `cito:discusses` | CiTO | 비평적 분석의 직접 대상 |
| 이론 인용 (이론가) | `cito:citesAsAuthority` | CiTO | 작가와 이론가 구별 — **기존 cito:discusses에서 변경** |
| 비평가 → 대상 직접 관계 | `critic:analyzes` | 이 온톨로지의 핵심 관계 | |
| 인물 이름 | `foaf:name` | FOAF | |
| 에세이 제목 | `dcterms:title` | Dublin Core | |
| 발표 연도 | `dcterms:date` | Dublin Core | 타입: `xsd:gYear` (**기존 xsd:decimal에서 수정**) |
| 개념어 | `dcterms:subject` | Dublin Core | |

### 통제어휘 규칙 (concept interp 정규화)
같은 개념을 에세이마다 다르게 표기하지 않는다. **표기가 다르면 별개 노드로 분리되어 essay_count가 늘지 않는다.**

기존 통합 결정:
- `심미 감각` → `심미적 감각` (기준어)
- `정돈된 언어` → `균제된 언어` (기준어)
- `농촌적 삶의 긍정` / `농경적 삶` → `농촌적 삶` (기준어)
- `자의식 있는 낭만주의` → `현실적 낭만주의` (기준어)
- 다층 개념(원초적 생명력/마적 힘/원시적 낭만주의 등)은 개념 계층 관계로 처리 — 무분별한 통합 금지

새 에세이에 개념어를 추가할 때, 기존 XML의 개념어 목록을 먼저 확인하고 동일 개념이 있으면 표기를 맞춰야 한다. 확인 방법:
```powershell
py -c "import json,sys; sys.stdout.reconfigure(encoding='utf-8'); [print(c['name']) for c in json.load(open('site/data/concepts.json',encoding='utf-8'))]"
```

### 온톨로지 인물 연결
- `_ONTOLOGY_WIKIDATA` 딕셔너리에 등록된 인물만 `owl:sameAs <http://kcritic.kr/ontology/한국어이름>` 추가
- 김우창 Wikidata: `Q17129594` (검증 완료)
- 새 인물이 온톨로지에 추가되면 `_ONTOLOGY_WIKIDATA` 딕셔너리도 함께 업데이트할 것

---

## 16. 프로젝트 단계 로드맵

### 완료 (Phase 0 — 파일럿)
- 김우창 비평 23편 TEI 인코딩
- RDF Turtle 생성 (169 트리플), Cytoscape.js 관계망, SPARQL 인터페이스
- 사이트 정체성: "kcritic — 한국 비평사 온톨로지 · 파일럿: 김우창 비평 (1979–1992)"

### 다음 단계 (Phase 1 — 비교 관계망)
**학술적 의미를 확보하려면 비평가가 2명 이상 필요.**
우선 추가 대상: 김윤식(반-김우창 입장), 유종호(구체적 비교 가능)
- 김윤식 에세이 최소 5편 인코딩 → 비평가 간 비교 가능
- `critic:respondsTo` 프로퍼티 추가 (에세이 → 에세이 응답 관계)
- 공유 개념어(같은 `dcterms:subject`가 다른 비평가에게 출현)가 진짜 비평사적 신호가 됨

### 다음 단계 (Phase 2 — 개념어 계층)
- 개념어 `encodingDesc` 계층 선언: `<taxonomy>` 요소로 상위-하위 개념 관계 명시
- 예: `명징성` > `언어적 명징화` > `명징한 간결성`
- SKOS 어휘 활용 (`skos:broader`, `skos:narrower`) → concepts.json에 계층 반영
