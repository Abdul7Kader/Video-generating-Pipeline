const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

async function voices(overrides={}){
  const choices=[
    {id:'thorsten',label:'Piper Thorsten',language:'de',provider:'piper',available:true,installed:true},
    {id:'qwen_narrator',label:'Qwen',language:'de',provider:'qwen_tts',available:true,installed:true,...overrides},
    {id:'other',label:'Weitere Stimme',language:'de',provider:'piper',available:true,installed:false},
    {id:'ljspeech',label:'Piper Englisch',language:'en',provider:'piper',available:true,installed:true}
  ];
  const requests=[],nodes={'new-voice-id':{value:'thorsten'},'new-voice-speed':{value:'1.1'}};
  const context={window:{},document:{getElementById:id=>nodes[id]},fetch:async url=>{
    requests.push(url);return {ok:true,json:async()=>choices};
  }};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../web/voices.js'),'utf8'),context);
  await context.window.VoiceEditor.load();
  return {editor:context.window.VoiceEditor,requests,nodes};
}

test('installed Qwen never replaces an explicitly chosen Piper; rendering starts no downloads',async()=>{
  const ui=await voices();
  const html=ui.editor.render('new',{voice_id:'thorsten'},'de');
  assert.match(html,/value="thorsten" selected/);
  assert.doesNotMatch(html,/value="qwen_narrator" selected/);
  assert.equal(ui.editor.collect('new').voice_provider,'piper');
  assert.deepEqual(ui.requests,['/api/voices']);
  assert.match(ui.editor.render('new',{voice_id:'qwen_narrator'},'de'),/value="qwen_narrator" selected/);
  assert.match(ui.editor.render('new',{},'en'),/value="ljspeech" selected/);
});

test('resource-blocked chosen voice stays visible with escaped reason and disables its preview',async()=>{
  const ui=await voices({available:false,reason:'RAM fehlt <script>unsafe</script>'});
  const html=ui.editor.render('new',{voice_id:'qwen_narrator'},'de');
  assert.match(html,/value="qwen_narrator" selected disabled/);
  assert.match(html,/data-voice-preview disabled/);
  assert.match(html,/data-voice-compare disabled/);
  assert.match(html,/RAM fehlt &lt;script&gt;unsafe/);
  assert.equal(ui.editor.available('qwen_narrator'),false);
  ui.nodes['new-voice-id'].value='missing';
  assert.throws(()=>ui.editor.collect('new'),/Stimme fehlt/);
});

function health(overrides={},available=true){
  const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
  const host={setAttribute(){}};
  const context={window:{},productionOptions:{default_voice_id:'thorsten'},VoiceEditor:{available:()=>available},$:()=>host};
  vm.runInNewContext(source.match(/function showHealth\(data\)\{[\s\S]*?\n\}/)[0],context);
  context.showHealth({dependencies:{node:true,renderer:true,browser:true,ffmpeg:true,ffprobe:true,piper_voice:true,tts_provider:'piper',...overrides},script_generation:{ready:true,provider:'antigravity',model:'chosen-model'}});
  return {host,context};
}

test('readiness requires actual voice and rendering prerequisites, and records the active ETA model',()=>{
  assert.match(health().host.textContent,/Bereit:/);
  assert.match(health({browser:false}).host.textContent,/Einrichtung nötig: Schnittwerkzeuge/);
  assert.match(health({},false).host.textContent,/Einrichtung nötig: Stimme/);
  assert.equal(health().context.window.PipelineScriptModel,'chosen-model');
});
