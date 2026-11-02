"""KCI 참고문헌 수집본 → 인용 관계 데이터셋 구축.

입력(읽기 전용)
  참고문헌_API/ART*.json   KCI Open API articleDetail 응답(참고문헌 목록, 키 제거본)
  참고문헌_API/ART*.xml    같은 응답의 원본 XML — 논문의 KCI 피인용 수(citation-count)만 읽는다
  서지정보/전체수집목록.csv 82,344편 서지(초록 포함 — 출력에는 싣지 않는다)
  persons.json             온톨로지 인물 전거(저자명 정확 일치만 후보로 표시)

출력(새 폴더 참고문헌_구축/, 모두 utf-8-sig CSV + JSON)
  논문_노드.csv              논문 노드표: 서지·selection·현대문학 여부·참고문헌 수집 상태·피인용 수
  인용_간선.csv              api_linked 참고문헌 한 줄 = 간선 하나. 방향: source(인용하는 논문) → target(인용되는 논문)
  미연결_참고문헌.csv        target 없는 참고문헌 서지 원형(raw_reference_xml 제외)
  미연결_서지_집계.csv       미연결 참고문헌을 제목·저자·연도로 묶은 집계(처리 방안 검토용)
  피인용_집계.csv            target 별 인용 횟수(전체·현대문학 포함 논문에서의 인용)
  피인용_집계_현대문학.csv   현대문학 포함 논문(target)만
  coverage.json              처리 수·미수집 수·상태 분포·기준 시각(수집 미완 명시)
  (옵션) site/data/kci-citations-public.json  공개용 후보(서지·링크·DOI·간선·피인용 수만)

결정성: 입력이 같으면 바이트 동일. 생성 시각 대신 입력의 마지막 retrieved_at 을 기록한다.
수집기가 돌고 있는 동안 두 번 실행해 비교하려면 --as-of 로 retrieved_at 상한을 고정한다.

방향 근거(검수_20261029.md): KCI 상세·KOAJ 화면의 참고문헌 항목에 붙은 링크가 arti-id 가 가리키는
논문 페이지이고, 그 논문 제목이 참고문헌 제목과 같다(표본 96% 정규화 일치). 즉 arti-id = 인용되는 논문.

표준 라이브러리만 사용. 원본 폴더에는 아무것도 쓰지 않는다.
"""
import argparse
import collections
import csv
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(r'C:\onedrive\문서\대학원 공부\박사이후 논문 투고\KCI_현대문학_2000-2026')
DEFAULT_REFDIR = ROOT / '참고문헌_API'
DEFAULT_LIST = ROOT / '서지정보' / '전체수집목록.csv'
DEFAULT_OUT = ROOT / '참고문헌_구축'
HERE = Path(__file__).resolve().parent
DEFAULT_PERSONS = HERE / 'persons.json'
DEFAULT_PUBLIC = HERE / 'site' / 'data' / 'kci-citations-public.json'

KCI_VIEW = 'https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId='
MODERN_SELECTIONS = ('전문지기준포함', '온톨로지초록일치포함', '포함후보')
SOURCE_METHOD = 'kci_open_api_articleDetail'
NODE_FIELDS = ['kci_id', 'kci_url', 'title', 'authors', 'journal', 'journal_id', 'publisher', 'year', 'publication_date',
               'volume', 'issue', 'first_page', 'last_page', 'doi', 'issn', 'field', 'selection', 'modern_literature',
               'reference_status', 'reference_count', 'linked_reference_count', 'cited_by_count', 'cited_by_modern_count',
               'kci_citation_count', 'retrieved_at']
EDGE_FIELDS = ['source_kci_id', 'target_kci_id', 'reference_order', 'reference_id', 'source_kci_url', 'target_kci_url',
               'source_year', 'target_year', 'target_in_list', 'target_modern_literature', 'title_check', 'self_citation',
               'duplicate_in_source', 'reference_author', 'reference_title', 'reference_journal', 'reference_year',
               'reference_doi', 'source_method', 'retrieved_at', 'raw_response_hash', 'resolution_status']
