const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

function ui(){
  const nodes=new Map(),requests=[],actions=[];
  let tick,downloaded=false,saved=false;
  const fixture={token:'test-token',device:{os:'Windows',architecture:'AMD64',ram_gb:16,available_gb:10,cpu_threads:4,gpu_gb:0,gpu_name:'<script>untrusted</script>',disk_free_gb:50},
    recommendation:{model:'qwen3.5:4b',allowed_models:['qwen3.5:0.8b','qwen3.5:2b','qwen3.5:4b'],voice:'piper',qwen_suitable:false,reason:'Memory budget',voice_reason:'Piper is suitable'},
    preferences:null,effective:{model:'qwen3.5:4b',voice:'piper'},installed_models:[],tools:{node:true,renderer:true,ffmpeg:true,browser:true,ollama:true,ollama_running:false,piper:true,qwen:false},
    task:{status:'idle',message:'idle',percent:null}};
  class Element{
    constructor(id){this.id=id;this.value=({'settings-model':'qwen3.5:4b','settings-voice':'piper','settings-script':'local','device-ram':'16','device-cpu':'4','device-gpu':'0'})[id]||'';this.dataset={};this.lastChild={textContent:''};this.open=false}
    set innerHTML(value){this.html=value;if(this.id==='settings-content'){
      actions.length=0;
      for(const match of value.matchAll(/<button[^>]*data-setup-action="([^"]+)"([^>]*)>/g)){
        const item=new Element(match[1]);item.dataset.setupAction=match[1];item.disabled=match[2].includes('disabled');actions.push(item);
      }
    }}
    get innerHTML(){return this.html||''}
    querySelectorAll(){return actions}
    showModal(){this.open=true}
    close(){this.open=false}
    addEventListener(){}
    scrollIntoView(){}
  }
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id)},querySelectorAll(selector){return selector==='[data-open-settings]'?[]:[...nodes.values(),...actions]}};
  const context={document,window:{},console,Date,Event:class{},setInterval(callback){tick=callback;return 1},clearInterval(){},
    async fetch(url,options){requests.push({url,...options});let value;
      if(url==='/api/settings/actions'){const input=JSON.parse(options.body);assert.equal(input.action,'script_model');downloaded=true;fixture.task={status:'running',message:'download',started_at:Date.now()/1000,percent:20};value=fixture.task}
      else if(url==='/api/settings/task'){fixture.task={status:'completed',message:'done',percent:100};fixture.installed_models=['qwen3.5:4b'];value=fixture.task}
      else if(url==='/api/settings/preferences'){saved=true;fixture.preferences=JSON.parse(options.body);value={saved:true,message:'saved'}}
      else value=fixture;
      return {ok:true,async json(){return structuredClone(value)}};
    }};
  context.window.dispatchEvent=()=>{};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/settings.js'),'utf8'),context);
  return {context,document,nodes,requests,actions,fixture,get tick(){return tick},get downloaded(){return downloaded},get saved(){return saved}};
}

test('settings show a safe small-device recommendation and do not start downloads on open',async()=>{
  const app=ui();await app.context.window.PipelineSettings.open();
  const html=app.document.getElementById('settings-content').innerHTML;
  assert.match(html,/qwen3\.5:4b/);assert.match(html,/&lt;script&gt;untrusted/);assert.doesNotMatch(html,/<script>untrusted/);
  assert.doesNotMatch(html,/test-token/);
  assert.equal(app.actions.find(action=>action.dataset.setupAction==='qwen_voice').disabled,true);
  assert.equal(app.requests.filter(request=>request.method==='POST').length,0);
});

test('the chosen fixed model downloads only after a click and progress completes before enabling setup',async()=>{
  const app=ui();await app.context.window.PipelineSettings.open();
  await app.actions.find(action=>action.dataset.setupAction==='script_model').onclick();
  const call=app.requests.find(request=>request.url==='/api/settings/actions');
  assert.deepEqual(JSON.parse(call.body),{action:'script_model',model:'qwen3.5:4b'});
  assert.equal(call.headers['X-Setup-Token'],'test-token');
  assert.equal(app.document.getElementById('settings-save').disabled,true);
  assert.match(app.document.getElementById('setup-progress').innerHTML,/progress/);
  await app.tick();
  assert.equal(app.fixture.task.status,'completed');
  assert.match(app.document.getElementById('settings-message').textContent,/done/);
  await app.document.getElementById('settings-save').onclick();
  assert.equal(app.saved,true);
  assert.deepEqual(app.fixture.preferences,{model:'qwen3.5:4b',voice:'piper',script:'local'});
});
