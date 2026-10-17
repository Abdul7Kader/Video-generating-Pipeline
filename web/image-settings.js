window.ImageSettings = {
  preferences(section) {
    return {provider:section.querySelector('#image-provider').value,
      cloudflare_account_id:section.querySelector('#image-account').value.trim(),
      cloudflare_free_confirmed:section.querySelector('#image-free').checked};
  },
  async mount(root, token) {
    const section=document.createElement('section');section.className='settings-section';
    section.innerHTML=`<h2>Frame · KI-Bilder</h2>
      <p>Wähle den Bildanbieter für Frame. Speichern startet keine Generierung. Ein Test erzeugt ein Bild zum eingegebenen Motiv und verbraucht Anbieterkontingent.</p>
      <label>Bildanbieter<select id="image-provider"><option value="cloudflare">Cloudflare · FLUX · kostenloses Tageskontingent</option><option value="antigravity">Google AI Pro / Antigravity · vorhandenes Abo</option></select></label>
      <div id="image-cloudflare"><p>Benötigt ein Cloudflare-Konto im Workers-Free-Tarif und einen auf dieses Konto begrenzten Workers-AI-Token. 10.000 Recheneinheiten pro Tag sind keine feste Bilderzahl. Im Free-Tarif stoppen Anfragen beim Limit.</p>
        <label>Cloudflare Account-ID<input id="image-account" maxlength="32" autocomplete="off" placeholder="32 Zeichen aus dem Cloudflare-Dashboard"></label>
        <label>Workers-AI-Token<input id="image-token" type="password" maxlength="1200" autocomplete="new-password"></label>
        <label class="check"><input id="image-free" type="checkbox"> Ich habe den Workers-Free-Tarif geprüft. Die App kann meinen Tarif nicht selbst bestätigen. Auf einem bezahlten Konto könnten Kosten entstehen.</label>
        <button type="button" class="ghost" id="image-token-clear">Gespeicherten Cloudflare-Token entfernen</button>
        <p><a href="https://developers.cloudflare.com/workers-ai/get-started/rest-api/" target="_blank" rel="noopener noreferrer">Konto und API-Token einrichten ↗</a> · <a href="https://developers.cloudflare.com/workers-ai/platform/pricing/" target="_blank" rel="noopener noreferrer">Aktuelle Limits ↗</a></p>
      </div>
      <div id="image-google" hidden><p>Nutzt die reguläre Anmeldung der installierten Antigravity-CLI. Kein Gemini-API-Schlüssel nötig. Unter „Skript-Zugang“ das angebotene Google-Modell wählen. Zusatzcredits müssen ausgeschaltet sein.</p>
        <p>Die App begrenzt den Aufruf auf Bildwerkzeuge. Kann die installierte Version diesen Schutz nicht bestätigen, stoppt der Test mit Fehler-ID. Intern verwendet Google eine Agentenlaufzeit; die Pipeline steuert den Ablauf.</p>
        <p><a href="https://antigravity.google/docs/install?tab=cli" target="_blank" rel="noopener noreferrer">Antigravity installieren und regulär anmelden ↗</a></p>
      </div>
      <p id="image-vault" class="field-hint"></p><button type="button" class="secondary" id="image-save">Bildanbieter speichern</button>
      <button type="button" class="ghost" id="image-access-check">Gespeicherten Zugang prüfen · ohne Bilderzeugung</button>
      <p id="image-access-result" role="status" aria-live="polite"></p>
      <label>Motiv für ein Testbild<textarea id="image-prompt" rows="3" maxlength="1400" placeholder="Zum Beispiel: Ein Strichmännchen adoptiert eine Katze. Zeige die Katze deutlich, während sie aus ihrer Transportbox tritt. Weißer Hintergrund, keine Schrift."></textarea></label>
      <p class="field-hint">Das Motiv wird an den gewählten Anbieter gesendet. In der Frame-Produktion prüft die bestehende Google-/Antigravity-Anmeldung den tatsächlichen Bildinhalt und Stil – auch bei Cloudflare-Bildern. Dieser einzelne Test prüft nur den Bildaufruf.</p>
      <button type="button" class="secondary" id="image-test">Speichern und ein Testbild erzeugen</button><button type="button" class="ghost" id="image-cancel" hidden>Testbild abbrechen</button>
      <progress id="image-progress" aria-label="Testbild erzeugen" hidden></progress><p id="image-task" role="status" aria-live="polite"></p>
      <img id="image-preview" alt="Erzeugtes Testbild zum eingegebenen Motiv" hidden style="max-width:100%;max-height:480px;object-fit:contain">
      <p class="field-hint">Testbilder: data/image-previews. Ein Video startest du im Reiter Frame nach deiner Textfreigabe. Endvideos findest du im unter „Ablage“ gewählten Ordner; Arbeitsdateien werden standardmäßig nur manuell aufgeräumt.</p>`;
    root.append(section);
    const $=id=>section.querySelector('#'+id),result=$('image-access-result');
    async function api(path='',method='GET',value) {
      const response=await fetch('/api/settings/'+path,{method,headers:{'Content-Type':'application/json','X-Setup-Token':token},...(value!==undefined?{body:JSON.stringify(value)}:{})});
      const data=await response.json();
      if(!response.ok)throw new Error(globalThis.PipelineErrors?.message(data)||data.detail||'Bildeinstellung konnte nicht verarbeitet werden.');
      return data;
    }
    const showProvider=()=>{$('image-cloudflare').hidden=$('image-provider').value!=='cloudflare';$('image-google').hidden=!$('image-cloudflare').hidden;};
    $('image-provider').onchange=showProvider;
    $('image-account').oninput=()=>{$('image-free').checked=false;};
    let state;
    const vault=value=>{
      state=value;$('image-token').value='';$('image-token').disabled=!value.vault_ready;
      $('image-token').placeholder=value.token_present?'Gespeichert – leer lassen zum Behalten':'Noch nicht gespeichert';
      $('image-token-clear').disabled=!value.token_present;
      $('image-vault').textContent=value.vault_ready?'Schlüssel bleiben im geschützten Betriebssystem-Tresor und werden hier nicht angezeigt.':'Betriebssystem-Tresor fehlt oder ist gesperrt. Kein Klartext-Ersatz. Google-Anmeldung verwaltet Antigravity.';
    };
    async function save(clear=false) {
      const body={preferences:window.ImageSettings.preferences(section)};
      if(clear)body.clear_token=true;
      else if($('image-token').value.trim())body.token=$('image-token').value.trim();
      vault(await api('images','PUT',body));
    }
    function busy(running) {
      ['image-save','image-test','image-access-check','image-provider'].forEach(id=>{$(id).disabled=running;});
      $('image-token-clear').disabled=running||!state?.token_present;
      $('image-cancel').hidden=!running;$('image-progress').hidden=!running;
    }
    function showTask(task) {
      busy(task.status==='running');
      const elapsed=task.started_at?Math.max(0,Math.floor(Date.now()/1000-task.started_at)):0;
      $('image-task').textContent=task.message+(task.status==='running'?' Vergangen: '+elapsed+' Sek. · Restzeit noch nicht messbar.':'')+(task.failure?' '+task.failure.next_action:'');
      if(task.status==='completed'&&/^\/api\/settings\/images\/files\/[a-f0-9]{32}$/.test(task.image_url||'')) {
        $('image-preview').src=task.image_url;$('image-preview').hidden=false;
      }
    }
    async function poll(task) {
      showTask(task);
      while(task.status==='running'&&section.isConnected) {
        await new Promise(resolve=>setTimeout(resolve,1000));
        if(!section.isConnected)return;
        task=await api('images/preview');showTask(task);
      }
    }
    $('image-save').onclick=async()=>{busy(true);try{await save();result.textContent='Bildanbieter gespeichert. Es wurde kein Bild erzeugt.';}catch(error){result.textContent=error.message;}finally{busy(false);}};
    $('image-token-clear').onclick=async()=>{busy(true);try{await save(true);result.textContent='Cloudflare-Token aus dem Tresor entfernt.';}catch(error){result.textContent=error.message;}finally{busy(false);}};
    $('image-access-check').onclick=async()=>{
      busy(true);result.textContent='Gespeicherten Zugang prüfen …';
      try{const value=await api('image-access','POST');result.textContent=value.message+' '+value.next_step;}
      catch(error){result.textContent=error.message;}finally{busy(false);}
    };
    $('image-test').onclick=async()=>{
      busy(true);$('image-preview').hidden=true;
      try{await save();await poll(await api('images/preview','POST',{prompt:$('image-prompt').value}));}
      catch(error){$('image-task').textContent=error.message;}finally{busy(false);}
    };
    $('image-cancel').onclick=async()=>{try{showTask(await api('images/cancel','POST'));}catch(error){$('image-task').textContent=error.message;}};
    try{
      const value=await api('images');if(!section.isConnected)return;
      $('image-provider').value=value.preferences.provider;$('image-account').value=value.preferences.cloudflare_account_id;$('image-free').checked=value.preferences.cloudflare_free_confirmed;
      vault(value);showProvider();await poll(await api('images/preview'));
    }catch(error){result.textContent=error.message;}
  },
};
