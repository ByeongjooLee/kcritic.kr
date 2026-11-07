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
> 2026-10-29 점검(Render 10-27 보안 안내 — eMudhra 중간 CA 키 유출·Node.js·PHP2Shell — 를 받고): 라이브 API 는 HEAD 와 같은 보안 코드다(CORS 가 kcritic.kr 만 허용·X-Admin-Token 헤더 = 2026-09-15 강화판). 인증서는 Render 가 관리하는 Google Trust Services 와일드카드(`*.onrender.com`, 2026-09-21 발급·12-20 만료)라 eMudhra 와 무관하고, Node.js·PHP 는 쓰지 않는다. **외부에서 확인 못 한 것**: 마지막 빌드 일시, Python 버전(`.python-version` 없음 → 서비스 생성 시점 기본값), 설치된 certifi 등 패키지 버전(`requirements.txt` 가 버전을 고정하지 않아 빌드 캐시에 따라 옛 판일 수 있음). 확인은 Render 대시보드 Deploys 페이지와 Shell `pip list`. 권장 조치: certifi ≥ 2026.10.23 을 포함해 버전 고정 + `.python-version` 추가 + 「Clear build cache & deploy」. GitHub Deployments 에 남은 `kcritic-api / production` 기록(2026-07)은 Railway 시험 배포(inactive)라 Render 와 무관.

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

### 학술연구(`/theses/*`) 는 별도 Worker — 데이터 파일은 이 저장소가 공급 (2026-10-28)

`/theses/*` 화면(박사논문 찾기·글·인물·개념어·학위수여기관·지도교수 탭)은 **다른 Worker `kcritic-theses-search`**(route `kcritic.kr/theses*`, 소스 `Documents/Codex/2026-10-23/…ddmkl…/work/public_search`)가 서빙한다. 그 화면이 쓰는 `/thesis-browse.js`·`/study.html`·`/site/data/research-public.json`·`/site/data/thesis-topics-public.json`·`/site/data/thesis-citations-public.json` 은 **이 저장소(메인 `kcritic` Worker)의 자산**이다.

- `site/data/thesis-topics-public.json` 은 theses-search 쪽 `export_browse.mjs` 가 만든다(논문별 공개 인물·개념어 태그 + 대학명 정규화 표, 1,593편). 2026-10-27 까지 git 에 없이 작업 폴더에서만 배포돼 있었고, 저장소 체크아웃에서 배포하자 404 → 글·인물·개념어·학위수여기관·지도교수 탭이 "서지정보를 불러오지 못했습니다" 로 멈췄다. 2026-10-28 저장소에 넣어 복구. **새로 export 하면 반드시 커밋한다.**
- 배포 전 확인: `curl -s -o /dev/null -w "%{http_code}" https://kcritic.kr/site/data/thesis-topics-public.json` 이 200 이어야 한다. `thesis-browse.js` 는 두 파일 중 하나라도 실패하면 탭 전체를 비운다.
- `research-public.json` 의 `works`(참고문헌 집계)는 저장소 판이 12종(김기림 관련 일부)이고, theses-search 의 `menu_release` 판은 236종(전체)이다. 어느 쪽을 공개할지는 연구자 결정 사항(2026-10-28 현재 12종 유지).
- **지도교수 탭은 학맥 데이터로 맞춘다 (2026-10-28)**: 학술연구 글·인물·학위수여기관·지도교수 탭은 `research-public.json` 의 `theses` 만 읽고, 학맥(`lineage.html`)은 `genealogy-library.json` 을 읽는다. 둘은 출처가 달라(전자는 RISS 통합목록 → 본문 색인 1,593편, 후자는 도서관·통합목록 검수) 양승국·권영민 지도학생을 학맥에 넣어도 지도교수 탭에는 안 보였다. `py enrich_research_public.py` 가 genealogy-library.json 의 지도교수를 research-public.json 에 되비춘다 — 공통 논문은 `advisor` 를 학맥의 한글 이름으로 통일(원 표기는 `advisor_raw`, 한자 지도교수명으로 갈라지던 항목 219건 통합), 학맥에만 있는 논문 295편(서울대 도서관 `snu:` 포함)은 서지만 `in_search_corpus: false` 로 덧붙인다. **genealogy-library.json 을 바꾸거나 theses-search 가 research-public.json 을 새로 내보낸 뒤에는 이 스크립트를 다시 돌린다**(두 번 실행해도 같음). 덧붙인 논문은 글 찾기(뜻 검색)·인용 관계·인물/개념어 태그에는 없고, `corpus_size`·"1,593편" 안내는 뜻 검색 범위라 그대로 둔다. 통합검색(`search.html`)의 박사논문 결과는 `/theses/api/search`(본문 뜻 검색)라 지도교수 이름으로는 찾히지 않는다.

- **학술연구 문단 색인 v2 (2026-10-29)**: `/theses/` 검색의 Vectorize 색인(`kcritic-theses-paragraphs-v2`, 문단 1,883,458)과 참고문헌 평가용 R2 벡터(`kcritic-theses-private/full-body-v2/`)는 KMMOCR 띄어쓰기본(`spaced`)으로 다시 임베딩한 것이다(이전 v1 은 OCR 문단 29% 가 공백 없이 들어가 있었음; v1 R2 객체는 그대로 남아 있음). Worker 소스·배포는 Codex `work/full_body_release`(R2 접두사 = `private/paragraph-manifest.json` 의 `version`), 재구축·업로드 스크립트와 기록은 `work/public_search/README.md` 「Full-body v2」. 비공개 본문 색인 v3(`kmmocr/색인_v3/`)와 함께 **문단 텍스트·벡터는 이 저장소에 넣지 않는다**.

