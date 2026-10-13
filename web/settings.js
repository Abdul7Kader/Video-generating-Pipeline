window.PipelineSettings = (() => {
  const dialog=document.getElementById('settings-dialog'), body=document.getElementById('settings-content');
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let state=null, token='', poll=null, manual=null;
  async function api(path='',method='GET',value) {
    const response=await fetch('/api/settings'+path,{method,headers:{'Content-Type':'application/json','X-Setup-Token':token},...(value?{body:JSON.stringify(value)}:{})});
    let result;try{result=await response.json()}catch{throw new Error('Die lokale Einrichtung antwortet nicht vollständig. Prüfe, ob die Pipeline noch läuft, und öffne die Einstellungen erneut.')}
    if(!response.ok) throw new Error(typeof result.detail==='string'?result.detail:'Prüfe die eingegebenen Geräteangaben.');
    return result;
  }
  const link=(url,label)=>`<a class="ghost" href="${url}" target="_blank" rel="noopener noreferrer">${label} ↗</a>`;
  const action=(id,label,disabled=false)=>`<button type="button" class="secondary" data-setup-action="${id}" ${disabled||state?.production_busy?'disabled':''}>${label}</button>`;
  function row(title,description,ready,buttons) {
    return `<div class="setup-tool"><div><h3>${title} <span class="setup-badge ${ready?'ready':''}">${ready?'Bereit':'Noch einrichten'}</span></h3><p>${description}</p></div><div class="setup-tool-actions">${buttons}</div></div>`;
  }
  function message(text,error=false){const host=document.getElementById('settings-message');if(host){host.textContent=text;host.className='notice'+(error?' error':'');host.hidden=false;if(dialog.open)host.scrollIntoView({block:'nearest'})}}
  function progress(task) {
    const host=document.getElementById('setup-progress');if(!host)return;
    const running=task.status==='running';
    const seconds=task.started_at?Math.max(0,Math.round(Date.now()/1000-task.started_at)):0;
    const elapsed=seconds<60?`${seconds} Sekunden`:`${Math.floor(seconds/60)} Min. ${seconds%60} Sek.`;
    host.hidden=task.status==='idle';
    host.innerHTML=`<strong>${escape(task.message)}</strong>${running?`<progress ${task.percent==null?'':`value="${task.percent}"`} max="100" aria-label="Fortschritt der Einrichtung"></progress><p>${elapsed} vergangen · ${task.remaining_seconds==null?'Restzeit noch nicht messbar.':`Aktueller Downloadabschnitt: ${task.percent} % · noch ungefähr ${task.remaining_seconds} Sek.`}</p>`:''}`;
    document.querySelectorAll('#settings-content button,#settings-content select,#settings-content input').forEach(control=>{if(running)control.disabled=true});
    document.getElementById('settings-button').dataset.busy=running?'true':'false';
    document.getElementById('settings-button').lastChild.textContent=running?' Einrichtung läuft':' Einstellungen';
  }
  function draw(){
    const {device:d,recommendation:r,tools:t,preferences:p,effective:e}=state;
    const choice=p?.model&&r.allowed_models.includes(p.model)?p.model:r.model;
    const voice=r.qwen_suitable?(p?.voice||r.voice):'piper', script=p?.script||'local';
    const qwenPlatform=['Windows','Linux'].includes(d.os)&&['amd64','x86_64'].includes(d.architecture.toLowerCase())||d.os==='Darwin'&&['arm64','x86_64'].includes(d.architecture.toLowerCase());
    body.innerHTML=`${state.production_busy?'<p class="notice" role="status">Gerade läuft eine Videoproduktion. Du kannst die Einrichtung ansehen; Downloads und Änderungen warten auf deren Abschluss.</p>':''}<p class="settings-intro">Einmal auf diesem Rechner einrichten. Danach bedienst du die gesamte Pipeline hier: Idee eingeben, Text freigeben, Video herunterladen.</p>
      <section class="settings-section"><h2>1 · Dein Rechner und die passende Qualität</h2><p>Die Prüfung liest nur lokale Gerätewerte. Sie sendet keine Hardwaredaten an einen Anbieter.</p>
        <dl class="device-facts"><div><dt>System</dt><dd>${escape(d.os)} · ${escape(d.architecture)}</dd></div><div><dt>Arbeitsspeicher</dt><dd>${d.ram_gb??'Unbekannt'} GB · ${d.available_gb??'?'} GB frei</dd></div><div><dt>CPU</dt><dd>${d.cpu_threads??'?'} Threads</dd></div><div><dt>Freier Plattenplatz</dt><dd>${d.disk_free_gb} GB</dd></div><div><dt>Grafik</dt><dd>${escape(d.gpu_name)}${d.gpu_gb?` · ${d.gpu_gb} GB`:''}</dd></div></dl>
        <div class="notice"><strong>${r.model?`Empfehlung: ${escape(r.model)}`:'Geräteangaben fehlen oder reichen noch nicht aus'}</strong><p>${escape(r.reason)} ${escape(r.voice_reason)}</p></div>
        <button type="button" id="settings-rescan" class="ghost">Rechner erneut prüfen</button>
        <details ${!r.model?'open':''}><summary>Geräteangaben ergänzen oder korrigieren</summary><p>Wenn die automatische Erkennung unvollständig ist, trage nur diese technischen Werte ein. Passwörter, Seriennummern und persönliche Daten werden nicht benötigt.</p><div class="grid2"><label>RAM insgesamt (GB)<input id="device-ram" type="number" min="2" max="2048" step="0.5" value="${d.ram_gb||''}"></label><label>CPU-Threads<input id="device-cpu" type="number" min="1" max="256" value="${d.cpu_threads||''}"></label><label>Separater Grafikspeicher (GB)<input id="device-gpu" type="number" min="0" max="256" step="0.5" value="${d.gpu_gb||0}"></label></div><button type="button" id="settings-manual" class="secondary">Empfehlung mit diesen Angaben prüfen</button></details>
      </section>
      <section class="settings-section"><h2>2 · Benötigte Bausteine einrichten</h2><p>Downloads starten erst mit deinem Klick. Programme mit eigenem Installer öffnest du über die Herstellerseite; die Pipeline ändert keine Firewall und verlangt keine Administratorrechte.</p>
        ${row('Node.js LTS','Grundlage für den Videoschnitt. Nach einer neuen Systeminstallation die Pipeline neu starten, damit sie Node findet.',t.node,link('https://nodejs.org/en/download','Node.js herunterladen'))}
        ${row('Videoschnitt und Medienwerkzeuge','Installiert die festgelegten Schnittpakete im Projektordner. Vorhandene Skripte werden bei der Installation nicht ausgeführt.',t.renderer&&t.ffmpeg,action('render_tools','Schnittwerkzeuge einrichten',!t.node)+(t.ffmpeg?'':link('https://ffmpeg.org/download.html','FFmpeg herunterladen')))}
        ${row('Browser für das Zeichnen','Ein installierter Chrome-, Chromium- oder Edge-Browser zeichnet die Videobilder. Er öffnet keinen zusätzlichen Netzwerkdienst.',t.browser,link('https://www.google.com/chrome/','Chrome herunterladen'))}
        ${row('Lokale Skript-KI','Ollama führt das ausgewählte Modell auf deinem Rechner aus. Ein Konto ist nicht nötig. Der von der Pipeline gestartete Dienst ist nur unter 127.0.0.1:11434 erreichbar.',t.ollama_running,link('https://ollama.com/download','Ollama herunterladen')+action('start_ollama','Lokalen Dienst starten',!t.ollama))}
        <label>Skriptmodell<select id="settings-model">${r.allowed_models.length?r.allowed_models.map(model=>`<option ${model===choice?'selected':''}>${model}</option>`).join(''):'<option value="">Zuerst Rechnerwerte prüfen</option>'}</select></label><p class="field-hint" id="settings-model-hint"></p>${action('script_model','Ausgewähltes Skriptmodell herunterladen',!t.ollama||!choice)}
        ${row('Piper · schnelle lokale Stimme','Die sparsame deutsche Stimme für kleine Rechner. Die Spracherzeugung läuft lokal.',t.piper,action('piper_voice','Piper-Stimme herunterladen'))}
        ${row('Qwen · natürlichere lokale Stimme','Option für stärkere Rechner. Benötigt Python 3.12, eine separate Laufzeit und etwa 4,5 GB Modelldaten; die Einrichtung reserviert 20 GB Plattenplatz. Auf der CPU kann eine Hörprobe mehrere Minuten dauern.',t.qwen,action('qwen_voice','Qwen-Stimme einrichten',!r.qwen_suitable||!qwenPlatform)+link('https://www.python.org/downloads/','Python herunterladen'))}
      </section>
      <section class="settings-section"><h2>3 · Betriebsart und Konten</h2><label>Skripterstellung<select id="settings-script"><option value="local" ${script==='local'?'selected':''}>Auf diesem Rechner · ohne Konto</option><option value="antigravity" ${script==='antigravity'?'selected':''}>Optional: vorhandenes Antigravity-Cloudprofil</option></select></label><p>Der lokale Betrieb funktioniert ohne Codex und ohne einen steuernden Agenten. Die Pipeline ruft das Skriptmodell selbst auf.</p>
        <div id="settings-account" hidden><p>Das optionale Cloudprofil benötigt die reguläre Herstelleranmeldung. Texte werden dabei an den Anbieter gesendet. Passwörter und Zugangstokens gibst du ausschließlich im Herstellerdialog ein.</p>${link('https://antigravity.google/docs/cli/install','Download und reguläre Anmeldung')}<button type="button" id="settings-accounts-check" class="ghost">Anmeldung prüfen</button><p id="settings-account-status" role="status">Noch nicht geprüft.</p></div>
        <label>Standardstimme für neue deutsche Videos<select id="settings-voice"><option value="piper" ${voice==='piper'?'selected':''}>Piper · schnell und sparsam</option><option value="qwen_tts" ${voice==='qwen_tts'?'selected':''} ${r.qwen_suitable&&(qwenPlatform||t.qwen)?'':'disabled'}>Qwen · natürlicher, mehr Rechenzeit</option></select></label>
        <p>Vorhandene Skripte, Videos und die gewählten Stimmen bleiben erhalten. Neue KI-Überarbeitungen verwenden das aktuelle Skriptmodell dieses Rechners.</p>
        <button type="button" class="primary" id="settings-save" ${state.production_busy?'disabled':''}>Auswahl speichern und verwenden</button><p class="field-hint">Aktuell: ${escape(e.model)} · ${escape(e.voice)}. ${p?'Geräteeinstellungen sind gespeichert.':'Noch keine Geräteeinstellungen gespeichert.'}</p>
      </section>
      <section class="settings-section"><h2>Lokal und geschützt</h2><p>Die Oberfläche bleibt ausschließlich auf diesem Rechner unter 127.0.0.1 erreichbar. Es werden keine Portweiterleitungen, Tunnel oder Firewallfreigaben eingerichtet. Geräteoptionen werden lokal gespeichert; bestehende Schlüssel aus deiner Umgebung werden weder angezeigt noch überschrieben.</p></section>
      <div id="settings-message" class="notice" role="status" hidden></div><div id="setup-progress" class="setup-progress" role="status" aria-live="polite" hidden></div>`;
    body.querySelectorAll('[data-setup-action]').forEach(button=>button.onclick=()=>start(button.dataset.setupAction));
    document.getElementById('settings-rescan').onclick=()=>{manual=null;load()};
    document.getElementById('settings-manual').onclick=async()=>{try{const value={ram_gb:Number(document.getElementById('device-ram').value),cpu_threads:Number(document.getElementById('device-cpu').value),gpu_gb:Number(document.getElementById('device-gpu').value)};const result=await api('/recommend','POST',value);manual=value;Object.assign(state,result);draw()}catch(error){message(error.message,true)}};
    document.getElementById('settings-model').onchange=modelHint;
    document.getElementById('settings-script').onchange=()=>document.getElementById('settings-account').hidden=document.getElementById('settings-script').value==='local';
    document.getElementById('settings-script').onchange();
    document.getElementById('settings-accounts-check').onclick=async()=>{const host=document.getElementById('settings-account-status');host.textContent='Reguläre Anmeldung wird geprüft …';try{const result=await api('/accounts');host.textContent=result.antigravity.ready?'Angemeldet und erreichbar.':result.antigravity.message}catch(error){host.textContent=error.message}};
    document.getElementById('settings-save').onclick=save;
    modelHint();progress(state.task);
    if(state.task.status==='running')watch();
  }
  function modelHint(){const model=document.getElementById('settings-model').value;document.getElementById('settings-model-hint').textContent=state.installed_models.includes(model)?'Dieses Modell ist bereits heruntergeladen.':'Dieses Modell muss vor dem lokalen Betrieb einmal heruntergeladen werden.'}
  async function load(){clearInterval(poll);body.innerHTML='<p role="status">Rechner, installierte Bausteine und lokale Dienste werden geprüft …</p>';try{state=await api();token=state.token;manual=state.preferences?.hardware||manual;draw()}catch(error){body.textContent=error.message}}
  async function start(actionId){try{const value={action:actionId,...(manual?{hardware:manual}:{})};if(actionId==='script_model')value.model=document.getElementById('settings-model').value;state.task=await api('/actions','POST',value);progress(state.task);document.getElementById('setup-progress').scrollIntoView({block:'nearest'});watch()}catch(error){message(error.message,true)}}
  function watch(){clearInterval(poll);poll=setInterval(async()=>{try{state.task=await api('/task');progress(state.task);if(state.task.status!=='running'){clearInterval(poll);const task=state.task;await load();message(task.message,task.status==='failed')}}catch(error){clearInterval(poll);message(error.message,true)}},1500)}
  async function save(){try{const value={model:document.getElementById('settings-model').value,voice:document.getElementById('settings-voice').value,script:document.getElementById('settings-script').value,...(manual?{hardware:manual}:{})};const result=await api('/preferences','PUT',value);await load();message(result.message);window.dispatchEvent(new Event('machine-settings-saved'))}catch(error){message(error.message,true)}}
  async function open(){if(window.ProcessProgress?.busy){document.getElementById('toast').textContent='Warte auf den laufenden Vorgang, bevor du die Einrichtung öffnest.';return}if(!dialog.open)dialog.showModal();await load()}
  document.getElementById('settings-button').onclick=open;
  document.querySelectorAll('[data-open-settings]').forEach(button=>button.onclick=open);
  document.getElementById('settings-close').onclick=()=>dialog.close();
  dialog.addEventListener('close',()=>{if(state?.task.status!=='running')clearInterval(poll)});
  return {open};
})();
