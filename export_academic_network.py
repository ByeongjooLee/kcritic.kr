"""Export only public bibliography, affiliation claims and relationship labels.
Usage: python export_academic_network.py INPUT_JSON [OUTPUT_JSON]
The input contains private provenance; never copy it into site/data.
"""
import hashlib, json, sys
from pathlib import Path
from urllib.parse import urlparse

# 천정환(성균관대) 박사논문(서울대 2002)의 지도교수 = 조남현(서울대 국어국문학과). 근거: 서울대 중앙도서관 Primo 레코드의
# 지도교수 항목 "조남현." + 연구자 확인(2026-10-27/28). genealogy-library.json 과 같은 판정. 입력 JSON 쪽이 고쳐지면 이 블록을 지운다.
CHUN={'thesis_id':'eeea758c003fa8ac','advisor_name':'조남현',
      'source':'faculty:ea3257552dd98526',   # 조남현 — 서울대 국어국문학과 명예교수(웹 확인 소속)
      'target':'person:2d1ff3affe546ada',    # 천정환 — 성균관대 교수(제공 정보)
      'institution_id':'org:84e40c965cf842a3',   # 서울대학교
      'sources':['https://snu-primo.hosted.exlibrisgroup.com/primo-explore/fulldisplay?context=L&vid=82SNU&lang=ko_KR&docid=82SNU_INST21422400670002591',
                 'https://www.riss.kr/search/detail/DetailView.do?p_mat_type=be54d9b8bc7cdb09&control_no=eeea758c003fa8ac&keyword=']}

def export(data):
    evidence={e['id']:e for e in data['evidence']}
    def links(ids):
        urls=[]
        for eid in ids:
            e=evidence.get(eid,{})
            for url in [e.get('url',''),*e.get('extra_urls',[]),*e.get('record',{}).get('identity_urls',[])]:
                if urlparse(url).scheme=='https' and url not in urls:urls.append(url)
        return urls
    people=[]
    for p in data['people']:
        affiliations=[]
        for a in p['affiliations']:
            if a.get('superseded_by'):continue
            affiliations.append({**{k:a.get(k) for k in ['institution_id','department','role','temporal_status','verification','display_status','end_date']},'sources':links(a['evidence_ids'])})
        people.append(dict(id=p['id'],name=p['name'],thesis_ids=p['thesis_ids'],affiliations=affiliations,death_year=p.get('life_status',{}).get('year'),books=[b['title'] for b in p.get('books',[])]))
    def thesis(t):
        result = {k:t.get(k) for k in ['id','title','author_raw','author_person_id','year_raw','institution_id','university_raw','riss_url','advisor_raw']}
        # Explicit correction (2026-10-27 unconfirmed -> 2026-10-28 confirmed): the input still carries the
        # withdrawn 김윤식 assignment as blank/unconfirmed. SNU library record + researcher confirmation
        # establish 조남현 (Seoul National University) as the advisor of 천정환's 2002 dissertation.
        if t['id']==CHUN['thesis_id']:
            result.update(advisor_raw=CHUN['advisor_name'], advisor_status='library_confirmed')
        return result
    relationships=[{**{k:e.get(k) for k in ['id','type','source','target','status','thesis_id','institution_id']},'sources':links(e['evidence_ids'])} for e in data['relationships']]
    assert not any(e['type']=='doctoral_supervision' and e['thesis_id']==CHUN['thesis_id'] for e in relationships), 'input already carries a doctoral advisor for Chun Jung-hwan; drop the explicit correction'
    ids={p['id'] for p in people}
    assert CHUN['source'] in ids and CHUN['target'] in ids, 'Chun Jung-hwan correction refers to unknown person ids'
    relationships.append({'id':'edge:'+hashlib.sha1(f"doctoral_supervision|{CHUN['source']}|{CHUN['target']}|{CHUN['thesis_id']}".encode()).hexdigest()[:16],
        'type':'doctoral_supervision','source':CHUN['source'],'target':CHUN['target'],'status':'library_confirmed',
        'thesis_id':CHUN['thesis_id'],'institution_id':CHUN['institution_id'],'sources':CHUN['sources']})
    summary={k:data['summary'][k] for k in ['thesis_records','normalized_degree_institutions','unresolved_school_records','user_mentorship_edges','prior_verified_supervision_edges','supplemental_thesis_records','web_reviewed_faculty_profiles']}
    summary['library_confirmed_supervision_edges']=sum(e['type']=='doctoral_supervision' and e['status']=='library_confirmed' for e in relationships)
    return dict(schema_version='1.0',updated_at=data['generated_at'],summary=summary,
        institutions=[{k:o[k] for k in ['id','name','thesis_count']} for o in data['institutions']],people=people,
        theses=[thesis(t) for t in data['theses']],reference_theses=[thesis(t) for t in data['reference_theses']],
        relationships=relationships,
        faculty_profiles=[{k:f[k] for k in ['person_id','name','institution','department','status','status_label','death_year','books']} for f in data['faculty_profiles']])

if __name__=='__main__':
    output=Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).parent/'site/data/academic-network-public.json'
    result=export(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f"Exported {len(result['theses'])} thesis records, {len(result['faculty_profiles'])} reviewed faculty profiles")
