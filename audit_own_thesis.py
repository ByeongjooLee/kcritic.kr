# -*- coding: utf-8 -*-
"""학맥 — 교수 본인 박사논문 연결 전수 재검토 (읽기 전용, 2026-11-04).

공개 `site/data/genealogy-library.json` 의 교수 노드마다 '본인 박사논문'(target 이 교수인 지도 간선 + 노드 thesis_ids)을
모으고, 교수 명단(checkpoint-705)·통합 박사논문목록·research-public 과 대조해 모순·의심을 등급으로 매긴다.
아무것도 고치지 않는다. 결과는 xlsx + csv + md.

  py -X utf8 audit_own_thesis.py --roster <checkpoint-705-advisors-r2.json> --catalog <통합논문목록_지도교수보완.json> --out <폴더>

등급
  오류   : 같은 교수에 서로 다른 논문 2편 / 명단 박사 대학·연도·제목·지도교수와 모순 / 지도 시작이 학위보다 3년 이상 앞섬(추론·미확인 판정일 때)
  의심   : 같은 이름 논문 여럿인데 미확인 판정 / 학과가 국문·현대문학 밖 / 명예·전직인데 2005년 이후 학위 / 학위~마지막 지도 40년 초과 / 지도 시작이 학위보다 앞섬(확정 판정)
  약함   : 미확인 판정인데 근거가 '학위 대학 = 소속 대학'뿐이거나 명단 밖(도서관) 노드
  정합   : 위 어느 것도 아님
"""
import argparse, csv, difflib, json, re, sys
from collections import defaultdict, Counter
from pathlib import Path
from hanja_norm import uni_norm, h2k

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
LIT_DEPT = re.compile(r'국어국문|국문학|국문과|국어교육|한국어문|한국학|문예창작|비교문학|공연예술|한국문학|국어문학|문학|國語國文|國文')
NON_LIT_DEPT = re.compile(r'국어학|고전|한문|언어학|國語學|古典|漢文')


def norm_title(t):
    return re.sub(r'[\s\W_]+', '', h2k(t or '')).lower()


def main_title(t):
    return norm_title(re.split(r'[:：]', t or '', maxsplit=1)[0])


def same_thesis(a_title, a_year, a_uni, b_title, b_year, b_uni):
    """국중 레코드(주제목만·발행 연도가 제출 연도와 다를 수 있음)와 우리 서지가 같은 논문인지"""
    ta, tb = main_title(a_title), main_title(b_title)
    near = bool(a_year and b_year and abs(a_year - b_year) <= 1 and a_uni and a_uni == b_uni)
    if ta and tb:
        if ta == tb or ta.startswith(tb) or tb.startswith(ta):
            return True
        # 표기 차이(두음법칙·조사·따옴표·'1930'↔'30')는 같은 해·같은 대학이면서 글자열이 절반 넘게 겹칠 때 같은 논문으로 본다
        return near and difflib.SequenceMatcher(None, ta, tb).ratio() >= 0.5
    return near


def pname(s):
    return re.sub(r'[^가-힣A-Za-z]', '', s or '')


