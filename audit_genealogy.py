# -*- coding: utf-8 -*-
"""학맥 데이터 전수 감사 (읽기 전용) — 2026-10-29

세 공개 파일(site/data/genealogy-library.json · research-public.json · academic-network-public.json)과
교수 명단(checkpoint-*-advisors*.json)·통합 박사논문목록(통합논문목록_지도교수보완.json)을 대조해
감사 표(xlsx + csv)·보고서(md)·연구자 검토표(xlsx)를 만든다. 데이터는 바꾸지 않는다.

사용법:
  py -X utf8 audit_genealogy.py --roster <checkpoint-705-advisors-r2.json> --catalog <통합논문목록_지도교수보완.json>
                               --merges <unconfirmed-merges-20261028.json> --out <출력 폴더>

항목:
  1a 동일인 후보(세대 단절): 교수 노드와 이름이 같은 학위자 노드, 그리고 이미 합쳤으나 미확인·추론인 본인 논문을
     교수 명단의 박사 정보(대학·연도·제목)와 대조해 등급(A 전부 일치 … E 모순)을 붙인다.
  1b 세 공개 파일 대조: 같은 논문 id 의 지도교수·대학·연도 불일치, 한쪽에만 있는 지도 관계.
  1c 판정 상태 분포와 「확정 / 추론 / 미확인」 재분류 표.
  1d 전공 범위 후보: 명단 전공·학과·논문 제목이 고전문학·국어학·한문학·어학인 사례 (자동 제외 없음).
  1e 결측: 연도·대학 없는 간선, 본인 박사논문 없는 지도교수, 명단의 지도교수 미조사 행 분포.
  1f 동명 처리: 같은 이름의 교수 노드, 같은 이름의 학위논문이 여럿인 저자, 보류 건 현황.
"""
import argparse, collections, csv, json, re, sys
from pathlib import Path

from hanja_norm import h2k, uni_norm
from export_genealogy_public import roster_person_id
from lineage_status import LEVEL_EDGE, LEVEL_NODE, LEVEL_OWN, level_of

sys.stdout.reconfigure(encoding='utf-8')
EMPTY = {'', '미확인', '미표기', '없음', 'None', 'null'}
RISS = 'https://www.riss.kr/search/detail/DetailView.do?p_mat_type=be54d9b8bc7cdb09&control_no={}&keyword='
# 1d: 고전문학·국어학·한문학·어학 쪽 낱말 (후보 표시용. 제외 여부는 연구자 결정)
SCOPE_RX = re.compile(r'고전|국어학|한국어학|한문|어학|음운|국어사|문법|형태론|통사|의미론|화용|어휘|방언|사전학|말뭉치|한국어교육|외국어로서|구비|설화|민요|무가|판소리|향가|시조|가사문학|고소설|고전소설|고전시가|경기체가|악장|한시|중세국어|근대국어|훈민정음|고려가요|조선\s?(?:전기|후기|시대|조)|신라|백제|고구려|李朝|朝鮮朝|朝鮮時代|高麗|新羅|鄕歌|時調|歌辭|漢詩|漢文|說話|民謠|音韻|文法|方言|語彙')


def clean(s):
    return re.sub(r'[\s\W_]+', '', h2k(str(s or ''))).lower()


def known(v):
    return str(v or '').strip() not in EMPTY


def year4(v):
    m = re.search(r'\d{4}', str(v or ''))
    return m.group(0) if m else ''


