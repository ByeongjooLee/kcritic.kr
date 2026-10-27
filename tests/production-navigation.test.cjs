const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
test('both headers preserve the three production navigation destinations',()=>{
 for(const file of ['kc.js','kc-shell.js']){
  const source=fs.readFileSync(path.join(root,file),'utf8');
  const declaration=source.match(/const NAV = \[[\s\S]*?\];/)[0];
  const nav=JSON.parse(JSON.stringify(vm.runInNewContext(declaration+'NAV')));
  assert.deepEqual(nav,[['search','통합검색','/search.html'],['find','현장비평','/explore.html?p=find'],['theses','학술연구','/theses/']]);
 }
});
test('restored research screens ship all local dependencies and resolvable citations',()=>{
 for(const page of ['index.html','search.html','study.html','academic-network.html']){
  const source=fs.readFileSync(path.join(root,page),'utf8');
  for(const [,url] of source.matchAll(/(?:src|href)="([^"?]+\.(?:js|css))"/g)){
   if(/^https?:/.test(url))continue;
   assert.ok(fs.existsSync(path.join(root,url.replace(/^\//,''))),url);
  }
 }
 const research=JSON.parse(fs.readFileSync(path.join(root,'site/data/research-public.json'),'utf8'));
 const citations=JSON.parse(fs.readFileSync(path.join(root,'site/data/thesis-citations-public.json'),'utf8'));
 const ids=new Set(research.theses.map(x=>x.id));
 for(const [id,links] of Object.entries(citations.citing_by_thesis)){
  assert.ok(ids.has(id),id);for(const ref of links)assert.ok(ids.has(ref),ref);
 }
});
