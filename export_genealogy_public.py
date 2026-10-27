# -*- coding: utf-8 -*-
"""학맥 계보 공개 파일 생성 — Codex 파이프라인 출력(학맥_그래프.json) → site/data/genealogy-library.json

사용법:
  py export_genealogy_public.py INPUT_JSON [--roster ROSTER_JSON] [--out site/data/genealogy-library.json]
                                [--check EXPECTED_JSON]

하는 일 (2026-10-27 사이트 파일을 역산해 같은 규칙으로 고정):
  1. --roster 가 있으면 교수 명단(checkpoint-*-advisors*.json)에서 advisor_status 가 '확인:' 으로 시작하는 행의
     본인 박사논문 지도교수 표기를 지도교수 → 교수 간선으로 추가한다. 후보·보류·제외 행은 넣지 않는다.
     지도교수는 이름 + 학위 수여 대학이 일치하는 교수 노드 하나에만 연결하고, 없으면 새 교수 노드
     (professor:roster-advisor:대학:이름)를 만든다. 동명 후보가 여럿이면 건너뛴다(자동 병합 금지).
  2. 근거 충돌 간선(advisor_conflict) 제거, 비공개·검수용 필드 제거, 간선에 연결되지 않은 교수 노드 제거,
     summary 재계산. 상위 키는 as_of·default_root·nodes·edges·summary·notes 만 남긴다.
  3. 로컬 경로·파일 URL 이 섞여 들어오지 않았는지 검사한다.
"""
import argparse, copy, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

NODE_DROP = {'alias_evidence'}
EDGE_DROP = {'advisor_conflict', 'formal_dissertation_advisor_confirmed', 'previous_advisor_evidence'}
TOP_KEEP = ['as_of', 'default_root', 'nodes', 'edges', 'summary', 'notes']
HANJA = [('忠南', '충남'), ('高麗', '고려'), ('延世', '연세'), ('梨花女子', '이화여자'), ('慶熙', '경희'), ('漢陽', '한양'), ('東國', '동국'), ('全南', '전남'),
         ('西江', '서강'), ('成均館', '성균관'), ('中央', '중앙'), ('檀國', '단국'), ('釜山', '부산'), ('嶺南', '영남'), ('亞洲', '아주'), ('國民', '국민'),
         ('全州', '전주'), ('朝鮮', '조선'), ('昌原', '창원'), ('韓南', '한남'), ('淑明女子', '숙명여자'), ('韓國外國語', '한국외국어'), ('慶北', '경북'),
         ('崇實', '숭실'), ('大學校', '대학교'), ('大學院', '대학원')]
KNOWN_EMPTY = {'', '미확인', '미표기', '없음'}


def uni(value):
    """학위 수여 대학 표기를 대학명으로 정규화 (lineage.js 의 affiliationName 과 같은 규칙)."""
    s = str(value or '').strip()
    for h, k in HANJA:
        s = s.replace(h, k)
    s = re.sub(r'^국립\s*', '', s).replace('경상국립대학교', '경상대학교')
    m = re.match(r'^.*?(?:대학교|사관학교|과학기술원|중앙연구원)', s)
    return m.group(0) if m else re.sub(r'\s*(?:일반|전문|특수|교육)?대학원.*$', '', s).strip()


def roster_person_id(i, r):
    """build_linked_roster.py 의 pid() 와 같은 규칙 (행 번호는 1부터). 명단은 앞부분 순서를 바꾸지 않고 뒤에만 덧붙인다는 전제."""
    if r['name'] in ('노대원', '유인혁'):
        return 'person:career:' + r['name']
    if r['name'] == '김현정' and r['university'] in ('세명대학교', '대전대학교'):
        return 'person:career:김현정-세명대'
    return f'person:roster614:{i:04}'