def grade(row, su, sy, st):
    """교수 명단의 박사 정보와 학위논문(대학·연도·제목) 대조 등급."""
    if row is None:
        return 'D', '명단 밖 교수(도서관·기존 노드) — 명단 박사 정보 없음'
    du = uni_norm(row.get('doctorate_university')) if known(row.get('doctorate_university')) else ''
    dy = year4(row.get('doctorate_year')) if known(row.get('doctorate_year')) else ''
    dt = row.get('doctorate_thesis') if known(row.get('doctorate_thesis')) else ''
    if not (du or dy or dt):
        return 'D', '명단에 박사 대학·연도·제목 모두 미확인'
    notes, bad, good = [], [], []
    if du:
        (good if du == su else bad).append(f'대학 명단 {du} / 논문 {su}')
    if dy:
        if dy == sy: good.append(f'연도 {dy}')
        elif abs(int(dy) - int(sy or 0)) == 1: notes.append(f'연도 ±1 (명단 {dy} / 서지 {sy})')
        else: bad.append(f'연도 명단 {dy} / 논문 {sy}')
    if dt:
        a, b = clean(dt), clean(st)
        if a == b or (len(a) >= 10 and (a in b or b in a)): good.append('제목 일치')
        else: bad.append(f'제목 명단 「{dt[:40]}」 / 논문 「{(st or "")[:40]}」')
    if bad:
        return 'E', '모순: ' + '; '.join(bad) + ('; ' + '; '.join(good + notes) if good or notes else '')
    if du and dy and dt and len(good) == 3:
        return 'A', '명단과 대학·연도·제목 모두 일치: ' + '; '.join(good)
    if du and dy and len(good) == 2 and not dt:
        return 'B', '대학·연도 일치(명단에 제목 없음): ' + '; '.join(good + notes)
    return 'C', '부분 일치: ' + '; '.join(good + notes) + f' (명단 확인 항목: {"대학" if du else ""}{" 연도" if dy else ""}{" 제목" if dt else ""})'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--graph', default='site/data/genealogy-library.json')
    ap.add_argument('--research', default='site/data/research-public.json')
    ap.add_argument('--academic', default='site/data/academic-network-public.json')
    ap.add_argument('--roster', required=True); ap.add_argument('--catalog', required=True); ap.add_argument('--merges')
    ap.add_argument('--out', required=True); ap.add_argument('--date', default='2026-10-29')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    G = json.loads(Path(a.graph).read_text(encoding='utf-8'))
    RP = json.loads(Path(a.research).read_text(encoding='utf-8'))
    AN = json.loads(Path(a.academic).read_text(encoding='utf-8'))
    roster = json.loads(Path(a.roster).read_text(encoding='utf-8-sig'))['records']
    catalog = {r['id']: r for r in json.loads(Path(a.catalog).read_text(encoding='utf-8-sig'))['rows']}
    merges = json.loads(Path(a.merges).read_text(encoding='utf-8')) if a.merges else {}

    N = {n['id']: n for n in G['nodes']}
    by_target = collections.defaultdict(list); by_source = collections.defaultdict(list); by_thesis = collections.defaultdict(list)
    for e in G['edges']:
        by_target[e['target']].append(e); by_source[e['source']].append(e); by_thesis[e['thesis_id']].append(e)
    rows_by_pid = {}
    for i, r in enumerate(roster, 1):
        rows_by_pid.setdefault(roster_person_id(i, r), []).append((i, r))
    def roster_of(nid):
        rs = rows_by_pid.get(nid) or []
        # 박사 정보가 있는 행 우선
        rs = sorted(rs, key=lambda x: (not known(x[1].get('doctorate_university')), x[0]))
        return rs[0] if rs else (None, None)
    def first_advisee_year(pid):
        ys = [int(year4(e['year'])) for e in by_source[pid] if year4(e['year'])]
        return min(ys) if ys else None
    def thesis_of(e):
        return e['university'], year4(e['year']), e['title']
    nm = lambda nid: N[nid]['name']
    sheets = collections.OrderedDict()

    # ── 1a ───────────────────────────────────────────────────────────────────
    prof_by_name = collections.defaultdict(list)
    for n in G['nodes']:
        if n['kind'] == 'professor': prof_by_name[n['name']].append(n)
    rows = []
    for s in sorted(G['nodes'], key=lambda n: (n['name'], n['id'])):
        if s['kind'] != 'student' or s['name'] not in prof_by_name: continue
        for p in prof_by_name[s['name']]:
            i, r = roster_of(p['id'])
            for e in by_target[s['id']]:
                su, sy, st = thesis_of(e)
                g, why = grade(r, su, sy, st)
                fay = first_advisee_year(p['id'])
                flags = []
                if p.get('thesis_ids'): flags.append('교수 노드에 본인 논문 이미 있음(' + ', '.join(p['thesis_ids']) + ')')
                if fay and sy and fay < int(sy): flags.append(f'교수 첫 지도논문 {fay} < 학위 {sy}')
                if r and SCOPE_RX.search((r.get('major') or '') + ' ' + (r.get('department') or '')): flags.append('명단 전공 범위 확인 필요: ' + (r.get('major') or ''))
                if su in p.get('affiliations', []): flags.append('학위 대학 = 소속 대학')
                if g == 'A' and not flags: rec = '병합(서지 일치)'
                elif g == 'E' or '이미 있음' in ' '.join(flags) or any('<' in f for f in flags): rec = '별개 인물로 둠'
                else: rec = '연구자 판단'
                rows.append({'구분': '학위자 노드 ≠ 교수 노드', '이름': s['name'], '학위자 노드': s['id'], '논문 id': e['thesis_id'], '학위 대학': su, '학위 연도': sy, '논문 제목': st,
                             '지도교수': nm(e['source']), '교수 노드': p['id'], '교수 소속': ' / '.join(p.get('affiliations', [])), '명단 행': i or '', '명단 전공': (r or {}).get('major', ''),
                             '명단 박사 대학': (r or {}).get('doctorate_university', ''), '명단 박사 연도': (r or {}).get('doctorate_year', ''), '명단 박사 제목': (r or {}).get('doctorate_thesis', ''),
                             '등급': g, '근거': why, '주의': '; '.join(flags), '추천 판정': rec, 'RISS': RISS.format(e['thesis_id']) if not e['thesis_id'].startswith(('snu:', 'roster-own:')) else ''})
    # 이미 합쳤으나 미확인·추론인 본인 논문
    for p in sorted(G['nodes'], key=lambda n: (n['name'], n['id'])):
        if p['kind'] != 'professor': continue
        own = p.get('own_thesis_identity') or {}
        st_ = own.get('status_raw', own.get('status')) or p.get('identity_status_raw', p.get('identity_status'))
        if st_ not in ('사용자 지시(미확인 반영)', '추론 연결', '근거 일치', '교수 동일인 미확정'): continue
        i, r = roster_of(p['id'])
        for tid in p.get('thesis_ids') or []:
            for e in by_thesis.get(tid, []):
                if e['target'] != p['id']: continue
                su, sy, st = thesis_of(e)
                g, why = grade(r, su, sy, st)
                fay = first_advisee_year(p['id']); flags = []
                if fay and sy and fay < int(sy): flags.append(f'교수 첫 지도논문 {fay} < 학위 {sy}')
                if r and SCOPE_RX.search((r.get('major') or '') + ' ' + (r.get('department') or '')): flags.append('명단 전공 범위 확인 필요: ' + (r.get('major') or ''))
                if su in p.get('affiliations', []): flags.append('학위 대학 = 소속 대학')
                if g == 'A': rec = '상태를 「도서관·서지 일치」로 올림'
                elif g == 'E': rec = '재검토(모순)'
                elif '학위 대학 = 소속 대학' in flags and not any('<' in f or '범위' in f for f in flags): rec = '확정 권고(학위 대학 = 소속 대학, 지도 시작이 학위 뒤) — 연구자 확인 필요'
                else: rec = '현 상태 유지(연구자 판단)'
                rows.append({'구분': f'이미 병합 · {st_}', '이름': p['name'], '학위자 노드': '', '논문 id': tid, '학위 대학': su, '학위 연도': sy, '논문 제목': st,
                             '지도교수': nm(e['source']), '교수 노드': p['id'], '교수 소속': ' / '.join(p.get('affiliations', [])), '명단 행': i or '', '명단 전공': (r or {}).get('major', ''),
                             '명단 박사 대학': (r or {}).get('doctorate_university', ''), '명단 박사 연도': (r or {}).get('doctorate_year', ''), '명단 박사 제목': (r or {}).get('doctorate_thesis', ''),
                             '등급': g, '근거': why, '주의': '; '.join(flags), '추천 판정': rec, 'RISS': RISS.format(tid) if not tid.startswith(('snu:', 'roster-own:')) else ''})
    sheets['1a_동일인후보'] = rows

    # ── 1b ───────────────────────────────────────────────────────────────────
    g_adv = {tid: sorted({nm(e['source']) for e in es}) for tid, es in by_thesis.items()}
    g_info = {tid: es[0] for tid, es in by_thesis.items()}
    rp = {t['id']: t for t in RP['theses']}
    an = {t['id']: t for t in AN['theses']}
    an_people = {p['id']: p['name'] for p in AN['people']}
    an_org = {o['id']: o['name'] for o in AN['institutions']}
    an_rel = collections.defaultdict(list)
    for rel in AN['relationships']:
        if rel['type'] == 'doctoral_supervision': an_rel[rel['thesis_id']].append(an_people.get(rel['source'], rel['source']))
    rows = []
    def add(kind, tid, g, rpv, anv, note=''):
        rows.append({'유형': kind, '논문 id': tid, '제목': (g_info.get(tid) or rp.get(tid) or an.get(tid) or {}).get('title', ''),
                     '저자': nm(g_info[tid]['target']) if tid in g_info else (rp.get(tid) or {}).get('author', (an.get(tid) or {}).get('author', '')),
                     '학맥(genealogy)': g, '학술연구(research-public)': rpv, '학교·소속(academic-network)': anv, '비고': note})
    for tid in sorted(set(g_adv) | set(rp) | set(an)):
        ga = g_adv.get(tid); r = rp.get(tid); x = an.get(tid)
        ra = sorted(s.strip() for s in (r or {}).get('advisor', '').split(',') if s.strip()) if r else None
        xa = ', '.join(sorted({h2k(v.strip(), name=True) for v in re.split(r'[,;/·]', (x or {}).get('advisor_raw') or '') if v.strip()})) if x else None
        xr = sorted(set(an_rel.get(tid, []))) if tid in an_rel else None
        if ga and r is not None and ra != ga: add('지도교수 불일치 G≠RP', tid, ', '.join(ga), ', '.join(ra), xa or '', 'RP advisor_raw=' + str(r.get('advisor_raw', '')))
        if ga and r is None: add('학술연구에 없음', tid, ', '.join(ga), '', xa or '')
        if ga and x is not None and xa and {clean(v) for v in xa.split(', ')} != {clean(v) for v in ga}: add('지도교수 불일치 G≠AN', tid, ', '.join(ga), ', '.join(ra or []), xa, 'AN advisor_raw=' + x.get('advisor_raw', ''))
        if ga and x is not None and not xa: add('AN 지도교수 빈칸(학맥에는 있음)', tid, ', '.join(ga), ', '.join(ra or []), '')
        if ga and x is None: add('학교·소속 논문목록에 없음', tid, ', '.join(ga), ', '.join(ra or []), '')
        if not ga and x is not None and xa: add('학맥에 없음(AN 지도교수 있음)', tid, '', ', '.join(ra or []), xa, 'AN advisor_raw=' + x.get('advisor_raw', ''))
        if not ga and r is not None and ra and x is None: add('학맥에 없음(RP 지도교수만)', tid, '', ', '.join(ra), '')
        if xr is not None:
            if not ga: add('AN 박사 지도 관계만 있음', tid, '', ', '.join(ra or []), ', '.join(xr))
            elif sorted(set(xr)) != ga and not all(any(clean(v) == clean(w) for w in ga) for v in xr): add('박사 지도 관계 불일치 G≠AN', tid, ', '.join(ga), ', '.join(ra or []), ', '.join(xr))
        if ga and r is not None:
            gu, ru = g_info[tid]['university'], r.get('university', '')
            if gu != ru: add('대학 불일치 G≠RP', tid, gu, ru, '')
            if year4(g_info[tid]['year']) != year4(r.get('year')): add('연도 불일치 G≠RP', tid, year4(g_info[tid]['year']), year4(r.get('year')), '')
        if ga and x is not None:
            gu, xu = g_info[tid]['university'], an_org.get(x.get('institution_id'), uni_norm(x.get('university_raw')))
            if gu != xu: add('대학 불일치 G≠AN', tid, gu, '', xu, 'AN university_raw=' + x.get('university_raw', ''))
            if year4(g_info[tid]['year']) != year4(x.get('year_raw')): add('연도 불일치 G≠AN', tid, year4(g_info[tid]['year']), '', year4(x.get('year_raw')))
    sheets['1b_파일대조'] = rows

    # ── 1c ───────────────────────────────────────────────────────────────────
    rows = []
    def dist(label, values, mapping):
        for v, c in sorted(collections.Counter(values).items(), key=lambda x: (-x[1], str(x[0]))):
            rows.append({'항목': label, '값': v if v is not None else '(없음)', '건수': c, '재분류(확정/추론/미확인)': level_of(v, mapping) if v is not None else '—'})
    dist('간선 student_identity.status', [e['student_identity'].get('status_raw', e['student_identity']['status']) for e in G['edges']], LEVEL_EDGE)
    dist('간선 basis', [e['basis'] for e in G['edges']], {})
    dist('노드 identity_status', [n.get('identity_status_raw', n['identity_status']) for n in G['nodes']], LEVEL_NODE)
    dist('노드 own_thesis_identity.status', [(n.get('own_thesis_identity') or {}).get('status_raw', (n.get('own_thesis_identity') or {}).get('status')) for n in G['nodes']], LEVEL_OWN)
    sheets['1c_상태분포'] = rows
    rows = []
    for label, mapping in (('간선 student_identity.status', LEVEL_EDGE), ('노드 identity_status', LEVEL_NODE), ('노드 own_thesis_identity.status', LEVEL_OWN)):
        for raw, lv in mapping.items():
            rows.append({'항목': label, '원래 값': raw, '재분류': lv})
    sheets['1c_재분류표'] = rows

    # ── 1d ───────────────────────────────────────────────────────────────────
    rows = []
    for p in sorted(G['nodes'], key=lambda n: (n['name'], n['id'])):
        if p['kind'] != 'professor': continue
        i, r = roster_of(p['id'])
        if not r: continue
        text = ' '.join(str(r.get(k) or '') for k in ('major', 'department', 'doctorate_thesis'))
        m = SCOPE_RX.search(text)
        if not m: continue
        own = [e['title'] for t in p.get('thesis_ids', []) for e in by_thesis.get(t, []) if e['target'] == p['id']]
        rows.append({'구분': '명단 전공·학과', '이름': p['name'], '노드': p['id'], '소속': ' / '.join(p.get('affiliations', [])), '명단 행': i, '명단 전공': r.get('major', ''), '명단 학과': r.get('department', ''),
                     '맞은 낱말': m.group(0), '본인 박사논문': ' | '.join(own), '지도논문 수': p['advisee_thesis_count'], '지도논문 제목(앞 3)': ' | '.join(e['title'] for e in by_source[p['id']][:3]),
                     '추천 판정': '연구자 결정(전공 범위)'})
    for e in sorted(G['edges'], key=lambda e: (e['title'], e['id'])):
        m = SCOPE_RX.search(e['title'] or '') or SCOPE_RX.search(e.get('title_raw') or '')
        if not m: continue
        rows.append({'구분': '논문 제목', '이름': nm(e['target']), '노드': e['target'], '소속': ' / '.join(N[e['target']].get('affiliations', [])), '명단 행': '', '명단 전공': '', '명단 학과': '',
                     '맞은 낱말': m.group(0), '본인 박사논문': e['title'], '지도논문 수': N[e['target']]['advisee_thesis_count'], '지도논문 제목(앞 3)': '지도교수 ' + nm(e['source']) + ' · ' + e['university'] + ' ' + str(e['year']),
                     '추천 판정': '연구자 결정(전공 범위)'})
    sheets['1d_전공범위후보'] = rows

    # ── 1e ───────────────────────────────────────────────────────────────────
    rows = []
    for e in G['edges']:
        if not year4(e['year']): rows.append({'구분': '연도 없는 간선', '대상': e['id'], '이름': nm(e['target']), '지도교수': nm(e['source']), '값': e['year'], '명단 박사 정보': '', '비고': e['title']})
        if not e.get('university'): rows.append({'구분': '대학 없는 간선', '대상': e['id'], '이름': nm(e['target']), '지도교수': nm(e['source']), '값': '', '명단 박사 정보': '', '비고': e['title']})
    for p in sorted(G['nodes'], key=lambda n: (-n['advisee_thesis_count'], n['name'])):
        if p['kind'] != 'professor' or p['advisee_thesis_count'] == 0 or p.get('thesis_ids'): continue
        i, r = roster_of(p['id'])
        if r is None: kind = '명단 밖(도서관·기존 노드)'; info = ''
        elif known(r.get('doctorate_thesis')) or known(r.get('doctorate_university')) or known(r.get('doctorate_year')): kind = '명단에 박사 정보 있음(논문 미연결)'; info = f"{r.get('doctorate_university')} {r.get('doctorate_year')} {r.get('doctorate_thesis')}"
        else: kind = '명단에 박사 정보 없음'; info = ''
        rows.append({'구분': '본인 박사논문 없는 지도교수 · ' + kind, '대상': p['id'], '이름': p['name'], '지도교수': '', '값': p['advisee_thesis_count'], '명단 박사 정보': info, '비고': ' / '.join(p.get('affiliations', []))})
    sheets['1e_결측'] = rows
    rows = []
    uni_tot = collections.Counter(); uni_un = collections.Counter(); uni_un_in = collections.Counter()
    for i, r in enumerate(roster, 1):
        u = uni_norm(r['university']); uni_tot[u] += 1
        if not str(r.get('advisor_status') or '').startswith(('확인', '연결', '제외')):
            uni_un[u] += 1
            if roster_person_id(i, r) in N: uni_un_in[u] += 1
    for u, c in sorted(uni_tot.items(), key=lambda x: (-x[1], x[0])):
        rows.append({'대학': u, '명단 행': c, '지도교수 미조사·보류': uni_un[u], '그중 학맥 노드 있음': uni_un_in[u]})
    rows.append({'대학': '합계', '명단 행': sum(uni_tot.values()), '지도교수 미조사·보류': sum(uni_un.values()), '그중 학맥 노드 있음': sum(uni_un_in.values())})
    sheets['1e_명단_지도교수미조사'] = rows

    # ── 1f ───────────────────────────────────────────────────────────────────
    rows = []
    for name, ps in sorted(prof_by_name.items()):
        if len(ps) < 2: continue
        for p in ps:
            i, r = roster_of(p['id'])
            own = [f"{e['university']} {e['year']} {e['title'][:30]}" for t in p.get('thesis_ids', []) for e in by_thesis.get(t, []) if e['target'] == p['id']]
            rows.append({'구분': '동명 교수 노드', '이름': name, '노드': p['id'], '소속': ' / '.join(p.get('affiliations', [])), '명단 행': i or '', '명단 전공': (r or {}).get('major', ''), '본인 논문': ' | '.join(own),
                         '지도논문 수': p['advisee_thesis_count'], '지도 대학': ', '.join(sorted({e['university'] for e in by_source[p['id']]})), '비고': p.get('identity_status_raw', p.get('identity_status', ''))})
    stu_by_name = collections.defaultdict(list)
    for n in G['nodes']:
        if n['kind'] == 'student': stu_by_name[n['name']].append(n)
    for name, ss in sorted(stu_by_name.items()):
        if len(ss) < 2 and name not in prof_by_name: continue
        if len(ss) < 2: continue
        for s in ss:
            for e in by_target[s['id']]:
                rows.append({'구분': '같은 이름 학위논문 여럿', '이름': name, '노드': s['id'], '소속': '', '명단 행': '', '명단 전공': '', '본인 논문': f"{e['university']} {e['year']} {e['title'][:40]}",
                             '지도논문 수': 0, '지도 대학': '지도교수 ' + nm(e['source']), '비고': '교수 노드 있음: ' + ', '.join(p['id'] for p in prof_by_name.get(name, []))})
    sheets['1f_동명'] = rows
    rows = []
    hold = ['김미라', '최민지', '김병욱', '김윤영', '김민수', '김소연', '이화진', '김윤정', '김동욱', '박동규']
    skipped = {s.get('name'): s.get('reason', '') for s in merges.get('skipped', [])} if merges else {}
    for name in hold:
        for n in sorted([n for n in G['nodes'] if n['name'] == name], key=lambda n: n['id']):
            i, r = roster_of(n['id'])
            inc = [f"{nm(e['source'])} → {e['university']} {e['year']} ({e['student_identity'].get('status_raw', e['student_identity']['status'])})" for e in by_target[n['id']]]
            rows.append({'이름': name, '노드': n['id'], '종류': n['kind'], '소속': ' / '.join(n.get('affiliations', [])), '본인 논문 상태': (n.get('own_thesis_identity') or {}).get('status_raw', (n.get('own_thesis_identity') or {}).get('status', '')), '들어오는 간선': ' | '.join(inc),
                         '지도논문 수': n['advisee_thesis_count'], '명단 행': i or '', '명단 박사 정보': f"{(r or {}).get('doctorate_university','')} {(r or {}).get('doctorate_year','')}".strip(), '2026-10-28 보류 사유': skipped.get(name, '')})
    sheets['1f_보류현황'] = rows

    # ── 출력 ──────────────────────────────────────────────────────────────────
    write_xlsx(out / f'학맥_감사_{a.date.replace("-", "")}.xlsx', sheets)
    for name, rows in sheets.items():
        write_csv(out / f'{name}.csv', rows)
    review = build_review(sheets)
    write_xlsx(out / f'연구자_검토표_{a.date.replace("-", "")}.xlsx', review)
    (out / f'학맥_감사_보고서_{a.date.replace("-", "")}.md').write_text(report(a, G, RP, AN, roster, sheets, review), encoding='utf-8')
    for name, rows in sheets.items(): print(f'{name}: {len(rows)}행')
    for name, rows in review.items(): print(f'검토표 {name}: {len(rows)}행')


