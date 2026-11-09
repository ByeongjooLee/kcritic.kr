import json
import re
from pathlib import Path
from build_changbi_toc import write

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT.parent / '문학과사회' / 'changbi_corpus'
APPROVED = {'CB-07335', 'CB-07374', 'CB-07375', 'CB-07376', 'CB-07378'}
FIELDS = ('u', 't', 'a', 'y', 'l', 's', 'h', 'kw', 'c')


def main():
    summaries = json.loads((CORPUS / 'summary/summaries.json').read_text(encoding='utf-8'))['arts']
    plan = {row['uid']: row for row in json.loads((CORPUS / 'summary/plan.json').read_text(encoding='utf-8'))['items']}
    bodies = {}
    for line in (CORPUS / 'data/articles_complete.jsonl').open(encoding='utf-8'):
        row = json.loads(line)
        uid = f"CB-{int(row['item_id']):05d}"
        if uid in APPROVED:
            bodies[uid] = re.sub(r'[\W_]+', '', row['body_text'])
    public = {}
    excluded = []
    for row in summaries:
        uid = row['u']
        if uid not in APPROVED:
            excluded.append(f'{uid}\t未검수: 기존 공개 보류 기준 유지')
            continue
        meta = plan[uid]
        assert meta['in_scope'] and meta['source'] == 'html'
        assert row['a'] == meta['author'] and row['g'] == '촌평' and not row.get('n')
        texts = [row['h'], row['s']] + [claim[0] for claim in row['c']]
        body = bodies[uid]
        grams = {body[start:start + 20] for start in range(len(body) - 19)}
        overlap = any(any(text[start:start + 20] in grams for start in range(len(text) - 19))
                      for text in (re.sub(r'[\W_]+', '', value) for value in texts))
        if overlap:
            excluded.append(f'{uid}\t원문 20자 이상 일치: 재서술 검수 대기')
            continue
        entry = {field: row[field] for field in FIELDS}
        assert not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', json.dumps(entry, ensure_ascii=False))
        public[meta['item_id']] = entry
    write(ROOT / 'site/data/v2/changbi_summaries.json', public)
    prep = CORPUS / 'site_prep'
    (prep / 'pending_20261109_summaries.txt').write_text('\n'.join(row['u'] for row in public.values()) + '\n', encoding='utf-8')
    (prep / 'exclude_20261109_summaries.tsv').write_text('uid\treason\n' + '\n'.join(excluded) + '\n', encoding='utf-8')
    print(f'Public: {len(public)}; held: {len(excluded)}')


if __name__ == '__main__':
    main()
