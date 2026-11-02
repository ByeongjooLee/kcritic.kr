const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'site/data/school-style-public.json'),'utf8'));
test('school-style data holds only derived, non-recoverable values and public bibliography',()=>{
 const text=JSON.stringify(data);
 for(const bad of ['CRT0','KAC2','abstract','onedrive','hgohg','Codex','\\Users'])assert(!text.includes(bad),bad);
 const allowedProf=new Set(['id','name','unis','root','advisor','identity','phd_year','n_articles','source','x','y','topics','group','n_advisees','top1_uni','n_ranked','resid','n_student_profs']);
 for(const p of data.professors){for(const k of Object.keys(p))assert(allowedProf.has(k),k);assert(typeof p.x==='number'&&typeof p.y==='number');if(p.topics)assert(p.topics.length<=5);}
 const allowedThesis=new Set(['id','edge','title','year','uni','advisor','root','identity','riss','x','y','sim_advisor','rank_all','rank_uni','n_uni','topics','group']);
 for(const t of data.theses)for(const k of Object.keys(t))assert(allowedThesis.has(k),k);
});
test('school-style references resolve: every thesis advisor and edge endpoint is a listed professor',()=>{
 const ids=new Set(data.professors.map(p=>p.id));
 for(const t of data.theses)assert(ids.has(t.advisor),t.advisor);
 for(const e of data.edges){assert(ids.has(e.s),e.s);assert(ids.has(e.t),e.t);assert(['확정','추론','미확인'].includes(e.status));}
 assert.equal(data.professors.filter(p=>p.source==='kci').length,data.summary.professors);
 assert.equal(data.theses.length,data.summary.theses);
 assert.equal(data.groups.length,8);assert.equal(data.topics.length,50);
 for(const l of data.lineages)assert.equal(l.theta.length,50);
});
test('school page ships its local dependencies and is linked from the lineage tab and the theses tab bar',()=>{
 const page=fs.readFileSync(path.join(root,'school.html'),'utf8');
 for(const [,url] of page.matchAll(/(?:src|href)="([^"?#]+\.(?:js|css))"/g)){if(/^https?:/.test(url))continue;assert.ok(fs.existsSync(path.join(root,url.replace(/^\//,''))),url);}
 assert(fs.readFileSync(path.join(root,'lineage.html'),'utf8').includes('/school.html'));
 assert(fs.readFileSync(path.join(root,'thesis-browse.js'),'utf8').includes('/school.html'));
 assert(fs.readFileSync(path.join(root,'lineage.js'),'utf8').includes('/school.html?prof='));
});
