# 데이터·온톨로지의 이용 조건

이 저장소의 **코드**(HTML·CSS·JavaScript·Python)는 `LICENSE` 의 MIT 라이선스를 따른다.
코드가 아닌 것의 조건은 아래와 같다. 사람이 읽는 안내는 <https://kcritic.kr/data.html>,
기계가 읽는 목록은 `site/data/datasets.json` 과 `site/data/void.ttl` 이다. 이 문서와 그 목록이 다르면 목록이 맞다.

| 대상 | 조건 |
|---|---|
| 직접 만든 메타데이터·관계 데이터 (글의 서지, 비평가–글–작가·이론가 관계, 개념어 색인, 인물 연결표, `graph.ttl`·`graph.json`, 학맥·학교 소속·학풍 파일에서 이 사이트가 더한 부분) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ko) |
| 온톨로지 (`critic_v8_schema.rdf`, `critic_v8_data.rdf`) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ko) |
| 해제·요지·주장 요약 (`site/data/v2/mhs_sum/`, `cb_sum/`, `changbi_summaries.json` 의 요약 문장) | 이용 조건을 붙이지 않음. 열람과 출처를 밝힌 인용만 할 수 있다. |
| 원문에서 옮긴 문장 (`interp_game.json`, `v2/examples.json`, `v2/contexts.json`, `concepts.json` 의 예시 문장) | 재이용 허락 없음. 저작권은 각 필자와 수록 지면의 권리자에게 있다. |
| 외부 기관에서 온 자료 (RISS 서지, 국립중앙도서관 전거, Wikidata·VIAF·ISNI 식별자, KCI 서지·인용 관계) | 각 제공처의 조건을 따른다. |
| 다른 연구자가 만든 목록 (`bibliography.json`, `criticism.json`) | 원 작성자에게 확인해야 한다. |
| 함께 실린 외부 라이브러리 (`site/sparql-bundle.js` 의 Comunica·N3 등) | 각자의 라이선스를 따른다. |

## 출처 표시

> 이병주, 「한국 비평사 온톨로지」(kcritic.kr), CC BY 4.0, https://kcritic.kr/data.html

고쳐 썼다면 고쳤다는 사실도 함께 밝힌다.

## 주의

박사논문 서지가 든 파일(`research-public.json`, `genealogy-library.json`, `academic-network-public.json`, `school-style-public.json`)의
제목·저자·연도·제어번호는 RISS 등 원 제공처에서 온 것이다. CC BY 4.0 은 이 사이트가 더한 부분(관계 판정, 표기 통일, 태그, 연결, 계산값)에만 적용된다.
