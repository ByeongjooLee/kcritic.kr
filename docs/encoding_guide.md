# TEI 인코딩 작업 가이드

이 문서는 본인이 새 비평글을 인코딩할 때, 또는 AI 어시스턴트에게 인코딩을 맡길 때 참조할 실무 매뉴얼입니다.

## 1. 새 비평글 시작하기

### 1-1. 파일 생성

`essays/` 폴더에 새 XML 파일 생성:

```
essays/비평가슬러그_대상슬러그_연도.xml
```

예시:
- `essays/kim-uchang_yun-dongju_1985.xml`
- `essays/baek-nakcheong_yi-sang_1973.xml`

같은 비평가·대상·연도 조합 여러 글이 있으면 `a`, `b` 접미사: `kim-uchang_yun-dongju_1985a.xml`

### 1-2. 기본 골격 복사

`essays/kim-uchang_yun-dongju_1985.xml`을 열어서 다음 부분을 새 파일에 복사 후 수정:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<?xml-model href="../schema/korean-critique-schema.xsd" type="application/xml"
            schematypens="http://www.w3.org/2001/XMLSchema"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <!-- 메타데이터 -->
  </teiHeader>
  <text>
    <body>
      <!-- 본문 -->
    </body>
  </text>
</TEI>
```

## 2. teiHeader 작성

### 2-1. fileDesc — 비평글 메타데이터

```xml
<fileDesc>
  <titleStmt>
    <title>비평글 제목</title>
    <author>
      <persName xml:id="p-비평가슬러그" 
                ref="https://www.wikidata.org/wiki/Q.." 
                role="critic">비평가 이름</persName>
    </author>
    <respStmt>
      <resp>디지털 인코딩</resp>
      <name>본인 이름</name>
    </respStmt>
  </titleStmt>
  
  <publicationStmt>
    <p>비평 온톨로지 프로젝트, 2026년 디지털 인코딩. 원문 © 저자, 발표연도.</p>
  </publicationStmt>
  
  <sourceDesc>
    <biblStruct type="publication">
      <analytic>
        <title>비평글 제목</title>
        <author><persName ref="#p-비평가슬러그">비평가 이름</persName></author>
      </analytic>
      <monogr>
        <title>수록된 책 제목</title>
        <author><persName ref="#p-비평가슬러그">비평가 이름</persName></author>
        <imprint>
          <pubPlace>서울</pubPlace>
          <publisher>출판사</publisher>
          <date when="1985">1985</date>
        </imprint>
      </monogr>
    </biblStruct>
  </sourceDesc>
</fileDesc>
```

**`biblStruct/@type` 값**: `journal`, `newspaper`, `coterie`, `publication`, `other`

### 2-2. encodingDesc — 인코딩 방침과 분류 체계

```xml
<encodingDesc>
  <editorialDecl>
    <p>원문 철자 보존. 명백한 오식만 교정. 인물명·작품명·개념을 의미적으로 마크업.</p>
  </editorialDecl>
  
  <tagsDecl>
    <namespace>
      <tagUsage gi="persName" occurs="추정 횟수"/>
      <!-- 다른 태그들 -->
    </namespace>
  </tagsDecl>
  
  <classDecl>
    <taxonomy xml:id="tax-stance">
      <category xml:id="affirmative"><catDesc>긍정적 평가</catDesc></category>
      <category xml:id="critical"><catDesc>비판적 평가</catDesc></category>
      <category xml:id="neutral"><catDesc>중립적 분석</catDesc></category>
    </taxonomy>
    <taxonomy xml:id="tax-concept">
      <!-- 이 비평글에서 사용되는 개념 카테고리들 -->
      <category xml:id="public-sphere"><catDesc>공론장</catDesc></category>
    </taxonomy>
  </classDecl>
