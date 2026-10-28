const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'site/data/academic-network-public.json'),'utf8'));

test('all public references resolve; general mentorship never becomes doctoral supervision',()=>{
 const people=new Map(data.people.map(p=>[p.id,p]));
 const orgs=new Set(data.institutions.map(o=>o.id));
 const theses=new Set([...data.theses,...data.reference_theses].map(t=>t.id));
 assert.equal(data.theses.length,2189);assert.equal(data.reference_theses.length,2);
 assert.equal(data.relationships.filter(e=>e.type==='doctoral_supervision'&&e.status==='previously_verified').length,164);
 assert.equal(data.relationships.filter(e=>e.type==='doctoral_supervision').length,165);   // 164 기존 검증 + 조남현→천정환 도서관 확인(2026-10-28)
 assert.equal(data.relationships.filter(e=>e.type==='mentorship').length,5);
 for(const t of data.theses){assert(people.has(t.author_person_id));assert(!t.institution_id||orgs.has(t.institution_id));}
 for(const p of people.values()){for(const t of p.thesis_ids)assert(theses.has(t));for(const a of p.affiliations)assert(orgs.has(a.institution_id));}
 for(const e of data.relationships){assert(people.has(e.source)&&people.has(e.target));if(e.type==='mentorship')assert.equal(e.thesis_id,null);else assert(theses.has(e.thesis_id));}
 const ho=[...people.values()].find(p=>p.name==='호창수');assert(ho);assert.equal(ho.thesis_ids.length,0);
 assert(![...people.values()].filter(p=>p.death_year).some(p=>p.affiliations.some(a=>a.temporal_status==='current_reported')));
 const yoon=data.theses.find(t=>t.author_raw==='윤대석');assert.equal(yoon.advisor_raw,'');
});

test('public projection contains no private evidence fields or filesystem paths',()=>{
 const forbidden=new Set(['record','evidence_ids','notes','reason','pdf_hits','pdf_path','download_record','identity_evidence_ids','advisor_evidence','verification_note','source_record','sha256','text','note','evidence']);
 function walk(v){if(Array.isArray(v))return v.forEach(walk);if(v&&typeof v==='object'){for(const [k,x]of Object.entries(v)){assert(!forbidden.has(k),k);walk(x);}}else if(typeof v==='string'){assert(!/(?:^|\s)[A-Z]:[\\/]|file:\/\/|Users[\\/]hgohg|pdf_image_verified/i.test(v));}}
 walk(data);
 const allowed=new Set(['id','title','title_raw','author','author_raw','author_person_id','year_raw','institution_id','university_raw','riss_url','advisor','advisor_raw','advisor_status']);for(const t of data.theses)for(const k of Object.keys(t))assert(allowed.has(k),k);   // title_raw·author = 한자 원표기·한글 표기 (2026-10-28)
});

async function render(ok=true){
 const nodes=new Map();const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',innerHTML:'',disabled:false,insertAdjacentHTML(_where,html){this.innerHTML+=html;}});return nodes.get(id);}};
 vm.runInNewContext(fs.readFileSync(path.join(root,'academic-network.js'),'utf8'),{document,fetch:async()=>({ok,json:async()=>data}),URL,URLSearchParams,location:{search:''},Map,String,Math});
 await new Promise(resolve=>setImmediate(resolve));return nodes;
}
test('directory filters, historical status and thesis pagination work',async()=>{
 const n=await render();assert.equal(n.get('thesis-count').textContent,'2,189건');
 assert(n.get('faculty-results').innerHTML.includes('2018년 작고'));
 n.get('faculty-status').value='deceased';n.get('faculty-status').onchange();assert(n.get('faculty-count').textContent.includes('7명'));
 n.get('faculty-status').value='';n.get('faculty-query').value='기억의 계단';n.get('faculty-query').oninput();assert(n.get('faculty-results').innerHTML.includes('김인환'));
 n.get('school').value='?';n.get('school').onchange();assert.equal(n.get('thesis-count').textContent,'4건');assert(n.get('next').disabled);
 n.get('school').value='';n.get('thesis-query').value='윤대석';n.get('thesis-query').oninput();assert(n.get('thesis-results').innerHTML.includes('1940년대'));
 n.get('relationship-type').value='mentorship';n.get('relationship-type').onchange();assert.equal(n.get('relationship-count').textContent,'5건');
 n.get('relationship-query').value='호창수';n.get('relationship-query').oninput();assert.equal(n.get('relationship-count').textContent,'1건');assert(n.get('relationship-results').innerHTML.includes('윤대석'));
});
test('network failure has a visible recovery message',async()=>{const n=await render(false);assert(n.get('load-status').textContent.includes('새로고침'));});
test('existing lineage links to the new screen without rewriting doctoral edges',()=>{
 assert(fs.readFileSync(path.join(root,'lineage.html'),'utf8').includes('/academic-network.html'));
 assert(fs.readFileSync(path.join(root,'lineage.js'),'utf8').includes('encodeURIComponent(t.name)'));
 assert(fs.readFileSync(path.join(root,'.assetsignore'),'utf8').includes('/tests'));
});

test('Chun Jung-hwan advisor is Cho Nam-hyun (SNU library record + researcher confirmation, 2026-10-28)',async()=>{
 const t=data.theses.find(t=>t.id==='eeea758c003fa8ac');
 assert.equal(t.advisor_raw,'조남현');assert.equal(t.advisor_status,'library_confirmed');
 const people=new Map(data.people.map(p=>[p.id,p]));
 const edge=data.relationships.find(e=>e.type==='doctoral_supervision'&&e.target===t.author_person_id);
 assert.equal(people.get(edge.source).name,'조남현');assert.equal(edge.status,'library_confirmed');assert.equal(edge.thesis_id,t.id);
 assert(people.get(edge.source).affiliations.some(a=>data.institutions.find(o=>o.id===a.institution_id).name==='서울대'));
 assert(edge.sources.some(u=>u.includes('82SNU_INST21422400670002591')));
 assert.equal(data.relationships.filter(e=>e.type==='doctoral_supervision').length,data.summary.prior_verified_supervision_edges+data.summary.library_confirmed_supervision_edges);
 const n=await render();n.get('thesis-query').value='천정환';n.get('thesis-query').oninput();
 assert(n.get('thesis-results').innerHTML.includes('조남현'));assert(!n.get('thesis-results').innerHTML.includes('미확인'));
 n.get('relationship-query').value='천정환';n.get('relationship-query').oninput();
 assert.equal(n.get('relationship-count').textContent,'1건');assert(n.get('relationship-results').innerHTML.includes('조남현 → 천정환'));assert(n.get('relationship-results').innerHTML.includes('도서관 기록'));
});

test('Kim In-hwan and Oh Hyeong-yeop mentorship identifies Korea University',async()=>{
 const people=new Map(data.people.map(p=>[p.id,p.name]));
 const edge=data.relationships.find(e=>people.get(e.source)==='김인환'&&people.get(e.target)==='오형엽');
 assert.equal(edge.type,'mentorship');assert.equal(edge.thesis_id,null);
 assert.equal(data.institutions.find(o=>o.id===edge.institution_id).name,'고려대');
 const n=await render();assert(n.get('mentorships').innerHTML.includes('고려대 사제관계'));
});
