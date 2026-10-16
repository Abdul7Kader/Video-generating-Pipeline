window.ImageSettings = {
  mount(root, token) {
    const section=document.createElement('section');section.className='settings-section';
    section.innerHTML=`<h2>Frame · KI-Bilder</h2><p>Für Frame fehlt noch der eigenständige Bildzugang. Der vorhandene SVG-Zeichner erstellt keine KI-Illustrationen. Die Skript-Anmeldung allein bestätigt keine Bildfunktion.</p><p>Antigravity bietet Bilder als Agentenwerkzeug an. Für die geplante feste Pipeline ohne Agenten ist dieser Weg derzeit nicht eingebunden. Die direkte Gemini-Bild-API ist separat kostenpflichtig; ein Pro-Abo ersetzt dort keinen API-Schlüssel.</p><button type="button" class="secondary" id="image-access-check">Vorhandenen Zugang prüfen · ohne Bilderzeugung</button><p id="image-access-result" role="status" aria-live="polite"></p><p class="field-hint">Die Prüfung liest nur Anmeldung und Modellangebot. Kein Modelldownload, keine Bilder, keine Änderung von Tarif oder Kontoeinstellungen.</p><p><a href="https://www.antigravity.google/blog/introducing-google-antigravity-sdk" target="_blank" rel="noopener noreferrer">Antigravity-Bildfunktion ↗</a> · <a href="https://ai.google.dev/gemini-api/docs/pricing" target="_blank" rel="noopener noreferrer">Gemini-API-Preise ↗</a></p>`;
    root.append(section);
    const button=section.querySelector('#image-access-check'),result=section.querySelector('#image-access-result');
    button.onclick=async()=>{
      button.disabled=true;result.textContent='Vorhandener Zugang wird geprüft …';
      const progress=document.createElement('progress');progress.setAttribute('aria-label','Bildzugang prüfen');result.before(progress);
      try{
        const response=await fetch('/api/settings/image-access',{method:'POST',headers:{'X-Setup-Token':token}});
        const value=await response.json();
        if(!response.ok)throw new Error(globalThis.PipelineErrors?.message(value)||'Zugangsprüfung fehlgeschlagen. Einstellungen erneut öffnen.');
        result.textContent=value.message+' '+value.next_step;
      }catch(error){result.textContent=error.message||'Zugang konnte nicht geprüft werden.'}
      finally{progress.remove();button.disabled=false}
    };
  },
};
