window.FrameUI=(()=>{
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const $=selector=>document.querySelector(selector);
  let mode='animated';
  function configureCreate(value){
    mode=value;
    $('#frame-input-kind').hidden=mode!=='frame';
    $('#duration-minutes').max=mode==='frame'?'30':'10';
    document.querySelectorAll('[data-duration]').forEach(button=>button.hidden=mode!=='frame'&&Number(button.dataset.duration)>600);
    $('#create-title').textContent=mode==='frame'?'Frame · Was möchtest du erzählen?':'Was möchtest du erzählen?';
    $('#create-dialog .dialog-intro').textContent=mode==='frame'?'Idee oder eigenen Sprechertext eingeben, Entwurf lesen und bei Bedarf von der KI verbessern lassen. Mit einer Freigabe starten passende Bilder, Bildprüfung, lokale Stimme und Videoschnitt. Danach prüfst du das fertige Video.':'Zuerst erhältst du einen durchgehenden Sprechertext und eine Bildidee. Nach deiner Freigabe plant die KI die Zeichnungen und erzeugt das Video.';
    updateInput();
  }
  function updateInput(){
    const own=mode==='frame'&&$('#frame-input-select').value==='narration';
    $('#frame-own-text').hidden=!own;$('#frame-narration').required=own;
    $('[name="topic"]').required=!own;$('#topic-label').textContent=own?'Titel · optional':'Thema oder Idee';
    window.dispatchEvent(new Event('frame-input-changed'));
  }
  function duration(minutes,seconds,valueMode){
    const total=Number(minutes)*60+Number(seconds),limit=valueMode==='frame'?1800:600;
    if(!Number.isInteger(Number(minutes))||!Number.isInteger(Number(seconds))||Number(minutes)<0||Number(seconds)<0||Number(seconds)>59||total<15||total>limit)throw new Error(`Wähle eine Zieldauer von 15 Sekunden bis ${limit/60} Minuten.`);
    return total;
  }
  function collect(body,form,valueMode){
    body.duration_seconds=duration(form.get('duration_minutes'),form.get('duration_extra_seconds'),valueMode);
    delete body.duration_minutes;delete body.duration_extra_seconds;
    body.generation_mode=valueMode;
    if(valueMode==='frame'){
      body.input_kind=form.get('input_kind')||'idea';
      if(body.input_kind==='narration'){
        body.narration=String(form.get('narration')||'');
        if(body.narration.trim().length<20)throw new Error('Bitte den vollständigen Sprechertext mit mindestens 20 Zeichen eingeben.');
        body.topic=String(body.topic||'').trim()||'Eigener Sprechertext';
      }else delete body.narration;
    }else{delete body.input_kind;delete body.narration}
    return body;
  }
  function availability(profile,scriptProvider){
    if(mode!=='frame')return false;
    const own=$('#frame-input-select').value==='narration',ready=own||Boolean(scriptProvider?.available&&scriptProvider.id!=='web_import');
    $('#create-submit').disabled=!ready;
    $('#create-submit').textContent=own?'Sprechertext zur Prüfung übernehmen':'Frame-Skript erstellen';
    $('#production-availability').textContent=own?'Dein Text wird unverändert übernommen. Es wird dabei keine KI und kein Bildgenerator aufgerufen. Die Zieldauer kürzt deinen Text nicht.':ready?'Die gespeicherte Skript-KI erstellt einen Fließtext passend zu deiner Idee. Bei langen Texten arbeitet sie intern abschnittsweise.':'Für den KI-Entwurf zuerst einen automatischen Skriptzugang unter ⚙ Einstellungen einrichten. Eigenen Sprechertext kannst du bereits übernehmen.';
    return true;
  }
  const format=seconds=>`${Math.floor(Number(seconds)/60)} Min. ${Math.round(Number(seconds)%60)} Sek.`;
  function editor(job){
    const metadata=job.script.metadata||{},quality=metadata.story_quality||{},plan=job.frame_plan,production=job.frame_production||{};
    return `<div class="panel story-editor"><h2>${plan?'Text freigegeben · Bildplan vorbereitet':'Deinen Sprechertext prüfen'}</h2><p class="panel-sub">Zieldauer: ${format(job.duration_seconds)} · Geschätzte Sprechzeit: ${format(quality.estimated_speech_seconds||0)} · Tatsächliche Dauer: ${production.actual_seconds?format(production.actual_seconds):'noch nicht gemessen'}.</p><p class="field-hint">Die Zieldauer ist ein Wunsch. Dein eigener Text wird dafür nicht automatisch gekürzt oder gestreckt.</p><div class="story-narration frame-narration">${esc(job.script.scenes[0].narration)}</div>
      ${production.issues?.length?`<section class="notice error"><strong>Letzte Bildprüfung · ${production.completed_images||0} von ${production.image_total||0} Bildern angenommen</strong><ul>${production.issues.map(issue=>`<li>${esc(issue)}</li>`).join('')}</ul><p>Gültige Bilder bleiben erhalten. Fortsetzen prüft bzw. erzeugt die fehlenden Ergebnisse erneut.</p></section>`:''}
      ${metadata.fact_check_notes?.length?`<details><summary>Sachliche Hinweise</summary><ul>${metadata.fact_check_notes.map(note=>`<li>${esc(note)}</li>`).join('')}</ul></details>`:''}
      ${plan?`<section class="notice"><strong>${plan.images.length} inhaltliche Bildabschnitte vorbereitet</strong><p>Alle Textstellen sind zugeordnet. Bildzeiten folgen später aus der gemessenen Tonspur. Eine Einzelbildfreigabe ist nicht nötig.</p><details><summary>So ist die Geschichte bebildert · optional</summary>${plan.images.map(image=>`<p><strong>${esc(image.setting)}</strong> · ${esc(image.action)} ${esc(image.visible_change)}</p>`).join('')}</details></section>`:`${metadata.visual_summary?`<section class="story-preview"><h3>Bildidee zu deinem Inhalt</h3><p>${esc(metadata.visual_summary)}</p></section>`:''}`}
      <p class="notice">Nach deiner Textfreigabe entstehen passende KI-Bilder und eine lokale Erzählspur. Die Pipeline prüft den tatsächlichen Bildinhalt und setzt das Video zusammen. Abbrechen ist jederzeit möglich; bei erneuter Freigabe werden gültige Dateien wiederverwendet. Bildzugang und Google-Anmeldung für die Bildprüfung unter ⚙ Einstellungen einrichten.</p>
      <div class="editor-status"><span id="script-metrics"></span><strong id="editor-dirty"></strong></div>
      <label>Was soll die KI am Text verbessern?<textarea id="revision-instructions" rows="3" maxlength="4000" placeholder="Beschreibe, was bei genau diesem Thema anders erklärt werden soll."></textarea></label>
      <div class="actions"><button id="revise-script" type="button" class="secondary">KI verbessert das Skript</button><button id="approve-story" type="button" class="primary">${plan?'Frame-Produktion fortsetzen':'Text freigeben & Video erstellen'}</button></div>
      <details><summary>Erzählerstimme ändern</summary>${window.FrameProductionEditor(job)}</details></div>`;
  }
  async function fingerprint(value){
    const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value)));
    return [...new Uint8Array(bytes)].map(byte=>byte.toString(16).padStart(2,'0')).join('');
  }
  function init(){
    $('#frame-input-select').onchange=updateInput;
    document.querySelectorAll('[data-duration]').forEach(button=>button.onclick=()=>{
      $('#duration-minutes').value=Math.floor(Number(button.dataset.duration)/60);$('#duration-extra-seconds').value=Number(button.dataset.duration)%60;
    });
  }
  init();return{configureCreate,collect,availability,editor,fingerprint,duration};
})();