def build_review(sheets):
    """연구자 검토표: 후보 · 근거 · 추천 판정 · 결정란."""
    rv = collections.OrderedDict()
    rows = []
    for r in sheets['1a_동일인후보']:
        if r['등급'] == 'A' and r['추천 판정'].startswith(('병합', '상태를')): continue
        rows.append({'후보': f"{r['이름']} — {r['구분']}", '학위논문': f"{r['학위 대학']} {r['학위 연도']} 「{r['논문 제목']}」 지도 {r['지도교수']}", '교수 노드': f"{r['교수 노드']} ({r['교수 소속']})",
                     '근거': f"등급 {r['등급']} · {r['근거']}" + (f" · 주의: {r['주의']}" if r['주의'] else ''), '추천 판정': r['추천 판정'], '결정란': '', 'RISS': r['RISS']})
    rv['1a_동일인(불일치·부분일치)'] = rows
    rows = []
    for r in sheets['1d_전공범위후보']:
        rows.append({'후보': f"{r['이름']} ({r['소속']})", '구분': r['구분'], '근거': f"{r['맞은 낱말']} · 전공 {r['명단 전공']} · 학과 {r['명단 학과']} · 논문 {r['본인 박사논문'][:60]}", '지도논문 수': r['지도논문 수'], '추천 판정': '학맥 유지 / 제외 중 결정', '결정란': ''})
    rv['1d_전공범위'] = rows
    rows = []
    for r in sheets['1f_동명']:
        rows.append({'후보': f"{r['이름']} — {r['구분']}", '노드': r['노드'], '근거': f"소속 {r['소속']} · 명단 전공 {r['명단 전공']} · 본인 논문 {r['본인 논문']} · {r['지도 대학']}", '추천 판정': '별개 인물 유지(합칠 근거 없음)' if r['구분'] == '동명 교수 노드' else '보류(어느 논문이 본인인지 미확정)', '결정란': ''})
    for r in sheets['1f_보류현황']:
        rows.append({'후보': f"{r['이름']} — 보류 건 현황", '노드': r['노드'], '근거': f"{r['종류']} · {r['소속']} · 본인 논문 상태 {r['본인 논문 상태']} · {r['들어오는 간선']} · 명단 {r['명단 박사 정보']} · 사유 {r['2026-10-28 보류 사유']}", '추천 판정': '현 상태 유지', '결정란': ''})
    rv['1f_동명·보류'] = rows
    return rv


