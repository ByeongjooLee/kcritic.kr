/* Public metadata only. Each source renders independently; stale searches cannot replace newer results. */
shell("search");
const ui = id => document.getElementById(id);
let generation = 0, corpus;
const make = (tag, text) => { const e=document.createElement(tag); e.textContent=text; return e; };
async function getJson(url, options={}) {
 const r=await fetch(url,{...options,signal:AbortSignal.timeout(45000)});
 if(!r.ok) throw new Error("검색 서버 응답 오류"); return r.json();
}
async function criticismData(){
 if(!corpus) corpus=Promise.all(["essays","people"].map(n=>getJson(`/site/data/v2/${n}.json`))).then(([essays,people])=>({essays,people,P:new Map(people.map(p=>[p.id,p]))})).catch(e=>{corpus=null;throw e;});
 return corpus;
}
function card(list,title,meta,url,external=false){
 const li=make("li",""),h=make("h3",""),a=make("a",title),p=make("p",meta);p.className="meta";
 if(url){a.href=url;if(external){a.target="_blank";a.rel="noopener noreferrer";}h.append(a);}else h.textContent=title;
 li.append(h,p);list.append(li);
}
async function run(event){
 event?.preventDefault();const q=ui("unified-query").value.trim();if(!q||q.length>160)return;
 const id=++generation;history.replaceState(null,"",`?q=${encodeURIComponent(q)}`);
 ui("criticism-more").href=`/explore.html?p=find&q=${encodeURIComponent(q)}`;
 ui("common-references").hidden=!/김\s*기\s*림|金起林|金基林/.test(q);
 ui("references-results").replaceChildren();ui("references-status").textContent="참고문헌 인용 빈도를 불러오고 있습니다…";
 for(const type of ["criticism","research"]){ui(`${type}-results`).replaceChildren();ui(`${type}-status`).textContent="찾고 있습니다…";}
 // 현장비평 = 인코딩한 비평글(뜻 검색 FIND) + 『창작과비평』(표제·키워드·필자·요지 낱말 검색, kc.js cbSearch) 을 한 목록으로 (2026-11-10).
 // 두 방식의 점수는 비교할 수 없으므로 각자의 순위를 번갈아 놓는다. 줄마다 지면을 적는다.
 const field=(async()=>{
  const [enc,cb]=await Promise.allSettled([
   criticismData().then(D=>FIND.find(q,D,20,async(query,words)=>getJson(`/api/find?q=${encodeURIComponent(query)}&w=${encodeURIComponent(words.join(","))}`)).then(result=>({D,result}))),
   getJson("/site/data/v2/cb_search.json").then(rows=>cbSearch(q,rows,10,true))]);
  if(id!==generation)return;
  if(enc.status==="rejected"&&cb.status==="rejected")throw enc.reason;
  const a=[],b=[];
  if(enc.status==="fulfilled"){const {D,result}=enc.value,E=new Map(D.essays.map(e=>[e.id,e]));
   for(const r of result.results){const e=E.get(r.id);if(e)a.push([e.title,[e.critic_name||D.P.get(e.critic)?.name,e.year,e.coll_name].filter(Boolean).join(" · "),`/entity.html?t=essay&id=${encodeURIComponent(e.id)}`,false]);}}
  if(cb.status==="fulfilled")for(const r of cb.value)b.push([r[3],[r[4],r[2],`『창작과비평』 ${r[1].replace(/^cb0*/,"")}호`,r[7]?"":"창비 웹진"].filter(Boolean).join(" · "),cbHref(r),!r[7]]);
  const merged=[];for(let i=0;i<Math.max(a.length,b.length);i++){if(a[i])merged.push(a[i]);if(b[i])merged.push(b[i]);}
  const slow=enc.status==="rejected"||enc.value.result.error;
  ui("criticism-status").textContent=merged.length?`${merged.length}편 · 『문학과사회』·전집 ${a.length}편, 『창작과비평』 ${b.length}편${slow?" · 일부 검색 기능 지연":""}`:"관련 비평이 없습니다.";
  for(const [t,m,u,ext] of merged)card(ui("criticism-results"),t,m,u,ext);
 })().catch(()=>{if(id===generation)ui("criticism-status").textContent="현장비평 검색을 불러오지 못했습니다. 다시 검색해 주세요.";});
 const research=(async()=>{
  const data=await getJson("/theses/api/search",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query:q})});
  if(id!==generation)return;
  ui("research-status").textContent=data.total?`${data.total.toLocaleString()}편 후보 · ${data.mode==="semantic"?"관련도순":data.mode==="filtered"?"조건 일치":"낱말 검색 (의미 검색 지연)"} 상위 ${Math.min(20,data.results.length)}편`:"일치하는 학술연구가 없습니다.";
  for(const r of data.results.slice(0,20)){let url=null;try{const u=new URL(r.riss_url);if(u.protocol==="https:"&&["riss.kr","www.riss.kr"].includes(u.hostname))url=u.href;}catch{}
   const sid=ResearchPublic.thesisId(r);
   card(ui("research-results"),r.title,[r.author,r.year,"박사학위논문"].filter(Boolean).join(" · "),sid?ResearchPublic.link("thesis",sid):url,!sid);}
 })().catch(()=>{if(id===generation)ui("research-status").textContent="학술연구 검색을 불러오지 못했습니다. 다시 검색해 주세요.";});
 const references=(async()=>{
  if(ui("common-references").hidden)return;
  const data=await ResearchPublic.load();if(id!==generation)return;
  const works=data.works.filter(w=>w.citation_count>=2);
  ui("references-status").textContent=`${works.length}종 · 같은 박사논문은 1편으로 집계`;
  for(const w of works)card(ui("references-results"),w.title,`${w.author} · ${w.year} · 참고문헌 수록 ${w.citation_count}편`,ResearchPublic.link("reference",w.id));
 })().catch(()=>{if(id===generation)ui("references-status").textContent="인용 빈도를 불러오지 못했습니다. 다시 검색해 주세요.";});
 await Promise.allSettled([field,research,references]);
}
ui("unified-form").addEventListener("submit",run);
ui("unified-query").value=(new URLSearchParams(location.search).get("q")||"").slice(0,160);
if(ui("unified-query").value.trim())run();
