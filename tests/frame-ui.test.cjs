const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const {webcrypto}=require('node:crypto');

function fixture(){
  const nodes=new Map(),presets=[60,300,600,1200,1800].map(value=>({dataset:{duration:String(value)}}));
  for(const selector of ['#topic-label','#frame-input-kind','#duration-minutes','#create-title','#create-dialog .dialog-intro','#frame-input-select','#frame-own-text','#frame-narration','[name="topic"]','#create-submit','#production-availability','#duration-extra-seconds'])nodes.set(selector,{value:selector==='#frame-input-select'?'idea':''});
  const context={window:{dispatchEvent(){},FrameProductionEditor:()=>''},Event:class{},document:{querySelector:selector=>nodes.get(selector),querySelectorAll:()=>presets},crypto:webcrypto,TextEncoder};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../web/frame.js'),'utf8'),context);
  return {ui:context.window.FrameUI,nodes,presets};
}

test('Frame duration accepts seconds and 30 minutes, animation retains its limit',()=>{
  const {ui,nodes,presets}=fixture();ui.configureCreate('frame');
  assert.equal(ui.duration(30,0,'frame'),1800);assert.equal(ui.duration(0,15,'frame'),15);assert.equal(ui.duration(10,22,'frame'),622);
  for(const args of [[30,1,'frame'],[0,60,'frame'],[0,14,'frame'],[1.5,0,'frame'],[11,0,'animated']])assert.throws(()=>ui.duration(...args));
  presets[4].onclick();assert.equal(nodes.get('#duration-minutes').value,30);assert.equal(nodes.get('#duration-extra-seconds').value,0);
  ui.configureCreate('animated');assert.equal(presets[4].hidden,true);assert.equal(nodes.get('#frame-input-kind').hidden,true);
});

test('owned text is preserved and needs no provider, while idea generation needs an automatic provider',()=>{
  const {ui,nodes}=fixture();ui.configureCreate('frame');
  ui.availability({}, {id:'antigravity',available:false});assert.equal(nodes.get('#create-submit').disabled,true);
  nodes.get('#frame-input-select').value='narration';nodes.get('#frame-input-select').onchange();
  ui.availability({},null);assert.equal(nodes.get('#create-submit').disabled,false);
  const text='  Eine neue Idee.\n\nSie wird im eigenen Wortlaut erklärt.  ';
  const form=new Map([['duration_minutes','30'],['duration_extra_seconds','0'],['input_kind','narration'],['narration',text]]);
  const body=ui.collect({topic:''},form,'frame');assert.equal(body.narration,text);assert.equal(body.duration_seconds,1800);assert.equal(body.topic,'Eigener Sprechertext');
  form.set('input_kind','idea');assert.equal(ui.collect({},form,'frame').narration,undefined);
  assert.equal(ui.collect({},new Map([['duration_minutes','1'],['duration_extra_seconds','0']]),'animated').input_kind,undefined);
});

test('Frame preview escapes script and plan, distinguishes measured duration and needs no scene approval',()=>{
  const {ui}=fixture();
  const html=ui.editor({duration_seconds:1800,script:{metadata:{story_quality:{estimated_speech_seconds:1400}},scenes:[{narration:'<img src=x>\nNächster Absatz.'}]},frame_plan:{images:[{setting:'<script>',action:'Ein Gegenstand verändert sich.',visible_change:'Die Folge wird sichtbar.'}]}});
  assert.match(html,/&lt;img src=x&gt;/);assert.doesNotMatch(html,/<img|<script>/);
  assert.match(html,/Tatsächliche Dauer: noch nicht gemessen/);assert.match(html,/Eine Einzelbildfreigabe ist nicht nötig/);
  assert.doesNotMatch(html,/id="approve-story"/);
});

test('resume fingerprint stores no narration and changes for a different idea or mode',async()=>{
  const {ui}=fixture(),first=await ui.fingerprint({topic:'Katze',narration:'Privater eigener Text',generation_mode:'frame'});
  assert.match(first,/^[a-f0-9]{64}$/);assert.doesNotMatch(first,/Privater/);
  assert.notEqual(first,await ui.fingerprint({topic:'Feuer',generation_mode:'frame'}));
});
