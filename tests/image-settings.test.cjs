const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

test('image settings contact the existing account only on explicit click, with local token and safe output',async()=>{
  const button={},result={before(){}},requests=[],progress={setAttribute(){},remove(){this.removed=true}};
  const section={querySelector:selector=>selector==='#image-access-check'?button:result};
  const context={window:{},document:{createElement:tag=>tag==='progress'?progress:section},fetch:async(url,options)=>{
    requests.push({url,options});return{ok:true,json:async()=>({ready:false,message:'Textzugang bereit <img>',next_step:'Bildzugang offen'})};
  }};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../web/image-settings.js'),'utf8'),context);
  context.window.ImageSettings.mount({append(){}},'fixture-local-token');
  assert.equal(requests.length,0);await button.onclick();
  assert.equal(requests[0].url,'/api/settings/image-access');
  assert.equal(requests[0].options.headers['X-Setup-Token'],'fixture-local-token');
  assert.equal(result.textContent,'Textzugang bereit <img> Bildzugang offen');
  assert.equal(result.innerHTML,undefined);assert.equal(progress.removed,true);assert.equal(button.disabled,false);
});
