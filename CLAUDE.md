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
│   ├── data/
│   │   ├── graph.json       ← build.py 출력: 관계망 데이터
│   │   ├── critics.json     ← build.py 출력: 비평가 목록 데이터
│   │   └── bibliography.json ← convert_phd.py 출력: 선행연구 데이터
│   └── graph.html           ← Cytoscape.js 관계망 시각화
├── index.html               ← 비평글 목록 (메인)
├── critics.html             ← 비평가 목록 탭
├── research.html            ← 선행연구 탭
├── style.css                ← 공유 스타일 (반응형 포함)
├── build.py                 ← TEI XML → HTML + JSON 빌드 스크립트
├── convert_phd.py           ← 박사논문 xlsx → bibliography.json 변환
├── wrangler.jsonc           ← Cloudflare Workers 배포 설정
├── .gitignore
└── CLAUDE.md                ← 이 파일
```

---

## 3. 사이트 구조 (탭 4개)

| 탭 | 파일 | 설명 |
|---|---|---|
| 비평글 | `index.html` | 수록 비평글 카드 목록 |
| 비평가 | `critics.html` | 비평가 카드 그리드 → 클릭 시 프로필 페이지 |
| 관계망 | `site/graph.html` | Cytoscape.js 네트워크 시각화 |
| 선행연구 | `research.html` | 박사·KCI 논문 작가 중심 검색 |

### 네비게이션 경로 (파일 위치별)
- 루트 페이지(`index.html`, `critics.html`, `research.html`): `site/graph.html`, `research.html`, `critics.html`
- `site/essays/*.html`: `../../index.html`, `../../critics.html`, `../graph.html`, `../../research.html`
- `site/critics/*.html`: `../../index.html`, `../../critics.html`, `../graph.html`, `../../research.html`
- `site/graph.html`: `../index.html`, `../critics.html`, `graph.html`, `../research.html`

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
- `site/data/graph.json` — 관계망 노드/엣지 데이터
- `site/data/critics.json` — 비평가 목록 데이터

### 박사논문 데이터 변환

```powershell
cd ..   # 온톨로지/ 디렉터리에서
py convert_phd.py
```

- 입력: `200805_현대문학_박사논문.xlsx` (1,528건)
- 출력: `critic-ontology/site/data/bibliography.json`
- `WRITER_NODE_MAP` 에 작가명 → 노드 ID 매핑 추가하면 노드 연결 확장

### 새 비평글 추가 절차

1. 원문 텍스트를 `essays/{stem}.txt` 저장
2. `essays/{stem}.xml` 생성 및 TEI 인코딩
3. `py build.py` 실행
4. `index.html` 에 essay-card 추가
5. Git diff 확인 (essays/ 제외) → push

---

## 5. graph.json 형식

```json
{
  "nodes": [
    { "id": "p-kim-uchang", "label": "김우창", "type": "critic",
      "ref": "https://www.wikidata.org/wiki/Q12498425", "degree": 4 },
    { "id": "kim-uchang_yun-dongju_1985", "label": "윤동주의 시와 근대적 자아",
      "type": "essay", "year": "1985", "degree": 3 }
  ],
  "edges": [
    { "source": "p-kim-uchang", "target": "kim-uchang_yun-dongju_1985",
      "type": "wrote", "weight": 1 }
  ]
}
```

- `node.degree` — 연결 엣지 수 합산 (weight 반영). 노드 크기에 반영
- `edge.weight` — 같은 source→target 쌍 반복 횟수. 엣지 굵기에 반영
- `node.type`: `critic` | `writer` | `theorist` | `essay`
- `edge.type`: `wrote` | `subject_of` | `uses_theory`

---

## 6. bibliography.json 형식

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

- 노드 크기: `degree` 비례 (56~120px). essay 노드 고정 110×56
- 엣지 굵기: `weight` 비례 (1.5~6px)
- 노드 클릭: 사이드패널 (데스크탑) / 하단 드로어 슬라이드업 (모바일 768px 이하)
- 비평가 노드 클릭 시 → "비평가 프로필 보기" 링크 포함
- 노드 hover: 연결 강조, 나머지 페이드
- 필터: 비평가/작가/이론가/비평글 유형별 토글

### 색상 시스템
| 유형 | 색상 |
|---|---|
| 비평가 (critic) | #c9986a |
| 작가 (writer) | #6a9bc9 |
| 이론가 (theorist) | #9a7ac9 |
| 비평글 (essay) | #c8c8a8 |

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

---

## 12. AI 행동 규칙

- **원문 텍스트를 HTML에 포함하는 코드 작성 금지**
- **essays/*.xml, *.txt 를 git staging에 추가하는 명령 실행 금지**
- 인물 xml:id 는 한 번 정해지면 변경 금지
- Wikidata ref 추측 채우기 금지 — 모르면 빈값
- build.py 수정 후 반드시 `py build.py` 테스트
- convert_phd.py 수정 후 반드시 `py convert_phd.py` 테스트
- PowerShell에서 한글 포함 git commit 메시지는 here-string 파싱 오류 발생 → ASCII 메시지 사용

---

## 13. 외부 연결 데이터

- 한국 인물: 국립중앙도서관 LOD (https://lod.nl.go.kr) → Wikidata → ISNI
- 외국 이론가: Wikidata (https://wikidata.org) 우선
- `ref` 속성에 전체 URI. 여러 URI는 공백 구분

---

## 14. 스택 요약

| 목적 | 도구 |
|---|---|
| 인코딩 | VS Code + Red Hat XML + `korean-critique-schema.xsd` |
| 빌드 | `build.py` (Python 표준 라이브러리만) |
| 데이터 변환 | `convert_phd.py` (openpyxl) |
| 관계망 시각화 | Cytoscape.js 3.28 |
| 호스팅 | Cloudflare Workers (무료) |
| 비용 | 도메인 갱신비만 |
| LOD | Wikidata + 국립중앙도서관 LOD |
