# CLAUDE.md — 한국 비평사 온톨로지 프로젝트 지침

AI 어시스턴트가 이 프로젝트에서 작업할 때 따를 규칙. 새로운 결정이 생기면 즉시 이 파일을 업데이트할 것.

**현재 상태 (2026-10-22 기준)** — 수치를 인용할 땐 여기를 먼저 확인하고, 다르면 재빌드 후 이 블록을 갱신할 것.

| 항목 | 값 |
|---|---|
| 수록 비평가 | 74인 — 전집 기반 4인(김현 136편·유종호 114편·김우창 109편·황현산 11편) + 『문학과사회』 1–13호(1988–1991) 필자 118편 |
| 수록 비평글 | 488편 (`essays/*.xml`) — 전집 370 + 『문학과사회』 118 (작업 폴더 `../문학과사회/`, 반영 스크립트 `../문학과사회/site_prep/`) |
| 관계망 | 노드 1,944 / 엣지 5,455 · graph.ttl 27,026 트리플 · `_redirects` 1,944줄(한도 2,000 근접) |
| 노드 구성 | theorist 840 · writer 542 · essay 488 · critic 74 |
| 엣지 구성 | uses_theory 2,573 · subject_of 2,394 · wrote 488 |
| 목록 데이터 | writers.json 588 · thinkers.json 878 · concepts.json 4,532(공개 519) |
| 인물 권위 목록 | persons.json 1,636명 — Wikidata 1,040 · NLK 967 (2026-09-30 전수 판정 + 2026-10-22 『문학과사회』 498명 추가: NLK 스냅샷 이름·생년·분야 일치만 연결) |
| 공식 온톨로지 | **v8** (`critic_v8_schema.rdf` + `critic_v8_data.rdf`) |

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
- **첫 번째 예외 (2026-09-15 연구자 결정) — 태도 판정 게임**: `build_interp_game.py` 가 TEI 태도 표시(`@ana` 의 affirmative/neutral/critical)가 붙은 **문장만** `site/data/interp_game.json` 으로 공개한다(현재 224문장, 김우창 17편). 각 문장에 비평문 제목·수록 단행본을 출처로 싣는다. 대상 확대(다른 비평가, 표시 없는 문장, 앞뒤 문맥 등)는 연구자의 명시적 결정 없이 하지 말 것
- **두 번째 예외 (2026-10-23 연구자 결정) — 개념어 예시 문장**: 개념어 화면에서 그 개념어를 쓴 글마다 **그 개념어가 든 문장 하나**를 연구용 인용으로 보인다. `build.py` `collect_interp_concepts()` 가 개념어마다 한 문장(220자 넘으면 개념어 둘레만)을 고르고, `site/data/v2/examples.json`({글 id: {개념어: 문장}}, 글마다 앞 12개 개념어)·`site/data/concepts.json`(예전 화면)에 싣는다. 문단 전체·앞뒤 문맥·한 개념어에 여러 문장으로 넓히지 말 것
- **문장째로 붙은 개념어 표시는 개념어로 나눠 쓴다 (2026-10-23)**: 김우창 등 42편에 `<interp type="concept">` 가 문장 전체(또는 문장 앞머리 요약 꼬리표 "머리 — 설명")를 감싼 곳이 579곳 있었다. XML은 그대로 두고 `concept_split.json`("글 stem|원래 표시 글의 sha1 앞 12자" → 개념어 1~3개, 원문 없음)으로 빌드 때 바꾼다. 문장 칸의 개념어는 그 문장 안에 글자 그대로 있어 예시 문장에 반드시 들어간다. **새로 인코딩할 때는 개념어 표시를 문장 전체가 아니라 개념어 낱말에만 붙일 것**. 이 표에 없는 새 문장째 표시가 생기면 개념어 이름이 문장이 되니 빌드 뒤 `site/data/v2/essays.json` 개념어 길이(20자 넘는 것)를 확인
- **세 번째 예외 (2026-10-23 연구자 결정) — 프로필 인용 문맥**: 작가·이론가 프로필에서 인물이 나온 자리마다 **인물이 나온 문장 하나**(그 문장이 40자보다 짧으면 다음 문장까지, **두 문장을 넘지 않음**, 300자 넘으면 인물 둘레만)를 보인다. build.py `collect_person_contexts` → `_mention_sentence`. 예전처럼 `<p>` 문단 전체를 싣지 말 것. 이번 빌드에서 만들지 않은 옛 프로필(분류 변경·not_person)은 빌드가 리다이렉트로 덮어 옛 문맥을 남기지 않는다
- 판정 수집기 `../판정수집_AppsScript.gs` 는 운영자 메일 주소를 담고 있어 **저장소 밖(부모 폴더)** 에 둔다. 저장소·사이트 코드에는 웹 앱 URL(`site/data/game_config.json`)만 들어간다
- `.env.example` 도 배포 제외 (`.assetsignore`) — 실값은 없어도 어떤 키를 쓰는지 스캐너에 알려주는 힌트가 됨
- **글 찾기 본문 색인 `worker/private/` 은 공개 금지 (2026-10-22)**: 본문 희귀어 역색인(원문에서 만든 낱말→글 번호)은 `.gitignore`·`.assetsignore` 로 막혀 있고 Worker 번들에만 들어간다. GitHub 공개 저장소에 올리거나 정적 파일로 내보내지 말 것. 본문 구간 벡터도 만들어 공개하지 않는다(임베딩 역추적으로 원문 일부 복원 가능). 공개되는 `site/data/find/` 벡터는 메타데이터(제목·개념어·인물)에서만 만든다
- **방문 통계 (2026-10-25)**: `kc-stat.js`(kc.js `shell()`·kc-shell.js 가 불러옴)가 화면을 열 때·머리말 검색 때 `POST /api/hit` 를 보내고, Worker 가 D1 `kcritic-stats` 의 `hits(day, kind, k, n)` 에 날짜(한국 시각)·항목별 건수만 +1 한다(표: `worker/stats.sql`). **IP·쿠키·방문자 식별자는 저장하지 않는다** — IP 는 분당 요청 상한을 셀 때 메모리에서만. 방문 = 그 탭에서 처음 연 화면(sessionStorage). 봇 UA·엉뚱한 키는 버린다. 14개월 넘은 기록은 지운다. 조회는 `GET /api/stats`(Authorization: Bearer `STATS_TOKEN` 비밀값, CORS 허용) — **통계 화면은 사이트·저장소에 두지 않는다**(연구자 결정): 관리자 컴퓨터의 `../kcritic_방문통계.html`, 토큰은 `../관리자_통계_토큰.txt`. 관리자 브라우저는 `?nostat=1` 로 한 번 열면 통계에서 빠진다. 글 찾기 질문은 `/api/find` 에서 센다(`ns=1` 이면 안 셈)
- `/api/find` 응답에는 질문 벡터와 '질문에 있던 낱말 → 글 번호'만 담는다. 원문 문장을 돌려주는 경로를 만들지 말 것

### API 서버(`neo4j_api.py`) 보안 규칙 — 2026-09-07 강화

정적 사이트가 아니라 **`https://kcritic-api.onrender.com` 이 실제 공격면**이다. 아래를 되돌리지 말 것.
> 2026-10-25 현황: 이 서버는 **기여하기·관리 화면용으로만 살아 있다** — `contribute.html` 이 `POST /contribute`, `admin.html` 이 `/admin/*` 를 부른다(제출은 서버 디스크의 JSON 파일, Neo4j 안 씀). `/ask`(GraphRAG)·`/stats` 는 Neo4j 에 기대는데 Neo4j 는 구자료라(§4 「Neo4j — 구자료」) 연결이 끊겨 `/stats` 가 500 이고, `/ask` 를 부르는 페이지는 없다. 아래 규칙은 서버가 떠 있는 동안 그대로 지킨다.

- **`/ask` 의 Cypher 는 반드시 `assert_read_only()` 를 통과시킨 뒤 실행**한다. LLM이 만든 쿼리를 그대로 `run_cypher` 에 넘기면 프롬프트 인젝션으로 `MATCH (n) DETACH DELETE n` 이 실행돼 DB가 통째로 지워진다
- `run_cypher` 는 `default_access_mode=READ_ACCESS` 세션을 쓴다 (검증과 이중 방어)
- **CORS `allow_origins=["*"]` 금지** — `ALLOWED_ORIGINS` 목록으로만. `*` 이면 아무 사이트나 방문자 브라우저로 `/ask` 를 불러 Anthropic 사용료를 전가할 수 있음
- 유료 API를 부르는 경로(`/ask`, Gemini 배치)는 **`check_global_budget()` 필수** — IP 위조로 개별 한도를 우회해도 비용이 무한정 늘지 않게
- `/contribute` 에도 `check_rate` 적용 유지. 없으면 자동 제출로 디스크를 채우고 10건마다 Gemini 배치가 돌아 비용이 증폭됨
- Pydantic 모델 필드는 전부 `max_length` 를 갖는다
- `EmailStr` 사용 금지 — `email-validator` 패키지가 `requirements.txt` 에 없어 기동이 실패한다. 정규식 검증으로 대체돼 있음
- 환경변수는 `_env()` 가 `NEO4J_*` 와 `AURA_*` 를 모두 허용한다 (과거 이름 불일치로 운영 Neo4j 연결이 끊겨 `/stats` 가 500이었음)

---

## 2. 실제 폴더 구조

