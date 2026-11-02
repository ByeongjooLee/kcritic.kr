# -*- coding: utf-8 -*-
"""학맥 판정 상태의 3단계 재분류 — 「확정 / 추론 / 미확인」 (2026-10-29 감사)

계보 그래프(Codex 파이프라인 출력)는 판정 경위를 세분한 상태값(사용자 확인·교수 명단·기존 확인 계승·추론 연결·근거 일치·
교수 여부 미확인·사용자 지시(미확인 반영) …)을 쓴다. 공개 파일(genealogy-library.json)과 화면은 이것을 세 단계로 묶어 보이고,
원래 값은 `status_raw`(간선 student_identity · 노드 own_thesis_identity)·`identity_status_raw`(노드)에 보존한다.

  확정   연구자가 확인했거나, 교수 명단·기존 검수·도서관 서지로 대학·연도·제목이 맞는 동일인
  추론   근거(제목·대학·연도)가 맞아 보이지만 연구자 확인이 없는 동일인
  미확인 교수 여부·동일인 여부를 확인하지 못한 학위자, 또는 연구자 지시로 반영했으나 근거가 없는 병합
"""
CONFIRMED, INFERRED, UNCONFIRMED = '확정', '추론', '미확인'
LEVELS = (CONFIRMED, INFERRED, UNCONFIRMED)

# 간선 student_identity.status (학위논문 저자 = 교수 노드 동일인 판정)
LEVEL_EDGE = {
    '사용자 확인': CONFIRMED, '사용자 확인 및 서지 대조': CONFIRMED, '사용자 지정': CONFIRMED, '교수 명단': CONFIRMED,
    '기존 확인 계승': CONFIRMED, '기존 동일인 검수': CONFIRMED, '공식 학력 대조 확인': CONFIRMED, '도서관·서지 일치': CONFIRMED,
    '추론 연결': INFERRED, '근거 일치': INFERRED,
    '교수 여부 미확인': UNCONFIRMED, '교수 동일인 미확정': UNCONFIRMED, '사용자 지시(미확인 반영)': UNCONFIRMED,
}
# 노드 identity_status (노드가 가리키는 사람의 확인 경위)
LEVEL_NODE = {
    '교수 명단': CONFIRMED, '사용자 확인': CONFIRMED, '기존 동일인 검수': CONFIRMED, '기존 소속 검수': CONFIRMED,
    '학위논문 지도교수': CONFIRMED, '도서관 지도교수 확인': CONFIRMED, '도서관·서지 일치': CONFIRMED,
    '추론 연결': INFERRED, '근거 일치': INFERRED,
    '교수 여부 미확인': UNCONFIRMED, '교수 동일인 미확정': UNCONFIRMED, '사용자 지시(미확인 반영)': UNCONFIRMED,
}
# 노드 own_thesis_identity.status (교수 노드에 붙인 본인 박사논문의 동일인 판정)
LEVEL_OWN = dict(LEVEL_EDGE)


def level_of(value, mapping):
    """상태값 → 3단계. 표에 없는 값은 낱말로 판단한다(미확인·미확정 → 미확인, 추론·근거 일치 → 추론, 그 밖은 확정)."""
    v = str(value or '').strip()
    if v in mapping:
        return mapping[v]
    if not v:
        return UNCONFIRMED
    if '미확인' in v or '미확정' in v:
        return UNCONFIRMED
    if '추론' in v or '근거 일치' in v:
        return INFERRED
    return CONFIRMED