UNLINKED_FIELDS = ['source_kci_id', 'reference_order', 'reference_id', 'type_code', 'type_name', 'title', 'author',
                   'journal', 'publisher', 'year', 'volume', 'issue', 'pages', 'doi', 'person_author_ids',
                   'person_title_ids', 'person_match', 'source_modern_literature', 'retrieved_at']
CITED_FIELDS = ['target_kci_id', 'target_kci_url', 'in_list', 'modern_literature', 'title', 'authors', 'journal', 'year',
                'cited_by_count', 'cited_by_modern_count', 'citing_reference_rows', 'kci_citation_count',
                'title_as_cited', 'author_as_cited', 'journal_as_cited']


def norm(s):
    s = unicodedata.normalize('NFKC', html.unescape(s or '')).casefold()
    return re.sub(r'[\s\W_]+', '', s)


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(s or '')).strip()


def strip_parens(s):
    return re.sub(r'[（(][^）)]*[）)]', '', s or '').strip()


def bigrams(s):
    return {s[i:i + 2] for i in range(len(s) - 1)}


def title_check(ref_title, art):
    """참고문헌 제목과 target 논문 제목의 일치 정도. exact > prefix(부제 유무) > similar(글자 2-gram Dice >= 0.5) > mismatch.
    저자·연도 일치는 쓰지 않는다 — KCI 참고문헌 레코드의 저자 칸이 잘못 연결된 논문 쪽 저자를 담는 사례가 있어(검수_20261029.md) 판별력이 없다."""
    if not art:
        return 'unknown'
    a, b = norm(ref_title), norm(art['title'])
    if a and a == b:
        return 'exact'
    if a and b and len(min(a, b, key=len)) >= 10 and (a.startswith(b) or b.startswith(a)):
        return 'prefix'
    ga, gb = bigrams(a), bigrams(b)
    if ga and gb and 2 * len(ga & gb) / (len(ga) + len(gb)) >= 0.5:
        return 'similar'
    return 'mismatch'


def load_persons(path):
    by_label = collections.defaultdict(list)
    if not path or not Path(path).exists():
        return by_label
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    for pid, rec in data.items():
        if rec.get('not_person'):
            continue
        label = clean(strip_parens(rec.get('label', '')))
        if label:
            by_label[label].append(pid)
    return {k: sorted(v) for k, v in by_label.items()}


