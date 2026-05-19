# CLAUDE.md — AI 어시스턴트 작업 지침서

이 문서는 본 프로젝트에서 AI 어시스턴트(Claude Code, Cursor, Continue 등)가 작업할 때 따를 가이드. VS Code의 AI 도구가 이 파일을 컨텍스트로 자동 로드함.

---

## 0. 프로젝트 개요

### 목표
한국 비평사를 노드-엣지 네트워크로 구축. 비평가가 어떤 작가를 비평할 때 어떤 이론가의 개념을 활용했는가를 추적 가능하게 만든다.

### 결과물
- TEI XML 형식 비평글 코퍼스 (`essays/`)
- 정적 웹사이트 (CETEIcean 기반 렌더링)
- Wikidata / 국립중앙도서관 LOD / ISNI 연결

### 도구 스택
- 편집: VS Code + Red Hat XML 확장
- 검증: `schema/korean-critique-schema.xsd` (TEI 기반)
- 버전관리: Git
- 렌더링: CETEIcean (브라우저 내 TEI 처리)
- 호스팅: Cloudflare Pages (무료)

---

## 1. 데이터 모델 — TEI 기반

### 왜 TEI인가
이 프로젝트는 단순 메타데이터(누가 누구를 비평) 수준을 넘어, **비평 텍스트 자체를 의미적으로 마크업**한다. 어떤 문장에서 어떤 인물이 언급되고, 어떤 인용이 어떤 분석축에 연결되며, 평가 태도가 긍정/비판/중립 중 무엇인지까지 데이터로 기록.

### 핵심 엔티티 (TEI 요소)

| 요소 | 용도 | 주요 속성 |
|---|---|---|
| `<persName>` | 인물 (비평가/작가/이론가) | `xml:id`, `ref`, `role` |
| `<title>` | 작품·저작 | `level`(m/a/j), `type`, `ref` |
| `<term>` | 개념·용어·사조 | `type`, `xml:id`, `ref` |
| `<quote>` | 인용 | `type`, `source`, `genre`, `ana` |
| `<interp>` | 비평 태도/해석 | `value`, `ana` |
| `<ref>` | 외부 참조 | `target` |
| `<orgName>` | 기관·단체 | `xml:id`, `ref` |

### 핵심 관계 (속성 기반)

- `persName/@role` — 인물의 문학사적 직능 (critic, poet, scholar 등)
- `title/@level` — m=단행본, a=수록 글, j=저널
- `quote/@type` — direct, indirect, paraphrase 등
- `interp/@value` — affirmative, neutral, critical
- `interp/@ana` — 분석 기준 카테고리 ID 참조 (필수)
- `ref` 속성 — 외부 URI (Wikidata, NLK, ISNI 등) 또는 내부 `#xml-id`

---

## 2. 인코딩 패턴 (가장 중요)

### 패턴 1: 최초 정의 + 이후 참조

처음 등장하는 인물에 `xml:id`와 외부 `ref`(URI)를 모두 부여:

```xml
<persName xml:id="p-habermas" 
          ref="https://www.wikidata.org/wiki/Q76509" 
          role="foreigner scholar">위르겐 하버마스</persName>
```

같은 문서 내 이후 모든 언급은 `ref="#xml-id"`:

```xml
<persName ref="#p-habermas">하버마스</persName>
```

**표기가 달라도 같은 `xml:id`로 묶이면 같은 노드.** 이게 핵심.

### 패턴 2: 비평 태도 명시

단순히 누구를 언급한 것과 **그 언급의 태도**를 구분.

```xml
<interp value="affirmative" ana="#modern-self">윤리적 주체성을 발명해야 했다</interp>
<interp value="critical" ana="#public-sphere">공론장이 부재한 조건</interp>
```

`@ana`는 `classDecl`의 `taxonomy/category` ID 참조 (필수).

### 패턴 3: 인용 다층 메타데이터

```xml
<quote type="direct" 
       genre="poet" 
       source="윤동주, 「자화상」, 1939" 
       ana="#modern-self">우물 속에는 달이 밝고...</quote>
```

인용 하나가 직접인용 / 시 장르 / 출처 / 분석축 연결까지 동시에 운반.

### 패턴 4: ID 명명 규칙

- 인물: `p-이름` (`p-yun-dongju`, `p-habermas`, `p-kim-uchang`)
- 개념: `t-개념명` (`t-public-sphere`, `t-modern-self`)
- 구획: `div-목적` (`div-intro`, `div-arg-1`, `div-conc`)
- 문장: `s-번호` (`s-1`, `s-2` — 옵션)

영문 슬러그 사용 (URL 호환).

---

## 3. 파일 명명 및 구조

### 비평글 파일명
`비평가-슬러그_대상-슬러그_연도.xml`

예시:
- `kim-uchang_yun-dongju_1985.xml`
- `baek-nakcheong_kim-suyoung_1973.xml`
- `kim-hyun_yi-sang_1980.xml`

