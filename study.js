shell("theses");
(async()=>{
 const root=document.getElementById('study-root');
 try{
 const data=await ResearchPublic.load(),params=new URLSearchParams(location.search),kind=params.get('type'),id=params.get('id');
 const searchQuery=(params.get('q')||'').trim().slice(0,160);
 const numberOption=(key,def,min,max)=>{const v=Number(params.get(key)??def);return Number.isFinite(v)?Math.min(max,Math.max(min,v)):def;};
 // Only conditions present in the URL are sent; the server fills its own defaults (e.g. minContext .45).
 const options={};
 if(['auto','lexical','semantic'].includes(params.get('mode')))options.mode=params.get('mode');
 if(params.has('minCount'))options.minCount=Math.round(numberOption('minCount',3,1,100));
 if(params.has('minPages'))options.minPages=Math.round(numberOption('minPages',2,1,100));
 if(params.has('minContext'))options.minContext=numberOption('minContext',0,0,1);
 if(params.has('minCentrality'))options.minCentrality=numberOption('minCentrality',0,0,1);
 for(const k of ['selectionStrength','relevanceStrength'])if(params.has(k))options[k]=Math.round(numberOption(k,0,0,100));
 let semanticAvailable=false;
 const isRef=kind==='reference',doc=(isRef?data.works:data.theses).find(x=>x.id===id);
 if(!doc){root.textContent='해당 연구를 찾을 수 없습니다.';return;}
 document.title=doc.title+' — kcritic';
 const citationResponse=await fetch('/site/data/thesis-citations-public.json');
 if(!citationResponse.ok)throw Error('citation data unavailable');
 const citationData=await citationResponse.json(),links=citationData.citing_by_thesis;
 const norm=s=>s.replace(/[\s\p{P}\p{S}]/gu,'');
 let outgoing=isRef?[]:data.works.filter(w=>w.citing_thesis_ids.includes(doc.id));
 let outgoingTheses=isRef?[]:data.theses.filter(t=>(links[t.id]||[]).includes(doc.id)&&!outgoing.some(w=>w.author===t.author&&norm(w.title)===norm(t.title)));
 let filterNote='서지정보가 대조된 선행연구입니다. 아직 연결되지 않은 참고문헌이 있어 전체 목록과는 다릅니다.',basis=new Map(),citation=null;
 if(searchQuery&&!isRef){
   try{
     const response=await fetch('/theses/api/references',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:searchQuery,thesisId:doc.id,options}),signal:AbortSignal.timeout(45000)});
     if(!response.ok)throw Error('filter unavailable');
     const filtered=await response.json();
     semanticAvailable=Boolean(filtered.capabilities?.semanticAvailable);
     if(filtered.mode==='citation-context'){
       // The thesis's own bibliography and footnotes were compared with the question (server-side, no text returned).
       citation=filtered;
       const t=filtered.topic||{},parts=[t.people?.length?'인물 '+t.people.join('·'):'',t.concepts?.length?'개념 '+t.concepts.join('·'):'',t.residual?.length?'그 밖의 말 '+t.residual.join('·'):''].filter(Boolean);
       filterNote=`이 논문의 참고문헌 ${Number(filtered.entries||0).toLocaleString()}건(각주에서만 확인된 ${Number(filtered.footnoteEntries||0).toLocaleString()}건 포함)을 질문과 대조했습니다. 질문 해석: ${parts.length?parts.join(' / '):'“'+(t.text||searchQuery)+'”'}. 제목 일치, 그 인물·개념이 나온 본문 문단에서의 인용, 질문과 인용 문맥의 뜻 유사도(기준 ${Number(filtered.options?.minContext??.45)}) 가운데 하나라도 충족한 항목입니다. ${filtered.topicTheses?`순서는 같은 주제의 보유 논문 ${Number(filtered.topicTheses.count||0).toLocaleString()}편(${{people:'인물 중심성',concepts:'개념 중심성',title:'제목 일치',all:'주제 집합 없음 → 전체'}[filtered.topicTheses.basis?.[0]]||'기준'}${filtered.topicTheses.basis?.length>1?' 등':''})이 같은 저작을 함께 인용한 수가 많은 순이고, 질문 인물 본인의 글은 뒤에 둡니다. `:''}OCR 에서 자동 추출한 서지(검수 전)이며, 보유 박사논문과 대조된 항목만 상세 페이지로 연결됩니다.${semanticAvailable?'':' 뜻 유사도는 이번 응답에서 계산되지 않았습니다.'}`;
     }else{
       basis=new Map(filtered.results.map(r=>[r.type+':'+r.id,r.basis]));
       outgoing=outgoing.filter(w=>basis.has('reference:'+w.id));
       outgoingTheses=outgoingTheses.filter(t=>basis.has('thesis:'+t.id));
       filterNote=filtered.mode==='semantic'?`문맥 관련성이 확인된 이 논문의 참고문헌 후보에서 중심성 선별 강도를 적용했습니다. 전체 검색의 연도·학교 조건은 인용 관계를 제한하지 않습니다. 관련성이 확정됐다는 뜻은 아닙니다. 본문 미확보로 판정하지 못한 자료 ${filtered.unassessed||0}건은 제외했습니다.`:filtered.mode==='no-linked-references'?'이 논문은 아직 참고문헌 색인이 없고 서지가 대조된 참고문헌도 없어 질문과 대조할 수 없습니다. 0편은 관련 연구가 없다는 뜻이 아닙니다.':filtered.mode==='unconfirmed-query'?'이 질문의 선행연구 관련성은 판정하지 못했습니다. 0편은 관련 연구가 없다는 뜻이 아닙니다.':`이 논문은 아직 참고문헌 색인이 없어, 서지가 대조된 참고문헌의 제목·본문 단어 출현으로만 찾은 잠정 후보입니다.`;
     }
   }catch{
     outgoing=[];outgoingTheses=[];filterNote='검색어 관련성을 확인하지 못해 목록을 표시하지 않았습니다. 잠시 후 다시 시도해 주세요.';
   }
 }
 const matching=isRef?doc:data.works.find(w=>w.author===doc.author&&norm(w.title)===norm(doc.title));
 const incomingIds=new Set([...(matching?.citing_thesis_ids||[]),...(!isRef?(links[doc.id]||[]):[])]);
 const incoming=data.theses.filter(t=>incomingIds.has(t.id)).sort((a,b)=>Number(b.year)-Number(a.year)||a.title.localeCompare(b.title));
 const safeLink=u=>{try{const x=new URL(u);return x.protocol==='https:'&&['riss.kr','www.riss.kr'].includes(x.hostname)?x.href:'';}catch{return '';}};
 const matchedThesis=isRef&&doc.format.includes('박사')?data.theses.find(t=>t.author===doc.author&&norm(t.title)===norm(doc.title)):null;
 const institution=isRef?matchedThesis:doc;
 const url=safeLink(doc.riss_url||matchedThesis?.riss_url);
 const bibliographyUrl=url||(isRef?'https://www.riss.kr/search/Search.do?query='+encodeURIComponent(doc.author+' '+doc.title):'');
 const bibliographyLabel=url?'RISS 상세 서지 ↗':'RISS에서 서명 검색 ↗';
 const rows=(items,ref)=>items.map(x=>`<article class="row"><div class="yr num">${esc(x.year||'—')}</div><div><h4><a href="${ResearchPublic.link(ref?'reference':'thesis',x.id)}">${esc(x.title)}</a></h4><div class="meta">${esc(x.author)} · ${esc(ref?x.format:'박사학위논문')}${ref?' · 참고문헌 수록 '+x.citation_count+'편':''}${basis.get((ref?'reference':'thesis')+':'+x.id)==='body'?' · 본문 출현 조건 충족':basis.get((ref?'reference':'thesis')+':'+x.id)==='semantic'?' · 문맥·중심성 조건 충족':''}</div></div></article>`).join('');
 const BASIS={title:'제목 일치',author:'질문 인물의 글(1차 자료)',context:'인용 문맥',semantic:'뜻 유사도'};
 const citationRows=items=>items.map(x=>{const link=x.thesis?ResearchPublic.link('thesis',x.thesis):'';const chips=(x.basis||[]).map(b=>b==='context'?`질문 용어가 나온 인용 문맥 ${x.hits}곳`:b==='semantic'?`뜻 유사도 ${Number(x.semantic).toFixed(2)}`:BASIS[b]||b).join(' · ');
   const cited=x.citedByAll?`<b>같은 주제 논문 ${x.citedByTopic}편</b>이 함께 인용 (보유 논문 전체 ${x.citedByAll}편)`:'';
   return `<article class="row"><div class="yr num">${esc(x.year||'—')}</div><div><h4>${link?`<a href="${link}">${esc(x.title)}</a>`:esc(x.title)}</h4><div class="meta">${esc(x.author)} · ${esc(x.kind)}${x.source==='footnote'?' · 각주에서만 확인':''}${cited?' · '+cited:''}${x.contexts?` · 본문 인용 ${x.contexts}곳`:''}${chips?' · '+esc(chips):''}${link?' · 보유 논문':''}</div></div></article>`;}).join('');
 const searchSettings=new URLSearchParams({q:searchQuery});for(const k of ['relevanceStrength','selectionStrength'])if(k in options)searchSettings.set(k,options[k]);
 const controls=searchQuery&&!isRef?`<p class="note"><a href="/theses/?${esc(searchSettings.toString())}">학술연구 전체 검색에서 범위 조절 ↗</a></p>`:'';
 root.innerHTML=`<div class="ent-head"><div class="crumb"><a href="/search.html?q=${encodeURIComponent(searchQuery||doc.title)}">통합검색</a><span>/</span><span>학술연구</span></div><span class="pill t-essay">${esc(isRef?doc.format:'박사학위논문')}</span><h1>${esc(doc.title)}</h1><div class="ent-sub">${esc(doc.author)} · ${esc(doc.year||'연도 미상')}${institution?.university?' · '+esc(institution.university):''}${url?` · <a href="${esc(url)}" target="_blank" rel="noopener noreferrer">RISS 서지정보 ↗</a>`:''}</div></div>
 <div class="ent"><div><div class="kv" style="grid-template-columns:repeat(2,1fr)"><div><b class="num">${incoming.length}</b><span>이 연구를 참고문헌에 수록한 박사논문</span></div><div><b class="num">${isRef?doc.topic:citation?citation.results.length:outgoing.length+outgoingTheses.length}</b><span>${isRef?'연결된 연구 주제':citation?'질문과 관련된 참고문헌':'연결된 선행연구'}</span></div></div>
 <div class="tabs" role="tablist" aria-label="연구 상세"><button id="tab-relations" role="tab" aria-controls="panel-relations" aria-selected="true" class="on">인용 관계</button><button id="tab-bibliography" role="tab" aria-controls="panel-bibliography" aria-selected="false">서지정보</button></div>
 <section id="panel-relations" role="tabpanel" aria-labelledby="tab-relations" style="padding-top:24px">${!isRef?(citation?`<div class="block"><h3>이 논문이 참고한 ‘${esc(citation.topic?.text||searchQuery)}’ 관련 선행연구 (${citation.results.length}건)</h3>${controls}<p class="note">${esc(filterNote)}</p>${citation.results.length?`<div class="tabs" role="tablist" aria-label="정렬" id="citation-sort" style="margin:8px 0 4px"><button role="tab" data-sort="cited" aria-selected="true" class="on">많이 인용한 순</button><button role="tab" data-sort="recent" aria-selected="false">최신순</button></div>`:''}<div class="rows" id="citation-rows">${citation.results.length?citationRows(citation.results):'<p class="note">참고문헌과 각주 인용 가운데 이 질문의 인물·개념이 제목이나 인용 문맥에 나오는 항목이 없습니다. OCR 누락일 수 있습니다.</p>'}</div></div>`:`<div class="block"><h3>이 논문이 참고한 ${searchQuery?'‘'+esc(searchQuery)+'’ ':''}선행연구 (${outgoing.length+outgoingTheses.length}편)</h3>${controls}<p class="note">${esc(filterNote)}</p><div class="rows">${outgoingTheses.length?rows(outgoingTheses,false):''}${outgoing.length?rows(outgoing,true):''}${!outgoing.length&&!outgoingTheses.length?'<p class="note">현재 선별 기준을 충족하는 선행연구 후보가 없습니다.</p>':''}</div></div>`):''}<div class="block"><h3>${isRef?'이 연구를':'이 논문을'} 참고한 후속연구 (${incoming.length}편)</h3><p class="note">보유 박사논문의 참고문헌에서 확인된 연결입니다. 같은 논문은 1편으로 셉니다. 이 목록에 없다고 인용되지 않은 것은 아닙니다.</p><div class="rows">${incoming.length?rows(incoming,false):'<p class="note">현재 확인된 후속연구가 없습니다. 인용이 없다는 뜻은 아닙니다.</p>'}</div></div></section>
 <section id="panel-bibliography" role="tabpanel" aria-labelledby="tab-bibliography" hidden style="padding-top:24px"><div class="panel"><h5>서지정보</h5><p>${esc(doc.author)} (${esc(doc.year||'연도 미상')}). ${esc(doc.title)}. ${esc(isRef?doc.format:'박사학위논문')}.</p>
 ${(!isRef||doc.format.includes('박사'))?`<dl><dt>학위수여 대학</dt><dd>${esc(institution?.university||'미확인')}</dd><dt>지도교수</dt><dd>${esc(institution?.advisor||'미확인 — 수집 서지정보에 명시되지 않음')}</dd><dt>학위·전공</dt><dd>${esc(institution?.degree||'미확인')}</dd></dl>`:''}
 ${bibliographyUrl?`<p><a class="btn" href="${esc(bibliographyUrl)}" target="_blank" rel="noopener noreferrer">${bibliographyLabel}</a></p>`:''}<p class="note">참고문헌의 표기를 정리한 정보이며 일부 연도·판본 표기가 다를 수 있습니다.</p></div></section></div>
 <aside class="aside"><div class="panel"><h5>집계 범위</h5><p class="note">박사논문 ${data.corpus_size.toLocaleString()}편의 참고문헌을 대상으로, 작가·주제 제한 없이 저자·제목·학위 유형·연도가 대조된 박사논문 간 연결과 기존 검수 연구를 보여줍니다. OCR 오류와 표기 차이로 연결이 빠질 수 있습니다.</p><p class="note">본문 각주만 확인된 연결은 이 수치에서 제외했습니다. 학계 전체 인용 빈도나 연구의 질·긍정 평가를 뜻하지 않습니다.</p></div><div class="panel"><h5>공개 정보</h5><p class="note">서지정보와 인용 관계만 제공합니다. 원문·평가·내부 검토 기록은 비공개입니다.</p></div></aside></div>`;
 for(const key of ['relations','bibliography'])document.getElementById('tab-'+key).onclick=()=>{for(const k of ['relations','bibliography']){const on=k===key,b=document.getElementById('tab-'+k);b.classList.toggle('on',on);b.setAttribute('aria-selected',String(on));document.getElementById('panel-'+k).hidden=!on;}};
 // Sort tabs for query-matched references: co-citation count (server order) or newest first. Primary sources stay last in both.
 const sortBar=document.getElementById('citation-sort');
 if(sortBar&&citation){
   const primary=x=>(x.basis||[]).includes('author')?1:0,order=citation.results.map((x,i)=>i);
   const sorters={cited:(a,b)=>order.indexOf(a)-order.indexOf(b),recent:(a,b)=>primary(a)-primary(b)||(Number(b.year)||0)-(Number(a.year)||0)||(b.citedByTopic||0)-(a.citedByTopic||0)||order.indexOf(a)-order.indexOf(b)};
   for(const btn of sortBar.querySelectorAll('button'))btn.onclick=()=>{for(const b of sortBar.querySelectorAll('button')){const on=b===btn;b.classList.toggle('on',on);b.setAttribute('aria-selected',String(on));}
     document.getElementById('citation-rows').innerHTML=citationRows([...citation.results].sort(sorters[btn.dataset.sort]||sorters.cited));};
 }
 }catch{root.textContent='자료를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.';}
})();