```
critic-ontology/
├── essays/                  ← 로컬 전용 (gitignored)
│   ├── *.xml                ← TEI XML 원문 인코딩
│   └── *.txt                ← 원문 텍스트 (XML 작업 전 저장)
├── schema/
│   └── korean-critique-schema.xsd   ← v5 활성본 (부모 폴더에 버전 아카이브)
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
│   │   ├── criticism.json   ← convert_criticism.py 출력: 2000년대 비평 데이터
│   │   ├── evaluations.json ← build_evaluations.py 출력: 태도 평가 대기열·판단
│   │   ├── interp_game.json ← build_interp_game.py 출력: 판정 게임 문장 224개 (§1 예외)
│   │   ├── game_config.json ← 판정 수집 웹 앱 URL (비어 있으면 브라우저 보관 모드)
│   │   └── bibliography.json ← convert_phd.py 출력: 선행연구 데이터
│   ├── graph.html           ← 예전 주소: 루트 `graph.html`(관계망 2판)로 #id 를 넘겨준다
│   ├── graph_full.html      ← 예전 관계망(Cytoscape.js, 1,944개 점 전체) 그대로 보관
│   └── sparql-bundle.js     ← Comunica + N3 로컬 번들 (ask.html SPARQL 탭)
├── index.html               ← 비평글 목록 (메인, essay-card 수동 관리)
├── critics.html             ← 비평가 목록 탭
├── writers.html             ← 작가 목록 탭
├── thinkers.html            ← 이론가 목록 탭
├── concepts.html            ← 개념어 탭
├── research.html            ← 선행연구 탭
├── criticism.html           ← 2000년대 비평 탭
├── ask.html                 ← 질문하기 탭 (SPARQL 탭만 동작 — 브라우저 Comunica 로 graph.ttl 질의. 자연어 GraphRAG 는 「준비 중」 안내만)
├── contribute.html          ← 기여하기 탭
├── about.html               ← 소개 탭 (수치·로드맵 하드코딩 — 갱신 시 §17과 함께 고칠 것)
├── admin.html               ← 관리 화면 (네비 미노출)
├── sparql.html              ← SPARQL 단독 페이지 (네비 미노출 — ask.html 내 탭으로 대체)
├── 404.html                 ← 자체 완결형 404 (§11 참조)
├── style.css                ← 공유 스타일 (반응형 포함)
├── evaluate.html            ← 태도 평가 탭 = 문장 단위 태도 판정 게임 (순위 배너, Apps Script 로 전송)
├── evaluate-essay.html      ← (비평문×작가) 태도 평가 연구자 도구 (브라우저 저장 + 파일 내보내기, 네비 미노출)
├── build.py                 ← TEI XML → HTML + JSON + TTL 빌드 스크립트 (Neo4j 동기화는 `--neo4j` 일 때만, 구자료)
├── build_evaluations.py     ← 평가 대기열 생성 (build.py 이후 실행)
├── build_interp_game.py     ← 판정 게임 문장 추출 → site/data/interp_game.json (build.py 이후 실행)
├── paper_stats.py           ← 논문 표·질의 수치 재현 (rdflib 필요)
├── persons.json             ← 인물 권위 소스 (LOD URI, Wikidata 등) — 슬러그 키
├── id_map.json              ← 슬러그 ↔ 숫자 xml:id 매핑 (build.py가 우선 참조)
├── critic_v8_schema.rdf     ← 공식 OWL 스키마 (배포·다운로드 대상)
├── critic_v8_data.rdf       ← 공식 OWL 데이터 (파일럿 스냅샷 152 개체)
├── neo4j_api.py             ← FastAPI 서버(Render 배포). 사이트가 쓰는 건 /contribute·/admin/* 뿐, /ask·/stats 는 Neo4j 구자료라 미사용
├── neo4j_load.py            ← graph.json → Neo4j 단독 로드 스크립트 (구자료)
├── verify_lod.py            ← LOD QID 검증 (§14 워크플로우)
├── suggest_qid_fixes.py     ← QID 교정 후보 제안
├── enhanced_qid_search.py   ← 외국 인물 영문명 재검색
├── apply_qid_fixes.py       ← 교정 CSV → persons.json 반영
├── sync_xml_refs.py         ← 교정값 → essays XML ref 동기화
├── verify_encykorea.py      ← encykorea ↔ Wikidata P9475 교차검증
├── enrich_en_names.py       ← 외국 인물 영문 레이블 보강
├── essays_backup_qidfix/    ← sync_xml_refs.py 백업 (gitignored)
├── deploy.ps1               ← build + commit + push + wrangler deploy 일괄
├── .env                     ← Neo4j(구자료)/Anthropic 크레덴셜 (gitignored, 절대 커밋 금지)
├── .assetsignore            ← Cloudflare 배포 제외 목록 (§11 주의사항 필독)
├── wrangler.jsonc           ← Cloudflare Workers 배포 설정
├── .gitignore
└── CLAUDE.md                ← 이 파일
```

> `convert_phd.py` · `convert_criticism.py` 는 저장소가 아니라 **부모 폴더(`온톨로지/`)** 에 있다. 출력만 `critic-ontology/site/data/` 로 들어온다.

---

## 3-0. 사이트 2판 (2026-10-22 공개)

첫 화면·탐색·개체 페이지를 새 체계로 바꿨다. 해외 DH 포털(프린스턴 Shakespeare and Company Project, 알토대 Sampo 포털)의 '관점 + 패싯 + 결과 보기' 구조를 따랐다.

| 파일 | 역할 |
|---|---|
| `index.html` | 첫 화면 — 글 찾기 검색창, 관점 카드 4, 컬렉션, 분석·참여 |
| `explore.html?p=find\|essays\|people\|concepts\|venues` | 관점별 탐색. 왼쪽 패싯(개수는 다른 조건을 반영), 오른쪽 목록·표·분석, CSV 내려받기 |
| `entity.html?t=person\|essay\|concept\|issue&id=` | 개체 페이지 — 유형 표시, 외부 전거, 핵심 수, 탭, 오른쪽 기본 정보·IRI |
| `kc.css` `kc.js` | 디자인 체계(흰 바탕·먹색·강조색 하나·유형별 고정 색)와 공통 머리글·바닥글 |
| `kc-find.js` | 글 찾기 브라우저 엔진 (아래) |
| `list.html` | 예전 첫 화면(카드 488개). 바닥글에서만 연결. `../문학과사회/site_prep/make_cards.py` 가 여기에 『문학과사회』 카드를 넣는다 |

- **주 메뉴(모든 페이지 동일)**: 글 찾기 · 글 · 인물 · 개념어 · 지면 · 관계망 · 질문하기 · 소개. 예전 페이지(critics/writers/thinkers/concepts/research/criticism/evaluate/contribute/about/ask/sparql/admin/list, site/graph.html, build.py 템플릿 4곳)의 `<nav class="site-nav">` 도 이 8개로 맞췄다. 태도 평가·선행연구·2000년대 비평·기여하기는 2판 바닥글에서 연결
- 2판 페이지는 '비평글' 대신 **'글'** 이라고 부른다 (좌담·심사평 등 비평 외 글도 포함하므로)
- **잡지 원문 안내**: 원문을 제공하지 않는 대신 발행처 공식 페이지로 연결한다. 『문학과사회』 → https://moonji.com/literatureAndSociety/intro (문학과지성사 소개·구독, 호별 과월호 목록은 없음). 등록은 build.py `JOURNAL_LINKS`(현행 글 페이지 출처 칸·안내문)와 kc.js `VENUE_LINK`(2판 글·호 페이지) 두 곳을 같게
- 데이터: `site/data/v2/{essays,people,concepts,issues}.json` ← `py build_site_v2.py` (build.py 다음). 호별 목차는 `../문학과사회/encode_ledger.json` 이 있을 때 다시 만든다

### 글 찾기 (2026-10-22)
작업도구/추천 「읽을 글 찾기」 2판을 kcritic 글에 옮긴 것. **DeepSeek(질문 해석·재순위)은 쓰지 않는다**(연구자 결정).
- 점수 = 뜻 0.62 + 낱말 0.23 + 인물 관계 0.15. 뜻 = bge-m3 글 전체 0.55 + 칸별(제목·개념어·인물) 최고 0.45. 낱말 = 개념어·인물 정확 일치(idf)·부분 일치·글자 2-gram BM25·**본문 희귀어**(Worker 조회)·드문 말 가산. 인물 관계 = 질문 속 인물이 쓴/다룬/인용한 글(「~가 쓴」「~를 인용한」「~론」 규칙)
- 구성: 브라우저(`kc-find.js`)가 공개 벡터 `site/data/find/{vec.bin,vocab.bin,meta.json}`(int8, 약 4MB)로 계산. `/api/find`(Worker `worker/index.js`)는 Workers AI `@cf/baai/bge-m3` 질문 벡터 + 비공개 본문 희귀어 조각(`worker/private/bodylex/*.txt` 256개, FNV-1a)만 돌려준다. Worker CPU 를 거의 쓰지 않아 무료 한도(10ms) 안
- 색인 다시 만들기(글이 바뀌면): `py build.py` → `py build_site_v2.py` → `<ocr_train venv python> -X utf8 find/build_find.py`(GPU, 1분). 벡터와 essays.json 순서가 어긋나도 id 로 맞추며, 벡터 없는 글은 낱말·관계로만 찾힌다
- 평가: 정답 정해진 질문 46개(`../site_proto/v2/find/eval_set.json`). 운영 구성 MRR 메타 0.903 / 본문 0.852 (로컬 GPU 서버판은 본문 구간 벡터까지 써서 0.903 / 0.938, 1판 0.933 / 0.293). Node 대조: `node ../site_proto/v2/find/node_parity.js`
- 시안·로컬 서버판·평가 도구는 저장소 밖 `../site_proto/v2/` 에 있다

## 3. 사이트 구조 (네비 탭 12개)

