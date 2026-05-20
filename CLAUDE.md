# CLAUDE.md — 한국 비평사 온톨로지 프로젝트 지침

이 파일은 AI 어시스턴트가 이 프로젝트에서 작업할 때 따를 규칙과 구조를 설명한다.

---

## 0. 프로젝트 목표

한국 비평사를 노드-엣지 네트워크로 구축. "김우창이 윤동주를 비평할 때 하버마스를 활용했다"는 관계를 TEI XML로 인코딩하고, 웹 시각화로 탐색 가능하게 만든다.

핵심 관계: **비평가 → 비평글 → 작가(비평 대상) / 이론가(개념 활용)**

---

## 1. 보안 규칙 (절대 위반 금지)

- `essays/*.xml` 및 `essays/*.txt` 는 `.gitignore` 에 등록되어 있음 — **절대 Git에 커밋/푸시하지 말 것**
- 이 파일들은 저작권 보호 원문. OneDrive/로컬에만 존재해야 함
- `site/essays/*.html` 은 메타데이터만 담으며 GitHub에 올라감 (원문 텍스트 없음)
- `build.py` 는 원문 본문을 HTML에 포함시키지 않음. 위반 시 즉시 수정

---

## 2. 실제 폴더 구조

```
critic-ontology/
├── essays/               ← 로컬 전용 (gitignored)
│   ├── *.xml             ← TEI XML 원문 인코딩
│   └── *.txt             ← 원문 텍스트 (XML 작업 전 저장)
├── schema/
│   └── korean-critique-schema.xsd
├── site/
│   ├── essays/           ← build.py 출력: 메타데이터 HTML (GitHub에 올라감)
│   │   └── *.html
│   ├── data/
│   │   └── graph.json    ← build.py 출력: 그래프 데이터
│   └── graph.html        ← Cytoscape.js 시각화 페이지
├── index.html            ← 메인 페이지 (비평글 목록)
├── style.css             ← 공유 스타일
├── build.py              ← TEI XML → 메타데이터 HTML + graph.json 변환
├── wrangler.jsonc        ← Cloudflare Workers 배포 설정
├── .gitignore
└── CLAUDE.md             ← 이 파일
```

---

## 3. 빌드 워크플로우

```
essays/*.xml  →  build.py  →  site/essays/*.html
                           →  site/data/graph.json
```

**build.py 실행:**
```powershell
cd critic-ontology
py build.py
```

build.py가 하는 일:
1. `essays/*.xml` 전체 파싱
2. 각 XML에서 메타데이터 추출: 서지정보, 인물(비평가/작가/이론가), 비평 대상, 활용 이론가, 언급 작품, 개념어, 인용 출처
3. 원문 본문은 **일절 추출하지 않음**
4. `site/essays/{stem}.html` 생성 (저작권 고지 포함)
5. `site/data/graph.json` 생성 (노드 + 엣지 + weight/degree)

---

## 4. graph.json 형식

```json
{
  "nodes": [
    { "id": "kim-uchang_yun-dongju_1985", "label": "윤동주의 시와 근대적 자아",
      "type": "essay", "year": "1985", "degree": 3 },
    { "id": "p-habermas", "label": "위르겐 하버마스",
      "type": "theorist", "ref": "https://www.wikidata.org/wiki/Q76509", "degree": 1 }
  ],
  "edges": [
    { "source": "p-kim-uchang", "target": "kim-uchang_yun-dongju_1985",
      "type": "wrote", "weight": 1 },
    { "source": "kim-uchang_yun-dongju_1985", "target": "p-habermas",
      "type": "uses_theory", "weight": 1 }
  ]
}
```

- `node.degree` — 연결 엣지 수 합산 (weight 반영). 노드 크기에 반영됨
- `edge.weight` — 같은 source→target 쌍이 여러 비평글에서 반복될 때 증가. 엣지 굵기에 반영됨
- `node.type`: `critic` | `writer` | `theorist` | `essay`
- `edge.type`: `wrote` | `subject_of` | `uses_theory`

---

## 5. 시각화 (site/graph.html)