같은 비평가·대상·연도 조합 여러 글: 끝에 `a`, `b` 추가

### XSD 참조 헤더 (모든 비평글 파일 첫 줄)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<?xml-model href="../schema/korean-critique-schema.xsd" type="application/xml"
            schematypens="http://www.w3.org/2001/XMLSchema"?>
```

이 줄 있으면 VS Code XML 확장이 자동 검증.

---

## 4. TEI 문서 구조 (필수)

```xml
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>...</titleStmt>          <!-- 제목·저자·책임 -->
      <publicationStmt>...</publicationStmt>  <!-- 발행 정보 -->
      <sourceDesc>                        <!-- 원 출처 (필수, 1+) -->
        <biblStruct>                      <!-- 구조 서지 -->
          <analytic>...</analytic>        <!-- 글 단위 -->
          <monogr>...</monogr>            <!-- 책 단위 -->
        </biblStruct>
      </sourceDesc>
    </fileDesc>
    <encodingDesc>
      <editorialDecl>...</editorialDecl>  <!-- 편집 원칙 -->
      <tagsDecl>...</tagsDecl>            <!-- 태그 사용 통계 -->
      <classDecl>                         <!-- 분류 체계 -->
        <taxonomy xml:id="...">
          <category xml:id="...">
            <catDesc>설명</catDesc>
          </category>
        </taxonomy>
      </classDecl>
    </encodingDesc>
  </teiHeader>
  
  <text>
    <body>
      <div type="introduction">           <!-- DivTypeEnum 값만 허용 -->
        <head>제목 (선택)</head>
        <p>
          <s>마크업된 문장.</s>          <!-- 텍스트는 모두 <s> 안에 -->
        </p>
      </div>
      <!-- 더 많은 div... -->
    </body>
  </text>
</TEI>
```

### 자주 빠뜨리는 것
- `<body>`는 **필수**, 최소 1개 `<div>` 필요
- 모든 본문 텍스트는 `<s>` 안에 (직접 `<p>` 안에 텍스트 두면 마크업 위치 잡기 어려움)
- `<interp>`의 `@ana`는 **필수** 속성
- 순서: `teiHeader` → `text`, 그 안 `front` → `body` → `back`

---

## 5. 외부 LOD 연결 가이드

### 검색 순서

**한국 인물 (비평가/작가)**:
1. 국립중앙도서관 LOD 검색 (https://lod.nl.go.kr)
2. Wikidata에 한국어 라벨로 검색
3. ISNI는 Wikidata 페이지의 Identifiers 섹션에서

**외국 이론가**:
1. Wikidata 검색 (https://wikidata.org)
2. 페이지 하단 Identifiers에서 ISNI, GND 등 확인
3. NLK에 한국어 표기로 별도 검색

### 인코딩 시 사용

`ref` 속성에 전체 URI 박아넣기:

```xml
<persName xml:id="p-yun-dongju"
          ref="https://www.wikidata.org/wiki/Q489582"
          role="poet">윤동주</persName>
```

여러 URI 필요하면 공백으로 구분:
```xml
ref="https://www.wikidata.org/wiki/Q489582 https://lod.nl.go.kr/page/KAC199611269"
```

---

## 6. AI 작업 프롬프트 모음

### 비평글 메타데이터 추출 + TEI 인코딩
```
이 비평글 텍스트를 읽고 schema/korean-critique-schema.xsd에 따라 TEI XML로 
인코딩해줘. 파일명 규칙은 CLAUDE.md 섹션 3 참조. 