| 탭 | 파일 | 설명 |
|---|---|---|
| 비평글 | `index.html` | 수록 비평글 카드 목록 |
| 비평가 | `critics.html` | 비평가 카드 그리드 → 클릭 시 프로필 페이지 |
| 작가 | `writers.html` | 비평 대상 작가 목록 → 클릭 시 프로필 페이지 |
| 이론가 | `thinkers.html` | 비평에서 인용된 이론가 목록 → 클릭 시 프로필 페이지 (인용 문맥 포함) |
| 관계망 | `graph.html` (루트) | 관계망 2판: 한 사람·글을 가운데 둔 1단계 이웃 SVG, 「비슷한 사람」(코사인), 세기 「글 수 / 특이도」, 구조 속 위치(`site/data/v2/graph_metrics.json`). 예전 화면은 `site/graph_full.html` |
| 개념어 | `concepts.html` | 개념어 색인 + 사용 에세이 목록 (좌우 분할 UI) |
| 선행연구 | `research.html` | 박사·KCI 논문 작가 중심 검색 |
| 2000년대 비평 | `criticism.html` | 2000년대 시 문학 비평 136건, 연대/대상/주제/논쟁 필터 |
| 질문하기 | `ask.html` | SPARQL 탭(브라우저 Comunica, `site/data/graph.ttl` — 서버 불필요). 자연어 GraphRAG 는 「준비 중」(Neo4j 구자료) |
| 태도 평가 | `evaluate.html` | 태도 표시 문장 224개 판정 게임 · 인코더 표시/참여자 분포 공개 · 판정 순위 배너 (비평문×작가 도구 `evaluate-essay.html` 로 연결) |
| 기여하기 | `contribute.html` | 참여·기여 안내 |
| 소개 | `about.html` | 프로젝트 소개·통계·기술 구성·로드맵 |

네비 미노출 페이지: `admin.html`(관리), `sparql.html`(ask.html 내 탭으로 대체), `404.html`.

### 네비게이션 경로 (파일 위치별)

**네비 항목은 build.py 템플릿에 하드코딩**되어 있다. 탭을 추가·삭제하면 루트 HTML 전부 + build.py의 네 군데 템플릿(essay·critics·writers·thinkers 프로필)을 함께 고쳐야 한다.

- 루트 페이지 — **12개 전부**: `비평글`, `비평가`, `작가`, `이론가`, `관계망`(`site/graph.html`), `개념어`, `선행연구`, `2000년대 비평`, `질문하기`, `기여하기`, `소개`
- `site/essays|critics|writers|thinkers/*.html` (build.py 생성) — **11개** (`기여하기` 제외): `../../index.html`, `../../critics.html`, `../../writers.html`, `../../thinkers.html`, `../graph.html`, `../../concepts.html`, `../../research.html`, `../../criticism.html`, `../../ask.html`, `../../evaluate.html`, `../../about.html`
- `site/graph.html` — `../index.html`, `../critics.html`, `../writers.html`, `../thinkers.html`, `graph.html`, `../concepts.html`, `../research.html`, `../criticism.html`, `../ask.html`, `../evaluate.html`

> 알려진 불일치: 하위 페이지 네비에만 `기여하기`가 빠져 있다. 의도한 것인지 확인 필요 — 맞추려면 build.py 템플릿 4곳에 `../../contribute.html` 추가.

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
- `site/thinkers/{person-id}.html` — 이론가 프로필 HTML (인용 문맥: 인물이 나온 문장, 두 문장 이내)
- `site/data/graph.json` — 관계망 노드/엣지 데이터
- `site/data/critics.json` — 비평가 목록 데이터
- `site/data/writers.json` — 작가 목록 데이터 (encykorea, nlk, ref 포함)
- `site/data/thinkers.json` — 이론가 목록 데이터 (context_count 포함)
- `site/data/concepts.json` — 개념어 색인 (concepts.html 전용, 관계망 노드 아님 — §5 참조)
- `site/data/graph.ttl` — RDF Turtle 직렬화 (v8 온톨로지 준거, 20,689 트리플, 끊긴 인물 IRI 0)

빌드 끝의 Neo4j 동기화는 기본으로 건너뛴다(2026-10-25, Neo4j 구자료). 로컬 DB 를 일부러 갱신할 때만 `py build.py --neo4j`.

**빌드 후 필수 검증** — `py build.py` 를 2회 연속 실행하고 `site/data/` 산출물이 바이트 단위로 동일한지 확인할 것(§13 결정성 규칙).

### 평가(태도) 대기열 생성

```powershell
cd critic-ontology
py build_graph_metrics.py    # build_site_v2.py 다음: site/data/v2/graph_metrics.json (연결·매개 중심성, Louvain 군집 seed 42, 참여 계수). networkx 필요
py build_evaluations.py      # build.py 실행 후에 돌릴 것 (graph.json 을 읽는다)
```

- 출력: `site/data/evaluations.json` (웹 UI 적재) · `../평가작업목록.xlsx` (연구자 배포용)
- 평가 단위는 **(비평문 × 대상작가) 쌍 1,624개** — `cito:discusses` 엣지 하나가 판단 항목 하나
- 기존 판단은 재생성해도 보존된다(`judgements` 배열을 읽어 되쓴다)

**평가 데이터를 본체 그래프에 병합하지 말 것.** 다른 트리플은 외부 전거로 대조 가능한 사실이라
불일치가 오류지만, 태도 판정은 외부에 정답이 없는 해석이라 **불일치 자체가 데이터**다.
같은 항목에 복수의 판단이 쌓이면 덮어쓰지 않고 판단자·일시와 함께 모두 보존한다.

**`evaluate-essay.html` 에는 원문 문장을 넣지 않는다** (§1). 서지 정보와 비평문 페이지 링크만 제공하며,
비평문을 읽은 연구자를 판단자로 전제한다.

### 태도 판정 게임 (문장 단위)

```powershell
cd critic-ontology
py build_interp_game.py      # build.py 실행 후 (graph.json 에서 제목·연도·비평가를 읽는다)
```

- 출력: `site/data/interp_game.json` — `interp`/`quote` 의 `@ana` 에 태도 값이 있는 문장. 점 표시(텍스트 없는 `<interp/>`)는 문장 전체 판정, 텍스트가 있으면 그 범위를 강조
- 항목 ID = `{stem}#{sha1(stem|span|sentence)[:10]}` — XML 순서가 바뀌어도 유지되지만 **문장·범위 텍스트를 고치면 ID가 바뀌어 기존 판정과 끊긴다**
- 줄 단위 개념어 꼬리표(`<interp type="concept">…</interp>` 뒤에 줄바꿈)는 원문이 아니므로 문장에서 뺀다
- 수집: `evaluate.html` → `game_config.json` 의 Apps Script 웹 앱에 `text/plain` POST → 운영자 Google 시트에 누적 + 매일 요약 메일. 순위는 GET(60초 캐시), 기준은 **uid별 서로 다른 문장 수**(재판정은 마지막 것만)
- 수집기 코드는 `../판정수집_AppsScript.gs` (배포 순서는 파일 머리 주석). 고친 뒤에는 Apps Script 에서 **새 버전으로 재배포**해야 반영된다
- 수집기 안전장치를 되돌리지 말 것: 항목 ID는 공개 `interp_game.json` 과 대조, 판정값 화이트리스트, uid·전체 시간당 한도, 닉네임 `= + - @` 시작 거부(시트 수식 주입), uid 비공개(순위에는 해시 태그만)
- 시트의 판정도 본체 그래프에 병합하지 않는다 — 위 원칙과 같다

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

### Neo4j — 구자료 (2026-10-25)

**사이트는 Neo4j 를 쓰지 않는다.** 질문하기 탭은 `graph.ttl` 을 브라우저에서 SPARQL 로 질의하고(서버 불필요), 자연어 GraphRAG 는 「준비 중」 안내만 있다. Render 의 `neo4j_api.py` 는 기여하기(`/contribute`)·관리(`/admin/*`)용으로만 살아 있고 그 경로는 Neo4j 를 쓰지 않는다. Aura·로컬 Neo4j 의 데이터는 예전 빌드의 스냅샷이다.
- `py build.py` 는 Neo4j 동기화를 하지 않는다. `sync_neo4j()` 는 `MATCH (n) DETACH DELETE n` 후 다시 넣으므로, 로컬 DB 를 일부러 갱신할 때만 `py build.py --neo4j`
- 비평글을 추가·공개할 때 Neo4j 재적재는 필요 없다(사이트 반영 = build.py → build_site_v2.py → 배포)
- GraphRAG 를 다시 살리려면 Neo4j(Aura) 재적재, `/stats` 복구, `ask.html` 연결이 함께 필요하다 — 그때 이 절을 고칠 것

수동 로드가 필요할 때(구자료 갱신):
```powershell
cd critic-ontology
py neo4j_load.py
```

