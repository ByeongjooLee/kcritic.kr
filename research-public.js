// Only the intentionally public bibliography file is fetched here.
const ResearchPublic=(()=>{
 let pending;
 const load=()=>pending??=(fetch('/site/data/research-public.json').then(r=>{if(!r.ok)throw Error('자료를 불러오지 못했습니다.');return r.json();}).catch(e=>{pending=null;throw e;}));
 const thesisId=r=>{try{return new URL(r.riss_url).searchParams.get('control_no')||'';}catch{return '';}};
 const link=(kind,id,q=new URLSearchParams(location.search).get('q')||'')=>{const here=new URLSearchParams(location.search),p=new URLSearchParams({type:kind,id});if(q)p.set('q',q.slice(0,160));for(const k of ['mode','minCount','minPages','minContext','minCentrality','selectionStrength','relevanceStrength'])if(here.has(k))p.set(k,here.get(k));return '/study.html?'+p.toString();};
 return {load,thesisId,link};
})();