- **학술연구 상세의 「이 논문이 참고한 ‘질문’ 선행연구」 = 그 논문의 참고문헌·각주 전체와 대조 (2026-10-29 재설계)**: 예전에는 "서지가 대조된 참고문헌"(보유 박사논문 간 정확 일치 연결 + 김기림 참고문헌 236종)에만 질문을 적용해 권경아 2011 처럼 연결 0건인 논문은 무엇을 물어도 0편이었고, 파서가 "연구·논문"을 먼저 지워 질문이 깨진 채 임베딩됐다. 지금은 theses-search Worker(`work/full_body_release/{query-topic,citation-context}.mjs`)가 논문별 비공개 색인 `kcritic-theses-private/citation-contexts-v1/<key>.json`(`work/public_search/build_citation_contexts.py`: 참고문헌 항목 + 각주 인용, 항목마다 인용된 본문·각주 문단 번호와 그 문단의 인물·개념 용어 id, 원문 없음)과 문단 벡터를 읽어 **제목 일치 / 질문 인물·개념이 나온 인용 문맥 수 / 질문–인용 문맥 뜻 유사도** 로 항목을 고르고, 질문 인물 본인의 글은 「1차 자료」로 뒤에 둔다. 질문 틀("~을 연구한 논문이 뭐있지?")은 용어 추출 전에 벗긴다. **순서는 같은 주제의 보유 논문이 함께 인용한 수(연구자 요청 2026-10-29)**: 색인의 `cb`(같은 저작을 인용한 다른 논문, `build_citation_crosslinks.py`)와 주제 논문 집합(인물 중심성 상위 100 교집합 · 개념 가중치 상위 100 합집합 · residual 제목 포함, 자기 제외)의 교집합 크기 → 근거 점수 → 전체 인용 수 순. 공동 인용 논문의 정체는 응답에 넣지 않는다(수만). **참고문헌 재검토(2026-10-29, 연구자 "이런 사례가 많다")**: 예전 `references_raw` 는 OCR 줄 단위라 두 줄 항목의 꼬리(발행처·연도)가 잘려 연도 없는 행이 22,550, 제목 속 "1950년대"를 연도로 집은 항목이 5,202건이었다. 지금은 `resegment_bibliography.py` 가 참고문헌 면의 줄을 들여쓰기·종결 표지로 다시 묶고(`private/bibliography-v2/`, 1,501편; 면 검출 실패 92편은 옛 행), 빌더가 넓힌 파서(괄호 변형·기관 저자·외국 이름·반복 표시·한 줄 두 항목)와 `pick_year()`(제목 속 연도 제외)를 쓰며, KCI 82,344편 서지와 제목·저자로 대조해 맞는 소논문은 연도·학술지(`venue`)·`kci` id 를 확정한다. 종류는 석사학위논문·박사학위논문·소논문·단행본·기타. 결과 283,468항목(연도 있음 87%, KCI 확정 9,964, 보유 논문 연결 2,899). 감사: `audit_citation_rebuild.py` → `_audit.json`. **외부 전거 검증(같은 날, 연구자 "배포 + 검증 시작")**: `verify_works.py`(보유 논문 간 표기 합의 — 같은 제목의 저자 오기·공저 붙음·잘림, 같은 저자의 제목 오자(유사도 ≥ .88), 단일 연도 저작의 연도 다수결, 띄어쓰기 변형 중 가장 온전한 표기; KCI 근사 대조 ≥ .9) + `nlk_books_lookup.py`(국중 LOD `https://lod.nl.go.kr/sparql`, `dc:creator` 리터럴 질의 + `format=` 파라미터 필수, 2편 이상 인용 단행본 저자 2,743명 → 저작 3,910종 확정, 발행처·판 연도, 제목은 같은 길이 치환형 오자만) → `private/works-verify/{corrections,nlk_corrections}.json` 을 빌더가 적용하고 항목에 `verified`(consensus/kci-fuzzy/nlk)와 원표기(`orig_*`)를 남긴다(재실행 멱등). 검토표 `review.csv`·`nlk_review.csv`. OCR 이 『』를 뺷뺸 으로 읽은 것(3,000여 건)도 걷어낸다. `study.js` 는 응답 `mode: citation-context` 를 받아 저자·제목·연도·종류·근거만 보이며(쪽·원문 없음) "OCR 자동 추출 서지(검수 전)" 라고 밝히고 보유 논문과 대조된 항목만 링크한다. 색인이 없는 논문은 예전 방식으로 떨어진다. 연구자 확인 사항: 검수 전 참고문헌 항목을 질문별 후보로 공개하는 범위(2026-10-26 "검수 안 된 후보는 확정 연결로 공개하지 않음" 결정을 넓힘).

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
- **lod.nl.go.kr** (NLK LOD): `http://` 는 연결 거부지만 **`https://lod.nl.go.kr/sparql` 은 열려 있다**(2026-10-29 확인, 「저자 식별」 절 참조). 로컬 RDF 스냅샷(`온톨로지/Person_rdf_20260401/`, 744,500건)은 오프라인 보조
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
  - **2026-10-27 밤 확정**: 서울대 중앙도서관 학위논문 레코드(Primo 82SNU_INST21422400670002591)의 지도교수 항목이 "조남현."이고 연구자도 "천정환은 조남현 제자"로 확인 → 학맥 계보(`genealogy-library.json`)에서는 조남현→천정환을 확정 간선으로 두고 김윤식→천정환(사용자 지정)은 철회해 `advisor_correction_history`에 보존(Codex `work/advisor_confirm_patch.py` + `advisor-confirmed-20261027.json`). `academic-network-public.json` 쪽도 **2026-10-28 확정으로 맞췄다**: `export_academic_network.py` 의 `CHUN` 블록이 입력(Codex 2026-10-26 `ddmkl-1970s-expansion/outputs/학교_소속_학맥정리/site-relationships.json`, 아직 미확인 상태)을 내보낼 때 논문의 `advisor_raw`=조남현·`advisor_status`=`library_confirmed` 로 바꾸고, `faculty:ea3257552dd98526`(조남현, 서울대 국어국문학과 명예교수)→`person:2d1ff3affe546ada`(천정환, 성균관대) 박사 지도 간선(status `library_confirmed`, 출처 Primo·RISS)을 더한다(요약 `library_confirmed_supervision_edges` 1). 화면은 「박사 지도 · 도서관 기록·연구자 확인」으로 표시하고 테스트도 이를 단언한다. 입력 JSON 쪽이 고쳐지면 `CHUN` 블록을 지운다(입력에 같은 간선이 있으면 assert 로 멈춘다).

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
- **2차·3차 판정 (2026-10-27~28)**: 나머지 미연결 92명을 웹 교차검증(알라딘·예스24·대학 교수소개·위키백과·RISS)으로 일치 37·불일치 48·미확인 30 → 연구자 승인으로 37명 병합(`author-review-confirmed-20261027b.json`). 이어 미확인·불일치 78건을 RISS 상세·대학 도서관 기록으로 재조사(핵심 기법: RISS 저자검색으로 **교수 본인의 다른 박사논문**을 찾아 동명이인 확정) → 일치 15·불일치 56·미확인 7 → 15명 병합(`author-review-confirmed-20261028.json`). 도서관 기록에서 확보한 지도교수 4건(오세영→김윤정 2004, 방민호→송민호 2012, 조남현→김민정 2000, 이형권→김영희 2022)은 `work/library-advisors-20261028.json` + `library_advisor_patch.py`(체인 마지막)로 간선 추가. 검토표 `outputs/저자_교수_연결검토/*.xlsx`에 교차검증·도서관 열이 있고, 남은 미확인 7건(김미라·최민지·김병욱·김윤영·김민수 2건·김소연)은 교수 측 학력 자료가 없어 보류. dCollection 은 대부분 WebFetch 로 읽히지 않고(검색 폼·인증서 오류), 서울대 Primo 는 브라우저로 직접 열어야 한다.
- **양승국 지도학생 전수 반영 (2026-10-28)**: 양승국(서울대 국문과, 현대희곡)은 교수 명단 705행에 없어 계보에는 도서관 지도교수 노드 `professor:library:서울대학교:양승국`으로만 있었고 간선이 2건뿐이었다(명단 밖 지도교수의 지도논문은 기본 빌드가 만들지 않는다 — 교수 명단 행 + 기존 검수 행만 간선이 된다). 서울대 Primo에서 "양승국" 학위논문 49건을 API(`/primo_library/libweb/webservices/rest/primo-explore/v1/pnxs`, 브라우저 세션 JWT)로 받아 학위논문주기가 박사인 16건만 채택(석사 30건 제외, 본인 논문 3건 제외 — 그중 1990 지질학 석사는 동명이인) → `work/library-advisors-20261028-yang.json`(16행, 신규 5건 RISS 번호는 RISS 제목 검색으로 확인: 이영석·김사량·이진주·서민수·손봉금, 모두 협동과정 공연예술학 박사라 현대문학 통합목록에 없음). 본인 박사논문(1992)은 Primo 레코드에 지도교수 항목이 없어 상위 간선 없음(석사 1988 지도교수는 권영민). 결과: 양승국 지도논문 2→16건. **명단 밖 교수의 지도학생을 채울 때는 이 방식(도서관 전수 조회 → library-advisors 행)을 쓴다.**
- **명단 밖 지도교수 전원 반영 (2026-10-28)**: 양승국 방식을 확장했다. ① 서울대: Primo API(`primo_pull2.py` 방식 — 지도교수 이름 한글·한자로 검색, lds47 이 그 이름이고 학위논문주기가 박사이며 국문과·한국학·비교문학·공연예술학인 레코드만)로 권영민·신범순·조남현·김윤식·오세영·박성창·방민호·손유경·김종욱·김유중·김대중·전광용·정한모·김용직 14명 227건 → `work/library-advisors-20261028-snu.json`. 통합목록과 제목으로 대조해 RISS 번호를 맞추고, 없는 42건은 RISS 제목 검색(브라우저 fetch)으로 29건 확보, RISS 에 없거나 2026년 신규인 13건은 `snu:<Primo docid>` 를 논문 ID 로 썼다. 동명이인(전기공학 박민호, 지리 김종욱 등)은 학과로 걸러냈고 김대중의 고전산문 2건은 뺐다. ② 타 대학: 통합 박사논문목록(2,189편)에서 지도교수가 적혀 있으나 간선이 없던 761건을 `work/library-advisors-20261028-catalog.json` 으로 연결(지도교수 263명, 한자 이름·교명은 `hanja` 패키지 + 두음법칙으로 한글화, 같은 대학에 이미 쓰인 한글 표기 우선; "권두 국문요지"·"서지적" 같은 비이름 토막은 제외; 공동지도는 `co_advisor` 로 둘 다 간선). `library_advisor_patch.py` 는 소속 대학을 정규화해(경상국립대=경상대, 강원대(강릉)=강릉원주대, 경원대=가천대 등) 기존 교수·legacy 노드에 붙이고, 없으면 `professor:library:<대학>:<이름>` 노드를 만든다. **같은 이름이라도 대학이 다르면 합치지 않는다**(정한모·전광용 서울대/단국대, 김종욱 서울대/세종대 등은 별도 노드 — 연구자 확인 후 합칠 것). 결과: 간선 1,046→1,865, 교수 248→508, 지도논문 있는 교수 171→421. 상위 간선 후보(전광용→권영민 1983, 정한모→오세영 1979·김용직 1977, 김윤식→... )는 학위자 노드로만 들어가 있고 교수 노드와 자동으로 합치지 않았다.
- **미확인 동일인 반영 (2026-10-28, 연구자 지시 "확인되지않은것들도 반영해줘")**: 학위자 노드와 이름이 같은 교수 노드 후보 125건을 `work/finalize_unconfirmed.py` 규칙으로 걸러 66건을 합쳤다(`work/unconfirmed-merges-20261028.json` + `unconfirmed_merge_patch.py`, 체인 마지막). 받아들인 근거 등급: 학위 대학 = 소속 대학(11) · 명단에 박사 정보 없음(미확인) · 도서관·기존 노드(미확인). 제외 규칙: 같은 이름의 학위논문이 여럿(김영희 5·김현주 4 등 14명), 명단 박사 대학·연도 모순, 명단 전공이 국어학·고전·한문(김성규·서철원·임경순 등), 명예·전직 교수인데 2005년 이후 학위, 교수 노드의 첫 지도논문이 본인 학위보다 앞섬(김재홍·이혜순). 동명 교수 노드 7쌍도 합쳤다(정한모·전광용 서울대←단국대, 권성우 숙명여대←동덕여대, 남길임·김종욱·서대석·김영민). 박동규(전주대 명단은 중앙대 1992 박사)는 서울대 박동규와 다른 사람이라 두었고, 이화진·김윤정은 후보가 여럿이라 보류. 간선의 `student_identity.status` 와 교수 노드의 `own_thesis_identity.status` 가 `사용자 지시(미확인 반영)` 이므로 되돌리기·재검토 대상을 골라낼 수 있다. 결과: 정한모 후손 148→285명(4세대), 전광용 7명→후손 149명(5세대: 전광용→권영민→…), 본인 박사논문이 연결된 교수 186→262명.
- **金 씨 성 표기 정정 (2026-10-28 낮)**: 통합목록 한자 지도교수명을 한글화할 때 `金` 을 두음법칙 없이 "금"으로 옮겨 김병욱·김승희·김상태 등 교수 21명(26행, 호환 한자 U+F90A `金` 3행 포함)이 "금○○" 노드로 들어가 있었다. `work/library-advisors-20261028-catalog.json` 의 `advisor_name` 을 고쳐 재빌드(김승희 서강대 13편 등이 제 이름으로, 같은 대학의 기존 노드와 합쳐져 교수 515→509). `advisor_raw` 는 그대로. 금동철(오세영 제자, 琴씨)은 실제 성이라 둔다. 서강대 김현주(金賢柱, 김지영 2009 지도 1편)는 이 정정으로 처음 이름이 드러난 노드였는데 **고전문학 전공이라 학맥에서 제외**(연구자 결정 2026-10-28, 2026-10-26 결정과 같음): `work/library-advisors-20261028-catalog.json` 에서 그 행을 뺐다(760행, 교수 509→508·간선 1,864→1,863). 연세대 김현주(명단 0129)는 그대로. `enrich_research_public.py` 는 학맥에서 빠진 논문의 `advisor` 를 원 표기(金賢柱)로 되돌리므로 지도교수 탭에는 통합목록 표기대로 남는다. build_genealogy.py 끝의 간선 무결성 단언은 패치 전 지역 변수를 보던 것이라 최종 `data` 를 보게 고쳤다. `export_genealogy_public.py --as-of YYYY-MM-DD` 로 화면 머리의 기준일을 바꿀 수 있다(없으면 build_genealogy.py 의 `as_of` 상수 2026-10-27 그대로). build_genealogy.py 끝의 `choi_direct_theses==37` 단언은 패치 뒤 수가 달라져 알림 출력으로 바꿨다(출력 파일은 단언 앞에서 이미 저장된다).
- **왼쪽 교수 목록 순서 = 학맥 인원(모든 세대 후손 수) 내림차순 (2026-10-28, 연구자 지시 "노드가 많은 순")**: `options()` 가 `metrics(id).descendants` 로 정렬(동수는 직접 제자 수 → 이름), 이름 옆 숫자도 후손 수(툴팁에 직접 제자 수). 정한모 286 · 전광용 176 · 조남현 76 · 권영민 67 순. 목록 자체는 지도논문이 1편 이상인 교수만.
- 보기 전환(2026-10-27 밤): 툴바의 「원형 / 간단 / 시간축」 세그먼트(`?view=radial|simple|time`, 마지막 선택은 localStorage `kc-lineage-view`). **기본은 원형 보기**: 시작 교수를 가운데, 세대를 고리로. 세로 트리에서 계산한 겹치지 않는 행 간격(학위자 27px·교수 56px)을 그대로 각도로 옮기고(첫 제자가 12시, 시계 방향, 12시에는 90px 상당의 빈 쐐기 → 고리 이름 자리), 고리 간격은 1세대 고리에서 학위자 행의 호 길이가 24px 이상 되도록 `max(170, H·24/(2π·27))` 로 정한다 — 이름이 서로 겹치지 않는 근거. 글자는 반지름 방향 바깥쪽에 눕히고 왼쪽 반은 180° 뒤집는다(안쪽은 부모의 선 다발이 모여 쓰지 않음). 시작 교수 이름은 수평. 상위 지도교수는 원형에서는 그리지 않고 버튼(mentorNav)으로만. 색은 역할 색(간단 보기와 같음). 기본 보기는 100% 배율로 시작 교수를 화면 가운데에. 큰 학맥(정한모 4세대)은 지름 3,400px 이므로 전체 보기는 축소본이고 기본 보기에서 끌어 본다. 간단 보기는 세대마다 250px 열, 역할 색(시작 교수 `--accent`, 교수 `--ln-prof`, 추론 흰 바탕 점선, 학위자 회청색 — `svg.simple` CSS 가 대학 색 인라인 fill 을 덮음), 지도 기간 띠·대학 범례 없음, 제자를 둔 교수 이름도 오른쪽. 열 머리글(시작 교수·제자 n세대)은 시간축의 연도 눈금과 같은 고정 눈금자에 표시. 지표 타일·비교표는 두 보기에서 같다.
- **클릭해 펼치기 (2026-10-28, 연구자 요청 "인물 클릭하면 하위 속성이 점차 확대되는 인터랙티브")**: 툴바의 「클릭해 펼치기」 체크(기본 켬, 마지막 선택은 localStorage `kc-lineage-stepwise`)가 켜져 있으면 처음에는 시작 교수와 직접 제자만 그리고, 제자를 둔 교수는 접힌 채(`collapsed`: 점선 겉고리 `circle.more`, 부제 「▸ 제자 n명」) 보인다. 클릭 한 번 = 접힌 교수면 그 아래 세대를 펼치고(`expanded` 집합) 카메라가 그 교수와 새 제자들을 감싸도록 부드럽게 확대·이동(`flyTo` → `animateZ`, 배율 0.4~1.6, 520ms), 이미 펼친 교수를 다시 클릭하면 그 아래를 모두 접고 부모 쪽으로 물러남, 그 밖의 인물은 계보 강조·상세와 함께 그쪽으로 확대. 더블클릭(시작점 이동)·Shift+Enter 는 그대로. 「한 세대 더」는 보이는 접힌 교수를 모두 펼치고 전체를 맞추며, 「모두 접기」는 직접 제자만 남긴다. 상세 패널에도 「다음 세대 펼치기 (n명)」/「접기」 버튼. 새 시작 교수를 고르면 `expanded` 는 비운다. 체크를 끄면 예전처럼 모든 세대를 한 번에 펼친다. 새로 나타난 인물은 점이 자라고 글자·선이 떠오르며(CSS `ln-grow`/`ln-fade`, `prefers-reduced-motion` 이면 없음), 자리가 바뀐 인물은 직전 자리에서 미끄러진다(Web Animations `g.animate`, 450ms; 뒤집힘 각도 차가 180° 넘으면 그냥 옮김). 지표 타일·비교표·왼쪽 목록은 펼친 범위와 무관하게 전체 자료 기준이다. `genealogyState()` 에 `stepwise`·`expanded`·`visible[].hidden` 이 추가됐다.
- 이름은 어느 보기에서든 그룹으로 접지 않는다(기존 원칙 유지). 「클릭해 펼치기」를 끄면 모든 세대를 한 번에 펼친다.
- **한자 → 한글, 대학명 「OO대」 통일 (2026-10-28, 연구자 결정 "모든 대학교 명칭은 학교 빼고 OO대로, 한자는 한글로, 박사논문 제목·이름·소속도 한글로, 그전 데이터는 유지")**: `hanja_norm.py`(`h2k`·`uni_norm`, `hanja` 패키지 + 보정: 낱말 가운데 두음법칙 사전 MID_WORDS(女性·歷史·理論·浪漫·韻律 …), 성씨 金=김, 세 글자 인명은 이름 첫 글자에도 두음법칙(韓龍雲 한용운; 끝 글자가 道·論·史 같은 꼬리면 낱말로 봄), 「이상(李箱)」의 괄호 제거, 一九三〇年代→1930년대, 호환 한자 NFKC). 세 공개 파일이 모두 이것을 쓴다 — `export_genealogy_public.py`(간선 title·university, 노드 name·display_name·affiliations → *_raw 보존), `enrich_research_public.py`(theses title·author·university·advisor → *_raw; 재실행은 *_raw 에서 다시 계산하므로 멱등), `export_academic_network.py`(theses title→title_raw 보존·`author` 표시 필드 추가, institutions name→name_raw). 대학명은 「대학교」→「대」·「여자대」→「여대」, 대학원·학과 제거, 캠퍼스 유지, 별칭(경상국립대=경상대·강원대(강릉)=강릉원주대·경원대=가천대·OCR 오류 慶경희대=경희대). 한국학중앙연구원·육군사관학교는 그대로. lineage.js 상세의 「원표기」 줄은 title_raw·university_raw 를 보인다. 변환 전수 목록(연구자 검토용)은 `../한자_한글_변환_20261028.csv`(OneDrive 온톨로지 폴더, 4,780행). **새 논문·인물을 넣을 때 한자 표기는 데이터 원본에 두고 공개 파일 생성 때만 바꾼다** — 공개 JSON 의 *_raw 를 손으로 고치지 말 것. 학술연구 「글 찾기」 결과(`/theses/api/search`, 별도 Worker)의 제목·대학 표기는 이 저장소 밖이라 아직 원표기다.
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

