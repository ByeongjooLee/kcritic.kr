const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
test('both headers search 현장비평 and 학술연구 together and send Enter to the unified search (2026-11-02)',()=>{
 for(const file of ['kc.js','kc-shell.js']){
  const s=fs.readFileSync(path.join(root,file),'utf8');
  assert(s.includes('research-public.json'),file+' loads public thesis bibliography');
  assert(s.includes('theses/api/search'),file+' asks the semantic thesis search');
  assert(s.includes('search.html?q='),file+' sends Enter to the unified search');
  assert(s.includes('박사논문 (학술연구)')&&s.includes('뜻으로 찾은 논문'),file+' labels the new groups');
  assert(s.includes('글·인물·개념어·박사논문 찾기'),file+' placeholder names theses');
  assert(!/abstract|본문/.test(s.slice(s.indexOf('theses/api/search')-400,s.indexOf('theses/api/search')+900)),file+' renders no abstract text');
 }
});
