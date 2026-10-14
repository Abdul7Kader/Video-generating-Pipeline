const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../web/app.js'),'utf8');

test('stickman provider selection includes both family paths while other media stay hidden',()=>{
  const context={productionOptions:{providers:{script:['qwen','antigravity','gemini_cli','web_import','unimplemented'].map(id=>({id})),media:[{id:'procedural_stickman'},{id:'pexels_stock'}]}}};
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('const providerChoices='),source.indexOf('function productionConfigAvailable('))+';this.choices=providerChoices;',context);
  assert.deepEqual(Array.from(context.choices('script'),x=>x.id),['qwen','antigravity','web_import']);
  assert.deepEqual(Array.from(context.choices('media'),x=>x.id),['procedural_stickman']);
});

test('manual web import explains its extra transfer and renders escaped content',()=>{
  const context={providerChoices:()=>[{id:'web_import',available:true}],productionConfigEditor:()=>'',esc:value=>String(value).replaceAll('<','&lt;').replaceAll('>','&gt;')};
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('function storyEditor('),source.indexOf('function sceneEditor(')),context);
  const job={script_version:1,production_config:{script_provider:'web_import'},script:{title:'<script>test</script>',integrity_verified:true,metadata:{workflow:'story_draft',provider:'web_import',visual_summary:'Figur geht spazieren.'},scenes:[{narration:'Ein zusammenhängender Text.'}]}};
  const html=context.storyEditor(job);
  assert.match(html,/Text freigeben & Zeichenprompt öffnen/);
  assert.match(html,/überträgst du einmal den Zeichenprompt/);
  assert.match(html,/Web-KI · manuell importiert/);
  assert.doesNotMatch(html,/<script>test/);
  job.script.metadata.workflow='storyboard';
  assert.match(context.storyEditor(job),/Freigeben & Video erzeugen/);
});

test('typing revision instructions prevents approval while still allowing AI revision',()=>{
  const nodes=new Map();
  for(const id of ['workspace','revision-instructions','editor-dirty','approve-story','revise-script'])nodes.set('#'+id,{value:'',disabled:false});
  const context={editorSnapshot:()=>null,editorBaseline:null,productionBaseline:null,dirtyScript:false,dirtyProduction:false,dirtyFeedback:false,actionPending:false,
    $:selector=>nodes.get(selector),document:{getElementById:id=>nodes.get('#'+id),querySelectorAll:()=>[]},setTimeout:fn=>fn()};
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('function bindEditorState('),source.indexOf("window.addEventListener('beforeunload'")),context);
  context.bindEditorState({script:{integrity_verified:true,scenes:[]},script_version:1});
  assert.equal(nodes.get('#approve-story').disabled,false);
  nodes.get('#revision-instructions').value='Mehr Details zeigen';nodes.get('#workspace').oninput();
  assert.equal(nodes.get('#approve-story').disabled,true);
  assert.equal(nodes.get('#revise-script').disabled,false);
  assert.equal(context.dirtyFeedback,true);
  nodes.get('#revision-instructions').value='';nodes.get('#workspace').oninput();
  assert.equal(nodes.get('#approve-story').disabled,false);
  context.providerChoices=()=>[{id:'antigravity',available:false}];context.productionConfigAvailable=()=>false;
  context.bindEditorState({production_config:{script_provider:'antigravity'},script:{integrity_verified:true,scenes:[]},script_version:1});
  assert.equal(nodes.get('#approve-story').disabled,true);
  assert.equal(nodes.get('#revise-script').disabled,true);
});

test('provider check leaves the prompt and cancel controls usable until the response arrives',async()=>{
  let complete;
  const pending=new Promise(resolve=>{complete=resolve});
  const nodes=new Map([['#create-progress',{replaceChildren(){}}],['#production-availability',{}],['#create-submit',{disabled:false}]]);
  const topic={disabled:false,value:'Meine Idee'},cancel={disabled:false};
  nodes.set('#create-form',{querySelectorAll:()=>[topic,cancel,nodes.get('#create-submit')]});
  const context={ProcessProgress:{busy:false},dirtyScript:false,dirtyProduction:false,dirtyFeedback:false,actionPending:false,
    $:selector=>nodes.get(selector),createDialog:{showModal(){}},toast:()=>{},loadProductionOptions:()=>pending};
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('const openCreate=async()=>'),source.indexOf("$('#new-button').onclick"))+';this.openCreate=openCreate;',context);
  const opening=context.openCreate();
  assert.equal(nodes.get('#create-submit').disabled,true);
  assert.equal(context.actionPending,true);
  assert.equal(topic.disabled,false);assert.equal(cancel.disabled,false);
  assert.match(nodes.get('#production-availability').innerHTML,/Idee schon eingeben/);
  complete();await opening;
  assert.equal(context.actionPending,false);
});
