# -*- coding: utf-8 -*-
"""학술연구(/theses/) 탐색 데이터 `site/data/research-public.json` 의 지도교수를 학맥 데이터와 맞춘다.

학술연구 글·인물·학위수여기관·지도교수 탭(`thesis-browse.js`)은 research-public.json 의 `theses` 만 읽고,
학맥(`lineage.html`)은 `genealogy-library.json` 을 읽는다. 지도교수 정보는 학맥 쪽이 권위(도서관·통합목록 검수)이므로
이 스크립트가 research-public.json 에 되비춘다.

- 두 데이터에 모두 있는 논문: `advisor` 를 학맥의 지도교수 한글 이름(공동지도는 ', ' 로 이음)으로 맞춘다.
  원래 표기(한자 등)가 다르면 `advisor_raw` 에 남긴다.
- 학맥에만 있는 논문(본문 색인 밖, 서울대 도서관 전용 `snu:` 포함): 서지(제목·저자·연도·대학·지도교수·RISS 링크)만
  `theses` 에 덧붙이고 `in_search_corpus: false` 로 표시한다. 글 찾기(뜻 검색)·인용 관계·인물/개념어 태그에는 들어가지 않는다.
- 대학 표기는 한글 교명(`대학교` 까지)으로 정규화한다. `corpus_size`·`works`·`scope` 는 손대지 않는다.

실행: `py enrich_research_public.py` (genealogy-library.json 을 바꾼 뒤, 또는 theses-search 쪽에서 research-public.json 을
새로 내보낸 뒤). 두 번 실행해도 결과가 같다(결정적).
"""
import json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RP = ROOT / 'site/data/research-public.json'
GEN = ROOT / 'site/data/genealogy-library.json'
RISS = 'https://www.riss.kr/search/detail/DetailView.do?p_mat_type=be54d9b8bc7cdb09&control_no={}&keyword='

HANJA = [('忠南', '충남'), ('高麗', '고려'), ('延世', '연세'), ('梨花女子', '이화여자'), ('慶熙', '경희'), ('漢陽', '한양'), ('東國', '동국'), ('全南', '전남'),
         ('西江', '서강'), ('成均館', '성균관'), ('中央', '중앙'), ('檀國', '단국'), ('釜山', '부산'), ('嶺南', '영남'), ('亞洲', '아주'), ('國民', '국민'),
         ('全州', '전주'), ('朝鮮', '조선'), ('昌原', '창원'), ('韓南', '한남'), ('淑明女子', '숙명여자'), ('韓國外國語', '한국외국어'), ('慶北', '경북'),
         ('崇實', '숭실'), ('全北', '전북'), ('仁荷', '인하'), ('建國', '건국'), ('世宗', '세종'), ('圓光', '원광'), ('東亞', '동아'), ('啓明', '계명'),
         ('韓國學中央硏究院', '한국학중앙연구원'), ('大學校', '대학교'), ('大學院', '대학원'), ('서울大', '서울대')]
ALIAS = {'경상국립대학교': '경상대학교', '국립창원대학교': '창원대학교', '강원대학교(강릉)': '강릉원주대학교', '강릉대학교': '강릉원주대학교', '경원대학교': '가천대학교'}


def uni(value):
    s = unicodedata.normalize('NFKC', str(value or '')).strip()
    for h, k in HANJA:
        s = s.replace(h, k)
    s = re.sub(r'^국립\s*', '', s)
    if s in ALIAS:
        return ALIAS[s]
    m = re.match(r'^.*?(?:대학교|사관학교|과학기술원|중앙연구원)', s)
    s = m.group(0) if m else re.sub(r'\s*(?:일반|전문|특수|교육)?대학원.*$', '', s).strip()
    return ALIAS.get(s, s)


def main():
    rp = json.loads(RP.read_text(encoding='utf-8'))
    g = json.loads(GEN.read_text(encoding='utf-8'))
    name = {n['id']: n['name'] for n in g['nodes']}
    advisors, info = {}, {}
    for e in g['edges']:
        tid = e['thesis_id']
        advisors.setdefault(tid, set()).add(name[e['source']])
        info.setdefault(tid, {'title': e['title'], 'author': name[e['target']], 'year': e['year'], 'university': e.get('university') or ''})
    # 1) 기존 레코드: 학맥에서 덧붙인 레코드는 지우고 다시 만든다(재실행 결정성)
    base = [t for t in rp['theses'] if t.get('in_search_corpus') is not False]
    changed = filled = 0
    for t in base:
        # 재실행이면 advisor_raw 가 원래 표기다(원 표기를 보존하며 결정적으로 다시 계산)
        old_raw = t.pop('advisor_raw', None)
        if t['id'] not in advisors:
            continue
        old = (old_raw or t.get('advisor') or '').strip()
        new = ', '.join(sorted(advisors[t['id']]))
        if old == new:
            continue
        if old:
            t['advisor_raw'] = old; changed += 1
        else:
            filled += 1
        t['advisor'] = new
    # 2) 학맥에만 있는 논문
    have = {t['id'] for t in base}
    added = []
    for tid in sorted(advisors):
        if tid in have:
            continue
        i = info[tid]
        y = str(i['year'])[:4]
        rec = {'id': tid, 'title': i['title'], 'author': i['author'], 'year': int(y) if y.isdigit() else i['year'],
               'university': uni(i['university']) or '미확인', 'advisor': ', '.join(sorted(advisors[tid])),
               'degree': '학위논문(박사)', 'in_search_corpus': False}
        if not tid.startswith('snu:'):
            rec['riss_url'] = RISS.format(tid)
        added.append(rec)
    added.sort(key=lambda r: (str(r['year']), r['title'], r['id']))
    rp['theses'] = base + added
    out = json.dumps(rp, ensure_ascii=False, separators=(',', ':'))
    assert 'C:\\' not in out and 'C:/' not in out and 'Codex' not in out, '로컬 경로가 섞였다'
    RP.write_text(out, encoding='utf-8')
    print(f'research-public.json: 기존 {len(base)}편 (지도교수 표기 통일 {changed}, 빈칸 채움 {filled}) + 학맥에서 덧붙임 {len(added)}편 = {len(rp["theses"])}편')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
