// 학맥·학풍 묶음(2026-11-27): 네 번째 상단 메뉴, 묶음 안 탭 줄, 학술연구 탭 줄의 넘김 링크, 학맥 화면의 교수·제자 이름 검색
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const read=f=>fs.readFileSync(path.join(root,f),'utf8');
const data=JSON.parse(read('site/data/genealogy-library.json'));

const CHAPTER=[['/lineage.html','학맥(學脈)'],['/school.html','학풍(學風)'],['/academic-network.html','학교·소속']];
test('the three chapter screens share one tab strip, mark their own tab, and light the 학맥·학풍 menu',()=>{
 for(const [page] of CHAPTER){
  const s=read(page.slice(1));
  assert(s.includes('<h1>학맥·학풍</h1>'),page+' chapter heading');
  assert(s.includes("shell('lineage')"),page+' active menu');assert(!s.includes("shell('theses')"),page);
  const nav=s.match(/<nav class="tabs" aria-label="학맥·학풍">([\s\S]*?)<\/nav>/)[1];
  const tabs=[...nav.matchAll(/<a ([^>]*)>([^<]*)<\/a>/g)].map(m=>({attr:m[1],label:m[2],href:m[1].match(/href="([^"]+)"/)[1]}));
  assert.deepEqual(tabs.slice(0,3).map(t=>[t.href,t.label]),CHAPTER);
  for(const t of tabs.slice(0,3))assert.equal(t.attr.includes('aria-current="page"'),t.href===page,page+' '+t.href);
  assert.equal(tabs.length,4);assert(tabs[3].attr.includes('class="out"'));assert(tabs[3].href.startsWith('/theses/'));   // 끝: 학술연구로 넘어가는 링크 하나
  assert(!nav.includes('글 찾기')&&!nav.includes('개념어'),page+' no thesis tabs inside the chapter');
 }
 // 옛 주소는 그대로: 파일이 제자리에 있고 Worker 화면 경로 목록에도 남아 있다
 const wr=read('wrangler.jsonc');for(const p of ['/lineage.html','/school.html','/academic-network.html'])assert(wr.includes(`"${p}"`),p);
});

test('the theses tab bar drops the lineage/school tabs and ends with one link to the chapter',()=>{
 const made=[],el=(tag,text,cls)=>({tag,textContent:text,className:cls||'',attrs:{},setAttribute(k,v){this.attrs[k]=v;}});
 const nav={children:[],replaceChildren(){this.children=[];},append(...n){this.children.push(...n);},insertBefore(n,ref){const i=this.children.indexOf(ref);this.children.splice(i<0?this.children.length:i,0,n);}};
 const h1={textContent:''};
 const document={title:'',createElement:t=>{const n=el(t);made.push(n);return n;},querySelector:q=>q.includes('.tabs')?nav:h1};
 vm.runInNewContext(read('thesis-browse.js')+';ThesisBrowse.tabs();',{document,location:{search:'?p=advisors'},URLSearchParams,Object,Map,Set,Promise,fetch:async()=>({ok:false})});
 assert.deepEqual(nav.children.map(a=>a.textContent),['글 찾기','글','인물','개념어','학위수여기관','지도교수','학맥·학풍 →']);
 const last=nav.children.at(-1);assert.equal(last.href,'/lineage.html');assert.equal(last.className,'out');
 assert.equal(nav.children.filter(a=>a.className==='on').map(a=>a.textContent).join(),'지도교수');
 assert.equal(h1.textContent,'학술연구');
 assert(read('kc.css').includes('.tabs a.out'));
});

test('footers, the home page and the about page point at the chapter',()=>{
 for(const f of ['kc.js','kc-shell.js'])assert(/lineage\.html">학맥·학풍/.test(read(f)),f+' footer');
 const home=read('index.html'),about=read('about.html');
 for(const p of ['lineage.html','school.html','academic-network.html']){assert(home.includes(`href="/${p}"`),'index '+p);assert(about.includes(`href="${p}"`),'about '+p);}
 assert(home.includes('<h3>학맥·학풍</h3>'));
});

// ── 학맥 화면을 가짜 DOM 에서 돌려 이름 검색·이동·주소를 확인한다
async function boot(search=''){
 const els=new Map(),timers=[];
 const stub=id=>({id,value:'',checked:id==='stepwise'||id==='inferred',innerHTML:'',textContent:'',hidden:false,disabled:false,dataset:{},style:{},clientWidth:1000,clientHeight:700,scrollTop:0,
  classList:{toggle(){},add(){},remove(){}},setAttribute(){},addEventListener(){},querySelectorAll:()=>[],querySelector:()=>null,getBoundingClientRect:()=>({top:0,bottom:700,left:0}),scrollIntoView(){}});
 const location={search,href:'https://kcritic.kr/lineage.html'+search};
 const ctx={document:{getElementById:id=>{if(!els.has(id))els.set(id,stub(id));return els.get(id);},createElement:()=>stub('x')},location,
  history:{replaceState(_s,_t,u){location.href=String(u);location.search=new URL(String(u)).search;}},
  localStorage:{getItem:()=>null,setItem(){}},fetch:async()=>({ok:true,json:async()=>JSON.parse(JSON.stringify(data))}),
  URL,URLSearchParams,Element:{prototype:{}},performance:{now:()=>0},requestAnimationFrame:()=>0,cancelAnimationFrame(){},innerHeight:800,console,addEventListener(){},
  setTimeout:f=>timers.push(f),clearTimeout:i=>{if(i)timers[i-1]=null;}};
 ctx.window=ctx;vm.runInNewContext(read('lineage.js'),ctx);
 for(let i=0;i<20&&!ctx.genealogyState;i++)await new Promise(r=>setImmediate(r));
 assert(ctx.genealogyState,'lineage.js started');
 return {ctx,els,location,q:()=>new URL(location.href).searchParams,flush:()=>{for(const f of timers.splice(0))f&&f();}};
}
const out=new Map(),inc=new Map();for(const e of data.edges){(out.get(e.source)||out.set(e.source,[]).get(e.source)).push(e);(inc.get(e.target)||inc.set(e.target,[]).get(e.target)).push(e);}
const byId=new Map(data.nodes.map(n=>[n.id,n]));
const canRoot=id=>byId.get(id).kind==='professor'&&out.has(id);

test('name search finds students as well as professors and never merges namesakes',async()=>{
 const {ctx}=await boot();
 // 같은 이름의 학위자가 가장 많은 이름을 자료에서 고른다(자료가 바뀌어도 통하게)
 const groups=new Map();for(const n of data.nodes)if(!canRoot(n.id))(groups.get(n.name)||groups.set(n.name,[]).get(n.name)).push(n);
 const [name,same]=[...groups].sort((a,b)=>b[1].length-a[1].length)[0];assert(same.length>=2,'namesakes exist');
 const f=ctx.lineageSearch(name),exact=f.students.filter(r=>r.name===name);
 assert.deepEqual(exact.map(r=>r.id).sort(),same.map(n=>n.id).sort());            // 노드마다 한 줄, 합치지 않음
 assert.deepEqual(f.students.slice(0,exact.length).map(r=>r.name),exact.map(r=>r.name),'exact matches come first');
 for(const r of exact){const es=inc.get(r.id);assert(es?.length,r.id);assert(r.university,'degree university');assert(r.advisors.length>=1,'advisor shown');
  assert(es.some(e=>String(e.year)===String(r.year))||r.year===null);assert(es.some(e=>r.advisors.includes(byId.get(e.source).display_name||byId.get(e.source).name)));}
 for(const r of f.professors)assert(canRoot(r.id));
 // 지도논문이 있는 교수는 교수 묶음에, 띄어쓰기는 무시
 const prof=data.nodes.find(n=>canRoot(n.id));
 assert(ctx.lineageSearch(' '+prof.name.split('').join(' ')+' ').professors.some(r=>r.id===prof.id));
 assert.deepEqual(JSON.parse(JSON.stringify(ctx.lineageSearch('   '))),{professors:[],students:[],total:0});
 const page=read('lineage.html');assert(page.includes('교수·제자'));assert(read('lineage.js').includes('data-go='));
});

test('choosing a student opens the advisor\'s lineage, selects the student and writes a shareable address',async()=>{
 const {ctx,q,els}=await boot();
 const student=data.nodes.find(n=>n.kind==='student'&&inc.has(n.id));
 assert.equal(ctx.lineageGo(student.id),true);
 let s=ctx.genealogyState();
 assert(inc.get(student.id).some(e=>e.source===s.root),'root is the advisor');assert.equal(s.selected,student.id);
 assert(s.visible.some(x=>x.id===student.id&&x.depth===1));
 assert.equal(q().get('person'),s.root);assert.equal(q().get('focus'),student.id);
 assert(els.get('detail').innerHTML.includes(student.name));
 // 교수를 고르면 지금처럼 시작점으로, focus 는 지운다
 const prof=data.nodes.find(n=>canRoot(n.id)&&n.id!==s.root);
 assert.equal(ctx.lineageGo(prof.id),true);s=ctx.genealogyState();
 assert.equal(s.root,prof.id);assert.equal(s.selected,prof.id);assert.equal(q().get('person'),prof.id);assert.equal(q().has('focus'),false);
 assert.equal(ctx.lineageGo('no-such-person'),false);
});

test('a focus address expands the collapsed generations down to that person, and ?person=<student> resolves to the advisor',async()=>{
 // 두 세대 아래 사람: 교수 A → 교수 B(A의 제자) → 사람 C
 let pick=null;
 for(const a of data.nodes){if(!canRoot(a.id))continue;for(const e1 of out.get(a.id)){if(!canRoot(e1.target)||e1.target===a.id)continue;const e2=out.get(e1.target).find(e=>e.target!==a.id&&e.target!==e1.target&&!(out.get(a.id)||[]).some(x=>x.target===e.target));if(e2){pick={a:a.id,b:e1.target,c:e2.target};break;}}if(pick)break;}
 assert(pick,'a two-generation chain exists');
 const deep=await boot('?person='+encodeURIComponent(pick.a)+'&focus='+encodeURIComponent(pick.c)+'&view=simple');
 const s=deep.ctx.genealogyState();
 assert.equal(s.stepwise,true);assert.equal(s.root,pick.a);assert.equal(s.selected,pick.c);
 assert(s.expanded.includes(pick.b),'the professor on the way is expanded');
 assert(s.visible.some(x=>x.id===pick.c&&x.depth>=2));
 assert.equal(deep.q().get('view'),'simple','view parameter is kept');
 // 펼치지 않은 다른 교수는 접힌 채 그대로
 assert(s.visible.filter(x=>x.depth===1&&x.hidden).every(x=>x.id!==pick.b));
 const student=data.nodes.find(n=>n.kind==='student'&&inc.has(n.id));
 const viaPerson=await boot('?person='+encodeURIComponent(student.id));
 const t=viaPerson.ctx.genealogyState();
 assert(inc.get(student.id).some(e=>e.source===t.root));assert.equal(t.selected,student.id);
 assert.equal(viaPerson.q().get('person'),t.root);assert.equal(viaPerson.q().get('focus'),student.id);
 // 주소가 없으면 예전과 같다
 const plain=await boot();assert.equal(plain.ctx.genealogyState().root,data.default_root);assert.equal(plain.location.search,'');
});

test('a search with exactly one match opens that person without a click; several matches wait for a choice',async()=>{
 const {ctx,els,flush}=await boot();
 const type=v=>{els.get('search').value=v;els.get('search').oninput();};
 const hits=name=>data.nodes.filter(n=>[n.name,n.display_name,...(n.aliases||[])].some(x=>x&&x.replace(/\s+/g,'').includes(name))||(canRoot(n.id)&&(n.affiliations||[]).join(' ').replace(/\s+/g,'').includes(name)));
 // 자료에서 이름이 하나뿐인 학위자(지도교수가 시작 교수가 아닌 사람)를 고른다
 const start=ctx.genealogyState().root;
 const solo=data.nodes.find(n=>n.kind==='student'&&inc.has(n.id)&&!inc.get(n.id).some(e=>e.source===start)&&hits(n.name).length===1);assert(solo,'a uniquely named student exists');
 type(solo.name);assert.equal(ctx.genealogyState().root,start,'nothing moves before the pause');
 flush();const st=ctx.genealogyState();
 assert.equal(st.selected,solo.id);assert(inc.get(solo.id).some(e=>e.source===st.root),'advisor is the root');
 // 고친 뒤 다시 타이핑하면 앞선 예약은 버린다
 const {ctx:c2,els:e2,flush:f2}=await boot();const s2=c2.genealogyState().root;
 e2.get('search').value=solo.name;e2.get('search').oninput();e2.get('search').value='';e2.get('search').oninput();f2();
 assert.equal(c2.genealogyState().root,s2);
 // 같은 이름이 여럿이면 자동으로 열지 않는다
 const groups=new Map();for(const n of data.nodes)if(!canRoot(n.id))(groups.get(n.name)||groups.set(n.name,[]).get(n.name)).push(n);
 const [many]=[...groups].sort((a,b)=>b[1].length-a[1].length)[0];
 e2.get('search').value=many;e2.get('search').oninput();f2();
 assert.equal(c2.genealogyState().root,s2);assert.equal(c2.genealogyState().selected,s2);
});

test('chapter pages version their scripts and styles so a deploy is not hidden by the browser cache',()=>{
 const vs=new Set();
 for(const f of ['lineage.html','school.html','academic-network.html']){const page=read(f);
  const tags=[...page.matchAll(/(?:src|href)="\/([\w-]+\.(?:js|css))(\?v=([\w-]+))?"/g)];assert(tags.length>=4,f);
  for(const t of tags){assert(t[3],f+' '+t[1]+' has ?v=');vs.add(t[3]);}}
 assert.equal(vs.size,1,'one version across the chapter');
});