### 학맥 전수 감사와 상태 3단계 (2026-10-29, 브랜치 `feat/lineage-audit` — main 미병합·미배포)

- **감사 도구** `py -X utf8 audit_genealogy.py --roster <checkpoint-705-advisors-r2.json> --catalog <통합논문목록_지도교수보완.json> --merges <unconfirmed-merges-20261028.json> --out <폴더>` (읽기 전용, openpyxl). 결과는 OneDrive `온톨로지/학맥_감사_20261029/`(반영 전 = 2026-10-28 커밋 데이터)와 그 아래 `반영후/`: `학맥_감사_20261029.xlsx`(1a 동일인 후보 · 1b 세 파일 대조 · 1c 상태 분포·재분류표 · 1d 전공 범위 후보 · 1e 결측 · 1f 동명·보류) + 같은 이름의 csv, `학맥_감사_보고서_20261029.md`, **연구자 검토표 `연구자_검토표_20261029.xlsx`**(후보·근거·추천 판정·결정란). 등급 A = 명단 박사 대학·연도·제목 모두 일치 … E = 모순.
- **판정 상태 3단계** `lineage_status.py`: 공개 파일의 간선 `student_identity.status`, 노드 `identity_status`·`own_thesis_identity.status` 는 「확정 / 추론 / 미확인」이고 원래 값(사용자 확인·교수 명단·추론 연결·사용자 지시(미확인 반영) …)은 `status_raw`·`identity_status_raw` 에 있다. `summary.identity_levels` 에 단계별 건수. 계보 그래프(Codex 출력)는 세분 값 그대로이며 `export_genealogy_public.py` 가 publish 때 묶는다. 화면(`lineage.js`)은 상세에 「동일인 판정 확정 (사용자 확인)」처럼 단계+경위를 보이고, 미확인 병합으로 교수가 된 제자는 촘촘한 점선 테두리(`.unconfirmed`, 범례 「동일인 미확인(연구자 지시 반영)」), 범례 아래 `#levelNote` 에 단계별 건수. 「추론 포함」 토글의 뜻은 바꾸지 않았다.
- **규칙으로 반영한 것(패치 체인 끝, Codex `work/`)**: ① `library-advisors-20261029-audit.json`(`make_audit_rows_20261029.py` 가 통합목록에서 생성, `library_advisor_patch` 가 glob 으로 읽음) — 학교·소속 데이터에는 지도교수가 있는데 학맥 간선이 없던 논문 6편(이상경→김윤식 1992, 김성리·김참→엄국현 인제대, 김일산→임승빈 청주대, 이정인→손병희 안동대, 실비안→박민호 서울대 2022)과 공동지도 둘 중 하나만 들어가 있던 3편의 두 번째 지도교수(김학면 이승복 홍익대, 조정현 김종회 경희대, 김보현 송재일 공주대). 후이잉=Liu, Huiying 2015·김정현 2017 은 다른 id 로 이미 있어 제외, 서강대 金賢柱 는 연구자 결정으로 제외, 「김영미, 유리」의 "유리" 는 검토표. ② `audit_fix_patch.py` + `audit-fixes-20261029.json`: 통합목록 한자 이름의 두음법칙 누락 노드 정정 — 조륭희→조융희(趙隆熙, id 도 바꿈), 이룡남 노드를 같은 명지대 이용남 노드에 병합(李龍男). 노드에 `name_correction`, 그래프에 `audit_corrections`. 결과: 노드 2,134→2,144 · 교수 508→512 · 지도논문 있는 교수 410→414 · 간선 1,863→1,872. **1a 의 명단 대조 병합은 0건** — 명단(checkpoint-705)에 박사 제목·연도가 적힌 행이 거의 없어 「모두 일치」가 성립하는 후보가 없었다(82건 모두 D·C 등급).
- **전파 수정**: `export_academic_network.py` 는 입력에 지도교수가 비어 있으나 학맥에 있는 논문 127편의 화면 표기 `advisor` 를 `genealogy-library.json` 에서 채우고 `advisor_status: "genealogy_library"` 로 표시한다(`advisor_raw` 는 그대로 빈칸, 관계 165건 불변). `enrich_research_public.py` 는 RISS 제어번호 꼴(16~32자 hex)이 아닌 id(`snu:`·`DDMKL_UNMATCHED_`)에는 `riss_url` 을 만들지 않고, 원표기와 학맥 지도교수가 같을 때 `advisor` 를 바로 맞춰 한 번 실행으로 수렴한다(전에는 두 번째 실행에서야 같아졌다). 테스트 `tests/academic-network.test.cjs` 에 채움·3단계 검사 추가(10 pass).
- **연구자 결정 반영 (2026-10-29 "확정권고는 확정해주고 현대문학만")** — `work/audit_decision_patch.py` + `audit-decisions-20261029.json`(`make_audit_decisions_20261029.py` 가 검토표 CSV 에서 생성, 체인 맨 끝): ① 「확정 권고」 18건(권영민·오세영·김용직·조남현·박동규·김윤식·한계전·윤대석·원종찬·송하섭·김진기·손종호·이동희·김예림·김정자·박유희·허윤·허정)의 본인 논문을 `사용자 확인`(확정)으로 올림 — 이전 상태는 `own_thesis_identity.previous_status`·`identity_confirmation_history`. ② **학맥은 현대문학만**: 명단 전공·학과가 고전문학·국어학·한문학·어학인 교수 24명(구사회·김대중·김대행·김상일·김정숙·남길임·민긍기·박애경·박재민·서대석·송원용·엄태웅·이돈주·이정원·장효현·전일환·정대림·정병설·정우봉·조경순·조광국·조태린·조현설·최귀묵)과 그 간선 전부, 제목이 고전·구비인 논문 3편(권두환 조선후기 시조가단·박종섭 거창 구비문학·이걸 전기소설)의 간선을 뺐다(서강대 김현주와 같은 처리; 임유경은 '남북한문학사'의 '한문' 오탐이라 유지). 뺀 노드·간선 36건은 그래프 `scope_exclusions` 에 보존. 빠진 교수가 지도한 현대문학 논문(정대림의 1920년대 모더니즘·정지용·오장환, 전일환의 영랑·신석정, 민긍기·송원용·이돈주 지도 등 약 15편)은 학맥에서 지도 간선이 사라지고 학술연구 탭에는 통합목록 원표기 지도교수로 남는다. 결과: 노드 2,083 · 교수 486 · 지도논문 있는 교수 389 · 간선 1,836 · 본인 논문 확정 100 / 추론 0 / 미확인 52. 명단 밖(도서관 노드) 교수의 전공은 명단이 없어 걸러지지 않았다 — 이혜순(이화여대, 명단 전공 미확인)은 dCollection 지도논문이 한문학이라 후보(검토표).
- **연구자 결정 대기(검토표, 위 반영 뒤 남은 것)**: ① 미확인 병합 52건 + 추론 0 — 현 상태; 같은 이름 학위자 노드 23건 중 3건은 명단 박사 정보와 모순(김지윤·박진영·임경순, 별개 인물). ② 전공 범위: 명단 밖 교수(이혜순 등)와 제목만 걸린 논문 24편은 유지 — 추가 제외는 연구자 결정. ③ 동명 교수 노드 3쌍(김용성 인하대/전북대, 김윤정 강릉원주대/울산대, 이화진 서울대/경국대)과 같은 이름 학위논문이 여럿인 저자 66명(146편), 보류 10명 현황. ④ 1b 잔여: G≠AN 지도교수 불일치 8건(모두 AN 쪽 "서지적·권두 국문요지" 같은 비이름 토막), 학맥에 없음 3건(서강대 金賢柱·후이잉 중복 id·김정현 중복 id), 연도 불일치 1건(박근예 2006/2005), 학교·소속 논문목록에 없는 학맥 논문 44편(`snu:`·신규 RISS id). ⑤ 타 대학 도서관 전수 조회 순서: 명단 지도교수 미조사 행이 많은 연세대 55 · 이화여대 46 · 고려대 38 부터(OPAC 가능 여부는 감사 보고서 끝 절).
- **교수 본인 박사논문 연결 전수 재검토 (2026-11-04, 연구자 「오류가 있을 수 있겠네 전체 재검토하자」)**: 지방대 질문에 답하다 교수 6명에 다른 대학 논문 2편이 붙은 것을 발견 → `py -X utf8 audit_own_thesis.py --roster <checkpoint-705> --catalog <통합논문목록_지도교수보완.json> --authority <KCI_현대문학_2000-2026/참고문헌_구축/저자전거> --out <폴더>`(읽기 전용, openpyxl). 공개 그래프의 본인 논문 261명·268건을 명단 박사 대학·연도·제목·지도교수, 같은 이름 논문 수, 지도 시작 vs 학위 연도, **국중 전거(`prof_kac_A.csv` 의 KAC 가운데 소속 표기에 노드 소속 대학이 든 것만) → 그 전거에 매인 NLK 박사논문(`nlk_phd_theses.csv`)** 과 대조(제목은 주제목 접두 일치 또는 같은 해·같은 대학 + 글자열 ≥ .5). 결과 OneDrive `온톨로지/학맥_감사_20261104/`(`재검토_요약_20261104.md` · `본인논문_재검토.xlsx` 「연구자 결정표」 · csv). **오류 11명**: 김주현(중앙대 2006 해제)·김현주 연세대(2003 대중소설 → 2002 「이광수의 문화 이념 연구」로 바꿈)·박정선(고려대 2011 해제)·신지연(조선대 2017 해제)·윤석진(한양대 2000 확정, 전남대 2009 해제 — 충남대 지도논문 9편이 모두 드라마·연극)·이동순 영남대(전남대 2008 → 경북대 1988 「일제시대 저항시가」; 10-26 사용자 정정과 모순, 전거 생년 1950)·이동희 단국대(1985 단국대·1996 조선대 둘 다 해제 — 전거 생년 1938 소설가, 박사는 1987 경희대 「이무영 연구」; **10-29 확정 권고 18건 중 유일한 오류**)·이승은 고려대(2011 연세대 해제, 전거는 고전문학 1985년생 → 범위 제외 후보)·전은주 부산대 국교과(2019 연세대 해제)·최현주(서강대 2004 해제)·허윤(서울대 2020 해제). 임경순은 학교·소속 데이터의 2003 서울대 논문과 일치(이상 없음). 의심 4(최승호 숭실대 = 시인 최승호, 1994 서울대 논문 해제 권고; 양명학 61세 학위; 이혜령 국중 중복 전거; 김윤영). **국중 전거 일치 195건 중 미확인·추론 79건은 확정으로 올릴 근거가 생김.** **반영(같은 날, 연구자 「반영해줘」)**: Codex `work/own_thesis_patch.py` + `own-thesis-decisions-20261104.json`(`make_own_thesis_decisions_20261104.py` 가 감사 CSV 에서 생성, 체인 맨 끝 audit_decision 다음) — detach 10(간선은 지우지 않고 대상을 학위자 노드 `student:<id>` 로 되돌림, 없으면 다시 만듦; 본인 논문이 안 남으면 `own_thesis_identity` 없앰) · replace 2(김현주 → 13f67ac02425733d, 이동순 → af46565fb4202754 경북대 1988, 지도 간선 없어 thesis_ids 만) · confirm 80(79 + 윤석진 한양대 2000; identity_status 가 추론·미확인이던 노드는 '사용자 확인'으로). 변경 기록은 그래프 `own_thesis_review`. 결과: 공개 노드 2,083→2,092 · 교수 486→484(이승은·전은주는 지도논문도 본인 논문도 없어 공개 파일에서 빠짐) · 간선 1,836 그대로 · 본인 논문 확정 177 / 미확인 10. 재감사(`학맥_감사_20261104/반영후/`) 오류 0 · 의심 4(최승호·양명학·이혜령·김윤영 — 미반영, 연구자 결정 대기). research-public·academic-network 는 바뀌지 않았다(지도교수만 쓰므로). **2차 교차검증(같은 날, 연구자 「나한테 묻지 말고 국중·ISNI·KCI 다 교차검증해」)**: 남은 의심·약함을 국중 전거의 **논문 저자 KAC 레코드**(`sparql/nlk_sparql_matches.jsonl` 의 소속·생년 — 감사 스크립트에 「논문 저자 전거 소속」 열·「논문 저자 전거의 소속에 이 교수의 소속 대학 있음」 표지로 넣음; 소속이 다르게 적힌 것은 전거 작성 시점의 강사·전임지일 수 있어 등급에 안 넣음)·명단 비고·KCI 저자 ID·RISS·위키백과로 대조 → `own-thesis-decisions-20261104b.json`(패치에 `attach` 동작 추가): 해제 3 — 최승호(명단은 숭실대 문창과 시창작 전직교수 = 1954년생 시인 전거; 1994 서울대 논문 저자는 1956년생 [前]서울과기대 문창과 교수 전거), 김윤희(순천대 외래교수, 명단 비고 "명지대 박사 수료"; 2014 경희대 논문 저자는 동명대 교수 전거), 김윤영(경희사이버대, 한예종 극작과 석사; 2004 수원대 북한소설 저자는 경찰대 치안정책연구소 전거) · 붙임 1 — 이동희 단국대에 경희대 1987 「李無影 硏究」(국중 전거 KAC201114958 의 박사논문 레코드, RISS 제목 검색 control_no 570033573ce75a19; 통합목록 밖이라 thesis_ids 만). 양명학(아주대 2003, 저자 전거에 소속 없음)·이혜령(국중 중복 전거, 리디북스 저자 소개 "성균관대 국문학 박사"+2007 저서로 정합)·김미라·김소연·최민지(2021~2026 학위, 전거 미등록)는 그대로. 신지연=신해욱(위키백과: 1974년생, 고려대 국문과 박사)으로 고려대 2006 유지 확인. 결과: 교수 484→481(최승호·김윤희·김윤영은 간선이 없어 공개 파일에서 빠짐), 본인 논문 확정 178 / 미확인 7, 재감사 오류 0·의심 2(양명학·이혜령). 스크립트·공개 파일은 워크트리 브랜치 `feat/own-thesis-audit`(main 547a6637 기준)에 커밋.
- **명단 직급은 표기하지 않는다 (2026-11-04, 연구자 「비전임을 표기하진 말자」)**: 같은 날 외래·초빙·출강 등 비전임 직급을 소속 옆에 적는 기능(공개 파일 `position`·`position_kind`·`summary.position_kinds`, lineage.js 직급 열·기울임 표시)을 만들었다가(커밋 e33652e6) 연구자 결정으로 되돌렸다(revert 7670403b). 공개 파일·화면에 직급 필드가 없어야 정상이며, 명단의 rank/status 는 OneDrive 명단에만 남는다. 다시 넣으려면 연구자의 명시적 지시가 필요하다.
- **박사논문 지도교수 미기재 → 석사논문 지도교수로 보완 (2026-11-06, 연구자 「권성우는 김윤식의 제자야」·「박사학위논문의 지도교수가 검색이 안 되는 경우 석사학위논문 지도교수를 각 대학 도서관에서 찾아보자」)**: 본인 박사논문은 붙어 있으나 상위 지도 간선이 없는 교수 48명(학위 대학: 고려대 7·연세대 8·이화여대 5·서강대 4·서울대 4·충남대 2·경희대 2 …)을 대상으로, 같은 대학 도서관에서 그 사람의 **석사학위논문** 레코드를 찾아 지도교수 항목을 간접 근거로 쓴다. 행은 Codex `work/library-advisors-20261106-masters.json`(`library_advisor_patch` 가 glob 으로 읽음; `evidence_kind` 를 간선 `advisor_evidence.kind` 로 넘기도록 패치 수정). 간선 `basis` 는 「석사학위논문 지도교수 도서관 기록(간접, 연구자 확인 전)」, 연구자가 사제관계를 직접 확인한 경우 「연구자 확인 + …」. 서울대 4명 완료(Primo 저자 검색 `query=creator,contains,이름` + 학위논문 facet, 레코드의 「지도교수」 행): 권성우 ← 김윤식(석사 1989, 연구자 확인) · 김승환(충북대) ← 김윤식(석사 1983, 간접) · 최병우(강릉원주대) ← 전광용(석사 1982, 간접) · 임경순(한국외대) ← 우한용(**박사 레코드 자체에 기재**, 국어교육과 — 10-28 전수 조회가 국문과 등 4개 학과만 봐서 빠졌던 것; 석사 1995 지도교수는 구인환, 참고만). 국중 KDM 레코드(권성우 KDM199430228 등)에도 지도교수 주기 없음. 결과: 교수 482 · 지도논문 있는 교수 390 · 간선 1,840(우한용 노드 신설). 간접 간선은 사제관계를 뜻하는 추정이므로 화면 상세의 「관계 연결」 문구로 구별되며, 연구자가 아니라고 하면 행을 지우고 재빌드한다. **나머지 44명 전수 조회 (2026-11-07, 연구자 「계속 찾기」)**: 연세대(8)·고려대(7)·이화여대(5)·서강대(4)·경희대(4)·충남대(2)·성균관대(2)·건국대(2)·중앙대·한양대·동국대·국민대·전북대·계명대·숙명여대 도서관 OPAC 에서 박사·석사 레코드(MARC)를 모두 열어 봤으나, **이 연대(1978~2004) 레코드에는 500 지도교수 주기가 없다**(연세·충남 등은 2000년대 레코드부터 있음; 고려대는 '지도교수' 검색 자체가 0건). 국중 LOD 학위논문 레코드(이름·문학 분야 KAC 로 4,352건 조회)도 이 연대에는 지도교수 노트가 없다. 유일한 예외 **송기섭(충남대) ← 김병욱**(충남대 석사 1989 「韓雪野 小說 硏究」 MARC 500 '지도교수: 김병욱', 간접·연구자 확인 전; 기존 노드 `professor:library:충남대학교:김병욱` 에 붙음) → 간선 1,841. 상지대(김종호)·영남대(오양호)는 접속 거부, 경북대(이동순)는 Summon 만이라 미조회. 조회 요령: 연세·이화·경희·충남·전북·계명·숙명(ctz) 은 `/search/tot/result?st=KWRD&si=TOTAL&q=` + 상세의 `toggleMarcView(id)`; 건국·중앙·한양·동국·성균관·국민(Pyxis)은 사이트 안에서 `/pyxis-api/1/collections/1/search?all=1|k|a|<q>` → `/pyxis-api/1/biblios/<id>` 의 `content`(MARC JSON); 고려대는 `/datause/advanced-search/…/advanced-search-result/?…&q1=` 뒤 상세로 **클릭 이동**(직접 URL 은 403); 서강대는 `/search/tot/result` 가 500 이라 `/searchTotal/result` 로. 남은 43명의 지도교수는 도서관 기록으로는 못 채우며, 다른 근거(학위논문 서문·교수 소개·연구자 확인)가 필요하다.