def person_match(by_label, name):
    ids = by_label.get(clean(strip_parens(name)))
    if not ids:
        return ''
    return '|'.join(ids)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--refdir', type=Path, default=DEFAULT_REFDIR)
    ap.add_argument('--list', type=Path, default=DEFAULT_LIST)
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--persons', type=Path, default=DEFAULT_PERSONS)
    ap.add_argument('--public', type=Path, default=None, help='공개용 JSON 경로(기본: 만들지 않음). 예: site/data/kci-citations-public.json')
    ap.add_argument('--as-of', default='', help='retrieved_at 이 이 ISO 시각 이하인 응답만 포함(결정성 대조용)')
    ap.add_argument('--no-xml', action='store_true', help='XML(citation-count) 읽기 생략')
    args = ap.parse_args()
    if args.out.resolve() == args.refdir.resolve() or args.refdir.resolve() in args.out.resolve().parents:
        sys.exit('출력 폴더는 참고문헌_API 안에 둘 수 없다(수집 중 폴더 보호)')
    args.out.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(1 << 30)

    # ---- 논문 서지(초록은 읽되 어디에도 쓰지 않는다)
    arts = {}
    list_hash = hashlib.sha256()
    with open(args.list, 'rb') as fb:
        for chunk in iter(lambda: fb.read(1 << 20), b''):
            list_hash.update(chunk)
    with open(args.list, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            kid = r['kci_id']
            if not re.fullmatch(r'ART\d+', kid):
                continue
            arts[kid] = {k: clean(r.get(k, '')) for k in ('kci_url', 'title', 'authors', 'journal', 'journal_id', 'publisher', 'year',
                                                           'publication_date', 'volume', 'issue', 'first_page', 'last_page', 'doi',
                                                           'issn', 'field', 'selection')}
            arts[kid]['kci_url'] = arts[kid]['kci_url'] or KCI_VIEW + kid
    modern = {k for k, a in arts.items() if a['selection'] in MODERN_SELECTIONS}
    by_label = load_persons(args.persons)

    # ---- 참고문헌 응답 순회(파일명 = kci_id 순, 결정적)
    files = sorted(p for p in args.refdir.glob('ART*.json') if re.fullmatch(r'ART\d+\.json', p.name))
    status = collections.Counter()
    type_counts = collections.Counter()
    node_ref = {}          # kci_id -> (status, count, linked, retrieved_at, kci_cc)
    edges = []
    cited_rows = collections.defaultdict(list)       # target -> [(source, order)]
    cited_as = collections.defaultdict(collections.Counter)  # target -> Counter((title, author, journal))
    unlinked_agg = collections.Counter()
    unlinked_agg_meta = {}
    unreadable, skipped_as_of, no_retrieved = [], 0, 0
    latest_retrieved = ''
    link_counter = collections.Counter()
    title_check_counter = collections.Counter()
    person_hits = 0

    unlinked_f = open(args.out / '미연결_참고문헌.csv', 'w', encoding='utf-8-sig', newline='')
    unlinked_w = csv.DictWriter(unlinked_f, fieldnames=UNLINKED_FIELDS)
    unlinked_w.writeheader()
    n_unlinked = 0
    for p in files:
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except Exception as exc:  # 수집기가 바꿔치는 중이거나 손상
            unreadable.append({'file': p.name, 'error': type(exc).__name__})
            continue
        sid = d.get('source_kci_id') or p.stem
        ra = d.get('retrieved_at') or ''
        if not ra:
            no_retrieved += 1
        if args.as_of and ra and ra > args.as_of:
            skipped_as_of += 1
            continue
        latest_retrieved = max(latest_retrieved, ra)
        st = d.get('status', '')
        status[st] += 1
        kci_cc = ''
        if not args.no_xml:
            x = p.with_suffix('.xml')
            if x.exists():
                try:
                    m = re.search(r'<citation-count kci="(\d+)"', x.read_text(encoding='utf-8'))
                    if m:
                        kci_cc = m.group(1)
                except Exception:
                    pass
        refs = d.get('references') or []
        src_modern = sid in modern
        src_art = arts.get(sid)
        seen_targets = set()
        linked = 0
        for r in refs:
            type_counts[(r.get('type_code', ''), r.get('type_name', ''))] += 1
            t = r.get('target_kci_id', '')
            if t:
                linked += 1
                link_counter['api_linked'] += 1
                tart = arts.get(t)
                chk = title_check(r.get('title', ''), tart)
                title_check_counter[chk] += 1
                dup = t in seen_targets
                seen_targets.add(t)
                edges.append({
                    'source_kci_id': sid, 'target_kci_id': t, 'reference_order': r.get('reference_order', ''),
                    'reference_id': r.get('reference_id', ''), 'source_kci_url': KCI_VIEW + sid, 'target_kci_url': KCI_VIEW + t,
                    'source_year': (src_art or {}).get('year', '') or d.get('source_year', ''),
                    'target_year': (tart or {}).get('year', ''), 'target_in_list': 'Y' if tart else 'N',
                    'target_modern_literature': 'Y' if t in modern else 'N', 'title_check': chk,
                    'self_citation': 'Y' if t == sid else 'N', 'duplicate_in_source': 'Y' if dup else 'N',
                    'reference_author': clean(r.get('author', '')), 'reference_title': clean(r.get('title', '')),
                    'reference_journal': clean(r.get('journal', '')), 'reference_year': r.get('year', ''),
                    'reference_doi': r.get('doi', ''), 'source_method': SOURCE_METHOD, 'retrieved_at': ra,
                    'raw_response_hash': d.get('redacted_xml_sha256', ''),
                    'resolution_status': 'api_linked' if chk in ('exact', 'prefix', 'similar', 'unknown') else 'api_linked_title_mismatch',
                })
                cited_rows[t].append((sid, r.get('reference_order', 0)))
                cited_as[t][(clean(r.get('title', '')), clean(r.get('author', '')), clean(r.get('journal', '')))] += 1
            else:
                link_counter['unlinked'] += 1
                pa = person_match(by_label, r.get('author', ''))
                pt = person_match(by_label, r.get('title', ''))
                if pa or pt:
                    person_hits += 1
                row = {
                    'source_kci_id': sid, 'reference_order': r.get('reference_order', ''), 'reference_id': r.get('reference_id', ''),
                    'type_code': r.get('type_code', ''), 'type_name': r.get('type_name', ''), 'title': clean(r.get('title', '')),
                    'author': clean(r.get('author', '')), 'journal': clean(r.get('journal', '')), 'publisher': clean(r.get('publisher', '')),
                    'year': r.get('year', ''), 'volume': r.get('volume', ''), 'issue': r.get('issue', ''), 'pages': r.get('pages', ''),
                    'doi': r.get('doi', ''), 'person_author_ids': pa, 'person_title_ids': pt,
                    'person_match': 'exact' if (pa or pt) else '', 'source_modern_literature': 'Y' if src_modern else 'N', 'retrieved_at': ra,
                }
                unlinked_w.writerow(row)
                n_unlinked += 1
                key = (norm(row['title']), norm(row['author']), row['year'])
                if key[0]:
                    unlinked_agg[key] += 1
                    if key not in unlinked_agg_meta:
                        unlinked_agg_meta[key] = (row['type_name'], row['title'], row['author'], row['journal'] or row['publisher'], row['year'], row['doi'])
        node_ref[sid] = (st, len(refs), linked, ra, kci_cc)
    unlinked_f.close()

    # ---- 피인용 집계
    cited_by = {t: sorted({s for s, _ in rows}) for t, rows in cited_rows.items()}
    cited_by_modern = {t: [s for s in srcs if s in modern] for t, srcs in cited_by.items()}

    # ---- 논문 노드표(목록 전체 + 목록 밖 target 은 노드표에 넣지 않고 피인용 집계에만)
    with open(args.out / '논문_노드.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=NODE_FIELDS)
        w.writeheader()
        for kid in sorted(arts):
            a = arts[kid]
            st, n, linked, ra, cc = node_ref.get(kid, ('not_collected', '', '', '', ''))
            w.writerow({**{k: a.get(k, '') for k in NODE_FIELDS if k in a}, 'kci_id': kid,
                        'modern_literature': 'Y' if kid in modern else 'N', 'reference_status': st, 'reference_count': n,
                        'linked_reference_count': linked, 'cited_by_count': len(cited_by.get(kid, ())),
                        'cited_by_modern_count': len(cited_by_modern.get(kid, ())), 'kci_citation_count': cc, 'retrieved_at': ra})

    # ---- 간선표
    edges.sort(key=lambda e: (e['source_kci_id'], int(e['reference_order'] or 0), e['target_kci_id']))
    with open(args.out / '인용_간선.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=EDGE_FIELDS)
        w.writeheader()
        w.writerows(edges)

    # ---- 미연결 서지 집계
    with open(args.out / '미연결_서지_집계.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['count', 'type_name', 'title', 'author', 'journal_or_publisher', 'year', 'doi', 'person_author_ids'])
        for key, c in sorted(unlinked_agg.items(), key=lambda kv: (-kv[1], kv[0])):
            tn, ti, au, jo, yr, doi = unlinked_agg_meta[key]
            w.writerow([c, tn, ti, au, jo, yr, doi, person_match(by_label, au)])

    def cited_row(t):
        a = arts.get(t)
        best = sorted(cited_as[t].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        cc = node_ref.get(t, ('', '', '', '', ''))[4]
        return {'target_kci_id': t, 'target_kci_url': KCI_VIEW + t, 'in_list': 'Y' if a else 'N',
                'modern_literature': 'Y' if t in modern else 'N', 'title': (a or {}).get('title', ''),
                'authors': (a or {}).get('authors', ''), 'journal': (a or {}).get('journal', ''), 'year': (a or {}).get('year', ''),
                'cited_by_count': len(cited_by[t]), 'cited_by_modern_count': len(cited_by_modern[t]),
                'citing_reference_rows': len(cited_rows[t]), 'kci_citation_count': cc,
                'title_as_cited': best[0], 'author_as_cited': best[1], 'journal_as_cited': best[2]}

    order = sorted(cited_by, key=lambda t: (-len(cited_by[t]), t))
    for name, keep in (('피인용_집계.csv', lambda t: True), ('피인용_집계_현대문학.csv', lambda t: t in modern)):
        with open(args.out / name, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=CITED_FIELDS)
            w.writeheader()
            for t in order:
                if keep(t):
                    w.writerow(cited_row(t))
    with open(args.out / '피인용_목록.json', 'w', encoding='utf-8') as f:
        json.dump({'direction': 'cited_by[target] = 그 논문을 참고문헌에 올린(인용한) 논문의 KCI ID',
                   'cited_by': {t: cited_by[t] for t in order}}, f, ensure_ascii=False, indent=0, sort_keys=False)

    # ---- coverage
    processed = set(node_ref)
    distinct_pairs = {(e['source_kci_id'], e['target_kci_id']) for e in edges}
    coverage = {
        'collection_complete': len(processed & set(arts)) == len(arts),
        'note': '참고문헌 수집이 끝나지 않은 상태의 산출물. 전체 수집 뒤 같은 명령으로 다시 만든다.' if len(processed & set(arts)) < len(arts) else '전체 수집분 반영.',
        'list_file': args.list.name, 'list_sha256': list_hash.hexdigest(), 'list_articles': len(arts),
        'modern_literature_articles': len(modern), 'modern_selection_values': list(MODERN_SELECTIONS),
        'as_of': args.as_of or None, 'latest_retrieved_at': latest_retrieved,
        'json_files_included': len(files) - skipped_as_of, 'unreadable': unreadable,
        'processed_articles': len(processed), 'processed_in_list': len(processed & set(arts)),
        'processed_modern': len(processed & modern), 'not_collected': len(set(arts) - processed),
        'not_collected_modern': len(modern - processed), 'responses_without_retrieved_at': no_retrieved,
        'status': dict(sorted(status.items())),
        'reference_rows': sum(link_counter.values()), 'link_status': dict(sorted(link_counter.items())),
        'reference_types': {f'{k[0]} {k[1]}': v for k, v in sorted(type_counts.items())},
        'edges': len(edges), 'edges_distinct_pairs': len(distinct_pairs),
        'edges_from_modern_sources': sum(1 for e in edges if e['source_kci_id'] in modern),
        'edges_target_in_list': sum(1 for e in edges if e['target_in_list'] == 'Y'),
        'edges_target_modern': sum(1 for e in edges if e['target_modern_literature'] == 'Y'),
        'edges_self_citation': sum(1 for e in edges if e['self_citation'] == 'Y'),
        'title_check': dict(sorted(title_check_counter.items())),
        'distinct_targets': len(cited_by), 'distinct_targets_in_list': sum(1 for t in cited_by if t in arts),
        'unlinked_rows': n_unlinked, 'unlinked_distinct_bibliographies': len(unlinked_agg),
        'unlinked_rows_with_person_exact_match': person_hits,
        'direction': 'source_kci_id(인용하는 논문, API 요청 ID) → target_kci_id(인용되는 논문, reference/@arti-id)',
        'source_method': SOURCE_METHOD,
    }
    (args.out / 'coverage.json').write_text(json.dumps(coverage, ensure_ascii=False, indent=1), encoding='utf-8')

    # ---- 공개용 후보 JSON
    if args.public:
        pub_sources = sorted(s for s in processed if s in modern)
        pub_edges = {}
        for e in edges:
            if (e['source_kci_id'] in modern and e['target_kci_id'] in modern and e['title_check'] != 'mismatch'
                    and e['self_citation'] == 'N'):
                pub_edges.setdefault(e['source_kci_id'], set()).add(e['target_kci_id'])
        pub_edges = {s: sorted(ts) for s, ts in sorted(pub_edges.items())}
        node_ids = set(pub_sources)
        for ts in pub_edges.values():
            node_ids.update(ts)
        articles = {}
        for kid in sorted(node_ids):
            a = arts[kid]
            rec = {'title': a['title'], 'authors': a['authors'], 'journal': a['journal'], 'year': a['year'], 'selection': a['selection']}
            if a['doi']:
                rec['doi'] = a['doi']
            st = node_ref.get(kid)
            if st:
                rec['reference_status'] = st[0]
                rec['reference_count'] = st[1]
            # 수집 목록 안의 어느 논문(현대문학 외 포함)이 인용했는지 센 값
            rec['cited_by_in_corpus'] = len(cited_by.get(kid, ()))
            articles[kid] = rec
        cited_count = collections.Counter()
        for ts in pub_edges.values():
            cited_count.update(ts)
        public = {
            'version': 1,
            'scope': ('KCI Open API(articleDetail)로 받은 참고문헌 가운데 KCI 논문 ID가 붙은 항목만의 인용 관계. '
                      '인용하는 쪽·인용되는 쪽 모두 현대문학 포함·후보 논문(전문지기준포함·온톨로지초록일치포함·포함후보)으로 한정했다. '
                      '제목이 맞지 않는 링크와 자기인용은 뺐다. cited_by_in_corpus 는 수집 목록(국어국문학·문학 학술지 124종) 안의 '
                      '어느 논문이 인용했는지 센 값이고 cited_count 는 이 파일의 간선 수다. '
                      + ('수집 목록 %d편의 참고문헌을 모두 받은 뒤 만든 것이다(2000–2003년과 일부 논문은 KCI 가 참고문헌을 구축하지 않아 빈 응답). ' % coverage['processed_articles'] if coverage['collection_complete']
                         else '참고문헌 수집이 끝나지 않았으므로 부분 자료다. ')
                      + '학계 전체 인용 수가 아니다. 초록·본문은 싣지 않는다.'),
            'kci_url_template': KCI_VIEW + '{kci_id}',
            'direction': 'citing_by_article[인용하는 논문] = [인용되는 논문 …]',
            'coverage': {k: coverage[k] for k in ('collection_complete', 'latest_retrieved_at', 'list_articles', 'modern_literature_articles',
                                                    'processed_articles', 'processed_modern', 'not_collected_modern', 'as_of')},
            'article_count': len(articles), 'citing_articles': len(pub_edges), 'edges': sum(len(v) for v in pub_edges.values()),
            'articles': articles,
            'citing_by_article': pub_edges,
            'cited_count': dict(sorted(cited_count.items())),
        }
        args.public.parent.mkdir(parents=True, exist_ok=True)
        args.public.write_text(json.dumps(public, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        coverage['public_json'] = {'path': args.public.name, 'bytes': args.public.stat().st_size, 'articles': len(articles),
                                   'edges': public['edges']}
        (args.out / 'coverage.json').write_text(json.dumps(coverage, ensure_ascii=False, indent=1), encoding='utf-8')

    print(json.dumps({k: coverage[k] for k in ('collection_complete', 'processed_articles', 'not_collected', 'status', 'reference_rows',
                                                 'link_status', 'edges', 'edges_distinct_pairs', 'title_check', 'unlinked_rows',
                                                 'unlinked_rows_with_person_exact_match', 'latest_retrieved_at')}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
