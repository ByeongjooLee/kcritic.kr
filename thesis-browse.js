/* Public bibliography and already-public keyword labels only. No source text. */
const ThesisBrowse=(()=>{
 const labels={find:'글 찾기',essays:'글',people:'인물',concepts:'개념어',institutions:'학위수여기관',advisors:'지도교수'};
 const params=new URLSearchParams(location.search),view=Object.hasOwn(labels,params.get('p'))?params.get('p'):'find';
 const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
 let pending;
 const load=()=>pending??=Promise.all(['/site/data/research-public.json','/site/data/thesis-topics-public.json'].map(async u=>{const r=await fetch(u);if(!r.ok)throw Error('서지정보를 불러오지 못했습니다.');return r.json();})).then(([b,t])=>{
   const tags=new Map(t.topics.map(t=>[t.id,t]));return b.theses.map(d=>({...d,institution:t.institutions?.[d.university]||d.university,people:tags.get(d.id)?.people||[],concepts:tags.get(d.id)?.concepts||[]}));
 }).catch(e=>{pending=null;throw e;});
 const href=(p,field='',term='')=>'/theses/?'+new URLSearchParams({p,...(field?{field,term}:{})});
 function tabs(){document.title=labels[view]+' · 학술연구 — kcritic';const nav=document.querySelector('.thesis-search .tabs');nav.replaceChildren();for(const [p,label] of Object.entries(labels)){const a=node('a',label,p===view?'on':'');a.href=href(p);if(p===view)a.setAttribute('aria-current','page');nav.append(a);}const lineage=node('a','학맥(學脈)');lineage.href='/lineage.html';nav.append(lineage);document.querySelector('.ex-head h1').textContent='학술연구';}
 function card(d,query='',options={}){
   const item=node('article',undefined,'row'),year=node('div',String(d.year||'—'),'yr num'),body=node('div'),h=node('h4'),a=node('a',d.title);
   const p=new URLSearchParams({type:'thesis',id:d.id});if(query){p.set('q',query);for(const k of ['relevanceStrength','selectionStrength'])p.set(k,options[k]||0);}
   a.href='/study.html?'+p;h.append(a);body.append(h);
   const meta=node('div',undefined,'meta');
   for(const [field,value] of [['author',d.author],['institution',d.institution||d.university]])if(value){const l=node('a',value);l.href=href('essays',field,value);meta.append(l);}meta.append(node('span','박사학위논문'));body.append(meta);
   for(const [field,values,label] of [['person',d.people,'인물'],['concept',d.concepts,'개념어']])if(values?.length){const tags=node('div',undefined,'tags');tags.append(node('span',label,'tag-label'));for(const value of values){const l=node('a',value);l.href=href('essays',field,value);tags.append(l);}body.append(tags);}
   if(d.riss_url){const u=new URL(d.riss_url);if(u.protocol==='https:'&&['www.riss.kr','riss.kr'].includes(u.hostname)){const l=node('a','RISS에서 확인 ↗','external');l.href=u.href;l.target='_blank';l.rel='noopener noreferrer';body.append(l);}}
   item.append(year,body);return item;
 }
 const match=(d,field,term)=>!field||({author:()=>d.author===term,institution:()=>((d.institution||d.university)===term||d.university===term),advisor:()=>(d.advisor||'').split(/[,·、]/).map(x=>x.trim()).includes(term),person:()=>d.people.includes(term),concept:()=>d.concepts.includes(term)}[field]?.()??false);
 async function render(){
   const side=document.querySelector('.thesis-search .ex>aside'),main=document.querySelector('.thesis-results');
   side.replaceChildren();main.replaceChildren(node('p','서지정보를 불러오고 있습니다…','note'));
   try{
     const docs=await load(),field=params.get('field')||'',term=params.get('term')||'';
     const label=node('label','목록에서 찾기'),input=node('input');input.type='search';input.placeholder=view==='essays'?'제목·저자·기관':'이름으로 찾기';label.append(input);side.append(label);
     const note=node('p',view==='people'||view==='concepts'?'인물·개념어는 본문에서 자동 추출한 주요 태그입니다. 논문 저자와 연구 대상 인물을 구분합니다.':'확인된 서지정보를 기준으로 탐색합니다. 미확인 정보는 임의로 채우지 않습니다.','note');side.append(note);
     let kind='all';if(view==='people'){const l=node('label','인물 구분'),select=node('select');for(const [v,t] of [['all','전체'],['author','논문 저자'],['person','연구 대상 인물']]){const o=node('option',t);o.value=v;select.append(o);}select.onchange=()=>{kind=select.value;draw();};l.append(select);side.append(l);}
     let limit=50;
     function draw(){main.replaceChildren();const q=input.value.trim().toLocaleLowerCase();
       const heading=node('h2',labels[view],'search-title');main.append(heading);
       if(field){const active=node('p',term+' · 선택한 조건','note'),clear=node('a','조건 해제');clear.href=href('essays');active.append(' ',clear);main.append(active);}
       if(view==='essays'){
         const found=docs.filter(d=>match(d,field,term)&&(!q||[d.title,d.author,d.university,String(d.year)].some(x=>x?.toLocaleLowerCase().includes(q)))).sort((a,b)=>b.year-a.year||a.title.localeCompare(b.title,'ko'));
         main.append(node('p',found.length.toLocaleString()+'편 · 최신 연도순','note'));const list=node('div',undefined,'rows');found.slice(0,limit).forEach(d=>list.append(card(d)));main.append(list);more(found.length);
       }else{
         const groups=new Map();const add=(f,t,id)=>{if(!t||t.includes('미확인'))return;const key=f+':'+t;if(!groups.has(key))groups.set(key,{field:f,name:t,ids:new Set()});groups.get(key).ids.add(id);};
         for(const d of docs){if(view==='people'){if(kind!=='person')add('author',d.author,d.id);if(kind!=='author')d.people.forEach(t=>add('person',t,d.id));}else if(view==='concepts')d.concepts.forEach(t=>add('concept',t,d.id));else if(view==='institutions')add('institution',d.institution||d.university,d.id);else if(view==='advisors')(d.advisor||'').split(/[,·、]/).forEach(t=>add('advisor',t.trim(),d.id));}
         const found=[...groups.values()].filter(g=>!q||g.name.toLocaleLowerCase().includes(q)).sort((a,b)=>b.ids.size-a.ids.size||a.name.localeCompare(b.name,'ko'));
         main.append(node('p',found.length.toLocaleString()+'개 항목 · 연결된 논문 수순','note'));const list=node('div',undefined,'rows');
         const kinds={author:'논문 저자',person:'연구 대상 인물',concept:'개념어',institution:'학위수여기관',advisor:'지도교수'};
         for(const g of found.slice(0,limit)){const row=node('article',undefined,'row'),n=node('div',g.ids.size+'편','yr num'),body=node('div'),h=node('h4'),a=node('a',g.name);a.href=href('essays',g.field,g.name);h.append(a);body.append(h,node('p',kinds[g.field],'meta'));row.append(n,body);list.append(row);}main.append(list);more(found.length);
       }
     }
     function more(n){if(n<=limit)return;const b=node('button','50개 더 보기','btn');b.type='button';b.onclick=()=>{limit+=50;draw();};main.append(b);}
     input.oninput=()=>{limit=50;draw();};draw();
   }catch(e){main.replaceChildren(node('p',e.message,'note'));}
 }
 return {view,tabs,load,card,render};
})();
