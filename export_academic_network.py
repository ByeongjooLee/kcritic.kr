"""Export only public bibliography, affiliation claims and relationship labels.
Usage: python export_academic_network.py INPUT_JSON [OUTPUT_JSON]
The input contains private provenance; never copy it into site/data.
"""
import json, sys
from pathlib import Path
from urllib.parse import urlparse

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
        # Explicit correction: do not re-import an unverified advisor assignment.
        if t['id']=='eeea758c003fa8ac':
            result.update(advisor_raw='', advisor_status='unconfirmed')
        return result
    assert not any(e.get('type')=='doctoral_supervision' and e.get('thesis_id')=='eeea758c003fa8ac' for e in data['relationships']), 'Unconfirmed doctoral advisor for Chun Jung-hwan'
    return dict(schema_version='1.0',updated_at=data['generated_at'],summary={k:data['summary'][k] for k in ['thesis_records','normalized_degree_institutions','unresolved_school_records','user_mentorship_edges','prior_verified_supervision_edges','supplemental_thesis_records','web_reviewed_faculty_profiles']},
        institutions=[{k:o[k] for k in ['id','name','thesis_count']} for o in data['institutions']],people=people,
        theses=[thesis(t) for t in data['theses']],reference_theses=[thesis(t) for t in data['reference_theses']],
        relationships=[{**{k:e.get(k) for k in ['id','type','source','target','status','thesis_id','institution_id']},'sources':links(e['evidence_ids'])} for e in data['relationships']],
        faculty_profiles=[{k:f[k] for k in ['person_id','name','institution','department','status','status_label','death_year','books']} for f in data['faculty_profiles']])

if __name__=='__main__':
    output=Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).parent/'site/data/academic-network-public.json'
    result=export(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f"Exported {len(result['theses'])} thesis records, {len(result['faculty_profiles'])} reviewed faculty profiles")