다음을 마크업할 것:
- 모든 인물명 → <persName> (최초는 xml:id + ref 부여, 이후 #참조)
- 작품명 → <title> (level/type 적절히)
- 핵심 개념 → <term>
- 인용 → <quote> (type/genre/source/ana)
- 평가/판단 → <interp> (value/ana)

새 인물의 xml:id 사용 전 essays/ 내 다른 파일들 검색해서 기존 id 있는지 확인.

[비평글 텍스트]
```

### 일관성 검사
```
essays/ 폴더 전체 스캔해서:
1. 같은 인물이 다른 xml:id로 정의된 경우 (예: p-habermas vs p-jhabermas)
2. xml:id 정의 없이 #참조만 있는 경우 (broken reference)
3. <interp>에 @ana 빠진 경우 (스키마 위반)
4. ref 속성에 잘못된 URI 형식

각 이슈를 docs/inconsistencies.md 에 정리.
```

### 외부 ID 일괄 조회
```
essays/ 내 모든 파일을 스캔해서 ref 속성 없는 <persName>들을 추출.
각각 Wikidata에서 검색해서 적절한 Q-번호 ref 추가 제안.
확실하지 않으면 추가 말고 따로 보고.
```

### 그래프 데이터 추출
```
essays/ 내 모든 TEI XML을 파싱해서 site/data.json 생성:
- nodes: [{id, type, label, refs}] — 모든 persName, title, term의 unique 집합
- edges: [{source, target, type, file}] — 비평글에서 추출된 관계
  - critic_of (비평가 → 비평글)
  - subject_of (비평글 → 대상 인물)
  - uses_theory_of (비평글 → 이론가)
  - cites (비평글 → 인용된 글)

Cytoscape.js 호환 JSON 형식으로.
```

### 절대 하지 말 것 (AI 행동 규칙)
- **인물 평전/개념 정의 자동 생성 금지** — 사실 오류 위험. stub 노트만 생성하고 본문은 비워둘 것.
- **표기 임의 변경 금지** — 한 번 정해진 xml:id는 절대 변경 안 됨. AI가 "더 표준적인 표기로 바꿔드릴까요"는 NO.
- **추측 ref 채우기 금지** — Wikidata Q번호 확실하지 않으면 빈 값으로 둘 것.
- **스키마 위반 시 강행 금지** — XSD 검증 실패하면 사용자에게 보고하고 수정안 제안.

---

## 7. 워크플로우

### 새 비평글 추가 표준 절차

1. `essays/` 폴더에 새 XML 파일 생성 (명명 규칙 준수)
2. 기존 비평글에서 헤더 복사 후 메타데이터만 수정
3. 본문 인코딩:
   - 처음 등장하는 인물: `xml:id` + `ref` 부여
   - 이미 다른 파일에서 정의된 인물: 같은 `xml:id` 사용 (`#참조`)
4. VS Code XML 확장이 실시간 검증 — 에러 표시 해결
5. Live Server로 미리보기 (`site/index.html`)
6. Git commit

### 새 인물 처음 추가 시 작업

해당 인물이 첫 등장하는 비평글에서 정의. 일관된 `xml:id` 부여.

외부 ID 조회는 batch로 처리해도 OK — 일단 인코딩 진행하고, 주기적으로 "외부 ID 일괄 조회" 프롬프트 돌리기.

---

## 8. 데이터 품질 원칙

1. **검증 통과 = 최소 기준** — XSD 검증 실패한 파일은 절대 커밋 금지
2. **xml:id 일관성** — 같은 인물·개념은 어디서나 같은 id
3. **빈 값 OK, 잘못된 값 NO** — 모르면 ref 비워둘 것
4. **점진적 확장** — 처음부터 모든 인물·개념 정의하려 하지 말 것. 50개 인코딩하며 패턴이 보이면 그때 정비
5. **삭제보다 마킹** — 잘못된 인코딩은 삭제 말고 `<note type="todo">` 추가

---

## 9. 자주 묻는 결정사항

**Q: 같은 인물이 다른 글에서 다른 역할인 경우 (예: 비평가가 시인이기도 함)?**
A: `role` 속성에 공백으로 여러 역할 나열. `role="critic poet"`.

**Q: 한 비평글이 여러 작가를 동시에 비평?**
A: 정상. 본문 내에서 각각 `<persName ref="#..."/>`로 표시되면 자연스럽게 다중 관계 형성.

**Q: 직접 인용은 아니지만 의역인 경우?**
A: `<quote type="paraphrase">` 또는 `<quote type="indirect">`.

**Q: 출처 미상의 인용?**
A: `source` 속성 비워두기. 본인 메모는 `<note type="todo">출처 확인 필요</note>`.

**Q: 한자 표기 함께 보여주고 싶을 때?**
A: `<persName>김우창<note type="hanja">金禹昌</note></persName>` 또는 별도 `<note>` 안에.

---

## 10. 향후 로드맵

| Phase | 목표 | 시점 |
|---|---|---|
| 1 | 데이터 축적 (10개 비평글 인코딩) | 지금 ~ 2-3주 |
| 2 | 사이트 배포 (Cloudflare Pages + 도메인) | 데이터 10개 도달 후 |
| 3 | 그래프 시각화 페이지 추가 (Cytoscape) | 30개 도달 후 |
| 4 | 분석 (시기별·이론별 패턴 발견, 새 비평글에 반영) | 50개 도달 후 |
| 5 | 본격 LOD 발행 (RDF 변환, SPARQL endpoint) | 100개 + 선택 |

---

## 11. 참고 자료

- TEI Guidelines: https://tei-c.org/release/doc/tei-p5-doc/en/html/
- CETEIcean (TEI 브라우저 렌더링): https://github.com/TEIC/CETEIcean
- Wikidata: https://www.wikidata.org
- 국립중앙도서관 LOD: https://lod.nl.go.kr
- ISNI: https://isni.org
- 본 프로젝트 인코딩 가이드: `docs/encoding_guide.md`

---

*이 지침서는 living document. 새 결정사항·예외 케이스는 즉시 추가할 것. AI에게 시키는 작업의 일관성은 이 문서의 명시성에 비례한다.*
