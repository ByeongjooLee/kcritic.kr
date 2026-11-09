import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from build_changbi_toc import write

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT.parent / '문학과사회' / 'changbi_corpus'
FIELDS = ('u', 't', 'a', 'y', 'l', 's', 'h', 'kw', 'c')
LABELS = {'주장', '논거', '비판', '제언'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def validate(entry, meta, screening, review, body):
    if screening['status'] != 'queued':
        return '; '.join(screening['reasons'])
    if not review:
        return '본문 대조 검수 대기'
    if review.get('status') != 'pass':
        return '본문 검수 보류: ' + review.get('reason', '사유 미기재')
    if review.get('uid') != entry['u'] or review.get('full_body_read') is not True or not review.get('reason') or not review.get('reviewer'):
        return '검수 증빙 불완전'
    for record in (screening, review):
        if record.get('summary_hash') != digest(entry) or record.get('body_hash') != digest(body):
            return '검수 후 자료 변경: 재검수 필요'
    if not meta['in_scope'] or meta['source'] != 'html' or entry['a'] != meta['author']:
        return '범위/본문 출처/저작자 재확인 필요'
    if not all(isinstance(entry.get(field), str) and entry[field].strip() for field in ('u', 't', 'a', 'l', 's', 'h')):
        return '필수 문자열 누락'
    if not isinstance(entry.get('y'), int) or not isinstance(entry.get('kw'), list) or not all(isinstance(word, str) for word in entry['kw']):
        return '연도/키워드 형식 오류'
    if not isinstance(entry.get('c'), list) or any(not isinstance(claim, list) or len(claim) != 2 or not isinstance(claim[0], str) or claim[1] not in LABELS for claim in entry['c']):
        return '주장 형식 오류'
    texts = [entry['h'], entry['s']] + [claim[0] for claim in entry['c']]
    normalized = re.sub(r'[\W_]+', '', body)
    grams = {normalized[start:start+20] for start in range(len(normalized)-19)}
    for value in texts:
        text = re.sub(r'[\W_]+', '', value)
        if any(text[start:start+20] in grams for start in range(len(text)-19)):
            return '원문 20자 이상 일치: 재서술 검토 필요'
    public_text = json.dumps({field: entry[field] for field in FIELDS}, ensure_ascii=False)
    if re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|[A-Za-z]:[\\/]|file://', public_text):
        return '전자우편/로컬 경로 노출 의심'
    return None


def main():
    prep = CORPUS / 'site_prep'
    parser = argparse.ArgumentParser()
    parser.add_argument('--reviews-dir', type=Path, default=prep / 'reviews')
    args = parser.parse_args()
    summaries = json.loads((CORPUS / 'summary/summaries.json').read_text(encoding='utf-8'))['arts']
    plan = {row['uid']: row for row in json.loads((CORPUS / 'summary/plan.json').read_text(encoding='utf-8'))['items']}
    screening = {row['uid']: row for row in json.loads((prep / 'publication_screening.json').read_text(encoding='utf-8'))}
    bodies = {}
    for line in (CORPUS / 'data/articles_complete.jsonl').open(encoding='utf-8'):
        row = json.loads(line)
        bodies[f"CB-{int(row['item_id']):05d}"] = row['body_text']
    public, decisions = {}, []
    for entry in sorted(summaries, key=lambda value: value['u']):
        uid = entry['u']
        review_path = args.reviews_dir / (uid + '.json')
        review = json.loads(review_path.read_text(encoding='utf-8')) if review_path.exists() else None
        reason = validate(entry, plan[uid], screening[uid], review, bodies[uid])
        decisions.append({'uid': uid, 'status': 'held' if reason else 'published', 'reason': reason or '본문 대조 및 공개 필드 검사 통과'})
        if not reason:
            public[plan[uid]['item_id']] = {field: entry[field] for field in FIELDS}
    destination = ROOT / 'site/data/v2/changbi_summaries.json'
    previous = json.loads(destination.read_text(encoding='utf-8')) if destination.exists() else {}
    removed = set(previous) - set(public)
    if removed:
        raise RuntimeError(f'기존 공개분이 검수 대장에서 빠짐: {sorted(removed)}. 대장 확인 후 다시 빌드')
    write(destination, public)
    write(prep / 'publication_decisions.json', decisions)
    stats = {'public': len(public), 'claims': sum(len(row['c']) for row in public.values()),
             'held': len(decisions)-len(public), 'reasons': dict(sorted(Counter(row['reason'] for row in decisions if row['status']=='held').items()))}
    write(prep / 'publication_stats.json', stats)
    print(json.dumps({key: value for key, value in stats.items() if key != 'reasons'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