### GraphRAG API 서버 실행 (구자료 — 사이트 미사용)

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
3. `py build.py` 실행 (사이트 데이터 갱신. Neo4j 는 구자료라 동기화 안 함)
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
    { "id": "p-yun-dongju", "label": "윤동주", "type": "writer", "degree": 3 }
  ],
  "edges": [
    { "source": "p-kim-uchang", "target": "kim-uchang_yun-dongju_1985",
      "type": "wrote", "weight": 1 },
    { "source": "kim-uchang_yun-dongju_1985", "target": "p-yun-dongju",
      "type": "subject_of", "weight": 1 }
  ]
}
```

- `node.degree` — 연결 엣지 수 합산 (weight 반영). 노드 크기에 반영
- `edge.weight` — 같은 source→target 쌍 반복 횟수. 엣지 굵기에 반영
- `node.type`: `critic` | `writer` | `theorist` | `essay`
- `edge.type`: `wrote` | `subject_of` | `uses_theory`

> **개념어는 관계망 노드가 아니다.** 과거에는 `concept` 노드와 `uses_concept` 엣지를 만들었으나 현재 build.py는 생성하지 않는다. 개념어가 사는 곳은 두 군데다:
> - `concepts.json` → `concepts.html` 색인 (UI)
> - `graph.ttl` 의 에세이별 `dcterms:subject "개념어"@ko` **리터럴** (RDF·SPARQL, 현재 4,258건)
>
> 즉 SPARQL로는 개념어를 조회할 수 있지만 Cytoscape 관계망에는 그려지지 않는다. graph.json에 개념어 노드를 되살리려면 build.py 신규 구현 + `site/graph.html` 필터·색상표 수정이 함께 필요하다.

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

## 7. bibliography.json 형식 (선행연구)

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

## 8. 시각화 (site/graph.html)

Cytoscape.js 3.28 기반.

- 노드 크기: `degree` 비례 (56~120px). essay 노드 고정 110×56
- 엣지 굵기: `weight` 비례 (1.5~6px)
- 노드 클릭: 사이드패널 (데스크탑) / 하단 드로어 슬라이드업 (모바일 768px 이하)
- 비평가 노드 클릭 시 → "비평가 프로필 보기" 링크 포함
- 에세이 노드 클릭 시 → "구조화 데이터 페이지 보기" 링크 포함
- 노드 hover: 연결 강조, 나머지 페이드
- 필터: 비평가/작가/이론가/비평글 유형별 토글 (개념어는 관계망에 없음 — §5 참조)
- 검색: 왼쪽 상단 검색창 — 한글 포함 노드 이름 실시간 검색, 클릭 시 해당 노드로 줌·포커스
- URL hash: `site/graph.html#essay-stem` 형태로 진입 시 해당 노드 자동 포커스 (index.html "관계망에서 보기" 버튼 연동)

### 색상 시스템
| 유형 | 색상 | 모양 |
|---|---|---|
| 비평가 (critic) | #c9986a | 원 |
| 작가 (writer) | #6a9bc9 | 원 |
| 이론가 (theorist) | #9a7ac9 | 원 |
| 비평글 (essay) | #c8c8a8 | 둥근 직사각형 |

---

## 9. 선행연구 탭 (research.html)

- 데이터: `site/data/bibliography.json` fetch
- 작가 중심 검색: 좌측 목록에서 작가 클릭 → 우측에 논문 목록
- 연도별 막대 차트 (클릭 시 해당 연도 필터)
- 장르 필터 (시/소설/비평/희곡 등)
- ● 표시 = 관계망 노드와 연결된 작가
- KCI 논문 추가 시: `type: "kci"` 레코드를 bibliography.json에 추가하면 자동 포함

---

## 10. 반응형 (768px 기준)

- 768px 이하: 모바일 레이아웃 자동 전환
- graph.html: 사이드패널 숨김 → 하단 드로어
- index/essay: 여백·폰트 축소
- critics.html: 카드 그리드 1열
- research.html: 좌우 분할 → 상하 분할

---

## 11. 배포

Cloudflare Workers (무료 티어). `wrangler.jsonc`의 `assets.directory = "."`.

```
py build.py → py build_site_v2.py → git push → npx wrangler deploy   (.\deploy.ps1 "메시지" 가 모두 수행. wrangler deploy 는 worker/private 을 번들에 넣으므로 이 PC 에서만 배포)
```

**⚠️ git push만으로는 라이브 반영 안 됨.** GitHub Actions/자동배포 없음 → 반드시 `npx wrangler deploy` 실행해야 Cloudflare에 반영. `deploy.ps1`이 build+add -A+commit+push+deploy를 한 번에 처리.

**배포 검증:** `curl -s -o /dev/null -w "%{http_code}" https://kcritic.kr/site/essays/{stem}.html` 로 200/307 확인. 보안 재확인: `/.env`·`/essays/*.xml`·`/build.py`·`/CLAUDE.md`가 **404**여야 함(노출 금지). 공개되어야 하는 것: `/critic_v8_schema.rdf`·`/critic_v8_data.rdf`·`/site/data/graph.ttl` 이 **200**.

### `.assetsignore` 주의 (배포 자산 제외)

`assets.directory="."` 라 폴더 전체가 업로드 대상 → `.assetsignore`가 원문·크레덴셜·스크립트를 막는다. **gitignore 문법이라 슬래시 없는 패턴은 모든 깊이에 매칭**된다.
- ❌ `essays` → 로컬 원문 `essays/` 뿐 아니라 **배포해야 할 `site/essays/`까지 제외**(과거 essay 전부 404 버그의 원인)
- ✅ `/essays`, `/schema` 처럼 **루트 앵커링**. 원문은 `/essays` + `*.xml` + `*.txt`로 보호, `.env`는 명시.
- 새 작업 산출물(*.bak·*.csv·결과 json)도 `.assetsignore`에 추가해 공개 배포 방지.

현재 제외 목록: `.git`, `node_modules`, `/essays`, `.env`, `*.py`, `*.xml`, `*.txt`, `*.jsonl`, `/schema`, `CLAUDE.md`, `wrangler.jsonc`, `package.json`, `package-lock.json`, `.wrangler`, `*.bak`, `*.csv`, `verify_lod_result.json`, `essays_backup_qidfix`, `.gitignore`, `.assetsignore`, `.vscode`, `.dev.vars*`, `id_map.json`

> **`.rdf`는 제외 대상이 아니다** — `critic_v8_schema.rdf`·`critic_v8_data.rdf` 는 의도적으로 배포되어 `about.html` 에서 내려받게 되어 있다. `*.xml` 패턴에 걸리지 않으니 확장자를 `.xml`로 바꾸지 말 것.

### 개체 IRI 역참조 (`_redirects`)

graph.ttl 의 개체 IRI(`kc:` = `https://kcritic.kr/resource/{id}`, `kce:` = `…/resource/essay/{stem}`)와 인물의 `schema:url` 은 실제 파일이 없는 주소다. `build.py` 가 루트 `_redirects` 를 생성해 이 주소를 프로필·비평문 페이지로 **303** 리다이렉트한다. 인물은 한 줄씩, 비평글은 `/resource/essay/* /site/essays/:splat 303` 한 줄(2026-10-25, 현재 1,616줄). Cloudflare 정적 리다이렉트 한도는 2,000줄 — 넘으면 빌드 로그에 경고가 뜬다. 손으로 고치지 말 것. 검증: `curl -sI https://kcritic.kr/resource/p-00078` 이 303.

### not_found_handling

`wrangler.jsonc` `not_found_handling: "404-page"` (정적 다중페이지 사이트). 루트 `404.html`은 **자체 완결형**(인라인 CSS + 절대경로 `/style.css`·`/index.html`)이어야 깊은 경로(`/site/essays/...`)에서 404 나도 스타일이 안 깨진다. (`single-page-application`은 모든 404를 깨진 index로 보여줘 부적절.)

---

## 12. TEI XML 인코딩 패턴

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

- `interp[type='concept']` **텍스트**가 `concepts.json` 의 개념어 항목으로 자동 추출
- slug = 특수문자 제거 후 최대 40자
- 같은 개념 표기가 여러 에세이에 반복 출현하면 `essay_count` 증가 → 비평 언어의 공유·전파 추적 가능
- **관계망(graph.json)에는 개념어 노드가 없다** — concepts.html 색인 전용 (§5 참조)

**금지 패턴 — 개념어가 추출되지 않음:**
- `<interp type="concept" corresp="#c-slug"/>` — 텍스트 없이 corresp 속성만 사용하면 build.py가 빈 문자열을 읽어 무시함
- `classDecl > taxonomy > category` 구조 — build.py가 처리하지 않음. 현재 61편의 essay에 `<taxonomy>` 선언이 들어 있으나 빌드는 이를 읽지 않는다(Phase 2 개념어 계층화의 준비 데이터, §17 참조)

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

### 운문·날짜 인코딩 (스키마 v5)

태깅 기준 스키마는 **korean-critique-schema (v5 기준)** — `schema/korean-critique-schema.xsd` (부모 폴더 `korean-critique-schema-v5.xsd`가 버전 아카이브). v5는 이전 활성본의 **순수 상위호환(superset)** — 기존 essay 그대로 유효. 추가 기능:

**운문(시) 인용 — `<quote>` 안에 행·연 구조:**
```xml
<quote type="direct">
  <lg>                          <!-- 연(stanza) -->
    <l>괴로웠던 사나이</l>        <!-- 행(line), 인라인 요소·persName 포함 가능 -->
    <l>행복한 예수 그리스도에게</l>
  </lg>
</quote>
```
- `<l>` = 운문 한 행(LineType, mixed content — 텍스트+인라인 요소), `<lg>` = 연(LineGroupType, `l` 또는 중첩 `lg` 포함). 산문 인용은 기존대로 `<quote>` 직접 텍스트.

**불확실/범위 날짜 — `notBefore`/`notAfter`:**
```xml
<date notBefore="1950" notAfter="1959">1950년대</date>
```
- 초출 연도가 범위·추정일 때 `when` 대신 `notBefore`/`notAfter` 사용.

> 주의: build.py는 XSD 검증을 하지 않고 XML을 직접 파싱하므로, 스키마 변경은 **에디터(VS Code Red Hat XML) 검증·자동완성에만** 영향. 사이트/그래프엔 영향 없음.

---

## 13. AI 행동 규칙