def add_roster_advisor_edges(data, roster):
    nodes = {n['id']: n for n in data['nodes']}
    pairs = {(e['source'], e['target']) for e in data['edges']}
    ids = {e['id'] for e in data['edges']}
    added, skipped = [], []
    for i, r in enumerate(roster['records'], 1):
        status = str(r.get('advisor_status') or '')
        adv = str(r.get('doctoral_advisor') or '').strip()
        if not status.startswith('확인') or adv in KNOWN_EMPTY:
            continue
        sid = roster_person_id(i, r)
        if sid not in nodes:
            skipped.append((i, r['name'], '명단 행의 인물 노드 없음')); continue
        u = uni(r.get('doctorate_university'))
        if not u:
            skipped.append((i, r['name'], '학위 대학 미확인')); continue
        cands = [n for n in nodes.values() if n['kind'] == 'professor' and n['name'] == adv and any(uni(a) == u for a in n.get('affiliations', []))]
        if len(cands) > 1:
            skipped.append((i, r['name'], f'지도교수 {adv} 동명 후보 {len(cands)}')); continue
        if cands:
            src = cands[0]
        else:
            lib = nodes.get(f'professor:library:{u}:{adv}')
            if lib:
                src = lib
            else:
                src = {'id': f'professor:roster-advisor:{u}:{adv}', 'name': adv, 'kind': 'professor', 'affiliations': [u],
                       'faculty_statuses': ['학위논문 지도 당시 소속; 현직 여부 별도'], 'urls': [x for x in [r.get('advisor_source')] if x],
                       'identity_status': '학위논문 지도교수', 'thesis_ids': [], 'advisee_thesis_count': 0,
                       'identity_note': '교수 명단에 적힌 본인 박사논문 지도교수 표기로 만든 인물. 교수 명단의 동명 행과 자동으로 합치지 않았다.'}
                data['nodes'].append(src); nodes[src['id']] = src
        if src['id'] == sid or (src['id'], sid) in pairs:
            skipped.append((i, r['name'], '이미 있는 관계')); continue
        own = nodes[sid].get('thesis_ids') or []
        tid = own[0] if own else f'roster-own:{i:04}'
        eid = f'{src["id"]}|{tid}'
        if eid in ids:
            skipped.append((i, r['name'], '같은 논문 간선 있음')); continue
        urls = [x for x in [r.get('advisor_source'), r.get('doctorate_thesis_source'), r.get('source')] if x]
        edge = {'id': eid, 'source': src['id'], 'target': sid, 'thesis_id': tid,
                'title': r.get('doctorate_thesis') or '', 'year': str(r.get('doctorate_year') or ''), 'university': r.get('doctorate_university') or '',
                'advisor_raw': adv,
                'student_identity': {'status': '교수 명단', 'note': '교수 명단 행 본인의 박사논문. 지도교수 표기는 명단 조사에서 확인.', 'urls': [x for x in [r.get('source')] if x]},
                'student_is_inferred_professor': False, 'urls': list(dict.fromkeys(urls)),
                'advisor_evidence': {'status': status, 'evidence': r.get('advisor_evidence') or '', 'source': r.get('advisor_source') or '', 'checked': r.get('checked') or ''},
                'basis': '교수 명단 지도교수 표기 확인'}
        data['edges'].append(edge); pairs.add((src['id'], sid)); ids.add(eid)
        src['advisee_thesis_count'] = src.get('advisee_thesis_count', 0) + 1
        added.append((i, r['name'], adv, u))
    return added, skipped


def publish(data):
    out = {k: copy.deepcopy(data[k]) for k in TOP_KEEP if k in data}
    out['edges'] = [{k: v for k, v in e.items() if k not in EDGE_DROP} for e in out['edges'] if not e.get('advisor_conflict')]
    linked = {e['source'] for e in out['edges']} | {e['target'] for e in out['edges']}
    out['nodes'] = [{k: v for k, v in n.items() if k not in NODE_DROP} for n in out['nodes'] if n['id'] in linked]
    nb = {n['id']: n for n in out['nodes']}
    for n in out['nodes']:
        n['advisee_thesis_count'] = sum(e['source'] == n['id'] for e in out['edges'])
    s = out.setdefault('summary', {})
    s['faculty_nodes'] = sum(n['kind'] == 'professor' for n in out['nodes'])
    s['faculty_with_advisees'] = sum(n['kind'] == 'professor' and n['advisee_thesis_count'] > 0 for n in out['nodes'])
    s['advisor_thesis_edges'] = len(out['edges'])
    root = out.get('default_root')
    direct = [e for e in out['edges'] if e['source'] == root]
    s['choi_direct_theses'] = len(direct)
    s['choi_professor_students'] = [{'name': nb[e['target']]['name'], 'identity_status': e.get('student_identity', {}).get('status', ''), 'next_theses': nb[e['target']]['advisee_thesis_count']} for e in direct if nb[e['target']]['kind'] == 'professor']
    for e in out['edges']:
        assert e['source'] in nb and e['target'] in nb and e['source'] != e['target'], e['id']
    assert len(nb) == len(out['nodes'])
    text = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    assert not re.search(r'(?:^|[\s"\'])[A-Za-z]:[\\/]|file://|Users[\\/]hgohg', text), '로컬 경로가 공개 파일에 섞였습니다'
    return out, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input'); ap.add_argument('--roster'); ap.add_argument('--out', default='site/data/genealogy-library.json'); ap.add_argument('--check')
    a = ap.parse_args()
    data = json.loads(Path(a.input).read_text(encoding='utf-8-sig'))
    if a.roster:
        added, skipped = add_roster_advisor_edges(data, json.loads(Path(a.roster).read_text(encoding='utf-8-sig')))
        print(f'명단 지도교수 간선 추가 {len(added)}건: ' + ', '.join(f'{adv}→{name}({u})' for _, name, adv, u in added))
        for row in skipped: print('  건너뜀', row)
    out, text = publish(data)
    if a.check:
        exp = json.loads(Path(a.check).read_text(encoding='utf-8-sig'))
        same = ({n['id'] for n in exp['nodes']} == {n['id'] for n in out['nodes']}, {e['id'] for e in exp['edges']} == {e['id'] for e in out['edges']}, exp['summary'] == out['summary'],
                sorted({k for n in exp['nodes'] for k in n}) == sorted({k for n in out['nodes'] for k in n}), sorted({k for e in exp['edges'] for k in e}) == sorted({k for e in out['edges'] for k in e}))
        print('검증(노드 집합, 간선 집합, 요약, 노드 키, 간선 키):', same)
        if not all(same): sys.exit(1)
        return
    Path(a.out).write_text(text, encoding='utf-8')
    s = out['summary']
    print(f"{a.out}: 노드 {len(out['nodes'])} (교수 {s['faculty_nodes']}, 지도논문 있는 교수 {s['faculty_with_advisees']}) · 간선 {s['advisor_thesis_edges']} · 기준일 {out.get('as_of')}")


if __name__ == '__main__':
    main()
