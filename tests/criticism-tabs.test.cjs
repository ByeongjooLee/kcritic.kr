// 현장비평 탭 줄(2026-11-28): 글 찾기·글·인물·개념어·지면·관계망 — kc.js 한 곳에서 만들고 explore.html 과 graph.html 이 같이 쓴다
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const read=f=>fs.readFileSync(path.join(root,f),'utf8');

test('the criticism tab strip is defined once in kc.js and ends with the relation graph',()=>{
 const kc=read('kc.js');
 const src=kc.slice(kc.indexOf('const PERSP'),kc.indexOf('function showPerspTabs'));
 const ctx={fmt:n=>String(n)};vm.createContext(ctx);
 vm.runInContext(src+';this.out={PERSP,hrefs:Object.keys(PERSP).map(perspHref),html:perspTabs("graph",{essays:3})};',ctx);
 assert.deepEqual(Object.entries(ctx.out.PERSP),[['find','글 찾기'],['essays','글'],['people','인물'],['concepts','개념어'],['venues','지면'],['graph','관계망']]);
 assert.deepEqual([...ctx.out.hrefs],['/explore.html?p=find','/explore.html?p=essays','/explore.html?p=people','/explore.html?p=concepts','/explore.html?p=venues','/graph.html']);
 assert.equal((ctx.out.html.match(/class="on"/g)||[]).length,1);
 assert(/<a href="\/graph\.html" class="on">관계망<\/a>/.test(ctx.out.html));
 assert(ctx.out.html.includes('<small class="num">3</small>'));
});

test('explore.html and graph.html both draw the shared strip and keep the 현장비평 menu lit',()=>{
 const ex=read('explore.html'),gr=read('graph.html'),kc=read('kc.js');
 for(const [name,s] of [['explore.html',ex],['graph.html',gr]]){
  assert(s.includes('id="ptabs"'),name+' has the strip');
  assert(s.includes('showPerspTabs('),name+' draws it with the shared function');
  assert(!/const PERSP\s*=/.test(s),name+' must not redeclare PERSP (kc.js owns it)');
 }
 assert(gr.includes('shell("graph")')&&gr.includes('showPerspTabs("graph"'));
 assert(/\["essays","people","concepts","venues","graph"\]\.includes\(current\)\) current="find"/.test(kc));
});
