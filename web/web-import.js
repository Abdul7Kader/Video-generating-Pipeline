window.PipelineWebImport = (() => {
  const dialog=document.getElementById('web-import-dialog');
  const prompt=document.getElementById('web-import-prompt'), response=document.getElementById('web-import-response');
  const notice=document.getElementById('web-import-message'), submit=document.getElementById('web-import-submit');
  let session=null, pending=false, resolve=null;
  async function post(path,payload){
    const res=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const value=await res.json();
    if(!res.ok)throw new Error(globalThis.PipelineErrors?.message(value)||(typeof value.detail==='string'?value.detail:'Die Antwort ist zu groß oder entspricht nicht dem angeforderten Format.'));
    return value;
  }
  function message(text){notice.textContent=text;notice.hidden=false;}
  function busy(value){pending=value;submit.disabled=value;document.getElementById('web-import-close').disabled=value;response.disabled=value;}
  document.getElementById('web-import-copy').onclick=async()=>{
    try{await navigator.clipboard.writeText(prompt.value);message('Prompt kopiert. In deiner Web-KI einfügen und die vollständige Antwort hierher kopieren.');}
    catch{prompt.focus();prompt.select();message('Mit Strg+C / Cmd+C den markierten Prompt kopieren.');}
  };
  document.getElementById('web-import-close').onclick=()=>{if(!pending)dialog.close()};
  dialog.addEventListener('cancel',event=>{if(pending)event.preventDefault()});
  dialog.addEventListener('close',()=>{if(resolve){resolve(null);resolve=null}});
  document.getElementById('web-import-form').onsubmit=async event=>{
    event.preventDefault();if(pending||!session)return;
    if(!response.value.trim()){message('Bitte zuerst die vollständige Antwort einfügen.');return}
    busy(true);
    const progress=window.ProcessProgress.start(document.getElementById('web-import-progress'),{key:'web-import',label:'Antwort prüfen und übernehmen',detail:'Textversion, Zeichenregeln und Freigaben werden lokal geprüft.'});
    try{
      const job=await post(session.importEndpoint,{...session.payload,response:response.value});
      progress.finish('Antwort geprüft und übernommen');
      const done=resolve;resolve=null;dialog.close();done(job);
    }catch(error){progress.fail(error.message);message(error.message)}finally{busy(false)}
  };
  async function open(options){
    if(dialog.open)return null;
    session=options;prompt.value='';response.value='';notice.hidden=true;
    document.getElementById('web-import-title').textContent=options.title;
    document.getElementById('web-import-stage').textContent=options.stage;
    submit.textContent=options.buttonText||'Antwort prüfen und Skript übernehmen';
    dialog.showModal();busy(true);
    const result=new Promise(done=>resolve=done);
    const progress=window.ProcessProgress.start(document.getElementById('web-import-progress'),{key:'web-prompt',label:'Passenden Prompt vorbereiten',detail:'Die Pipeline stellt die Regeln und deinen Inhalt zusammen. Es wird keine Web-KI aufgerufen.'});
    try{
      const data=await post(options.promptEndpoint,options.payload);prompt.value=data.prompt;
      progress.finish('Prompt bereit');message('1 · Prompt kopieren. 2 · In deiner Web-KI ausführen. 3 · Die vollständige JSON-Antwort unten einfügen.');
    }catch(error){progress.fail(error.message);message(error.message)}finally{busy(false);submit.disabled=!prompt.value}
    return result;
  }
  return {open};
})();