</encodingDesc>
```

**핵심**: `category/@xml:id`는 본문에서 `<interp ana="#아이디"/>` 형태로 참조됨. 본문에서 쓸 분석축을 먼저 여기서 선언해야 함.

## 3. 본문 마크업

### 3-1. div로 구획 나누기

`@type`은 [DivTypeEnum](#enum-참조) 중 선택:

```xml
<div type="introduction" xml:id="div-intro">
  <head>들어가며</head>
  <p>
    <s>...</s>
  </p>
</div>

<div type="argument" xml:id="div-arg-1">
  <head>1. 첫 번째 논증</head>
  <p>...</p>
</div>

<div type="conclusion" xml:id="div-conc">
  <head>나가며</head>
  <p>...</p>
</div>
```

### 3-2. 모든 텍스트는 `<s>` 안에

```xml
<!-- 잘못된 예 -->
<p>
  김우창이 윤동주를 분석한다.  <!-- 직접 텍스트, 마크업 위치 잡기 어려움 -->
</p>

<!-- 올바른 예 -->
<p>
  <s>김우창이 윤동주를 분석한다.</s>
</p>
```

### 3-3. 인명 마크업

**처음 등장**: `xml:id` + `ref` 부여

```xml
<persName xml:id="p-yun-dongju" 
          ref="https://www.wikidata.org/wiki/Q489582" 
          role="poet">윤동주</persName>
```

**이후 등장** (같은 문서 내): `#xml-id` 참조만

```xml
<persName ref="#p-yun-dongju">윤동주</persName>
```

**다른 표기로 부르더라도 같은 ID로 묶기**:

```xml
<persName ref="#p-habermas">위르겐 하버마스</persName>
<persName ref="#p-habermas">하버마스</persName>
<persName ref="#p-habermas">유르겐 하버마스</persName>
```

### 3-4. 작품 제목 마크업

```xml
<!-- 단행본 -->
<title level="m" type="critic">궁핍한 시대의 시인</title>
→ 렌더링: 『궁핍한 시대의 시인』

<!-- 글/시/소설 -->
<title level="a" type="poem">자화상</title>
→ 렌더링: 「자화상」

<!-- 저널/잡지 -->
<title level="j">창작과비평</title>
→ 렌더링: 《창작과비평》
```

### 3-5. 인용 마크업

```xml
<quote type="direct" 
       genre="poet" 
       source="윤동주, 「자화상」, 1939" 
       ana="#modern-self">
  우물 속에는 달이 밝고...
</quote>
```

**`type` 선택**:
- `direct`: 따옴표 그대로
- `indirect`: 의미만 전달 ("…라고 했다")
- `paraphrase`: 요약/의역

**`ana`**: classDecl의 카테고리 ID를 `#`으로 참조 (필수 아님이지만 가능하면 채울 것)

### 3-6. 비평 태도 마크업 (interp)

이게 본 스키마의 핵심 차별점:

```xml
<!-- 긍정적 평가 -->
<interp value="affirmative" ana="#modern-self">윤리적 주체성을 발명해야 했다</interp>

<!-- 비판적 평가 -->
<interp value="critical" ana="#public-sphere">공론장이 부재한 조건</interp>

<!-- 중립적 분석 -->
<interp value="neutral" ana="#modern-self">자아의 분열은 근대 주체의 조건이다</interp>
```

**`@ana`는 필수**. 분석축이 무엇인지 명시해야 함.

### 3-7. 개념·용어 마크업

```xml
<!-- 처음 등장 (정의) -->
<term xml:id="t-public-sphere" ref="#public-sphere">공론장</term>

<!-- 이후 -->
<term ref="#t-public-sphere">공론장</term>
```

`@ref`가 `#`으로 시작하면 내부 참조 (xml:id 또는 category id), `http`로 시작하면 외부 URI.

## 4. 자주 막히는 상황

### Q: 비평가가 다른 비평가를 비평하는 경우