Cytoscape.js 기반. 기능:
- 노드 크기: `degree` 비례 (최소 56px, 최대 120px). essay 노드는 고정 110×56
- 엣지 굵기: `weight` 비례 (최소 1.5px, 최대 6px)
- 노드 클릭: 사이드패널에 관련 비평글/인물 목록 표시
- 노드 hover: 연결된 노드/엣지 강조, 나머지 페이드
- 필터 버튼: 비평가/작가/이론가/비평글 유형별 토글
- 색상: 비평가 #c9986a, 작가 #6a9bc9, 이론가 #9a7ac9, 비평글 #c8c8a8

---

## 6. 배포

Cloudflare Workers (무료 티어). `wrangler.jsonc`의 `assets.directory = "."` 로 repo 루트 전체를 정적 파일로 서빙.

```
GitHub push → Cloudflare Workers (wrangler 배포)
```

---

## 7. TEI XML 인코딩 패턴

### 파일명 규칙
`비평가-슬러그_대상-슬러그_연도.xml` (및 동일 이름 `.txt`)

예: `kim-uchang_yun-dongju_1985.xml`, `kim-uchang_yun-dongju_1985.txt`

### 새 비평글 추가 절차
1. 원문 텍스트를 `essays/{stem}.txt` 로 저장
2. `essays/{stem}.xml` 생성 및 TEI 인코딩
3. `py build.py` 실행 → HTML + graph.json 자동 갱신
4. `index.html` 에 essay-card 추가
5. Git commit (essays/ 제외 확인 후 push)

### 핵심 인코딩 패턴

**인물 최초 정의 (xml:id + ref 필수):**
```xml
<persName xml:id="p-habermas"
          ref="https://www.wikidata.org/wiki/Q76509"
          role="foreigner scholar">위르겐 하버마스</persName>
```

**이후 참조:**
```xml
<persName ref="#p-habermas">하버마스</persName>
```

**비평 태도 마크업:**
```xml
<interp value="affirmative" ana="#modern-self">윤리적 주체성을 발명해야 했다</interp>
```

**인용:**
```xml
<quote type="direct" genre="poet"
       source="윤동주, 「자화상」, 1939"
       ana="#modern-self">우물 속에는 달이 밝고...</quote>
```

### role 속성 값 → build.py 분류
| role 값 | 분류 |
|---|---|
| `critic` | 비평가 (비평글 저자) |
| `poet`, `novelist`, `writer` | 작가 (비평 대상) |
| `scholar`, `foreigner scholar` | 이론가 (이론 활용) |

### build.py 이론가 추출 로직
- `role`에 `scholar`가 포함되고
- 비평 대상 작가(`subjects`)에 포함되지 않고
- 비평가 본인(`author_id`)이 아닌 인물 → `theorist`

---

## 8. AI 행동 규칙

- **원문 텍스트를 HTML에 포함시키는 코드 절대 작성 금지**
- **essays/*.xml 또는 *.txt 를 Git staging에 추가하는 명령 절대 실행 금지**
- 인물 xml:id 는 한 번 정해지면 변경 금지
- 추측으로 Wikidata ref 채우기 금지 — 모르면 빈값
- build.py 수정 후에는 반드시 `py build.py` 로 테스트

---

## 9. 외부 연결 데이터

- 한국 인물: 국립중앙도서관 LOD (https://lod.nl.go.kr) → Wikidata → ISNI
- 외국 이론가: Wikidata (https://wikidata.org) 우선
- `ref` 속성에 전체 URI. 여러 URI는 공백으로 구분

---

## 10. 스택 요약

| 목적 | 도구 |
|---|---|
| 인코딩 | VS Code + Red Hat XML + `korean-critique-schema.xsd` |
| 빌드 | `build.py` (Python 표준 라이브러리만 사용) |
| 시각화 | Cytoscape.js 3.28 |
| 호스팅 | Cloudflare Workers (무료) |
| 비용 | 도메인 갱신비만 발생 |
| LOD | Wikidata + 국립중앙도서관 LOD |
