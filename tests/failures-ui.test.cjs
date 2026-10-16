const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function setup(){
  class Element {
    constructor(tag){this.tag=tag;this.children=[];this.attributes={};this.textContent='';}
    append(...children){for(const child of children){child.parent=this;this.children.push(child);}}
    prepend(child){child.parent=this;this.children.unshift(child);}
    remove(){if(this.parent)this.parent.children=this.parent.children.filter(child=>child!==this);}
    setAttribute(name,value){this.attributes[name]=value;}
    set innerHTML(_value){throw new Error('Diagnostic content must never use innerHTML');}
  }
  const body=new Element('body');const workspace=new Element('main');workspace.id='workspace';body.append(workspace);
  const flatten=root=>[root,...root.children.flatMap(flatten)];let copied;
  const context={document:{body,createElement:tag=>new Element(tag),getElementById:id=>flatten(body).find(element=>element.id===id),querySelector:selector=>selector==='#workspace'?workspace:null},
    navigator:{clipboard:{writeText:async value=>{copied=value;}}},window:{addEventListener:()=>{}},Date};
  vm.createContext(context);vm.runInContext(fs.readFileSync('web/failures.js','utf8'),context);
  return {errors:context.PipelineErrors,workspace,all:()=>flatten(body),copied:()=>copied};
}
const report={id:'a'.repeat(16),job_id:'fixture',stage:'voice',stage_label:'Stimme',code:'timeout',message:'<img src=x onerror=attack()>',next_action:'Erneut prüfen',retryable:true,context:{scene_id:'s2'},technical:{component:'rendering.py',line:22}};

test('persistent diagnostics render as text and copy only the public report',async()=>{
  const ui=setup();ui.errors.show({...report,provider_body:'secret-fixture'});
  assert.ok(ui.all().some(element=>element.textContent===report.message));
  assert.equal(ui.all().some(element=>element.tag==='img'),false);
  assert.equal(ui.all().find(element=>element.id==='pipeline-error-card').attributes.role,'alert');
  await ui.all().find(element=>element.textContent==='Fehlerdetails kopieren').onclick();
  assert.equal(JSON.parse(ui.copied()).id,report.id);
  assert.equal(JSON.parse(ui.copied()).technical.component,'rendering.py');
  assert.doesNotMatch(ui.copied(),/secret-fixture/);
});
test('recoverable history is distinguished from a current error and duplicate cards are removed',()=>{
  const ui=setup();ui.errors.show(report);ui.errors.mount({events:[{event_type:'pipeline_failure',metadata:{failure:report}}]});
  assert.equal(ui.all().filter(element=>element.id==='pipeline-error-card').length,1);
  assert.equal(ui.all().find(element=>element.id==='pipeline-error-card').attributes.role,'status');
  assert.ok(ui.all().some(element=>element.textContent.startsWith('Letzter protokollierter Fehler')));
});
test('local connection failures stay visible and structured server errors use the same card',()=>{
  const ui=setup();assert.match(ui.errors.local(),/nicht erreichbar/);
  assert.match(ui.errors.message({failure:report,detail:'Stimme fehlgeschlagen'}),/fehlgeschlagen/);
  assert.ok(ui.all().some(element=>element.textContent==='Fehler-ID: '+report.id));
});