- **원문 텍스트를 HTML에 포함하는 코드 작성 금지**
- **essays/*.xml, *.txt 를 git staging에 추가하는 명령 실행 금지**
- **`.env` 파일을 git staging에 추가하는 명령 실행 금지** (크레덴셜 포함)
- 인물 xml:id 는 한 번 정해지면 변경 금지 (예외 기록: 2026-10-12 한 id 가 두 사람을 가리키던 `p-kim-jongchul` 을 시인 쪽 비평문 2편(김현 1984 황지우론·1990 곽재구론)에서 기존 시인 id `p-kim-jongcheol` 로 교체. 백업 `essays_backup_review_20261012/`)
- Wikidata ref 추측 채우기 금지 — 모르면 빈값
- build.py 수정 후 반드시 `py build.py` 테스트
- convert_phd.py 수정 후 반드시 `py convert_phd.py` 테스트
- PowerShell에서 한글 포함 git commit 메시지는 here-string 파싱 오류 발생 → ASCII 메시지 사용 (Bash 툴도 안전하게 ASCII 권장)
- (구자료) Neo4j 를 다룰 때 URI는 반드시 `bolt://127.0.0.1:7687` 사용 — `neo4j://` 프로토콜은 라우팅 오류 발생
- **빌드 결정성 유지**: set을 출력/직렬화할 땐 항상 `sorted()`, count 기준 정렬엔 `key=lambda x: (-x[1], x[0])` 같은 안정적 tiebreaker 사용. (검증: `py build.py` 2회 연속 실행 후 `git diff`가 비어야 함.) 위반 시 빌드마다 칩·노드 순서가 바뀌어 무의미한 diff가 쏟아짐
- **graph.ttl 의 인물 id 는 반드시 정본 id 로**: `build_graph_data()` 가 같은 라벨의 인물 노드를 병합하며 `_CANON_ID`(병합 id → 정본 id)를 채우고, `build_turtle()` 은 이 표로 비평문의 `dcterms:creator`·`cito:discusses`·`cito:citesAsAuthority` 를 정본에 맞춘다. 이를 빼면 병합돼 사라진 id 를 가리키는 **끊긴 IRI**(이름·클래스·전거 없음)가 생겨 이름으로 조인하는 SPARQL 결과가 줄어든다(2026-09-15 수정 전 252개·622트리플). 빌드 로그에 `[경고] graph.ttl 끊긴 인물 IRI` 가 나오면 원인을 찾을 것
- **인물 id 정본화 (2026-09-30 해결)**: 비평문 XML 의 모든 인물 id 는 persons.json 레코드의 `ids` 목록으로 정본 키에 묶인다. `process()` 가 `_canon_pid()` 로 persons/subjects/theorists/author/문맥을 정본으로 바꾸므로 목록·프로필·관계망·graph.ttl 이 같은 id 를 쓴다. 병합된 옛 id 의 프로필 주소는 정본 페이지로 넘기는 리다이렉트 HTML 로 남는다(`_redirect_html`). 라벨 병합(`build_graph_data`)은 미등록 id 에만 쓰는 안전망이며, 같은 이름의 등록 정본이 둘 이상이면 동명이인으로 보고 합치지 않는다(예: 김종철 시인/사상가, 유진오)
- **LOD 외부링크 추가는 build.py `LOD_SOURCES` 한 곳만**: 새 식별자(예: 새 사전) 추가 = 레지스트리 1줄 + persons.json 필드. 프로필·칩·카드3종·관계망 패널 6곳이 자동 반영. 개별 HTML/JS를 손대지 말 것 (§14 참조)
- 커밋 전 `git status`로 변경 파일 확인 — site/* 빌드 산출물은 커밋 OK, `essays/*.xml`·`.env`·`*.bak`·`essays_backup*/`·`qid_fix_*.csv`는 절대 staging 금지(.gitignore 등록됨)

---

## 14. 외부 연결 데이터 (LOD)

- 한국 인물: 국립중앙도서관 LOD (https://lod.nl.go.kr) → Wikidata → ISNI
- 외국 이론가: Wikidata (https://wikidata.org) 우선
- `ref` 속성에 전체 URI. 여러 URI는 공백 구분

### persons.json — 인물 권위 소스

`persons.json` 파일이 LOD 링크의 권위 소스이자 **비평문에 나오는 모든 인물의 정본 목록**(2026-09-30부터).
- 키 = 정본 id. 숫자 id(`p-00247`)가 있으면 그것(관계망 정본과 같음), 없으면 기존 슬러그.
- `ids` = 같은 인물을 가리키는 다른 XML id·옛 슬러그 목록 (예: `p-chae-mansik`·`p-chaemansik`·`p-chae-manshik`). 새 비평문에서 기존 인물을 다른 id 로 인코딩했다면 여기에 추가하면 된다.
- `wikidata: null` 은 "확인된 연결 없음" 판정이다. build.py 는 등록 인물에 대해 XML ref 의 Q번호로 보완하지 않는다(XML ref 에 엉뚱한 Q번호가 많았음 — 김승옥→노르웨이 지자체, 벤야민→독일 코미디언 등).
- `not_person: true` = 사람이 아닌 항목(학파·작중인물 등). 2026-10-12부터 `process()` 가 이 항목을 인물 집합에서 빼므로 목록·관계망·graph.ttl 어디에도 인물로 나오지 않는다.
- graph.ttl 의 `foaf:name`·`rdfs:label` 은 비평문 표기가 아니라 persons.json 정본 표시명이다(질의가 표기 변형으로 갈리지 않게).
- **논문 수치 재현**: `py paper_stats.py --json` → `site/data/paper_stats.json`. 논문 표·질의 결과는 이 스크립트 출력과 같은 시점이어야 한다.
- 2026-09-30 전수 판정: 근대잡지 열람사이트 인물 전거(`../../../../스캔/인물카드/people_ids/`)·Wikidata 검색·국중 LOD 스냅샷(QID→KAC)을 대조해 판정. 판정 원칙은 "확실할 때만 연결". 변경 내역은 부모 폴더 `인물_갱신결과_20260930.csv`.
- 국중(nlk)은 국중 LOD 스냅샷의 owl:sameAs(QID→KAC 유일) > Wikidata P5034 > 근대잡지 판정 순으로 채웠다. encykorea 는 Wikidata P9475 가 권위.

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

**`naver_munhak` 필드:** 네이버 지식백과 「한국현대문학대사전」 항목의 전체 URL (terms.naver.com/entry.naver?docId=...&cid=41708&...). 2000년대 이후 활동 비평가(김우창·유종호·백낙청·김병익 등)에 추가. 황현산은 사전범위(1895~1994)상 항목 없음.

**`en` 필드 (외국 인물 영문 병기):** Wikidata 영문 레이블. `enrich_en_names.py`가 P27(국적)로 외국/한국 분류 — 외국 인물에만 `en` 기록(한국 인물 미표시). 카드·프로필 heading·관계망 패널에서 한글 옆 작은 괄호로 표시(`_name_en_html`, `_en_of`, CSS `.name-en`/`.card-name-en`/`.panel-name-en`). 에세이 칩은 한자 병기 충돌로 제외. 재실행: `py enrich_en_names.py --apply`.

**LOD 배지 단일 레지스트리 (build.py `LOD_SOURCES`):** 모든 외부 식별자 배지는 build.py 상단 `LOD_SOURCES` 리스트 한 곳에서 정의(field·url·full/chip/card 라벨·색·title). 표시 위치별 렌더가 모두 이 정의를 따름:
- 프로필 페이지: `_lod_links_html` 이 `LOD_SOURCES` 순회 → "{full} ↗" 배지
- 에세이 칩: `person_chip` 이 순회 → chip 라벨(None이면 미표시)
- 카드(critics/writers/thinkers): build.py가 `_lod_card_badges`로 **`lod` 배열**(href·label·bg·fg)을 각 JSON에 넣고, HTML의 JS는 `c.lod`를 그대로 렌더(ref 문자열 파싱 제거)
- **새 LOD 소스 추가 = `LOD_SOURCES`에 1줄 + persons.json 필드.** 5곳(프로필·칩·카드3개)이 자동 반영. 개별 카드 JS 수정 불필요.

**숫자 xml:id → persons.json 연결 (id_map):** build.py는 id_map(슬러그→숫자)을 역인덱스(`_NUM_TO_SLUG`)로 로드한다. 경로는 **저장소 안 `id_map.json` 우선, 없으면 부모 폴더 `../id_map.json`(레거시)** — 현재는 저장소 사본이 쓰인다. 부모 폴더 사본만 고치면 반영되지 않으니 주의. 에세이가 숫자 xml:id(p-00117 등)로 인물을 참조해도 `_persons_record`/`_registry_ref`가 슬러그로 해석해 persons.json 권위 레코드(올바른 wikidata·encykorea·naver_munhak 등)를 사용. author_ref·TTL 노드 ref도 이 경로로 persons.json 우선. → XML ref가 낡아도 persons.json만 고치면 사이트 전체에 반영됨.

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

### LOD QID 일괄 검증·교정 워크플로우 (스크립트)

persons.json의 잘못된 Wikidata QID를 찾아 고치는 4단계 도구 (critic-ontology/). **검색(wbsearchentities)이 아니라 저장된 QID 직접 역조회(wbgetentities)로 검증** — 동명이인·미발견 오류를 피하는 핵심 원칙.

1. `py verify_lod.py` — 저장 QID 역조회 → 이름·직업(P106)·인간(Q5)·NLK교차 검증. 결과 verify_lod_result.{csv,json}
2. `py suggest_qid_fixes.py` — 깨진 QID에 올바른 후보 제안. 엄격필터: Q5 + 문학/학술직업 + 이름유사도 + **role대조(동명이인 차단)** + 언어판수(유명도). 결과 qid_fix_proposals.csv
3. `py enhanced_qid_search.py` — 1차에서 못 찾은 외국 인물을 영문명으로 재검색 (HINTS 딕셔너리에 영문명 제공, QID는 라이브 검증)
4. `py apply_qid_fixes.py <csv> [등급]` — 지정 CSV의 해당 등급만 persons.json 반영(persons.json.bak 백업)
5. `py sync_xml_refs.py <csv>` — essays XML의 persName ref QID를 교정값에 동기화(essays_backup_qidfix/ 백업). xml:id→슬러그(id_map) 해석으로 한 인물의 여러 잘못 QID 통합

**검증 도구 사각지대:** 한글 레이블 없는 외국인(NO_KO_LABEL)은 이름 대조를 못 해 직업만 맞으면 통과 → 엉뚱한 인물(흄→화학자 등)을 놓침. NO_KO_LABEL은 자동 정상 아니라 **en_label 수동 확인 필요**.

### encykorea(한국민족문화대백과) 검증 — Wikidata P9475 (중요)

**encykorea E번호는 절대 이름 검색·추측으로 채우지 말 것.** 동명이인 오류가 빈발(김우창→의병, 이상→이상희, 영랑→동명이인). **검증된 QID의 Wikidata P9475("Encyclopedia of Korean Culture ID")가 권위 소스** — 그 인물의 정확한 E번호를 줌(동명이인 불가).
- `py verify_encykorea.py [--apply]` — 저장 encykorea ↔ Wikidata P9475 교차검증·교정.
- **한계:** Wikidata에 P9475가 없는 인물(생존 비평가·일부 작가 등)은 교차검증 불가 → encykorea 페이지(`encykorea.aks.ac.kr/Article/{E}`, fetch 가능)에서 생년·직업을 직접 대조해야 함. encykorea 신규 추가 시에도 이 절차로 검증.

### multi-URI href 주의

persons.json의 `ref`/`_registry_ref()`는 여러 URI를 **공백으로 이어 붙인 문자열**이다. `href="{ref}"` 처럼 통째로 넣으면 링크가 깨진다. 반드시 wikidata 등 **단일 URI만 추출**해서 href에 사용 (`next((u for u in ref.split() if "wikidata" in u), "")`). 카드/패널은 `lod` 배열의 개별 `href`를 쓰므로 안전.

### 중복 슬러그 처리

같은 인물이 persons.json에 두 슬러그로 존재할 수 있다(예: 음역 차이). 병합 절차: ① essay에서 실제 쓰이는 숫자 xml:id 확인(`id_map.json`) ② 한쪽이 다른 숫자면 그래프 노드가 분리되므로 essay에서 숫자 id를 통일(리네임) ③ 중복 슬러그를 persons.json·id_map에서 삭제 ④ 데이터(필드) 손실 없는지 확인 후 재빌드. (essays·id_map은 git 미추적/parent라 로컬 변경)

### 환경 제약 (외부 접근)

- **terms.naver.com** (네이버 지식백과): WebFetch 차단 + 미국기반 WebSearch 미인덱싱 → 개별 항목 URL(docId)은 **사용자가 직접 복사 제공**해야 함
- **lod.nl.go.kr** (NLK LOD): 직접 연결 차단 → NLK URI 라이브 검증 불가. 로컬 RDF 스냅샷(`온톨로지/Person_rdf_20260401/`)으로만 조회
- **wikidata.org API**: 정상. 단 429(rate limit) 주의 — 호출 사이 sleep + 재시도 백오프

---

## 15. 스택 요약

| 목적 | 도구 |
|---|---|
| 인코딩 | VS Code + Red Hat XML + `korean-critique-schema.xsd` (v5 — 운문 `l`/`lg`·날짜범위 `notBefore`/`notAfter` 지원, §12 참조) |
| 빌드 | `build.py` (Python 표준 라이브러리만. neo4j driver 는 `--neo4j` 때만) |
| 데이터 변환 | `convert_phd.py` (openpyxl), `convert_criticism.py` (openpyxl) |
| 관계망 시각화 | Cytoscape.js 3.28 |
| 그래프 DB | (구자료, 사이트 미사용) Neo4j Desktop·Aura — §4 「Neo4j — 구자료」 |
| API 서버 | FastAPI (`neo4j_api.py`, Render) — 사이트는 기여하기·관리 경로만 사용. GraphRAG `/ask` 는 미사용 |
| AI 답변 | (구자료) Anthropic Claude API (`neo4j_api.py` `/ask`) — Cypher 생성 + 학술 답변, 현재 호출하는 페이지 없음 |
| 공식 온톨로지 | OWL v8 — `critic_v8_schema.rdf`(스키마) + `critic_v8_data.rdf`(데이터) (§16 참조) |
| SPARQL | Comunica + N3 로컬 번들 (site/sparql-bundle.js, ask.html SPARQL 탭에 통합) — 질문하기 탭의 실제 질의 수단 |
| 호스팅 | Cloudflare Workers (무료) |
| 비용 | 도메인 갱신비 + Anthropic API 사용료 |
| LOD | Wikidata + 국립중앙도서관 LOD |

---

## 16. 공식 OWL 온톨로지 (v8 — 현행)

**현행 버전: v8 (`8.0-kcritic`).** 스키마와 데이터가 분리되어 있고, 저장소 사본이 사이트 배포·다운로드 대상이다.

| 파일 | 저장소 사본 (배포됨) | 원본 |
|---|---|---|
| 스키마 | `critic-ontology/critic_v8_schema.rdf` | `온톨로지/critic_v8_schema.rdf` |
| 데이터 | `critic-ontology/critic_v8_data.rdf` | `온톨로지/critic_v8_data.rdf` |

`about.html` 의 "OWL 온톨로지 (v8)" 항목에서 두 파일을 내려받는다. **원본을 고치면 저장소 사본에도 복사할 것** — 사이트가 배포하는 건 저장소 사본이다.

### 버전 이력 (원본은 모두 `온톨로지/` 폴더)
- `critic_v5_kcritic.rdf`
- `critic_v6_kcritic.rdf` — v5 대비 `critic:Thinker` 클래스, `cito:citesAsAuthority` 프로퍼티 추가
- `critic_v7_kcritic.rdf` — v6 대비 `critic:Writer` 클래스, 한국 작가 40명 NamedIndividual + owl:sameAs 추가
- `critic_v7_kcritic_archive_20260608_withRole.rdf` — 폐기된 `critic:Role` 개체 11개가 남아 있는 구버전 아카이브. 사용 금지
- **`critic_v8_schema.rdf` + `critic_v8_data.rdf` (현행)** — v7에서 미사용 `critic:Role` 클래스·`critic:hasRole` 프로퍼티를 제거하고 스키마/데이터로 분리. **NamedIndividual 152개는 v7과 동일**(비평가 2 · 이론가 69 · 작가 40 · 비평문 41)

> v8 데이터는 김우창·유종호 시절의 **파일럿 스냅샷**이며 사이트 전체(370편)와 다르다. 사이트의 전체 RDF는 매 빌드마다 생성되는 `site/data/graph.ttl`(20,689 트리플)이다. 둘의 역할을 혼동하지 말 것.

`build.py`의 `build_turtle()`은 v8 스키마를 준거로 삼아 `graph.ttl`을 생성한다.

### 온톨로지 URI
- Base: `http://kcritic.kr/ontology/`
- 접두사: `critic: <http://kcritic.kr/ontology/critic#>`