대상에 비평가의 `xml:id`를 그대로 참조. 같은 인물 한 명이 다른 글에서 비평 주체, 또 다른 글에서 비평 대상일 수 있음. 정상.

### Q: 한 비평글이 여러 작가를 동시에 비평

본문 내에서 각 인물을 `<persName ref="#..."/>`로 표시하면 자동으로 다중 관계 형성. 별도 표시 불필요.

### Q: 같은 인물이 다른 역할로 등장 (예: 비평가이자 시인)

`role` 속성에 공백 구분:
```xml
<persName xml:id="p-kim-kyudong" role="critic poet">김규동</persName>
```

### Q: 한자/영문 표기를 함께 보여주려면

방법 1 — note로:
```xml
<persName xml:id="p-kim-uchang">김우창
  <note type="hanja">金禹昌</note>
</persName>
```

방법 2 — 별도 노트에 정리하고 본문에서는 한글만.

### Q: 출처를 모르는 인용

`source` 속성 비워두기 + todo 노트:
```xml
<quote type="direct">...</quote>
<note type="todo">출처 확인 필요</note>
```

### Q: 외부 ID (Wikidata 등)를 모름

`ref` 속성 생략. 나중에 일괄 조회.

## 5. 검증

VS Code 좌측 하단 또는 파일 상단의 빨간 밑줄/노란 밑줄로 스키마 위반이 표시됨. 모두 해결 후 저장·커밋.

자주 마주치는 오류:
- `body is missing` → `<body>` 빠짐
- `attribute 'ana' is required` → `<interp>`에 `@ana` 없음
- `value '...' is not facet-valid` → enum 값 오타 (예: `affirmative`를 `affermative`로)
- `xml:id duplicated` → 같은 ID를 두 번 정의

## 6. AI 어시스턴트 활용

VS Code AI 도구에 다음 컨텍스트 제공:
- `CLAUDE.md`
- `schema/korean-critique-schema.xsd`
- 이 가이드
- 기존 essays/ 내 파일 1-2개 (참고 패턴)

그 다음 프롬프트:

```
[비평글 원문 텍스트 또는 사진]

위 비평글을 본 프로젝트의 TEI XML 형식으로 인코딩해줘.
- 파일명 규칙: 비평가슬러그_대상슬러그_연도.xml
- 기존 인물이 등장하면 같은 xml:id 사용 (essays/ 내 파일 확인)
- 새 인물은 xml:id + ref(Wikidata 검색해서) 부여
- 모든 인물/작품/개념/인용을 의미적 마크업
- interp는 가능한 곳마다 적극 활용 (이게 데이터의 핵심)
```

## Enum 참조

### DivTypeEnum (div/@type)
`contents`, `introduction`, `body`, `conclusion`, `section`, `argument`, `criticism`, `review`, `editorial`, `column`, `interview`, `notes`

### TitleLevelEnum (title/@level)
- `m` — monograph (단행본)
- `a` — analytic (수록 글)
- `j` — journal (저널/잡지)

### TitleTypeEnum (title/@type)
`critic`, `novel`, `poem`, `play`, `essay`, `translation`, `children`, `contribution`, `foreign`, `other`, `journal`, `newspaper`, `coterie`, `publication`

### QuoteTypeEnum (quote/@type)
`direct`, `indirect`, `paraphrase`, `contribution`, `criticism`, `review`, `commentary`

### QuoteGenreEnum (quote/@genre)
`critic`, `novel`, `poet`, `play`, `essay`, `translation`, `children`, `contribution`, `foreign`, `other`

### InterpValueEnum (interp/@value)
`affirmative`, `neutral`, `critical`

### BiblTypeEnum (biblStruct/@type)
`journal`, `newspaper`, `coterie`, `publication`, `other`

### RoleEnum (persName/@role)
`critic`, `novelist`, `poet`, `playwright`, `essayist`, `translator`, `childrenauthor`, `scholar`, `foreigner`, `other`
