const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

function fixture() {
  const nodes={},requests=[];
  const section={isConnected:true,querySelector:selector=>nodes[selector]??=( {value:'',checked:false,textContent:''} )};
  const preferences={provider:'cloudflare',cloudflare_account_id:'a'.repeat(32),cloudflare_free_confirmed:false};
  const context={window:{},Date,setTimeout,document:{createElement:()=>section},fetch:async(url,options)=>{
    requests.push({url,options});return{ok:true,json:async()=>url.endsWith('/image-access')?{message:'Textzugang bereit <img>',next_step:'Bildzugang offen'}:
      url.endsWith('/preview')?{status:'idle',message:'Kein Testbild'}:{preferences,vault_ready:true,token_present:true}};
  }};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../web/image-settings.js'),'utf8'),context);
  return {context,nodes,requests,section};
}

test('mount only reads local settings; explicit account check uses the token and safe text output',async()=>{
  const {context,nodes,requests}=fixture();
  await context.window.ImageSettings.mount({append(){}},'fixture-local-token');
  assert.ok(requests.every(item=>item.options.method==='GET'));
  await nodes['#image-access-check'].onclick();
  assert.equal(requests.at(-1).url,'/api/settings/image-access');
  assert.equal(requests.at(-1).options.headers['X-Setup-Token'],'fixture-local-token');
  assert.equal(nodes['#image-access-result'].textContent,'Textzugang bereit <img> Bildzugang offen');
  assert.equal(nodes['#image-access-result'].innerHTML,undefined);
  assert.equal(nodes['#image-access-check'].disabled,false);
});

test('save sends only chosen provider fields, clears typed token and never starts generation',async()=>{
  const {context,nodes,requests}=fixture();
  await context.window.ImageSettings.mount({append(){}},'fixture-local-token');
  nodes['#image-token'].value='fixture-secret';nodes['#image-free'].checked=true;
  await nodes['#image-save'].onclick();
  const write=requests.find(item=>item.options.method==='PUT');
  assert.equal(JSON.parse(write.options.body).token,'fixture-secret');
  assert.equal(JSON.parse(write.options.body).preferences.cloudflare_free_confirmed,true);
  assert.equal(nodes['#image-token'].value,'');
  assert.ok(!requests.some(item=>item.options.method==='POST'));
});
