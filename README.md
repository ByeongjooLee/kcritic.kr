# 한국 비평사 온톨로지 프로젝트

비평가 / 작가 / 이론가 / 비평글의 관계망을 TEI XML로 인코딩하고, 정적 사이트로 발행하는 프로젝트.

## 핵심 질문

이 그래프로 답하려는 것:

- 윤동주를 비평한 비평가들은 누구이며, 각각 어떤 이론적 도구를 썼는가?
- 하버마스 개념을 가장 적극적으로 활용한 한국 비평가들은 누구인가?
- 특정 작가에 대한 비평 방식이 시기별로 어떻게 변화했는가?
- 어떤 이론가들이 함께 인용되는 경향이 있는가?

## 폴더 구조

```
.
├── README.md                    # 이 파일
├── CLAUDE.md                    # AI 어시스턴트 작업 지침서
├── schema/
│   └── korean-critique-schema.xsd   # TEI 기반 스키마 (검증 기준)
├── essays/                      # 비평글 TEI XML 파일들
│   └── kim-uchang_yun-dongju_1985.xml   # 샘플
├── site/                        # 정적 사이트 (CETEIcean 렌더링)
│   ├── index.html
│   └── style.css
├── docs/
│   └── encoding_guide.md        # TEI 인코딩 작업 가이드
└── .vscode/                     # VS Code 설정 (자동 적용)
    ├── settings.json
    └── extensions.json
```

## 빠른 시작

### 1. VS Code로 폴더 열기

```bash
code /path/to/critic-ontology
```

처음 열면 권장 확장 설치 프롬프트가 떠요. 모두 설치하세요 (Red Hat XML, Live Server 등).

### 2. 샘플 비평글 확인

`essays/kim-uchang_yun-dongju_1985.xml` 열기. XML 편집기가 자동으로 `schema/korean-critique-schema.xsd`와 비교 검증해줘요. 에러 없으면 OK.

### 3. 사이트 미리보기

`site/index.html` 우클릭 → **Open with Live Server** 선택. 브라우저가 열리면서 샘플 비평글이 학술 사이트 스타일로 렌더링되는 걸 볼 수 있어요.

### 4. 새 비평글 추가

`docs/encoding_guide.md` 참조. 핵심은:

- 파일명: `비평가_대상_연도.xml` (소문자, 하이픈 또는 언더스코어)
- `essays/` 폴더에 저장
- 샘플과 같은 패턴으로 인코딩
- 저장하면 검증 자동, 사이트 자동 반영

## 발행 (배포)

GitHub 비공개 레포 → Cloudflare Pages 연결 → 가비아 도메인 DNS 설정. 전 과정 무료.

자세한 단계: `docs/deployment_guide.md` (작성 예정)

## 기술 스택

| 영역 | 도구 | 비용 |
|---|---|---|
| 편집 | VS Code + Red Hat XML | 무료 |
| 검증 | XSD (이 프로젝트의 스키마) | 무료 |
| 버전관리 | Git + GitHub | 무료 |
| 렌더링 | CETEIcean (브라우저 내 TEI 렌더) | 무료 |
| 호스팅 | Cloudflare Pages | 무료 |
| 도메인 | 가비아 (이미 보유) | 연 갱신비만 |

## 외부 LOD 연결

각 인물·작품·개념은 다음 외부 권위 데이터와 연결됨:

- **Wikidata** — 글로벌 구조화 데이터 (https://wikidata.org)
- **국립중앙도서관 LOD** — 한국 인물·서지 (https://lod.nl.go.kr)
- **ISNI** — 개인 고유 식별자 (https://isni.org)

TEI 마크업의 `@ref` 속성에 외부 URI를 그대로 박는 방식.

---

자세한 작업 방법은 [CLAUDE.md](./CLAUDE.md), 인코딩 패턴은 [docs/encoding_guide.md](./docs/encoding_guide.md) 참조.
