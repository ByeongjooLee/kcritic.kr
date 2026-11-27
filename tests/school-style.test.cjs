const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'site/data/school-style-public.json'),'utf8'));
const K=20;
test('school-style data holds only derived, non-recoverable values and public bibliography',()=>{
 const text=JSON.stringify(data);
 for(const bad of ['CRT0','KAC2','abstract','onedrive','hgohg','Codex','\\Users'])assert(!text.includes(bad),bad);
 const allowedProf=new Set(['id','name','unis','root','advisor','identity','phd_year','n_articles','source','x','y','topics','group','n_advisees','top1_uni','n_ranked','resid','n_student_profs']);
 for(const p of data.professors){for(const k of Object.keys(p))assert(allowedProf.has(k),k);assert(typeof p.x==='number'&&typeof p.y==='number');if(p.topics)assert(p.topics.length<=5);}
 const allowedThesis=new Set(['id','edge','title','year','uni','advisor','root','identity','riss','x','y','sim_advisor','rank_all','rank_uni','n_uni','topics','group']);
 for(const t of data.theses){for(const k of Object.keys(t))assert(allowedThesis.has(k),k);if(t.topics)assert(t.topics.length<=5);}
 // 문서별 토픽 비중은 상위 5개까지만 싣는다. 20개 전체 비중은 계보(여러 논문의 평균)에만 있다
 const allowedTopic=new Set(['id','name','words','share_thesis','share_kci','n_top','n_ge10','stable','runs_matched','runs_other','review','group']);
 for(const t of data.topics){for(const k of Object.keys(t))assert(allowedTopic.has(k),k);assert(t.words.length<=10);}
 const allowedLineage=new Set(['root','name','n_theses','n_topic','n_professors','topics','theta']);
 for(const l of data.lineages)for(const k of Object.keys(l))assert(allowedLineage.has(k),k);
});
test('school-style references resolve: every thesis advisor and edge endpoint is a listed professor',()=>{
 const ids=new Set(data.professors.map(p=>p.id));
 for(const t of data.theses)assert(ids.has(t.advisor),t.advisor);
 for(const e of data.edges){assert(ids.has(e.s),e.s);assert(ids.has(e.t),e.t);assert(['확정','추론','미확인'].includes(e.status));}
 assert.equal(data.professors.filter(p=>p.source==='kci').length,data.summary.professors);
 assert.equal(data.theses.length,data.summary.theses);
 assert.equal(data.groups.length,8);
});
test('school-style topics are the formal 20-topic model and stay internally consistent',()=>{
 assert.equal(data.topics.length,K);assert.equal(data.summary.topics,K);
 assert.deepEqual(data.topics.map(t=>t.id),[...Array(K).keys()]);
 const withTopics=data.theses.filter(t=>t.topics);
 assert.equal(withTopics.length,data.summary.theses_with_topics);
 assert.equal(data.professors.filter(p=>p.source==='kci'&&p.topics).length,data.summary.professors_with_topics);
 assert.equal(data.topics.filter(t=>t.stable).length,data.summary.topics_stable);
 // 주제별 '가장 큰 논문' 수는 논문 쪽 상위 토픽과 맞아야 한다
 const top=new Map();for(const t of withTopics)top.set(t.topics[0][0],(top.get(t.topics[0][0])||0)+1);
 for(const t of data.topics)assert.equal(t.n_top,top.get(t.id)||0,'n_top t'+t.id);
 for(const x of [...data.theses,...data.professors])for(const [k,v] of x.topics||[]){assert(k>=0&&k<K);assert(v>=0&&v<=1);}
 for(const g of data.groups)assert(g.topic===null||(g.topic>=0&&g.topic<K));
 for(const l of data.lineages){assert(l.n_topic<=l.n_theses);if(l.theta){assert.equal(l.theta.length,K);assert(Math.abs(l.theta.reduce((a,b)=>a+b,0)-1)<0.01);}else assert.equal(l.n_topic,0);}
 // 이름은 연구자가 정하기 전까지 비워 둔다. 검토 중인 토픽은 표시가 있어야 화면이 주제로 단정하지 않는다
 for(const t of data.topics)assert.equal(t.name,null);
 const review=data.topics.filter(t=>t.review);assert.equal(review.length,1);assert(review[0].words.includes('타자')&&review[0].words.includes('담론'));
 // 토픽 20개 모형의 효과 행은 표본이 다르므로 따로 표시된다
 const e20=data.effects.filter(e=>e.rep==='lda20'&&e.tier==='all');assert.equal(e20.length,7);for(const e of e20)assert.equal(e.n_theses,data.summary.theses_with_topics);
});
test('school page defaults to the topic view, keeps the map view as a choice, and never prints topic numbers',()=>{
 const page=fs.readFileSync(path.join(root,'school.html'),'utf8'),js=fs.readFileSync(path.join(root,'school.js'),'utf8');
 for(const id of ['view-topic','view-map','topicList','topicSelect','topicPanel','map','heat','effects','detail'])assert(page.includes(`id="${id}"`),id);
 assert(/id="view-map"[^>]*hidden/.test(page));assert(!/id="view-topic"[^>]*hidden/.test(page));
 assert(page.includes('data-view="topic"')&&page.includes('data-view="map"'));
 assert(js.includes("'kc-school-view'"));assert(js.includes("q.get('view')"));
 assert(!js.includes('`t${k} `'),'topic labels must be words, not t-numbers');
 assert(js.includes("colorBy = 'root'"),'map colours default to lineage');assert(page.indexOf('<option value="root">')<page.indexOf('<option value="group">'));
 for(const old of ['형제','삼촌','조부 '])assert(!page.includes(old)&&!js.includes(old),old);
});
test('school page ships its local dependencies and is linked from the lineage tab; the theses tab bar links the chapter',()=>{
 const page=fs.readFileSync(path.join(root,'school.html'),'utf8');
 for(const [,url] of page.matchAll(/(?:src|href)="([^"?#]+\.(?:js|css))"/g)){if(/^https?:/.test(url))continue;assert.ok(fs.existsSync(path.join(root,url.replace(/^\//,''))),url);}
 assert(fs.readFileSync(path.join(root,'lineage.html'),'utf8').includes('/school.html'));
 const browse=fs.readFileSync(path.join(root,'thesis-browse.js'),'utf8');assert(browse.includes('/lineage.html'));assert(!browse.includes('/school.html'));   // 학맥·학풍은 별도 묶음(2026-11-27): 학술연구 탭 줄에는 묶음으로 가는 링크 하나만
 assert(page.includes('<h1>학맥·학풍</h1>')&&page.includes("shell('lineage')"));
 assert(fs.readFileSync(path.join(root,'lineage.js'),'utf8').includes('/school.html?prof='));
});