def yr(v):
    m = re.search(r'(19|20)\d{2}', str(v or ''))
    return int(m.group()) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--graph', default=str(HERE / 'site/data/genealogy-library.json'))
    ap.add_argument('--research', default=str(HERE / 'site/data/research-public.json'))
    ap.add_argument('--academic', default=str(HERE / 'site/data/academic-network-public.json'))
    ap.add_argument('--roster', required=True)
    ap.add_argument('--catalog', required=True)
    ap.add_argument('--authority', default='', help='저자전거 폴더(prof_kac_A.csv · 전거연결후보.csv · thesis/nlk_phd_theses.csv · thesis/thesis_matches.csv). 주면 국중 전거 대조를 더한다')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    G = json.loads(Path(a.graph).read_text(encoding='utf-8'))
    RP = json.loads(Path(a.research).read_text(encoding='utf-8'))
    roster = json.loads(Path(a.roster).read_text(encoding='utf-8'))['records']
    catalog = json.loads(Path(a.catalog).read_text(encoding='utf-8'))['rows']
    nodes = {n['id']: n for n in G['nodes']}
    rp = {t['id']: t for t in RP['theses']}
    cat = {r['id']: r for r in catalog}
    AN = json.loads(Path(a.academic).read_text(encoding='utf-8')) if Path(a.academic).exists() else {'theses': []}
    for t in AN.get('theses', []) + AN.get('reference_theses', []):   # 학교·소속 데이터에만 있는 논문(예: 서울대 2003 국어교육 박사)을 보조로
        cat.setdefault(t['id'], {'id': t['id'], 'title': t.get('title_raw') or t.get('title', ''), 'author': t.get('author_raw') or t.get('author', ''), 'year': str(t.get('year_raw') or ''), 'university': t.get('university_raw') or '', 'advisor': t.get('advisor_raw') or '', 'degree': ''})
    by_name = defaultdict(list)
    for r in catalog:
        by_name[h2k(r['author'], name=True).replace(' ', '')].append(r)
    for t in RP['theses']:
        if t['id'] not in cat:
            by_name[t['author'].replace(' ', '')].append({'id': t['id'], 'title': t['title'], 'author': t['author'], 'year': str(t['year']), 'university': t.get('university_raw') or t['university'], 'advisor': t.get('advisor_raw') or t.get('advisor', ''), 'degree': t.get('degree', '')})
    prof_names = Counter(n['name'] for n in G['nodes'] if n['kind'] == 'professor')

    # 국중 전거(KAC) 대조 자료 — 2026-10-29 저자 식별 작업 산출물(읽기만)
    prof_kac = defaultdict(list)   # node id -> [{kac, birth, corporate}]
    kac_theses = defaultdict(list) # kac -> NLK 박사논문 [{title, year, uni, dept, kdm}]
    kac_fields = {}                # kac -> (fields, jobs)
    thesis_kac = {}                # our thesis id -> (kac, grade)
    kac_rec = {}                   # kac -> 국중 전거 레코드(소속·생년·분야)
    if a.authority:
        A = Path(a.authority)
        for r in csv.DictReader(open(A / 'prof_kac_A.csv', encoding='utf-8-sig')):
            for i in r['our_ids'].split(' ; '):
                if i.startswith(('person:', 'professor:', 'student:')):
                    prof_kac[i].append({'kac': r['kac'], 'birth': yr(r['birth_year']), 'corporate': r['corporate']})
        for r in csv.DictReader(open(A / '전거연결후보.csv', encoding='utf-8-sig')):
            if r['kac']: kac_fields.setdefault(r['kac'], (r['fields'], r['jobs']))
        for r in csv.DictReader(open(A / 'thesis' / 'nlk_phd_theses.csv', encoding='utf-8-sig')):
            if r['kac']:
                kac_theses[r['kac']].append({'title': h2k(r['title']), 'year': yr(r['year']), 'uni': uni_norm(r['pub_norm'] or r['pub']), 'dept': r['dept'], 'kdm': r['kdm'], 'by_kac': 'kac:' in r['found_by']})
        for r in csv.DictReader(open(A / 'thesis' / 'thesis_matches.csv', encoding='utf-8-sig')):
            thesis_kac[r['thesis_id']] = (r['kac'], r['grade'])
        sp = A / 'sparql' / 'nlk_sparql_matches.jsonl'
        if sp.exists():
            for line in open(sp, encoding='utf-8'):
                rec = json.loads(line); kac_rec.setdefault(rec['kac'], rec)

    own = defaultdict(list)      # professor id -> own thesis edges
    advisees = defaultdict(list) # professor id -> advisee edges
    for e in G['edges']:
        advisees[e['source']].append(e)
        if nodes[e['target']]['kind'] == 'professor':
            own[e['target']].append(e)

    def thesis_info(tid, edge=None):
        t = rp.get(tid) or {}; c = cat.get(tid) or {}
        title = (edge or {}).get('title') or t.get('title') or h2k(c.get('title', ''))
        year = yr((edge or {}).get('year') or t.get('year') or c.get('year'))
        uni = uni_norm((edge or {}).get('university_raw') or (edge or {}).get('university') or t.get('university_raw') or t.get('university') or c.get('university', ''))
        adv = (edge or {}).get('advisor_raw') or t.get('advisor_raw') or t.get('advisor') or c.get('advisor', '')
        deg = next((x for x in (t.get('degree'), c.get('degree')) if x and re.search(r'--|:', x)), '')
        dept = re.sub(r'^.*?(--|:)\s*', '', deg)
        dept = re.sub(r'(19|20)\d{2}.*$', '', dept).strip(' ,')
        dept = re.sub(r'^[^,:]*(大學院|대학원)\s*[,:]?\s*', '', dept).strip(' ,')
        return dict(id=tid, title=title, year=year, uni=uni, advisor=h2k(adv, name=True) if adv else '', dept=dept)

    rows = []; edge_rows = []
    for n in G['nodes']:
        if n['kind'] != 'professor':
            continue
        items = {e['thesis_id']: thesis_info(e['thesis_id'], e) | {'src': '지도 간선', 'status_raw': e['student_identity'].get('status_raw', ''), 'status': e['student_identity'].get('status', ''), 'note': e['student_identity'].get('note', ''), 'advisor_node': nodes[e['source']]['name'], 'advisor_affil': ' · '.join(nodes[e['source']].get('affiliations') or [])} for e in own[n['id']]}
        for tid in n.get('thesis_ids') or []:
            if tid not in items:
                oti = n.get('own_thesis_identity') or {}
                items[tid] = thesis_info(tid) | {'src': 'thesis_ids', 'status_raw': oti.get('status_raw', ''), 'status': oti.get('status', ''), 'note': oti.get('note', ''), 'advisor_node': '', 'advisor_affil': ''}
        if not items:
            continue
        m = re.match(r'person:roster614:(\d+)$', n['id'])
        R = roster[int(m.group(1)) - 1] if m else None
        if R and R['name'] != n['name'] and h2k(R['name'], name=True) != n['name']:
            R = None  # 행 번호와 이름이 다르면 명단 대조를 포기하고 표시
            roster_mismatch = True
        else:
            roster_mismatch = False
        r_uni = uni_norm(R['doctorate_university']) if R and R['doctorate_university'] not in ('', '미확인') else ''
        r_year = yr(R['doctorate_year']) if R else None
        r_title = R['doctorate_thesis'] if R and R['doctorate_thesis'] not in ('', '미확인') else ''
        r_adv = R['doctoral_advisor'] if R and R['doctoral_advisor'] not in ('', '미확인') else ''
        adv_years = sorted(y for y in (yr(e.get('year')) for e in advisees[n['id']]) if y)
        first_adv, last_adv = (adv_years[0], adv_years[-1]) if adv_years else (None, None)
        affil = ' · '.join(n.get('affiliations') or [])
        same_name = by_name.get(n['name'], [])
        multi = len(items) > 1 and len({(i['uni'], i['year']) for i in items.values()}) > 1
        for tid, it in sorted(items.items(), key=lambda kv: (kv[1]['year'] or 0, kv[0])):
            flags = []; grade = '정합'
            lvl = it['status'] or ''
            nlk_note = ''
            kacs_all = prof_kac.get(n['id'], [])
            affs_n = [uni_norm(x) for x in (n.get('affiliations') or [])]
            # 전거의 소속 표기에 이 노드의 소속 대학이 들어 있는 전거만 '이 교수의 전거'로 쓴다(동명 전거 섞임 방지)
            kacs = [k for k in kacs_all if any(x and (x in k['corporate'] or x.replace('여대', '여자대') in k['corporate']) for x in affs_n)]
            tk, tg = thesis_kac.get(tid, ('', ''))
            if kacs:
                kset = {k['kac'] for k in kacs}
                nlk_own = [t for k in kset for t in kac_theses.get(k, [])]
                same = [t for t in nlk_own if same_thesis(t['title'], t['year'], t['uni'], it['title'], it['year'], it['uni'])]
                if same:
                    flags.append('국중 전거(소속 일치)의 박사논문과 같음')
                    nlk_note = 'NLK-same'
                if not it['title'] and not it['year']:
                    flags.append('목록 밖 논문(우리 서지 없음 — own_thesis_identity 의 RISS 링크로 확인)'); same = nlk_own
                if nlk_own and not same:
                    other = nlk_own[0]
                    in_corpus = any(same_thesis(h2k(x['title']), yr(x['year']), uni_norm(x['university']), other['title'], other['year'], other['uni']) for x in same_name)
                    flags.append(f"국중 전거의 박사논문은 {other['year']} {other['uni']} 「{other['title'][:30]}」" + ('(우리 목록에 있음)' if in_corpus else '(우리 목록에 없음)'))
                    nlk_note = 'NLK-other' + ('-in' if in_corpus else '')
                elif not nlk_own and tk and tg in ('A', 'A*') and tk not in {k['kac'] for k in kacs_all}:
                    flags.append(f'국중 전거(KAC {"·".join(sorted(kset))})에 박사논문 없음, 붙은 논문 저자는 다른 전거({tk})')
                    nlk_note = 'NLK-kac-diff'
                b = next((k['birth'] for k in kacs if k['birth']), None)
                if b and it['year'] and (it['year'] - b < 25 or it['year'] - b > 70):
                    flags.append(f'전거 생년 {b} 기준 학위 나이 {it["year"]-b}')
                fj = ' '.join(' '.join(kac_fields.get(k, ('', ''))) for k in kset)
                if NON_LIT_DEPT.search(fj):
                    flags.append('국중 전거 분야 고전·국어학·한문')
            if multi:
                flags.append('복수 본인논문(서로 다른 대학·연도)')
            if r_uni and it['uni'] and r_uni != it['uni']:
                flags.append(f'명단 박사 대학 불일치({r_uni})')
            if r_year and it['year'] and abs(r_year - it['year']) > 1:
                if (r_uni and r_uni == it['uni'] and abs(r_year - it['year']) <= 2) or nlk_note == 'NLK-same':
                    flags.append(f'명단 박사 연도 차이({r_year}, 같은 대학)')
                else:
                    flags.append(f'명단 박사 연도 불일치({r_year})')
            if r_title and norm_title(r_title) and norm_title(r_title) != norm_title(it['title']):
                flags.append('명단 박사 제목 불일치')
            if r_adv and it['advisor'] and pname(h2k(r_adv, name=True)) != pname(it['advisor']):
                flags.append(f'명단 지도교수 불일치({r_adv})')
            if first_adv and it['year'] and first_adv < it['year']:
                flags.append(f'지도 시작({first_adv})이 학위({it["year"]})보다 {it["year"]-first_adv}년 앞섬')
            if last_adv and it['year'] and last_adv - it['year'] > 40:
                flags.append(f'학위~마지막 지도 {last_adv-it["year"]}년')
            dept = it['dept']
            if dept and (NON_LIT_DEPT.search(dept) or not LIT_DEPT.search(dept)):
                flags.append(f'학과 「{dept}」')
            if R and re.search(r'명예|전직|퇴임', (R.get('status') or '') + (R.get('rank') or '')) and it['year'] and it['year'] >= 2005:
                flags.append(f'명예·전직인데 {it["year"]} 학위')
            if len(same_name) > 1 and lvl != '확정':
                flags.append(f'같은 이름 논문 {len(same_name)}편')
            if prof_names[n['name']] > 1:
                flags.append(f'같은 이름 교수 노드 {prof_names[n["name"]]}개')
            if roster_mismatch:
                flags.append('명단 행 번호와 이름 불일치')
            trec = kac_rec.get(tk) if tk and tg in ('A', 'A*') else None
            t_corp = ' | '.join((trec or {}).get('corporate') or [])
            t_birth = yr((trec or {}).get('birth_year'))
            if trec and nlk_note != 'NLK-same':
                corp_unis = {uni_norm(re.sub(r'\(.*?\)|\[前\]', '', c).strip()) for c in ((trec or {}).get('corporate') or [])}
                corp_unis |= {uni_norm(re.sub(r'\(.*?\)|\[前\]', '', c).split(' ')[0]) for c in ((trec or {}).get('corporate') or [])}
                aff_unis = {a.split(' ')[0] for a in affs_n}
                if aff_unis & corp_unis or any(x and (x in t_corp or x.replace('여대', '여자대') in t_corp) for x in affs_n):
                    flags.append('논문 저자 전거의 소속에 이 교수의 소속 대학 있음'); nlk_note = 'NLK-same'
                # 소속이 다르게 적힌 것은 전거 작성 시점(강사·전임지)일 수 있어 표지로만 적고 등급에는 안 넣는다 → '논문 저자 전거 소속' 열 참고
            if nlk_note == 'NLK-same':   # 국중 전거가 같은 논문을 가리키면 동명·학과·연령 표지는 뜻이 없다
                flags = [f for f in flags if f.startswith(('국중 전거(소속', '논문 저자 전거의 소속에', '복수', '명단 박사 대학', '명단 박사 제목', '명단 지도교수', '지도 시작', '명단 행'))]
            errs = [f for f in flags if f.startswith(('복수', '명단 박사', '명단 지도교수', '명단 행')) and '차이' not in f]
            if nlk_note.startswith('NLK-other'):
                errs.append('국중 전거 논문 다름')
            if first_adv and it['year'] and it['year'] - first_adv >= 3 and lvl != '확정':
                errs.append('지도 시작 3년+ 앞섬(미확정)')
            if errs:
                grade = '오류'
            elif [f for f in flags if not f.startswith(('국중 전거(소속 일치)', '논문 저자 전거의 소속에', '목록 밖 논문'))]:
                grade = '의심'
            elif nlk_note == 'NLK-same':
                grade = '정합(국중 일치)'
            elif lvl == '미확인' or (not R and lvl != '확정'):
                grade = '약함'
            # 권고
            if nlk_note.startswith('NLK-other'):
                rec_act = '국중 전거의 논문으로 바꿈(우리 목록에 있음)' if nlk_note.endswith('-in') else '연결 해제(전거의 논문은 우리 목록에 없음)'
            elif multi and nlk_note == 'NLK-same':
                rec_act = '유지(국중 전거 일치) — 다른 쪽 해제'
            elif multi:
                matched = {k['kac'] for k in kacs}
                if matched and tk and tg in ('A', 'A*') and tk not in matched:
                    rec_act = '연결 해제(붙은 논문 저자의 전거가 이 교수의 전거와 다름)'
                elif matched:
                    rec_act = '유지 권고(이 교수의 전거와 모순 없음) — 연구자 확인'
                else:
                    rec_act = '연구자 판정(둘 중 하나)'
            elif nlk_note == 'NLK-kac-diff':
                rec_act = '연구자 판정(전거는 다른 사람을 가리킴)'
            elif grade == '정합(국중 일치)' and lvl != '확정':
                rec_act = '확정으로 올림 권고(국중 전거 일치)' if '국중 전거(소속 일치)' in ' '.join(flags) else '확정으로 올림 권고(논문 저자 전거의 소속 일치)'
            elif grade == '오류':
                rec_act = '연구자 판정'
            else:
                rec_act = ''
            rec = {'등급': grade, '권고': rec_act, '교수 노드': n['id'], '이름': n['name'], '소속': affil, '명단': '명단' if R else ('명단 밖' if not m else '행 불일치'),
                   '명단 전공': R['major'] if R else '', '명단 상태': R['status'] if R else '', '명단 박사 대학': r_uni, '명단 박사 연도': r_year or '', '명단 박사 제목': r_title, '명단 지도교수': r_adv,
                   '논문 id': tid, '논문 제목': it['title'], '학위 연도': it['year'] or '', '학위 대학': it['uni'], '학과': it['dept'], '지도교수(서지)': it['advisor'], '지도교수 노드': it['advisor_node'], '지도교수 노드 소속': it['advisor_affil'],
                   '연결 경로': it['src'], '판정 단계': lvl, '판정 원값': it['status_raw'], '판정 근거': it['note'],
                   '첫 지도': first_adv or '', '마지막 지도': last_adv or '', '지도 편수': len(advisees[n['id']]), '같은 이름 논문 수': len(same_name),
                   '같은 이름 논문 목록': ' | '.join(f"{x['year']} {uni_norm(x['university'])} 「{h2k(x['title'])[:30]}」({x['id'][:8]})" for x in sorted(same_name, key=lambda x: str(x['year']))),
                   '교수 KAC(국중 전거 A)': ' · '.join(sorted({k['kac'] for k in kacs})), '전거 생년': next((k['birth'] for k in kacs if k['birth']), ''), '전거 소속 표기': ' | '.join(k['corporate'] for k in kacs)[:200],
                   '국중 전거의 박사논문': ' | '.join(f"{t['year']} {t['uni']} 「{t['title'][:30]}」" for k in sorted({k['kac'] for k in kacs}) for t in kac_theses.get(k, [])),
                   '붙은 논문 KAC': tk, '논문 대응 등급': tg, '논문 저자 전거 소속': t_corp[:200], '논문 저자 전거 생년': t_birth or '',
                   '점검 표지': '; '.join(flags)}
            rows.append(rec)

    # 지도 간선: 명단 교수의 명단 대학 ≠ 논문 대학(외부 지도 또는 동명 오귀속), 소속이 둘 이상인 노드(동명 병합)
    for e in G['edges']:
        s = nodes[e['source']]
        m = re.match(r'person:roster614:(\d+)$', s['id'])
        R = roster[int(m.group(1)) - 1] if m else None
        affs = [uni_norm(x) for x in (s.get('affiliations') or [])]
        r_uni = uni_norm(R['university']) if R else ''
        u = uni_norm(e.get('university_raw') or e.get('university') or '')
        if (r_uni and u and u != r_uni) or len(set(affs)) > 1:
            edge_rows.append({'지도교수 노드': s['id'], '지도교수': s['name'], '명단 대학': r_uni, '노드 소속': ' · '.join(affs), '논문 대학': u, '학위 연도': e.get('year', ''), '저자': nodes[e['target']]['name'],
                              '저자 구분': nodes[e['target']]['kind'], '논문 제목': e.get('title', ''), '논문 id': e['thesis_id'], '지도교수 서지 표기': e.get('advisor_raw', ''), '근거': e.get('basis', ''),
                              '같은 이름 교수 노드': prof_names[s['name']], '명단·주소속 대학 지도 편수': sum(uni_norm(x.get('university_raw') or x.get('university') or '') == (r_uni or (affs[0] if affs else '')) for x in advisees[s['id']])})

    order = {'오류': 0, '의심': 1, '약함': 2, '정합(국중 일치)': 3, '정합': 4}
    rows.sort(key=lambda r: (order[r['등급']], r['이름'], r['학위 연도'] or 0))
    edge_rows.sort(key=lambda r: (r['지도교수'], r['학위 연도']))

    def write_csv(name, rs):
        if not rs: return
        with open(out / name, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rs[0].keys())); w.writeheader(); w.writerows(rs)
    write_csv('본인논문_정합성.csv', rows); write_csv('지도대학_불일치.csv', edge_rows)
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        wb = Workbook(); ws = wb.active; ws.title = '본인논문 정합성'
        fill = {'오류': 'F8CBAD', '의심': 'FFE699', '약함': 'E2EFDA', '정합(국중 일치)': 'DDEBF7'}
        for ws, rs in ((ws, rows), (wb.create_sheet('지도대학 불일치'), edge_rows)):
            if not rs: continue
            ws.append(list(rs[0].keys()))
            for c in ws[1]: c.font = Font(bold=True)
            for r in rs:
                ws.append([str(v) if isinstance(v, (list, dict)) else v for v in r.values()])
                g = r.get('등급')
                if g in fill: ws.cell(ws.max_row, 1).fill = PatternFill('solid', fgColor=fill[g])
            ws.freeze_panes = 'C2'
        ws3 = wb.create_sheet('연구자 결정표')
        cols = ['등급', '권고', '이름', '소속', '명단 전공', '학위 연도', '학위 대학', '논문 제목', '지도교수(서지)', '판정 단계', '판정 원값', '국중 전거의 박사논문', '전거 생년', '점검 표지', '교수 노드', '논문 id']
        ws3.append(cols + ['결정(유지/해제/바꿈/확정)', '비고']); [setattr(c, 'font', Font(bold=True)) for c in ws3[1]]
        for r in rows:
            if r['등급'] in ('오류', '의심') or r['권고'].startswith('확정으로'):
                ws3.append([r[c] for c in cols] + ['', ''])
                if r['등급'] in fill: ws3.cell(ws3.max_row, 1).fill = PatternFill('solid', fgColor=fill[r['등급']])
        ws3.freeze_panes = 'D2'
        wb.save(out / '본인논문_재검토.xlsx')
    except ImportError:
        print('openpyxl 없음 — csv 만 저장')

    # 요약
    profs = {r['교수 노드'] for r in rows}
    by_grade = Counter(); seen = set()
    for r in rows:
        if r['교수 노드'] in seen: continue
        seen.add(r['교수 노드']); by_grade[r['등급']] += 1
    flag_counter = Counter(re.sub(r'\(.*', '', f).strip() for r in rows for f in r['점검 표지'].split('; ') if f)
    lines = [f"# 교수 본인 박사논문 연결 재검토 ({Path(a.graph).name} 기준)", '',
             f"- 본인 논문이 붙은 교수 {len(profs)}명, 논문 연결 {len(rows)}건 (지도 간선 {sum(r['연결 경로']=='지도 간선' for r in rows)} · thesis_ids 만 {sum(r['연결 경로']=='thesis_ids' for r in rows)})",
             f"- 교수 최고 등급: " + ' · '.join(f'{g} {by_grade[g]}' for g in order if by_grade[g]),
             f"- 판정 단계(연결 기준): " + ' · '.join(f'{k} {v}' for k, v in Counter(r['판정 단계'] for r in rows).most_common()),
             f"- 국중 전거(소속 일치) 박사논문과 같은 연결 {sum('국중 전거(소속 일치)' in r['점검 표지'] for r in rows)}건 — 그중 아직 확정이 아닌 것 {sum(r['권고'].startswith('확정으로') for r in rows)}건(확정 권고)",
             '', '## 점검 표지 빈도', ''] + [f'- {k}: {v}' for k, v in flag_counter.most_common()] + ['', '## 오류·의심 목록', '']
    for r in rows:
        if r['등급'] in ('오류', '의심'):
            lines.append(f"- [{r['등급']}] {r['이름']}({r['소속']}, {r['명단']}) — {r['학위 연도']} {r['학위 대학']} 「{r['논문 제목'][:40]}」 지도 {r['지도교수(서지)']} · 판정 {r['판정 단계']}({r['판정 원값']}) · {r['점검 표지']} → **{r['권고'] or '-'}**")
    lines += ['', f'## 명단 대학 ≠ 논문 대학 또는 소속이 둘 이상인 지도교수의 간선 ({len(edge_rows)}건)', '', '외부 지도일 수도, 동명 교수에게 잘못 붙은 것일 수도 있다. 명단 밖(도서관) 노드는 소속이 지도한 대학 그 자체라 여기서는 소속이 둘 이상인 노드만 잡힌다.', '']
    for r in edge_rows:
        lines.append(f"- {r['지도교수']}(명단 {r['명단 대학'] or '-'} / 소속 {r['노드 소속']}) → {r['학위 연도']} {r['논문 대학']} {r['저자']} 「{r['논문 제목'][:30]}」 · 동명 노드 {r['같은 이름 교수 노드']} · 주소속 대학 지도 {r['명단·주소속 대학 지도 편수']}편")
    (out / '본인논문_재검토_보고.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines[:12])); print(f'... 저장: {out}')


if __name__ == '__main__':
    main()