### 클래스 매핑 (2026-09-07 v8 정합화)
| build.py 내부 타입 | graph.ttl 클래스 | 비고 |
|---|---|---|
| `critic` | `critic:Critic, foaf:Person` | |
| `writer` | `critic:Writer, foaf:Person` | **기존 foaf:Person 단독에서 변경** |
| `theorist` | `critic:Thinker, foaf:Person` | **기존 foaf:Person 단독에서 변경** |
| `essay` | `critic:CriticalEssay` | |

v8은 `critic:Writer`/`critic:Thinker`/`critic:Critic` 을 `critic:Person`(≡ `foaf:Person`)의 하위 클래스로 정의한다. `foaf:Person` 을 함께 부여하는 이유는 **기존 SPARQL 예제(`sparql.html` 의 `VALUES ?class { critic:Critic foaf:Person }`)를 깨뜨리지 않기 위해서**다. 이 두 줄은 함께 유지할 것.

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
같은 개념을 에세이마다 다르게 표기하지 않는다. **표기가 다르면 concepts.json에서 별개 항목으로 분리되어 essay_count가 늘지 않고, `dcterms:subject` 리터럴도 갈라져 SPARQL 집계가 어긋난다.**

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

> **폐지된 규칙 주의** — 예전 지침에 있던 `_ONTOLOGY_WIKIDATA` 딕셔너리는 build.py에서 제거되었다(현재 코드에 존재하지 않음). "새 인물을 이 딕셔너리에 등록하라"는 지시를 따르지 말 것.

현재 인물의 외부 연결은 **`persons.json` 단일 권위 소스**로 처리된다:
- `graph.ttl` 의 `owl:sameAs` 는 `_registry_ref()`(persons.json 우선, 없으면 TEI ref) → Wikidata URI 순으로 생성
- TEI ref에 Wikidata URI가 없는 인물은 build.py의 `_WIKIDATA_FALLBACK`(이름 → URI)이 보완
- 즉 **새 인물 추가 시 손댈 곳은 persons.json 하나** (§14 절차 참조). 코드 내 딕셔너리 등록은 불필요
- 김우창 Wikidata: `Q17129594` (검증 완료)

---

## 17. 프로젝트 단계 로드맵

### 완료 (Phase 0 — 파일럿)
- 김우창·유종호 비평 48편 TEI 인코딩
- RDF Turtle 생성, Cytoscape.js 관계망, SPARQL 인터페이스
- 공식 OWL 온톨로지 v5 → v8

### 완료 (Phase 1 — 비교 관계망)
학술적 의미 확보에 필요한 "비평가 복수" 조건 달성. **김윤식 대신 김현·황현산으로 확장**했다.
- 비평가 4인 370편 — 김현 136 · 유종호 114 · 김우창 109 · 황현산 11
- 관계망 노드 1,451 / 엣지 4,111, graph.ttl 20,689 트리플 (2026-10-12 기준)
- 미완: **`critic:respondsTo`(에세이 → 에세이 응답 관계) 미구현** — 스키마·build.py 어디에도 없음. 기교주의 논쟁 같은 논쟁 구조를 표현하려면 이게 필요

