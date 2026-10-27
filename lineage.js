(()=>{'use strict';
const el=id=>document.getElementById(id), ns='http://www.w3.org/2000/svg';let data,selected,scale=1;
const text=(tag,value)=>{const n=document.createElement(tag);n.textContent=value;return n;};
const svg=(tag,attrs={})=>{const n=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
const school=s=>s.replace(/대학교(?: 일반)?대학원|대학교 대학원|대학교|大學校 大學院|大學校|대학원/g,'대').replace(/\s+/g,' ').trim();
const edges=g=>g.edges.filter(e=>e.status==='confirmed'||el('pending').checked);
function detail(t,edge){const box=el('detail');box.replaceChildren(text('h3',t.name),text('p',`${t.university} · 박사 ${t.year||'연도 미상'}`),text('p',t.title));const a=text('a','학위논문 서지 · RISS ↗');a.href=t.url;a.target='_blank';a.rel='noopener noreferrer';box.append(a);const profile=text('a','학교·소속 및 사제관계 보기 →');profile.href='/academic-network.html?name='+encodeURIComponent(t.name)+'#faculty';box.append(text('p',''),profile);if(t.advisor)box.append(text('p',`학위논문 지도교수: ${t.advisor}`));if(edge)box.append(text('p',edge.status==='confirmed'?'지도 관계 확인':`추가 확인: ${edge.pending==='chronology'?'학위 취득과 지도 시점':'지도교수 직접 근거'}`));else{box.append(text('p',`지도논문 ${edges(selected).length}편`));const list=document.createElement('ol');for(const e of edges(selected)){const li=document.createElement('li'),a=text('a',`${e.student.name} · ${e.student.year} · ${e.student.title}${e.status==='pending'?' (추가 확인)':''}`);a.href=e.student.url;a.target='_blank';a.rel='noopener noreferrer';li.append(a);list.append(li);}box.append(list);}}
function draw(){
 const root=el('network');root.replaceChildren();
 if(!selected){el('selected-title').textContent='검색 결과 없음';el('selected-meta').textContent='다른 이름이나 학교로 찾아보세요.';el('detail').replaceChildren();return;}
 const family=selected.upstream?data.groups.filter(g=>g.upstream?.id===selected.upstream.id&&edges(g).length):[selected];
 const total=family.reduce((n,g)=>n+edges(g).length,0),height=Math.max(540,total*43+family.length*30+130);
 root.setAttribute('viewBox',`0 0 1100 ${height}`);root.style.height=`${height*.75}px`;root.style.minWidth='760px';
 el('selected-title').textContent=selected.upstream?`${selected.upstream.name}의 학맥`:selected.thesis.name;
 el('selected-meta').textContent=`교수가 된 연구자 ${family.length}명 · 이후 지도논문 ${total}편`;
 root.setAttribute('aria-label',`3단계 학맥: ${selected.upstream?.name||'상위 지도교수 미확인'} → ${family.map(g=>g.thesis.name).join(', ')} → 학위자 ${total}명`);
 const defs=svg('defs'),marker=svg('marker',{id:'arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:5,markerHeight:5,orient:'auto'});
 marker.append(svg('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'#a7b4c6'}));defs.append(marker);root.append(defs);
 const scene=svg('g',{id:'scene',transform:`translate(550 ${height/2}) scale(${scale}) translate(-550 ${-height/2})`});root.append(scene);
 for(const [x,label] of [[130,'1 · 박사 지도교수'],[460,'2 · 교수가 된 연구자'],[850,'3 · 이후 지도한 학위자']]){const l=svg('text',{x,y:36,'text-anchor':'middle',fill:'#5b6270','font-size':18});l.textContent=label;scene.append(l);}
 const links=svg('g'),nodes=svg('g');scene.append(links,nodes);
 function curve(x1,y1,x2,y2,pending){links.append(svg('path',{d:`M ${x1+20} ${y1} C ${(x1+x2)/2} ${y1}, ${(x1+x2)/2} ${y2}, ${x2-20} ${y2}`,fill:'none',stroke:pending?'#b9a7c7':'#cddbf6','stroke-width':2,'stroke-dasharray':pending?'5 5':'none','marker-end':'url(#arrow)'}));}
 function node(t,x,y,color,fn,sub=''){const g=svg('g',{class:'ln-node',transform:`translate(${x} ${y})`,tabindex:0,role:'button','aria-label':`${t.name} ${sub} 상세 보기`});g.append(svg('circle',{r:17,fill:color,stroke:'white','stroke-width':2}));const l=svg('text',{x:25,y:4});l.textContent=t.name;g.append(l);if(sub){String(sub).split('\n').forEach((line,i)=>{const small=svg('text',{x:25,y:21+i*17,style:'font-size:13px;fill:#687080'});small.textContent=line;g.append(small);});}g.onclick=fn;g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fn();}};nodes.append(g);}
 let cursor=95;const centers=[];
 for(const g of family){const es=edges(g),span=Math.max(70,es.length*43),y=cursor+span/2;centers.push(y);
  es.forEach((e,i)=>{const ey=cursor+(i+.5)*span/es.length;curve(460,y,850,ey,e.status==='pending');node(e.student,850,ey,'#a7beec',()=>detail(e.student,e),`${e.student.year} 박사${e.status==='pending'?' · 확인 필요':''}`);});
  node(g.thesis,460,y,g.id===selected.id?'#ca8560':'#e4b196',()=>choose(g),`지도 대학: ${(g.teachingUniversities||[]).join(' · ')||'미확인'}\n${g.thesis.year} 박사 · ${es.length}편 지도`);cursor+=span+30;
 }
 const uy=(centers[0]+centers[centers.length-1])/2;
 if(selected.upstream){const u=selected.upstream;centers.forEach(y=>curve(130,uy,460,y,false));node(u,130,uy,'#a987c8',()=>{const box=el('detail');box.replaceChildren(text('h3',u.name),text('p',`${u.university} · 박사논문 지도교수`),text('p',`확인된 지도 학위자: ${family.map(g=>g.thesis.name).join(' · ')}`),text('p','각 연구자의 박사논문 지도 근거로 묶었습니다. 이 지도교수 본인의 학위는 여기서 추정하지 않습니다.'));},u.university);}
 else{const l=svg('text',{x:130,y:uy,'text-anchor':'middle',fill:'#98a0ad','font-size':13});l.textContent='지도교수 미확인';nodes.append(l);}
 detail(selected.thesis);
}
function choose(g){selected=g;scale=1;const u=new URL(location.href);u.searchParams.set('person',g.id);history.replaceState(null,'',u);renderList();draw();}
function rankedFamilies(){
 const map=new Map();
 for(const g of data.groups){if(!edges(g).length)continue;const key=g.upstream?.id||'unknown:'+g.id;
 if(!map.has(key))map.set(key,{key,upstream:g.upstream,members:[]});map.get(key).members.push(g);}
 return [...map.values()].sort((a,b)=>Number(!a.upstream)-Number(!b.upstream)||b.members.length-a.members.length||(a.upstream?.name||a.members[0].thesis.name).localeCompare(b.upstream?.name||b.members[0].thesis.name,'ko'));
}
function renderList(){
 const families=rankedFamilies(),box=el('people');box.replaceChildren();
 el('list-count').textContent=`지도교수 ${families.filter(f=>f.upstream).length}명 · 교수 배출 인원순`;
 let rank=0;
 for(const f of families){const active=f.members.some(g=>g.id===selected?.id);const b=text('button','');b.type='button';b.className='ln-person'+(active?' on':'');b.setAttribute('aria-pressed',String(active));
 if(f.upstream){rank++;b.append(text('strong',`${rank}. ${f.upstream.name} · ${f.members.length}명`),text('small',f.upstream.university),text('small',f.members.map(g=>g.thesis.name).join(' · ')));}
 else b.append(text('strong',f.members[0].thesis.name),text('small','박사 지도교수 미확인'),text('small',f.members[0].thesis.university));
 b.onclick=()=>choose(f.members[0]);box.append(b);}
 return families.flatMap(f=>f.members);
}
function filter(){const groups=renderList();if(!groups.some(g=>g.id===selected?.id)){selected=groups[0]||null;scale=1;renderList();}draw();}
el('person-search').oninput=filter;el('pending').onchange=filter;el('zoom-in').onclick=()=>{scale=Math.min(2,scale+.2);draw();};el('zoom-out').onclick=()=>{scale=Math.max(.6,scale-.2);draw();};el('reset-view').onclick=()=>{scale=1;draw();};
fetch('/site/data/lineage-public.json').then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{data=d;el('totals').textContent=`확인된 지도교수 ${d.confirmedPeople}명 · 연결 ${d.confirmedEdges}건`;const id=new URLSearchParams(location.search).get('person');selected=d.groups.find(g=>g.id===id)||rankedFamilies()[0]?.members[0]||d.groups[0];if(selected.edges.some(e=>e.status==='pending')&&!selected.edges.some(e=>e.status==='confirmed'))el('pending').checked=true;renderList();draw();}).catch(()=>{el('totals').textContent='학맥 데이터를 불러오지 못했습니다. 새로고침해 주세요.';});
})();
