const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');

function fixture(){
  const nodes=new Map(['workspace','jobs','new-button','jobs-title','empty-new-button'].map(id=>['#'+id,{innerHTML:'existing home',setAttribute(){}}]));
  const buttons=['animated','frame'].map(mode=>({dataset:{mode},setAttribute(name,value){this[name]=value},focus(){}}));
  const state={activeMode:'animated',selected:'old',jobs:[{id:'old',topic:'Legacy',video_type:'stickman',status:'script_review',aspect_ratio:'16:9'},{id:'new',topic:'<img>',generation_mode:'frame',video_type:'stickman',status:'script_review',aspect_ratio:'9:16'}],
    dirtyScript:false,dirtyProduction:false,dirtyFeedback:false,actionPending:false,ProcessProgress:{busy:false},timer:123,
    $:selector=>nodes.get(selector),document:{querySelectorAll:selector=>selector==='[data-mode]'?buttons:[]},labels:{script_review:'Skript prüfen'},
    esc:value=>String(value).replaceAll('<','&lt;').replaceAll('>','&gt;'),openCreate(){},openJob(){},addContextHelp(){},toast(){},clearTimeout(){},window:{PipelineSettings:{open(){}}}};
  vm.createContext(state);
  vm.runInContext(source.slice(source.indexOf('const animatedHome='),source.indexOf('async function openJob(')),state);
  return {state,nodes,buttons};
}

test('mode navigation filters legacy and Frame jobs without changing stored jobs',()=>{
  const {state,nodes,buttons}=fixture();
  state.drawJobList();assert.match(nodes.get('#jobs').innerHTML,/Legacy/);assert.doesNotMatch(nodes.get('#jobs').innerHTML,/data-id="new"/);
  assert.equal(state.switchMode('frame'),true);
  assert.equal(state.selected,null);assert.equal(nodes.get('#new-button').hidden,false);
  assert.equal(nodes.get('#new-button').textContent,'＋ Frame-Skript');
  assert.match(nodes.get('#jobs').innerHTML,/&lt;img&gt;/);assert.doesNotMatch(nodes.get('#jobs').innerHTML,/Legacy/);
  assert.match(nodes.get('#workspace').innerHTML,/erst nach dem vollständigen Funktionstest/);
  assert.equal(buttons[1]['aria-selected'],'true');assert.equal(buttons[0].tabIndex,-1);
  assert.equal(state.jobs.length,2);
  state.switchMode('animated');assert.equal(nodes.get('#new-button').hidden,false);assert.equal(nodes.get('#workspace').innerHTML,'existing home');
});

test('mode changes preserve unsaved input and pending work, keyboard uses the same guard',()=>{
  for(const field of ['dirtyScript','dirtyProduction','dirtyFeedback','actionPending']){
    const {state,buttons}=fixture();state[field]=true;
    assert.equal(state.switchMode('frame'),false);buttons[0].onkeydown({key:'End',preventDefault(){}});
    assert.equal(state.activeMode,'animated');assert.equal(state.selected,'old');
  }
  const {state}=fixture();state.ProcessProgress.busy=true;assert.equal(state.switchMode('frame'),false);
});

test('editing the narrator preserves the exact saved production configuration',()=>{
  const {state}=fixture();
  state.productionConfigAvailable=()=>false;state.VoiceEditor={render:()=>'<div>voice</div>'};
  vm.runInContext(source.slice(source.indexOf('function productionConfigEditor('),source.indexOf('function targetList(')),state);
  const config={profile_id:'custom',video_type:'stickman',script_provider:'antigravity',media_provider:'procedural_stickman',voice_provider:'piper',editor:'remotion'};
  const html=state.productionConfigEditor({production_config:config,script_version:4,language:'de',script:{scenes:[{narration:'Text'}]}});
  assert.match(html,/<div hidden>/);assert.match(html,/value="custom" selected/);assert.match(html,/value="antigravity" selected/);
  assert.doesNotMatch(html,/Nicht verfügbar:|MoneyPrinter|Podcast|Cloudprofil/);
  assert.match(html,/Stimmenauswahl speichern/);
});

test('a delayed job response cannot overwrite the other mode after navigation',async()=>{
  const {state}=fixture();let finish,started,rendered=false;
  const requested=new Promise(resolve=>{started=resolve});
  state.api=()=>new Promise(resolve=>{finish=resolve;started()});state.refreshList=async()=>{};
  state.renderJob=()=>{rendered=true};
  vm.runInContext(source.slice(source.indexOf('async function openJob('),source.indexOf('const esc=')),state);
  const opening=state.openJob('old');await requested;
  state.switchMode('frame');finish({id:'old',status:'script_review'});await opening;
  assert.equal(state.activeMode,'frame');assert.equal(rendered,false);
});