## KCI 학술지 참고문헌 → 인용관계 (2026-10-29)

- 자료: KCI 국어국문학·문학 학술지 124종 82,344편(2000–2026)의 참고문헌을 KCI Open API `articleDetail` 로 받는다. 수집기 `KCI_현대문학_2000-2026\수집도구\kci_references.py`(OneDrive, 2초 간격, 키는 환경변수 `KCI_API_KEY` 만 — 파일·로그·저장소에 적지 말 것)가 `참고문헌_API\ART*.json/xml` 에 쌓는다. 2026-10-29 새벽 34,000편 처리, 완료까지 하루 남짓. 잠금 `참고문헌_API\.running.lock`. 수집 중인 폴더는 읽기만.
- 구축: `py -X utf8 build_kci_citations.py --public site/data/kci-citations-public.json`(표준 라이브러리, 결정적, `--as-of` 로 시각 고정) → OneDrive `참고문헌_구축\`(논문_노드·인용_간선·미연결_참고문헌·미연결_서지_집계·피인용_집계(+현대문학)·피인용_목록.json·coverage.json) + 공개 초안. 스크립트는 브랜치 `feat/kci-citations`(main 미병합). **전체 수집이 끝나면 같은 명령을 한 번 더 돌린 뒤 공개 JSON 을 커밋한다** — 수집 중 부분 자료는 커밋하지 않는다.
- 검수 확정(`참고문헌_구축\검수_20261029.md`): `reference/@arti-id` = **인용되는 논문**(KOAJ 화면 28편 128링크 전부 일치). `empty_referenceInfo` 는 KCI 미구축이지 「인용 0」이 아니다(2000–2003년 전부 빈 응답, 스캔 PDF 에는 참고문헌 인쇄). KCI 자체 오연결(같은 호 이웃 논문)이 있어 간선표 `title_check` 가 mismatch 인 간선은 공개본에서 뺀다.
- **연구자 결정 (2026-10-29 「그대로 확정」)**: ① 빈 응답 논문은 **재조회하지 않는다**(2026년 발행분 `referenceInfo_absent` 992편만 KCI 구축이 끝난 뒤 — 이듬해 — 다시 받을 수 있음). ② 공개 범위는 **현대문학 포함·후보 논문(selection 전문지기준포함·온톨로지초록일치포함·포함후보)끼리의 인용 간선만**, 자기인용·제목 불일치 제외, 초록·본문·로컬 경로 없음. 미연결 참고문헌(단행본·학위논문 등 KCI ID 없는 항목)은 비공개 CSV 에만 두고, RISS·NLK 서지 대조는 미구현.
- 공개 JSON 을 사이트 화면에 붙이는 일은 별도 결정 사항(아직 없음). `site/data/kci-citations-public.json` 은 `.assetsignore` 에 걸리지 않으므로 커밋하면 배포된다.
- **수집기 중단·재개 (2026-10-29)**: 04:33 연구자 요청으로 `참고문헌_API\STOP` 이 만들어져 36,698편에서 멈췄다. 재개는 `수집도구\resume_references.ps1` 을 연구자가 직접 실행(키를 가려진 입력으로 받아 자식 프로세스 환경변수로만 넘김; 키는 어디에도 저장되지 않으므로 세션이 대신 띄울 수 없다).
- **수집 완료·재구축 (2026-10-30 13:01 UTC 완료, 10-31 재구축)**: 82,344편 전부 처리(참고문헌 행 1,970,465, 빈 응답 6,163·구축 중 2,635). `build_kci_citations.py` 재실행 → 간선 438,200(제목 불일치 1,572 제외), 공개본 `site/data/kci-citations-public.json` 논문 42,575·간선 97,027·`coverage.collection_complete: true`. 공개본 `scope` 문구는 이제 수집 완료 여부에 따라 바뀐다(예전 "부분 자료다" 고정 문구 제거). 스크립트·공개 JSON 은 아직 **미커밋**(main 에 미추적 파일) — 커밋 여부는 연구자 결정.

## 저자 식별 — KCI 연구자 ID · 국중 전거(KAC/ISNI) · NLK 학위논문 LOD (2026-10-29)

학위자 1,787명 + 학맥 교수 483명 = 이름 2,045개(`참고문헌_구축\저자전거\names.csv`)를 외부 전거에 잇는 작업. **이름만 같은 저자를 자동 병합하지 않는다** — 모두 후보 등급표로 연구자 검토. 스크립트는 OneDrive `KCI_현대문학_2000-2026\수집도구\`, 결과는 `참고문헌_구축\`. 자격증명 없음(API 키는 환경변수로만).

- **KCI 연구자 ID(cretId)**: Open API 응답에는 없고 논문 웹페이지 저자 링크(`poCretDetail.kci?citationBean.cretId=CRT…`)에 공개. `kci_author_ids.py` 가 이름 겹치는 논문 23,512편(`저자ID\targets.csv`)을 2초 간격으로 읽어 `저자ID\author_ids.csv`(kci_id, 순번, cret_id, 표기, 소속)에 쌓는다(약 15시간). 첫 저자 링크 글자에 저자 전원이 든 행(ART000888601)이 있어 name_ko 는 걸러 쓸 것. 연구자 상세·KRI 는 로그인 필요(학위 항목 공개 여부 미확인).
- **국중 LOD SPARQL 은 열려 있다**: `https://lod.nl.go.kr/sparql`(https 만, http 는 거부; §14 「직접 연결 차단」은 http 얘기). SELECT 는 100행에서 잘리고(OFFSET 가능) CONSTRUCT 는 안 잘린다. **이름 조건을 `?s a nlon:Author ; ?p ?o` 보다 앞에 둘 것**(뒤에 두면 전체 스캔으로 이름 하나에 150초). `nlk_sparql_lookup.py` → `저자전거\sparql\nlk_sparql_matches.{jsonl,csv}`(2026-10-08 갱신 데이터, 인물 전거 2.18M). 오프라인 스냅샷(`온톨로지\Person_rdf_20260401`, 744,500건)은 `nlk_snapshot_scan.py`(58초)로 같은 스키마 → `저자전거\nlk_snapshot_matches.*`.
- **등급표** `grade_authority_candidates.py` → `저자전거\전거연결후보.{csv,xlsx}`(A 문학 분야+소속/논문제목 일치 · B 문학+생년 또는 학위대학 일치·후보 유일 · C 문학이나 동명 여럿 · D 비문학 · — 없음). 현행 SPARQL 데이터(`저자전거\sparql\`, 63,308건) 기준 이름별 최고 등급 **A 722 · B 445 · C 767 · D 54 · 없음 57; 교수 483명 중 A 434**(스냅샷판은 A 360). 전거 레코드의 99%에 ISNI 가 있다. names.csv 는 공백·쉼표를 뗀 이름이라 로마자 이름은 원표기로 다시 조회해야 한다(2026-10-29 보완 49건).
- **박사논문 대응 결과(2026-10-29)**: 우리 1,888편 중 **A 1,529 · A* 84(논문은 같은데 저자 표기가 다름 — 개명·필명·음역·오기, 검토) · B 5 · C 1 · X 173 · 없음 96**(없음은 2020년대 미정리가 65). A+A* 가운데 KAC 링크 1,387. 지도교수 노트 534건 중 **일치 531 · 일부 1 · 불일치 2**(김은정 제주대 허남춘↔임화순, 유미애 가천대 장현숙↔張賢淅) → 우리 학맥 지도교수 데이터의 외부 검증. 연구자 검토표 `저자전거\연구자_검토표_저자식별_20261029.xlsx`(시트: 지도교수불일치·저자표기상이·미대응·전거A충돌·전거없음). 연구 설계 문서 `참고문헌_구축\연구설계_학풍_20261029.md`.
- **NLK 학위논문 LOD 가 핵심 연결 고리**: 박사논문 레코드(`bibo:Thesis`, `bibo:degree <http://purl.org/ontology/bibo/degrees/phd>`)에 `dc:creator` 표기·`dcterms:creator` **KAC 전거 링크**·`nlon:degreeYear`·`dc:publisher`(대학)·`nlon:department`·`dcterms:description` "지도교수: ○○○"(2015년 박사 13,363편 중 6,586편). `nlk_thesis_lookup.py` 가 이름(→ 2차 `--kac-from` 으로 KAC)별 박사논문을 받아 우리 박사논문과 연도·대학·제목으로 대응(`저자전거\thesis\thesis_matches.csv`, 등급 A/B/C/X/—)하고 지도교수 노트를 우리 학맥 지도교수와 대조한다(`advisor_agree`). 제목은 주제목(`dcterms:title`)과 부제(`nlon:remainderOfTitle`)가 나뉘고 옛 논문은 한자 표기라 `hanja_norm.h2k` 로 맞춘다. **이 대응이 A 면 학위자 ↔ KAC ↔ ISNI 가 이름이 아닌 논문 레코드로 확정**된다.
- **공공데이터포털 「국립중앙도서관_저자 정보 제공 서비스」**(`apis.data.go.kr/1371029/AuthorInformationService`, 연구자 개발계정 키 — 환경변수로만): `getPersonList`(`label`=이름 검색, `authorId`=KAC, `type=json`, 한 쪽 최대 20건, 일 10,000건) · `getPersonBiblioList`(KAC → 저작 URI). 전거 2,179,710건. SPARQL 이 있어 보조 수단.
- **ISNI 공개 SRU**(`isni.oclc.org/sru`, `pica.nw="이름"`, isni-b): 레코드에 KAC·K-Scholar(scholarKR P번호)·**KRI/NTIS 번호**·저작 제목이 있어 KCI 쪽과 잇는 다리가 되지만, 익명 조회는 **약 90개 이름(수백 요청) 뒤 recordData 가 빈 채로 온다**(쿼터). `isni_sru_harvest.py` 는 `저자전거\isni\STOP` 으로 멈춰 있고 빈 응답 raw 는 지웠다 — 재개는 하루쯤 뒤 소량씩. 국중 쪽 ISNI 는 SPARQL 전거 레코드(`nlon:isni`)로 이미 확보되므로 SRU 는 KRI 번호 용도.
- **국중 LOD 데이터셋 전체 내려받기**(`lod.nl.go.kr/home/dataset/datasetdownload.do?fileName=…`, 설문 팝업 뒤): 개인명 `Person_ttl_20261008.zip` 353MB, 학위논문 `thesis_ttl_20261008.zip` 462MB(2,225,440건). SPARQL 로 필요한 만큼 받고 있어 아직 내려받지 않았다 — 전수 분석(전체 박사논문 지도교수 네트워크)을 하려면 학위논문 TTL 을 받는 것이 맞다(연구자 결정).
- 국중 Open API 목록에는 전거·ISNI API 가 없고 ISNI-Korea 포털(`nl.go.kr/isni`)은 검색 화면만 있다.
- **학풍 예비 분석 (2026-10-29, 연구자 지시 「예비 분석 시작」)**: `수집도구\prelim_similarity.py`(ocr_train venv python — bge-m3 로컬 ONNX GPU, `작업도구\추천\embed_local_bge.py`) → `참고문헌_구축\학풍_예비분석\`(예비분석_보고서.md·edges_similarity·professors_summary·universities_summary·university_distance·decade_summary·permutation.json·prof_docs). 교수 묶음 = 전거 A급 KAC 의 국중 저작 제목(`nlk_works_fetch.py` → `저자전거\works\`, 447명 24,000여 건) + 이름·소속 대학이 모두 맞는 KCI 논문(ART*.xml author-group institution). 결과: 간선 1,759건·교수 351명, 제자 논문↔지도교수 묶음 코사인 0.586 vs 대학×연대 안 지도교수 순열 0.574(z 27, p<.001), 같은 대학 교수 중 지도교수 1위 맞힘 28.3%(우연 12.6%). **대학 센트로이드 코사인(0.97~0.99)은 변별력이 없으니 학풍은 within/between·혼합모형·식별 가능성으로 볼 것**(보고서 해석 메모). 연구 설계 `참고문헌_구축\연구설계_학풍_20261029.md`.
- **학풍 검증 (2026-10-29, 「학풍 검증 이어서」)**: `수집도구\school_effect.py --prelim <학풍_예비분석> --repo <kcritic.kr> --out <학풍_검증>`(예비 분석이 저장한 `vectors.npz`·`vectors_meta.json` 사용; `--raw` 는 원값 보고). **원 코사인은 교수 묶음이 '일반적'일수록 모든 논문과 가까워 편향되므로 논문·교수 고정효과를 뺀 잔차로 분석한다**(원값에서는 옛 교수의 한자 단행본 묶음 때문에 조부 교수가 남보다 멀게 나오는 가짜 결과가 생겼다). 결과(`참고문헌_구축\학풍_검증\학풍검증_보고서.md`): 고정효과 회귀 같은 지도교수 +0.018(t 28) vs 같은 대학 다른 교수 +0.0013(t 6.4) → **대학 효과는 지도교수 효과의 약 7%**; 교수 프로필끼리 같은 대학 쌍이 더 닮음(z 4.1); 제자 논문으로 대학 맞히기 3.0% vs 우연 2.6%; 세대 전승 조부 교수 0.0049 > 같은 대학 타 교수 0.0011 > 전체 −0.0001(지도교수 0.020). 서울대 계보가 표본을 지배해 세대 전승과 대학 효과가 아직 분리되지 않음 — 다음 단계는 대학×계보 분리, KCI 연구자 ID 기반 묶음, 지도 시점 창.
- **대학×계보 분리 (2026-10-29, 「대학×계보 분리」)**: `수집도구\lineage_vs_school.py`(같은 입력; 교수 간 지도 간선으로 뿌리 교수를 구해 계보를 만들고, 논문별 다른 교수를 지도교수·조부·형제(같은 지도교수의 제자 교수)·삼촌(조부의 다른 제자)·같은 계보 기타·계보 밖으로 나눠 잔차 회귀) → `참고문헌_구축\학풍_검증\계보분리_보고서.md`. **결과: 앞의 "대학 효과"는 대부분 계보 효과였다** — 계보 밖 같은 대학 +0.0007(t 3.2, 지도교수의 4%) vs 형제 교수 +0.0164(t 20)·삼촌 +0.0082(t 12)·조부 +0.0055(t 5.5)·계보 기타 0. **학풍은 대학이 아니라 지도교수 단위 학파**로 정의하는 것이 자료에 맞다. 같은 대학×계보 안 추가분은 음(−0.0016): 다른 대학으로 나간 계보 교수가 조부 주제를 더 지킨다(정한모 계보 주도, 사례 확인 필요). 서울대는 같은 대학 교수 쌍의 30%가 계보 안.
- **코호트 분리 (2026-10-29, 「코호트 분리 이어서」)**: `수집도구\cohort_vs_lineage.py`(교수 박사학위 연도 = 학맥 간선 target 연도 → research-public; 419명 중 186명 확보) → `학풍_검증\코호트분리_보고서.md`. **형제 교수 효과는 학위 연도 차 ≤5·6–15·>15년에서 +0.0169·+0.0145·+0.0163 로 같다 → 코호트가 아니라 계보**. 순수 코호트(계보 밖 같은 대학·연도 차 ≤5) −0.0006(0). 시대 거리(>15년) −0.001. 종합 정의: **학풍 = 지도교수를 뿌리로 하는 2세대 학파(지도교수·형제·삼촌·조부)**; 대학·코호트 자체는 주제를 닮게 하지 않는다.
- **학위 연도 보강 (2026-10-29, 「학위 연도 보강」)**: `수집도구\fill_prof_phd_years.py` → `저자전거\prof_phd_years.csv`(교수 486명 중 442명: 학맥 간선 216 · research-public 2 · **NLK 박사논문 KAC 확정 205** · 이름+국문학 학과 유일 19; 애매 4·없음 40). `cohort_vs_lineage.py --phd-years … --suffix _보강` → `코호트분리_보고서_보강.md`. **186명 판의 "지도교수 효과는 경력 초기 최대" 는 표본 편향이었다**(연도가 있던 교수 = 학맥 안의 젊은 교수): 390명으로는 학위 후 ≤10년 +0.0174 → >30년 +0.0202 로 경력과 무관(약간 증가). 형제(계보)·순수 코호트(0) 결론은 그대로. 같은 대학 10년 선배 교수와 +0.0021(t 4.8)이 유일한 대학 쪽 효과. 분석 수치를 인용할 때는 보강판을 쓸 것.
- **cretId ↔ 우리 인물 식별기 (2026-10-29 16시)**: `수집도구\match_cret_ids.py --base … --repo … --out 참고문헌_구축\저자ID\식별` → cret_candidates.csv(인물×cretId)·cret_best.csv·요약.json·`연구자_검토표_KCI저자ID.xlsx`. 근거 순서: 국중·ISNI 저작 제목 일치(인물의 A/B KAC 경유 — `저자전거\works\nlk_works.csv` 를 A/B KAC 1,796 전체로 넓혔다) > 소속 일치(교수 소속 / 학위자의 학위 대학, `uni_norm`) > 학위논문 제목 2-gram 겹침; 학위 10년 전부터 활동한 cretId 는 의심(D). **KCI 는 한 사람에게 cretId 를 여럿 준다**(소속·시기별 분리, 같은 소속·같은 저작 제목이 두 ID 에서 맞는 교수 50명+) — 인물의 KCI 식별자는 A 등급 cretId **집합**(`cret_ids_A`)이고, KCI 논문을 인물에 붙이는 분석은 KAC(우리 인물) 단위로 한다. 소속 근거의 약점: 교수가 되기 전 시간강사 시절 논문은 소속이 달라 D 로 남는다(이경재 숭실대 ← 육군사관학교·서울대·아주대) → 제목 근거로 보완. 'orcid 바로가기'·저자 묶음 행은 식별기가 거른다. 저자 ID 수집은 2.6초/편으로 2026-10-30 새벽, 참고문헌 수집은 10-30 저녁 완료 예상 — **둘 다 끝난 뒤 같은 명령으로 다시 만들고**, 이름만 같은 저자를 자동 병합하지 않는다는 원칙은 그대로.
- **A 등급만 자료 갱신 (2026-10-29 17시, 연구자 지시 「확정되어있는 A만 먼저」)**: ① `수집도구\build_identity_table.py` → `저자전거\인물식별표_A.{csv,json}` — 인물 ↔ KAC(전거A·학위논문A/A*)·ISNI·KRI·A 등급 cretId 집합, B·C·D 제외. 교수 486: KAC 454·cretId 250 / 학위자 1,665: KAC 1,220·cretId 365. `kac_shared_with`(동명 인물이 같은 KAC 를 받은 행 — 교수 21·학위자 84, 등급표가 이름 단위라 생김)와 `review` 열은 연구자 판정 전까지 어느 쪽에도 주지 않는다. ② `prelim_similarity.py --cret-ids <cret_best.csv> --abstract --prof-source both|kci|nlk`: KCI 논문을 이름·소속 대신 A 등급 cretId 집합으로만 모으고 국문 초록(600자, max_len 512)을 붙인다(prof_docs.csv 에는 제목만). 결과 `참고문헌_구축\학풍_A기준\`(국중 저작+KCI) · `학풍_A기준_KCI만\`, 비교 메모 `학풍_A기준\A기준_비교_보고서.md`. **핵심 결론 불변**(지도교수 +0.0182 > 형제 +0.0169 > 삼촌 > 조부 > 계보 기타 0, 코호트 0, 경력 무관). 계보 밖 같은 대학 효과는 +0.0007(t 3.2) → +0.0003(t 1.6). **재검토(「다시검토」, 같은 날 17:40)에서 "동명 오염이 빠진 탓"이라는 첫 해석은 철회** — 두 판의 차이는 z 1.1 로 우연 범위이고, 예전 묶음에서 다른 cretId 로 간 논문 113편은 대부분 같은 교수의 **B 등급(같은 소속, 경합) cretId**(KCI 의 ID 분할)였다. 즉 A 만 쓰면 같은 사람의 논문을 빼먹는다(교수 60명·cretId 105개·논문 242편 = KCI 묶음의 13%). 국중 저작만 쓴 네 번째 판(`학풍_A기준_국중만`)까지 네 판에서 계보 밖 같은 대학 효과는 +0.0001~+0.0011(지도교수의 1~5%, t<3.2) — "있다면 약한 동료 효과"; 같은 대학 6–15년 선배 효과(+0.0013~+0.0021, t 3.0~4.8)만 일관되게 양. 지도교수 ≈ 형제 > 삼촌 > 조부 > 기타 0·코호트 0·경력 무관은 네 판 모두 재현. KCI 논문+초록만 쓴 묶음은 신호가 또렷(지도교수 +0.0237, 같은 대학 안 1위 맞힘 55% vs 우연 29%)하나 교수 166명·간선 761건의 부분 자료(수집 40%)라 수치 인용은 수집 완료 뒤 재실행판으로. ~~연구자 결정 대기~~ → **2026-10-30 06:50 연구자 「적용」**: `match_cret_ids.py` 에 "소속 일치 후보가 모두 같은 한 대학이면 A"(rule `inst_same_uni_split`; 서로 다른 대학에 걸치면 B 유지, 학위자 논문 1편·주제 무관은 B) 규칙을 넣었다. `cret_candidates.csv` 의 `rule` 열(title / inst_unique / inst_same_uni_split)로 어느 규칙으로 A 가 됐는지 본다. 저자 ID 수집은 10-30 04:10 완료(23,512편 전부, 오류 0, 저자 행 25,106, cretId 묶음 5,852). **완료 자료 + 새 규칙 결과**: 교수 486명 중 A 396(제목 394행·유일 소속 79·같은 소속 분할 302) · B 6 · D 15 · 이름 없음 69(전문수·홍일식·정현종 등 2000년 이전 세대); 학위자 1,665명 중 A 1,007 · B 160 · C 68 · D 116 · 없음 314. A 교수의 KCI 논문 6,600편(중앙값 13, cretId 1개 183·2개 118·3개 58·4개+ 37), A 학위자 10,448편. `인물식별표_A.csv` 교수 cretId 396(KAC 와 둘 다 383), 학위자 1,007(755). 남은 D 는 교수 되기 전 다른 기관 시절(김유중 서울대 ← 한국항공대 12편, 이경재 숭실대 ← 육사·서울대) — 소속이 달라 규칙에 안 걸림, 연구자 판정 또는 시기 규칙 필요. 분석 재실행 결과 `학풍_A기준_전체\`(국중 저작+KCI 초록, 교수 446·간선 1,802) · `학풍_A기준_KCI만_전체\`(KCI 논문·초록만, 교수 324·간선 1,334) — **수치 인용은 이 두 판, 본 분석은 KCI만 판**(학술 논문만이라 묶음 성격이 같고 지도교수 1위 맞힘 40.3% vs 우연 16.9%). KCI만: 지도교수 +0.0263(t 27) · 형제 +0.0166 · 삼촌 +0.0123 · **조부 +0.0152(t 6.6, 쌍 190) = 지도교수의 58%** · 계보 기타 0 · 계보 밖 같은 대학 +0.0005(t 1.4) · 순수 코호트 0 · 경력 무관. 국중 저작을 섞은 판의 조부 1/4 은 옛 교수의 한자 단행본 묶음이 주제를 흐린 탓 → **3세대 전승은 앞서 보고한 것보다 강하다**. 핵심 결론(지도교수 뿌리의 학파, 대학·코호트 효과 없음) 유지. 표 전체는 `학풍_A기준\A기준_비교_보고서.md` 「전체 자료」 절.
- **통계 재검토 (2026-10-30 09:20, 연구자 「총체적으로 재검토, 유의성 검정 포함」「시계열 검증」)**: `수집도구\stat_review.py --prelim <학풍 폴더> --repo … --out <폴더>/검증 [--boot 300 --perm 300]` → `통계검증_보고서.md`·`stat_review.json`; 종합은 `학풍_A기준\통계재검토_종합_20261030.md`. `prelim_similarity.py` 가 이제 `vectors.npz` 에 문서 벡터(`docs_vec` float16·`docs_pid`·`docs_year`)도 저장한다(시계열 창용). **앞 보고서들의 t 는 논문 클러스터만 잡아 과대였다** — 논문+교수 **양방향 클러스터 SE** 로 지도교수 t 27→14.6, 형제 16→10.3, 삼촌 11→7.0, 조부 6.6→**2.6**. Holm 보정·교수/논문 부트스트랩·같은 대학 안 순열 검정 모두 같은 결론: 지도교수(+0.026, 0.9 SD)·형제·삼촌은 p<0.001 로 확고, **계보 밖 같은 대학은 모든 검정에서 0**(t 0.9, 순열 p 1.0), **조부는 KCI 판에서만 유의(Holm p 0.039, 순열 p 0.003)이고 국중+KCI 판에서는 비유의 → "3세대 전승 증거는 있으나 보통 수준"으로 낮춰 쓸 것**(어제 "지도교수의 58%, 안정적"은 과장). 시계열(지도교수 묶음을 학위 연도 기준 창으로): 제자 논문은 지도교수의 **학위 전 10년** 연구와 가장 닮고(+0.029) 학위 후 10년 +0.022, 11년 이상 뒤 +0.012(부트스트랩 구간 분리) → **전승 방향은 지도교수→제자**(공동 진화·역방향 아님); 11~30년 전 위약 창도 +0.024 라 교수 전공은 오래전에 자리 잡힌 것. 연대별 "최근일수록 강함"은 KCI 2000년 이후 범위 효과이니 쓰지 말 것. 남은 한계: 계보(뿌리) 클러스터 SE, 다른 임베딩 모델 재현. 수치 인용은 이 재검토 표로.
- **제자 쪽 시계열 (2026-10-30 09:50, 「이어서 하자」)**: `수집도구\student_trajectory.py --prelim <학풍_A기준_KCI만_전체> --repo … --base … --out <…>/제자궤적` → `제자궤적_보고서.md`·`trajectory.json`·`student_articles.csv`(초록 없음)·`student_vecs.npz`(임베딩 캐시). 학위자 896명의 본인 KCI 논문 9,834편(학위 후 7,598)을 교수 묶음과 잔차 비교(본인 교수 열은 결측; 물려받은 주제 열은 모든 교수를 같은 '학위 전 10년' 창으로 맞춘 이원 잔차 — 처음 판은 행 평균만 빼서 분야 전체의 시간 이동과 섞였음, 고침). **결과**: 지도교수 각인은 경력 내내 남음(학위 직후 +0.023 → 16년 뒤 +0.020, 기울기 −0.0006/년), 물려받은 옛 주제에서는 16년에 절반으로(+0.031 → +0.013); 형제 교수와는 갈수록 더 닮음(+0.012 → +0.022); **재직 대학 동료 효과는 학위 후 7~10년 +0.003(t 3.1)뿐, 11년 뒤 0, 옮긴 사람은 새 대학 쪽으로 가지 않음** → 대학 효과는 경력 뒤에도 없고 학풍 단위는 끝까지 계보. venv 에 `hanja` 가 없어 소속 정규화는 스크립트 안 간단 판(대학교→대) 사용. 종합 `학풍_A기준\통계재검토_종합_20261030.md` §6.
- **어휘 기반 재현 — TF-IDF · LSA · LDA, 박사논문 본문 포함 (2026-10-31, 연구자 「tf idf나 빈도 토픽모델링을 활용해서 같이 진행, 박사논문도 포함」)**: `수집도구\tfidf_topic_replication.py`(시스템 `py` — sklearn·kiwipiepy·hanja; venv 에는 없음) → `참고문헌_구축\학풍_TFIDF_토픽\`. 말뭉치 = KCI 82,344편(제목+국문 초록 72,042편) + 박사논문 본문 1,593편(색인 v3 `text_sp`, body·abstract·heading 문단, 문단 단위로 kiwipiepy 명사 추출 — 본문 통째로 넘기면 느리고 segfault). 어휘 = 한글 명사(한자는 h2k, 숫자+년대 유지, 상투어 불용어) min_df 5·max_df 0.4·상위 30,000. 변형 `tfidf`(sublinear) · `lsa300` · `lda50`(online LDA, 문서 벡터 = sqrt θ, 내적 = Bhattacharyya) · `bge_subset`(대조) 를 각각 `stat_review.py` 형식으로 저장해 같은 검정을 돌림. 표본 = bge 간선 1,334 중 본문 있는 **1,177편 × 교수 324명**, 제자 문서 = 박사논문 본문 전체(bge 판은 제목+태그). **결과(표준화 효과, bge / tfidf / lsa / lda)**: 지도교수 +0.85 / +1.30 / +1.11 / +0.90 · 형제 +0.55 / +0.81 / +0.67 / +0.71 · 삼촌 +0.45 / +0.62 / +0.60 / +0.74 · 조부 +0.48 / +0.30 / +0.43 / +0.69(양방향 t 2.4~3.1, Holm 유의, 순열 p 는 tfidf 0.23 비유의) · 계보 기타 0 · **계보 밖 같은 대학 +0.01 / +0.09(t 3.5) / +0.07(t 2.5) / +0.02** — 어휘 표현에서만 작게 잡히고 지도교수의 7% 이하. 시계열(학위 전 10년 창 최대)도 lsa·lda 에서 재현. 토픽 η²(sqrt θ, K=50, 순열 귀무 평균을 뺀 초과): 지도교수 +0.22 · 계보 뿌리 +0.16 · 학위 대학 +0.06; 중첩 「대학 위에 계보」 +0.13 vs 「계보 위에 대학」 +0.04 — 후자는 2세대 지도교수 정체와 뒤섞이므로(한 교수 = 한 대학) 대학 자체 효과는 회귀의 같은-대학 항으로 판단. 계보 특이 토픽: 정한모 시·생명, 전광용 소설·여성·가족, 최동호·김인환·정명교 언어·시학, 최원규 생명·불교. **결론은 표현(임베딩 vs 어휘)에 기대지 않는다.** 순열 검정은 같은 대학 안에서 섞으므로 같은-대학 항에는 정보가 없다(p=1.0). 캐시 `cache/*.jsonl.gz`(낱말 빈도)·θ 는 비공개; `topics_k50.csv` 상위 낱말 표는 공개 가능.
- **계보 판정 민감도 (2026-10-31 21시, 연구자 「돌려」)**: 형제·삼촌·조부 관계는 교수→교수 동일인 간선 223건(확정 139 · 추론 30 · 미확인 54)에 기댄다. `stat_review.py --edge-status 확정|확정,추론`(새 옵션; 지도교수→논문 간선은 건드리지 않음) 을 `수집도구\lineage_sensitivity.py` 가 다섯 표현(bge KCI만 본 분석·bge_subset·tfidf·lsa300·lda50)에 돌려 `학풍_TFIDF_토픽\계보민감도_보고서_20261031.md`(+ `계보민감도_20261031.json`, 각 폴더 `검증_확정\`·`검증_확정추론\`). **결과**: 지도교수 계수는 세 열에서 동일(확인). 형제·삼촌은 확정만 139건으로도 전체와 같은 크기·Holm 유의(본 분석 형제 +0.0168 vs +0.0166, 삼촌 +0.0114 vs +0.0123) → 미확인·추론 간선에 기대지 않음. **조부는 민감**: 본 분석 +0.0152(t 2.6, 유의) → 확정만 +0.0112(t 2.4, Holm 비유의), 쌍 179→136; tfidf 도 비유의로, lsa·lda 는 유의 유지 → 「3세대 전승 증거는 보통 수준이고 판정 상태에 민감」으로 쓴다. 「계보 밖 같은 대학」은 세 열에서 넷째 자리까지 같아(+0.0005) 대학 효과 0 결론은 판정과 무관. 그림 1 포레스트 플롯에는 확정만 추정치를 작은 표지로 겹쳐 그릴 것.
- **공개 파생표 (2026-10-31 22시, 연구자 「파생표 먼저」)**: `수집도구\export_derived_tables.py --base <KCI_현대문학_2000-2026> --repo <kcritic.kr> [--as-of YYYY-MM-DD]`(시스템 py, 17초) → OneDrive `참고문헌_구축\공개_파생표_20261031\`(19 파일, 약 22MB). theses(1,334: RISS control_no·riss_url·학위 대학·지도교수·동일인 판정 3단계+원 판정·어휘 표본 여부·간선 단계별 계보 뿌리) · professors(324: 소속·본인 논문·박사 연도와 출처·KAC·ISNI·A 등급 cretId 집합과 규칙·묶음 수·단계별 지도교수/뿌리) · professor_articles(6,435: KCI ART id·kci_url·cretId·학술지·제목·현대문학 선별 상태 — A 등급 cretId×author_ids 에서 제목 중복 제거로 다시 만들어 324명 전원 n_docs 일치) · lineage_professor_edges(223, 3단계) · **pair_relations_similarity.csv.gz**(논문×교수 432,216쌍: same_university, 간선 단계 3개(all/confirmed/confirmed_inferred)의 관계 부호와 같은 대학×계보 표지, 다섯 표현(bge·bge_subset·tfidf·lsa300·lda50)의 잔차·원 유사도; 어휘 표본 밖 157편은 어휘 열 빈칸) · thesis/professor_topics_k50(θ = 저장 벡터의 제곱, 합 1) · topics/lineage_topics/university_topics_k50·eta2_k50 복사 · regression_results(5표현×3단계×7항 = 105행, SE 세 종·Holm·순열·부트스트랩 구간·표준화) · decade·window·trajectory_bins/regression·student_articles(9,834, 초록 없음) · methods.json · README.md(재계산 요령 포함). **검증**: 쌍 표에서 relation 더미 OLS 를 다시 돌리면 regression_results 계수가 1e-7 안에서 재현(bge all/confirmed·tfidf all·lda50 confirmed_inferred 확인), 관계 행렬 쌍 수는 stat_review.json 과 일치(assert). **넣지 않은 것**: 원문·초록·임베딩·토큰/θ 캐시·로컬 경로(스크립트 끝 정규식 점검이 assert 로 막음). 동명 인물과 KAC 를 공유하는 교수 13명은 kac·isni 를 비우고 `kac_shared_with_namesake` 로 표시(묶음은 cretId 기반이라 분석 불변). **저장소·사이트에는 넣지 않았다** — 공개 장소(논문 부록·Zenodo 등)·라이선스는 연구자 결정. 교수 이름·KCI 식별자 공개 범위도 결정 사항(현재는 전부 포함).
- **계보 강건성 — 서울대 계보 지배 검토 (2026-11-01, 연구자 「돌려」)**: `수집도구\lineage_robustness.py --tables <공개_파생표_20261031> --repo <kcritic.kr> --out <폴더>`(시스템 py, 4분; **입력은 공개 파생표만** — 파생표만으로 재계산되는지 확인하는 뜻) → OneDrive `참고문헌_구축\학풍_계보강건성_20261101\`(계보강건성_보고서.md · lineage_robustness.json · lineage_robustness_results.csv). 쌍 분포: 서울대 뿌리 계보(정한모·전광용·신범순·박성창·조동일)가 논문 25%·형제 41%·삼촌 82%·조부 56%(정한모 91/179). 세 분석: A 논문·교수·뿌리 삼방향 클러스터 SE(논문이 뿌리에 중첩돼 V(교수)+V(뿌리)−V(교수×뿌리)로 줄어 삼촌 t 가 7.0→13.9 처럼 커질 수 있음 — 두 SE 중 큰 쪽을 쓸 것) + 뿌리 단위 와일드 클러스터 부트스트랩 499회 · B 정한모/전광용/둘/최동호/서울대 뿌리 전부 빼기(빼고 다시 잔차화) · C 서울대 안/밖 층화 + 상호작용 차이 검정. **결과**: 지도교수·형제·삼촌은 어느 계보를 빼도 같거나 커지고(서울대 전부 제외: +0.0255·+0.0170·+0.0138, 삼촌 쌍 354) 층화 차이 |t|≤1.5, 다섯 표현 모두 → 서울대 계보에 기대지 않음. 계보 밖 같은 대학 0 도 불변. **조부는 bge 에서 정한모 계보에 집중**: 정한모 제외 +0.0152→+0.0070(88쌍, t 1.9), 서울대 밖 +0.0073(78쌍), 와일드 p 0.15; lsa300(+0.0128, t 2.6)·lda50(+0.0696, t 3.4)은 서울대 밖에서도 남음 → 「3세대 전승은 어휘·토픽 표현에서는 계보를 가리지 않으나 임베딩에서는 정한모 계보가 이끄는 보통 수준 증거」로 쓴다(민감도 분석의 「판정 상태에 민감」과 합쳐 가장 약한 결론). 임베딩 다양화(다국어 e5 + 한국어 특화 모델, ONNX 또는 새 venv)는 아직 안 함.
- **임베딩 모델 다양화 (2026-11-01, 연구자 「임베딩 시작」)**: bge-m3 와 계열이 다른 세 모델로 **같은 문서·간선·묶음**을 다시 임베딩해 같은 검정을 돌렸다. 모델은 HF ONNX 변환본을 저장소·OneDrive 밖 로컬 `C:\Users\hgohg\models\` 에 둠: jhgan/ko-sroberta-multitask(한국어 특화, 768d, 학습 길이 128 이지만 512 로 넣음) · Xenova/multilingual-e5-large(1024d, 대칭 비교라 모두 'query: ' 접두사) · Xenova/paraphrase-multilingual-mpnet-base-v2(768d); 모두 마스크 평균 풀링 + L2. 스크립트 `수집도구\embed_variants.py`: `build-texts`(시스템 py — hanja 필요; prelim_similarity.py 규칙으로 문서를 다시 만들고 원본 vectors.npz 의 prof_ndocs·docs_year·prof_docs.csv 제목과 **assert 로 일치 확인**, 교수 문서 6,435·논문 1,334·초록 5,352; 출력 texts.jsonl.gz 는 초록 포함 **비공개**) → `embed`(ocr_train venv `…\작업도구\ocr_train\venv\Scripts\python.exe`, onnxruntime-gpu 1.22 — **`import torch` 를 onnxruntime 보다 먼저 해야 CUDAExecutionProvider 가 뜬다**, 안 하면 조용히 CPU 로 떨어짐; GPU 로 모델당 35~103초) → stat_review 전체·확정 → `report`. 결과 OneDrive `참고문헌_구축\학풍_임베딩다양화_20261101\`(임베딩다양화_보고서.md 「결과 요약」, 모델별 vectors.npz·검증·검증_확정). **결과**: 일곱 표현(bge·e5·ko-sroberta·MPNet·tfidf·lsa·lda) 모두 지도교수 > 형제 ≳ 삼촌 > 조부 ≫ 계보 기타 0, 계보 밖 같은 대학 ≈ 0 (임베딩 넷은 표준화 +0.01~+0.03·Holm ≥ 0.14; tfidf·lsa 만 +0.07~+0.09 유의). 표준화 지도교수 bge +0.89 · e5 +0.91 · ko-sroberta +0.90 · MPNet +0.43(패러프레이즈용이라 전반적으로 약하나 순서 같음). **조부**: 간선 전체 7개 중 6개 Holm 유의(MPNet 만 ×), 확정만 4개(e5·ko-sroberta·lsa·lda ○, bge·MPNet·tfidf ×); ko-sroberta 가 가장 강함(+0.67 SD, 확정만 t 4.8) → 「있으되 표현·판정 상태에 민감한 보통 수준 증거」, bge 의 「정한모 계보 주도」는 8표현 강건성 재실행(`lineage_robustness.py --tables 공개_파생표_20261101 --reps …8개` → `학풍_계보강건성_20261101/8표현/`)으로 재검토했다: 지도교수·형제·삼촌·같은 대학 0 은 여덟 표현 모두 서울대 계보를 빼도 불변(층화 차이 |t| ≤ 1.8); **조부는 서울대 밖 78쌍에서 ko-sroberta(t 2.7)·lsa·lda 유의, bge·e5·tfidf·MPNet 비유의** → 「3세대 전승은 7표현 중 3개에서 서울대 밖에서도 유의, 전체적으로 보통 수준」으로 쓴다. 전승 방향(학위 전 10년 창 > 후 10년 > 위약 +11년)도 모델 무관. 절대 계수는 공간마다 달라(e5 는 1/4) 표준화·t 로만 비교. 공개 파생표는 세 표현을 더해 `공개_파생표_20261101\` 로 다시 냈다(`export_derived_tables.py --extra 이름=폴더,…`, regression_results 147행, 쌍 표에 resid_/raw_ 열 6개 추가; 기존 표현 수치는 20261031판과 같음). 논문 초안은 별도 세션 paper-draft(2026-11-01 시작)가 쓰고 있다 — 산출물 `참고문헌_구축\논문초안_20261101\`.
- **논문 그림 (2026-11-01, 연구자 「그림 시작」)**: `수집도구\make_figures.py --base <KCI_현대문학_2000-2026> [--tables 공개_파생표_20261101] [--out 그림_YYYYMMDD]`(시스템 py, matplotlib 3.11, 글꼴 Malgun Gothic — Noto Sans KR 은 이 PC 에 Thin 만 있어 가늘고, Malgun 에는 U+2212 가 없어 라벨은 하이픈) → OneDrive `참고문헌_구축\그림_20261101\`: 그림 1 관계별 표준화 효과 포레스트(7표현×5관계, 교수 부트스트랩 95%, 확정 간선만 = 빈 마름모) · 그림 2 전승 방향(창별 평균 잔차, 학위 전 10년 창=100 지수, bge 강조+띠, 다른 6표현 회색) · 그림 3 제자 궤적(지도교수 각인·학위 전 주제·재직 대학 동료, 95%) · 그림 4 지도교수 식별(같은 대학 교수 중 순위 분포 vs 우연 기대선; 1위 40.3% vs 16.9%, 1,311편) · 그림 7 계보×토픽 히트맵(뿌리 10×토픽 11, 파랑 순차 램프). 각 그림 SVG+PNG(300dpi)+`_data.csv` 표 쌍둥이, `그림_캡션.md` 에 캡션·출처. 색은 dataviz 기본 범주형 1~3(파랑=임베딩/본 분석, 주황=어휘/둘째, 청록=셋째; 검증기 통과, 청록은 대비 경고라 표 쌍둥이로 보완). 그림 5(교수 블록)·6 은 만들지 않음. 입력은 공개 파생표 20261101판 + edges_similarity.csv(순위) + lineage_topics_k50.csv.
- **학풍(學風) 탭 (2026-11-02, 연구자 「만들기 시작」)**: 학술연구 탭 줄에 「학맥」 다음 「학풍」(`school.html` / `school.js` / `school.css`, `lineage.html` 정적 탭·`thesis-browse.js` `tabs()`·`lineage.js` 상세의 「학풍(연구 주제) →」 링크). 데이터 `site/data/school-style-public.json`(0.9MB) ← `수집도구\export_school_style.py --base <KCI_현대문학_2000-2026> --repo <kcritic.kr> [--tables 공개_파생표_20261101]`(시스템 py, sklearn). 담은 것: 교수 324명(KCI 묶음, 소속·계보 뿌리·박사 연도·토픽 상위 5·2차원 좌표·표본 안 지도논문 수·지도교수 묶음 1위 비율·잔차 유사도 4종) + 표본 밖 상위 지도교수 32명 가상 노드(`source: descendants`, 표본 안 제자 교수 평균 위치, 토픽은 계보 논문 평균) · 박사논문 1,334편(제목·연도·대학·지도교수·RISS 번호·좌표·토픽·지도교수 묶음 순위) · 교수 간 간선 178(3단계) · 계보 27(θ 50) · 토픽 50 상위 낱말 · 관계 효과(7표현 전체 + bge 확정만). **넣지 않은 것**: 벡터·초록·본문·cretId·KAC(정규식 assert). 좌표 = 교수·논문 벡터에서 **유형별 평균을 뺀 뒤** PCA 50 → t-SNE(코사인, seed 42) — 빼지 않으면 교수 묶음과 논문이 유형만으로 갈라진다. 투영 점검 `projection_check`: 2차원 최근접 교수 = 지도교수 1.0%(우연 0.3%), 순위 중앙값 94/324 — 원 공간에서도 지도교수 1위는 4%뿐이라 지도교수 효과는 '최근접'이 아니라 평균적 쏠림이고 화면 안내문에 그렇게 적었다(교수를 누르면 제자 논문으로 선). 화면: 색 기준(주제 묶음 = 교수 주된 토픽 상위 7 + 기타 / 계보 뿌리 상위 7 / 대학 상위 7, dataviz 8색 = lineage.js PALETTE) · 교수·논문 지도(휠·드래그, 점 클릭 → 상세: 토픽 막대·학풍 지표 타일·지도논문 목록·교수 간 간선·학맥/학교·소속 링크) · 계보×토픽 히트맵(파랑 순차, 행 클릭 = 지도 강조) · 관계 효과 표(표준화, n.s. 표시) · CSV. 테스트 `tests/school-style.test.cjs`(허용 필드 목록·금지 문자열·참조 무결성·탭 링크). 미리보기는 `.claude/launch.json` `static`(python http.server 8765); `/theses/` 탭 줄은 다른 Worker 라 로컬에서 안 보인다. **아직 미커밋·미배포**.
- **상단 검색에 학술연구 (2026-11-02, 연구자 「맨 상단 검색이 현장비평만 되는데 학술검색도 같이, 단어 임베딩에서도」)**: 두 머리글(`kc.js` `globalSearch()` · `kc-shell.js` `search()`, 같은 동작 유지)의 제안 상자에 「박사논문 (학술연구)」 묶음(`site/data/research-public.json` 1,888편을 처음 입력 때 한 번 받아 제목·저자·지도교수 이름 부분 일치 4건 → `/study.html?type=thesis&id=<RISS control_no>&q=`)을 더하고, 입력이 600ms 멈추면 `/theses/api/search`(별도 Worker, bge-m3 뜻 검색, POST {query}) 상위 4건을 「학술연구 · 뜻으로 찾은 논문」 묶음으로 덧붙인다(질문별 캐시, 실패·404 는 조용히 생략 — 로컬 http.server 에서는 POST 가 501 이라 안 보임). **Enter(선택 없음)와 「전체 검색」 첫 항목은 통합검색 `/search.html?q=`**(현장비평 + 학술연구 뜻 검색)로, 둘째 항목이 예전 `explore.html?p=essays&q=`. 안내문 「글·인물·개념어·박사논문 찾기」(좁은 화면 「이름·논문 찾기」). 응답에서 쓰는 것은 제목·저자·연도·RISS 번호뿐(초록·본문 없음). 테스트 `tests/header-search.test.cjs`. 통계(`kcStat('search')`)는 explore·search 로 가는 전체 검색 링크는 세지 않는다(그 화면이 센다). **미커밋·미배포**.
