globalThis.PipelineErrors = {
  message(value) {
    if (value?.failure) this.show(value.failure);
    const detail=value?.detail;
    return typeof detail==='string'?detail:Array.isArray(detail)?detail.map(item=>`${(item.loc||[]).slice(1).join('.')}: ${item.msg}`).join('; '):'Dieser Schritt konnte nicht abgeschlossen werden.';
  },
  local(code='network') {
    const report={id:'lokal-'+Date.now().toString(16),stage:'request',stage_label:'Verbindung und Oberfläche',code,
      message:code==='network'?'Die lokale Pipeline ist gerade nicht erreichbar.':code==='invalid_response'?'Die Antwort der lokalen Pipeline konnte nicht gelesen werden.':'Die Oberfläche konnte diesen Schritt nicht abschließen.',
      next_action:'Anwendung und Auftragsstatus prüfen. Fehlerdetails bei wiederholtem Auftreten kopieren.',retryable:false,context:{}};
    this.show(report);return report.message;
  },
  show(report, {history=false}={}) {
    document.getElementById('pipeline-error-card')?.remove();
    const parent=document.querySelector('dialog[open]')||document.getElementById('workspace')||document.body;
    if(!parent)return;
    const card=document.createElement('section');card.id='pipeline-error-card';card.className='panel notice error';
    card.setAttribute('role',history?'status':'alert');
    const add=(tag,text)=>{const element=document.createElement(tag);element.textContent=String(text||'');card.append(element);return element;};
    add('h2',(history?'Letzter protokollierter Fehler · ':'Fehler · ')+report.stage_label);
    add('p',report.message);add('p','Nächster Schritt: '+report.next_action);
    if(report.job_id)add('small','Auftrag: '+report.job_id);
    const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Fehlerdetails';details.append(summary);
    const publicReport={id:report.id,job_id:report.job_id||null,stage:report.stage,code:report.code,
      message:report.message,next_action:report.next_action,retryable:Boolean(report.retryable),context:report.context||{},technical:report.technical||{}};
    const text=JSON.stringify(publicReport,null,2);const pre=document.createElement('pre');pre.textContent=text;details.append(pre);card.append(details);
    add('p','Fehler-ID: '+report.id);
    const copy=add('button','Fehlerdetails kopieren');copy.type='button';copy.className='secondary';
    copy.onclick=async()=>{try{await navigator.clipboard.writeText(text);copy.textContent='Fehlerdetails kopiert';}catch{details.open=true;copy.textContent='Kopieren nicht verfügbar · Details markieren und kopieren';}};
    const close=add('button','Meldung ausblenden');close.type='button';close.className='ghost';close.onclick=()=>card.remove();
    parent.prepend(card);
  },
  mount(job) {
    document.getElementById('pipeline-error-card')?.remove();
    const latest=job.events?.find(event=>event.event_type==='pipeline_failure')?.metadata?.failure;
    if(job.error_report)this.show(job.error_report);else if(latest)this.show(latest,{history:true});
    const meta=document.querySelector('#workspace .meta');
    if(meta){const mode=document.createElement('span');mode.className='pill';mode.textContent=job.generation_mode==='frame'?'Frame':'Animiert';meta.append(mode);}
    const step=job.events?.find(event=>event.event_type==='production_step');
    if(step&&['render_planning','rendering'].includes(job.status)){
      const line=document.createElement('p');line.setAttribute('role','status');line.textContent='Aktueller Schritt: '+step.message;
      if(step.metadata?.context?.scene_id)line.textContent+=' · Abschnitt '+step.metadata.context.scene_id;
      document.querySelector('#workspace .topline')?.append(line);
    }
  },
};
window.addEventListener('error',()=>PipelineErrors.local('ui'));
window.addEventListener('unhandledrejection',()=>PipelineErrors.local('ui'));