def write_csv(path, rows):
    if not rows:
        path.write_text('', encoding='utf-8-sig'); return
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def write_xlsx(path, sheets):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name[:31])
        if not rows:
            ws.append(['(해당 없음)']); continue
        cols = list(rows[0].keys()); ws.append(cols)
        for c in ws[1]: c.font = Font(bold=True); c.fill = PatternFill('solid', fgColor='DDE4EE'); c.alignment = Alignment(vertical='top', wrap_text=True)
        for r in rows: ws.append([r.get(c, '') for c in cols])
        for i, c in enumerate(cols, 1):
            width = max(8, min(60, max(len(str(r.get(c, ''))) for r in rows[:300]) * 1.1 + 2))
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width
        ws.freeze_panes = 'A2'
    wb.save(path)


def report(a, G, RP, AN, roster, sheets, review):
    c = collections.Counter
    s1 = sheets['1a_동일인후보']; s2 = sheets['1b_파일대조']; s5 = sheets['1e_결측']; s6 = sheets['1f_동명']
    L = [f'# 학맥 데이터 전수 감사 보고서 ({a.date})', '',
         f'대상: `genealogy-library.json`(노드 {len(G["nodes"])} · 교수 {G["summary"]["faculty_nodes"]} · 간선 {G["summary"]["advisor_thesis_edges"]}, 기준일 {G.get("as_of")}) · `research-public.json`(논문 {len(RP["theses"])}) · `academic-network-public.json`(논문 {len(AN["theses"])}, 박사 지도 {sum(r["type"]=="doctoral_supervision" for r in AN["relationships"])}) · 교수 명단 {len(roster)}행.',
         '읽기 전용 감사. 표는 같은 폴더의 xlsx·csv. 등급: A = 명단 박사 대학·연도·제목 모두 일치, B = 대학·연도 일치(제목 없음), C = 부분 일치, D = 대조할 명단 정보 없음, E = 모순.', '',
         '## 1a 동일인 후보(세대 단절)', '',
         f'- 교수 노드와 이름이 같은 학위자 노드(합치지 않은 것): {sum(r["구분"].startswith("학위자") for r in s1)}건 — 등급 ' + ', '.join(f'{k} {v}' for k, v in sorted(c(r["등급"] for r in s1 if r["구분"].startswith("학위자")).items())),
         f'- 이미 합쳤으나 미확인·추론 상태인 본인 논문: {sum(not r["구분"].startswith("학위자") for r in s1)}건 — 등급 ' + ', '.join(f'{k} {v}' for k, v in sorted(c(r["등급"] for r in s1 if not r["구분"].startswith("학위자")).items())),
         f'- 추천 판정: ' + ', '.join(f'{k} {v}' for k, v in sorted(c(r["추천 판정"] for r in s1).items())), '',
         '## 1b 세 공개 파일 대조', '']
    for k, v in sorted(c(r['유형'] for r in s2).items(), key=lambda x: (-x[1], x[0])): L.append(f'- {k}: {v}건')
    L += ['', '## 1c 판정 상태 분포', '']
    for r in sheets['1c_상태분포']: L.append(f'- {r["항목"]} · {r["값"]}: {r["건수"]} → {r["재분류(확정/추론/미확인)"]}')
    L += ['', '재분류 규칙(`lineage_status.py`): 확정 = 연구자 확인·교수 명단·기존 검수·도서관 서지 일치 / 추론 = 근거 일치·추론 연결 / 미확인 = 교수 여부 미확인·동일인 미확정·미확인 반영 병합.', '',
          '## 1d 전공 범위 후보', '', f'- 명단 전공·학과·본인 논문에 고전·국어학·한문·어학 낱말: {sum(r["구분"]=="명단 전공·학과" for r in sheets["1d_전공범위후보"])}명', f'- 지도논문 제목에 그런 낱말: {sum(r["구분"]=="논문 제목" for r in sheets["1d_전공범위후보"])}편', '',
          '## 1e 결측', '']
    for k, v in sorted(c(r['구분'] for r in s5).items(), key=lambda x: (-x[1], x[0])): L.append(f'- {k}: {v}')
    tot = sheets['1e_명단_지도교수미조사'][-1]
    L += [f'- 교수 명단 {tot["명단 행"]}행 중 지도교수 미조사·보류 {tot["지도교수 미조사·보류"]}행(그중 학맥 노드 있음 {tot["그중 학맥 노드 있음"]}). 대학별 분포는 `1e_명단_지도교수미조사.csv`.', '',
          '## 1f 동명 처리', '', f'- 같은 이름의 교수 노드: {len({r["이름"] for r in s6 if r["구분"]=="동명 교수 노드"})}이름 {sum(r["구분"]=="동명 교수 노드" for r in s6)}노드',
          f'- 같은 이름의 학위논문이 여럿인 저자(학위자 노드): {len({r["이름"] for r in s6 if r["구분"]!="동명 교수 노드"})}이름 {sum(r["구분"]!="동명 교수 노드" for r in s6)}편',
          f'- 보류 건 현황 {len(sheets["1f_보류현황"])}행 (`1f_보류현황.csv`)', '',
          '## 연구자 검토표', '', *[f'- {k}: {len(v)}행' for k, v in review.items()], '']
    return '\n'.join(L)


if __name__ == '__main__':
    main()