### 진행 중 (잡지 확장 — 『문학과사회』)
- 2026-10-22: 1–13호(1988–1991) 비평 118편 공개. 원본 초안·OCR·기사 분할·인코딩 대장은 `../문학과사회/` (README 참조)
- 2026-10-25: 14–28호(1991–1994) 101편 추가 공개 → 비평글 589 · 비평가 109 · 노드 2,203 · 엣지 6,377. 반영은 `publish_mhs.py --batch 20261025`(README §6-1). 좌담·심사평은 별도 컬렉션(`../문학과사회/site_prep/jwadam_simsa_collection.tsv`), 편집 동인·발행처 명의 글과 번역 글은 제외. 인물 전거 보강 지침 `../문학과사회/site_prep/NLK_ENRICH_GUIDE.md`
- 반영 절차: `../문학과사회/site_prep/census.py`(점검) → `publish_mhs.py --apply`(개념어 통일·persons.json 등록·XML 복사) → `py build.py` → `make_cards.py`(index.html 카드 섹션 `MHS-START`~`MHS-END` 자동 생성)
- 심사평(복수 심사위원)은 build.py 가 titleStmt 첫 저자만 비평가로 잡아 오귀속되므로 **사이트에서 제외**(작업 폴더에만 있음). 복수 저자 지원은 미구현
- 역할이 `critic` 뿐인 언급 인물(다른 비평가를 논하는 경우)은 build.py 분류상 관계망 엣지가 생기지 않는다. 비평가 간 논쟁 관계는 `critic:respondsTo` 구현과 함께 다룰 것
- 이 확장으로 사이트 수치는 논문(4인 370편) 시점과 달라졌다. 논문 수치 재현은 그 시점 스냅샷 기준
- 수록지면(2026-10-22): 『문학과사회』 XML 의 sourceDesc 는 가이드 §2-1 의 `<biblStruct type="journal">` 구조다 — analytic=비평글, monogr=`문학과사회`·문학과지성사·발행 계절 + `biblScope unit="issue"`·`unit="page"`, 비고 note 는 biblStruct 안. 변환은 `../문학과사회/site_prep/convert_sourcedesc.py`(이미 바뀐 파일은 건너뜀). 스키마는 monogr/author 선택화·`biblScope`·biblStruct/`note` 를 추가한 상위호환
- build.py 수정(2026-10-22): biblStruct 의 호수·쪽·비고를 읽어 비평글 페이지에 표시하고, 프로필 카드 출처 줄(`_source_short`)은 비평글 제목이 아니라 수록지면(수록 단행본 → 비고의 《잡지》)을 쓴다. critics.json 은 글 수 내림차순(동수는 이름순)

### 진행 중 (Phase 2 — 개념어 계층)
- 현황: 370편 중 **61편에 `<taxonomy>` 선언이 이미 들어가 있으나 build.py가 읽지 않는다** (§12 금지 패턴 항목 참조)
- 개념어 `encodingDesc` 계층 선언: `<taxonomy>` 요소로 상위-하위 개념 관계 명시
- 예: `명징성` > `언어적 명징화` > `명징한 간결성`
- SKOS 어휘 활용 (`skos:broader`, `skos:narrower`) → concepts.json·graph.ttl에 계층 반영. 현재 build.py·v8 스키마 모두 SKOS 미사용

### 예정 (Phase 3)
- SPARQL 공개 엔드포인트 제공 (현재는 브라우저 내 Comunica로 `graph.ttl` 질의)

> 로드맵을 고칠 땐 `about.html` 의 "로드맵"·통계 섹션도 **함께** 갱신할 것 — 하드코딩되어 있어 자동 반영되지 않는다.


## 수록지면 메타데이터 필수 (2026-10-22)
- 매 글에 수록지명·통권 호수·발행 연도/계절·난 이름·실제 인쇄쪽 범위를 기록한다. PDF 파일의 면 번호와 인쇄쪽을 혼동하지 않는다. 발행 월/일은 확인된 경우에만 적는다.
- TXT 2행, XML sourceDesc, encode_ledger.json의 publication_metadata를 대조한다. 기존 대장의 추정 범위보다 실제 기사 끝·각주까지 대조한 범위를 우선한다. 불연속 수록면은 구간을 각각 보존한다.
- 기존 초출 비고를 보존하고 같은 bibl 안에 별도 note를 반드시 추가한다: `<note>수록: 『문학과사회』 14호, 1991년 여름, 오늘의 한국 문학 1, 522–539면.</note>`.
- 글 제목과 수록지명은 별개이다. 서평 대상 책을 수록지로 기록하지 않는다. build.py의 extract_sources/collected_in으로 수록지명이 문학과사회로 추출되는지 확인한다.
- 근거가 충돌하거나 확인되지 않은 항목은 추측하지 않고 대장에 보류 이유와 근거를 남긴다. 서지 보완 완료는 원문 정밀교감·연구자 검토 완료를 뜻하지 않는다.
- 완료 보고에는 수록지명·호수·발행시기·난·인쇄쪽과 메타데이터 대조 결과를 포함한다.


## 학맥 탭 (2026-10-26)
- `lineage.html` / `lineage.js` / `lineage.css`: 공통 박사 지도교수 → 교수가 된 연구자 → 이후 지도 학위자의 3단계 곡선 네트워크.
- 학술연구 `thesis-browse.js` 탭에서 연결. 왼쪽은 수록 자료 내 교수가 된 지도학생 수 내림차순, 동률은 이름순. 인물 자유 검색 대신 지도교수 선택.
- `site/data/lineage-public.json`은 서지 및 연결 상태만 포함. 원본 PDF, OCR, 로컬 경로, 검수 메모, 사용자 대화는 포함하지 않음.
- 학위논문 ID로 동명이인을 분리. 상위 지도교수는 이름 표기 정규화와 학위수여대학을 함께 사용. 서강대 김현주는 요청에 따라 제외.
- 확인 관계 164건 기본 표시, 동일인 지정 후 시점 확인이 필요한 6건은 선택 시 점선. 실선과 점선은 구별 유지.
- 공개 논문 데이터는 수집 범위의 부분 관계망이며 전체 학계 또는 실제 교수 배출 총수로 해석하지 않음.

- 2026-10-26 PDF 추가 점검: 표언복의 표지 지도교수 표기를 직접 확인하여 조남현 → 표언복 반영. 나머지 미확인은 원문 미확보 또는 직접 표기 미확인 상태 유지. 검수 근거는 별도 비공개 작업 기록에 보존.

- 학맥 탭은 개념어 바로 뒤에 표시. 연구자 아래의 지도 대학은 연결된 지도논문의 학위수여기관을 정규화한 값이며, 현재 재직 대학 또는 본인 박사학위 대학과 구분한다.


## 학교·소속·사제관계 탐색 (2026-10-27)
- `academic-network.html/js/css`를 기존 `lineage.html` 안내 및 인물 상세에서 연결한다.
- `site/data/academic-network-public.json`: 논문 레코드 2189건, 별도 학맥 보완 서지 2건, 웹 소속 확인 교수 52명, 기존 검증 박사 지도 164건, 제공 정보에 따른 일반 사제관계 5건.
- 학위 수여 대학과 재직 소속, 일반 사제관계와 박사 지도를 구분한다. 명예교수 이력을 현직이나 생존 여부로 해석하지 않는다.
- 이름만 일치하는 학위 저자를 교수와 합치지 않는다. 일반 사제관계로 논문의 지도교수 빈칸을 채우지 않는다.
- 공개 데이터는 `export_academic_network.py INPUT_JSON`의 명시적 필드 허용 목록으로 재생성한다. 비공개 입력·검수 메모·원문·OCR·로컬 경로·대화 원문은 복사하지 않는다.
- 검증: `node --test tests/academic-network.test.cjs`. 일반 재빌드나 배포 스크립트는 이 공개 JSON을 생성하지 않는다.

### 운영 상단 복구 및 배포 기준 (2026-10-27)
- 상단 메뉴는 통합검색·현장비평·학술연구 3개다. kc.js와 kc-shell.js를 함께 유지한다.
- 이전 별도 배포본의 상단·통합검색·연구 상세·공개 서지 데이터를 저장소에 포함한다. academic-network와 기존 학맥 연결을 유지한다.
- Git 미커밋 파일이라도 이미 운영 중일 수 있다. 배포 전 운영 자산과 직전 배포본을 대조하고, 커밋 추출만으로 기존 운영 기능이 보존된다고 판단하지 않는다.

- 지도교수 정정(2026-10-27): 천정환 본인 학위논문 `eeea758c003fa8ac`의 지도교수는 미확인. 김윤식으로 확정하지 않는다. 공개 내보내기는 advisor_raw를 비우고 advisor_status=unconfirmed로 표시한다. 천정환이 지도한 제자 관계에는 적용하지 않는다.

- 김인환→오형엽: 사용자 확인에 따라 고려대학교 사제관계로 표시한다. 관계의 institution_id를 사용하며 박사 지도관계로 자동 승격하지 않는다.


## 학맥 세대별 계보 트리 (2026-10-27, 원형 보기 대체)

- `lineage.html`(껍데기) / `lineage.js`(배치·탐색) / `lineage.css`(스타일)로 분리. 데이터는 `/site/data/genealogy-library.json`을 fetch 하며 HTML에 더 이상 내장하지 않는다. 데이터 빌드(Codex `build_genealogy.py`)는 JSON만 갱신하면 되고, HTML 템플릿 치환은 쓰지 않는다.
- 배치(시간축, 2026-10-27 저녁 개편): **가로축 = 박사학위 연도**(1년 32px, 5년마다 눈금·세로 보조선). 시작 교수는 상위 지도 간선에 연도가 있으면 그 해, 없으면 첫 제자보다 4년 앞. 연도 없는 간선은 부모 +3년에 두고 "연도 미상" 표기. 같은 지도교수의 제자는 연도순으로 세로로 쌓는 정돈 트리(말단 24px, 교수 56px, 시작 교수 76px 행, 교수 묶음 사이 12px). 제자를 둔 사람마다 첫 제자~마지막 제자 사이에 대학 색의 옅은 "지도 기간" 띠. 상위 지도교수는 왼쪽 "지도교수" 구역(연도 미상)에 점선으로.
- 이름 자리: 시작 교수·상위 지도교수는 점 왼쪽, 제자를 둔 교수는 점 위(이름 → 소속·지도 편수 순), 말단은 점 오른쪽. 들어오는 선·나가는 선과 겹치지 않게 하려는 규칙이니 바꾸지 말 것.
- 색 = **학위 수여 대학**(간선의 university 를 `affiliationName` 으로 정규화, 한자 교명은 `HANJA` 표로 한글화). 전체 지도논문 수 상위 8개 대학에 dataviz 검증 범주형 8색(`PALETTE`)을 고정 배정, 나머지는 회색 '기타'. 역할은 모양으로: 시작 교수 = 큰 점 + 강조색 테두리, 교수가 된 제자 = 중간 점 + 먹색 테두리, 동일인 추론 = 점선 테두리, 학위자 = 작은 점. 범례의 대학 칩을 누르면 그 대학 학위자만 강조. 이름 옆 작은 숫자는 학위 연도.
- 지표(`metrics()`, Rossi 외 2018 계보 지표를 자료에 맞게 축약): 직접 제자(저자 수, 공동지도 1명), 지도논문, 교수가 된 제자(수·비율), 후손, 세대, 지도 기간(첫~마지막 제자 연도), 다음 세대까지(교수가 된 제자가 첫 제자를 내기까지 평균 연수), 모교 잔류(교수 제자 중 학위 대학 재직), 학위 대학 수. 시작 교수의 지표 타일 7개가 화면 위, 교수 상세에 한 줄, 아래 "학맥 비교" 표(교수 170명, 열 정렬, 행 클릭 = 시작점 이동, 중앙값 행, CSV 내려받기). "추론 포함" 토글은 지표에도 반영되고 "교수가 된 제자만"은 배치에만 반영된다.
- 모든 수치는 수집 자료 안의 연결만 센 값이라는 안내를 타일·표·바닥글에 유지한다.
- **공개 데이터 생성 (2026-10-27 밤)**: `py export_genealogy_public.py <Codex outputs/학맥_계보탐색/학맥_그래프.json> --roster <교수 명단 checkpoint-*-advisors*.json>` → `site/data/genealogy-library.json`. 근거 충돌 간선과 검수용 필드(alias_evidence·advisor_conflict·formal_dissertation_advisor_confirmed·previous_advisor_evidence)를 빼고, 간선에 연결되지 않은 교수 노드를 빼고, summary 를 다시 센다. `--roster` 는 명단 행의 본인 박사논문 지도교수 표기 가운데 `advisor_status` 가 `확인:` 으로 시작하는 행만 지도교수→교수 간선으로 더한다(후보·보류·제외 행은 넣지 않음, 동명 후보가 여럿이면 건너뜀, 새 지도교수는 `professor:roster-advisor:대학:이름` 노드). `--check 기존파일` 로 규칙이 같은지 대조할 수 있다. 로컬 경로가 섞이면 assert 로 멈춘다.
- 파이프라인(Codex `C:\Users\hgohg\Documents\Codex\2026-10-27\c-users-hgohg-documents-codex-2026\work\`): `build_linked_roster.py`(명단 경로가 `checkpoint-614.json` 으로 박혀 있음 → 2026-10-27 밤에는 `checkpoint-705-advisors-r2.json` 으로 바꿔 실행) → `advisor_first.py`(`len(profiles)==614` 단언을 명단 행 수로) → `build_genealogy.py`(사용자 확인·도서관 검수 패치 12개 적용). 인물 id `person:roster614:NNNN` 은 명단 행 번호라 **명단은 뒤에만 덧붙이고 앞 행 순서를 바꾸지 말 것**(614→705 은 앞 614행이 그대로였음). 스크립트의 `C:/onedrive/.../critic-ontology` 경로는 OneDrive 쪽 체크아웃이며, 두 체크아웃(OneDrive·`C:\Users\hgohg\kcritic.kr`)의 사이트 파일이 같은지 확인한 뒤 배포한다. 배포용 `worker/private/` 은 OneDrive 체크아웃에만 있다.
- **저자-교수 동일인 판정 (2026-10-27 밤)**: Codex `work/build_author_review.py` 가 명단 705행 중 박사논문 목록에 같은 이름이 있으나 미연결인 교수를 근거 등급(A 제목/대학+연도 일치, B 박사대학 일치·유일, C 이름만·유일, D 후보 여럿, E 박사대학 불일치)으로 나눠 `outputs/저자_교수_연결검토/*.xlsx` 로 내보낸다(데이터 변경 없음). 연구자가 판정한 결과는 `work/author-review-confirmed-*.json`(decision '확인')에 두고, `work/author_review_patch.py` 가 `build_genealogy.py` 패치 체인 마지막에서 학위자 노드(또는 기존 professor:legacy 노드)를 명단 교수 노드에 합친다(근거 '사용자 확인', 같은 사람의 명단 두 행은 한 노드로). 2026-10-27 1차: 세대 고리가 이어지는 37명을 채팅으로 전원 확인 → 교수 간선 95→115건, 본인 논문이 연결된 교수 128→147명. **이름만 같은 저자를 자동으로 합치지 않는다**는 원칙은 그대로다.
- 보기 전환(2026-10-27 밤): 툴바의 「원형 / 간단 / 시간축」 세그먼트(`?view=radial|simple|time`, 마지막 선택은 localStorage `kc-lineage-view`). **기본은 원형 보기**: 시작 교수를 가운데, 세대를 고리로. 세로 트리에서 계산한 겹치지 않는 행 간격(학위자 27px·교수 56px)을 그대로 각도로 옮기고(첫 제자가 12시, 시계 방향, 12시에는 90px 상당의 빈 쐐기 → 고리 이름 자리), 고리 간격은 1세대 고리에서 학위자 행의 호 길이가 24px 이상 되도록 `max(170, H·24/(2π·27))` 로 정한다 — 이름이 서로 겹치지 않는 근거. 글자는 반지름 방향 바깥쪽에 눕히고 왼쪽 반은 180° 뒤집는다(안쪽은 부모의 선 다발이 모여 쓰지 않음). 시작 교수 이름은 수평. 상위 지도교수는 원형에서는 그리지 않고 버튼(mentorNav)으로만. 색은 역할 색(간단 보기와 같음). 기본 보기는 100% 배율로 시작 교수를 화면 가운데에. 큰 학맥(정한모 4세대)은 지름 3,400px 이므로 전체 보기는 축소본이고 기본 보기에서 끌어 본다. 간단 보기는 세대마다 250px 열, 역할 색(시작 교수 `--accent`, 교수 `--ln-prof`, 추론 흰 바탕 점선, 학위자 회청색 — `svg.simple` CSS 가 대학 색 인라인 fill 을 덮음), 지도 기간 띠·대학 범례 없음, 제자를 둔 교수 이름도 오른쪽. 열 머리글(시작 교수·제자 n세대)은 시간축의 연도 눈금과 같은 고정 눈금자에 표시. 지표 타일·비교표는 두 보기에서 같다.
- 모든 세대를 펼치며 말단 이름을 그룹으로 접지 않는다(기존 원칙 유지).
- 기본 보기: 배율 0.8~1로 시작 교수를 세로 중앙에. 전체 보기: 트리 전체를 맞춤. 휠 확대·드래그 이동. 클릭은 그 인물의 계보(조상+후손) 강조와 상세, 더블클릭·Shift+Enter는 시작점 이동.
- `tests/academic-network.test.cjs`가 `lineage.html`의 `/academic-network.html` 링크와 `lineage.js`의 `encodeURIComponent(t.name)`을 검사하므로 유지한다. `site/data/lineage-public.json`은 더 이상 화면에서 쓰지 않는다(데이터 파일은 그대로 둠).

### 이전 원형 보기 기록 (2026-10-27, 대체됨)

- lineage.html은 선택 교수를 중심으로 세대별 동심원에 제자를 배치한다. 모든 세대를 펼치며 말단 이름을 그룹으로 접지 않는다.
- 교수 색상·소속, 교수만 보기, 동일인 추론 필터, 클릭 관계 강조, 더블클릭 중심 이동, 지도교수 이동 버튼을 유지한다.
- 학맥 데이터와 표시 배치를 분리한다. 이번 변경은 데이터 수정 없이 배치와 탐색 UI만 변경했다.

- 2026-10-27: 원형 학맥 이름은 회전하지 않는 수평 표시, 화면 기준 최소 17px. 소속 표시에서 대학원·학과·전공을 제거하고 캠퍼스는 유지한다. 서지 근거의 원표기는 보존한다.

- 2026-10-27 후속 수정: 수평 라벨안을 철회하고 최초 원형 회전 라벨을 복원했다. 고리 간격 360, 최소 각도 간격 기준 62, 이름 시작 간격 36으로 확장. 대학명·캠퍼스 정규화는 유지. 곽효환(경남대), 신용목(계명대), 김행숙(강남대), 신철규(명지전문대학)는 사용자 확인 교수 정보로 반영.

- 같은 날 추가 사용자 확인: 임곤택·이찬·문혜윤은 고려대학교 세종캠퍼스 교수로 반영.

- 같은 날 추가 사용자 확인: 주영중은 대구대학교 교수로 반영.
