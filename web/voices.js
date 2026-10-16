window.VoiceEditor = (() => {
  let choices = [];
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sample = language => language === 'en'
    ? 'Mila puts down her phone and opens a book. A small idea becomes a new plan. She shows Ben what she has discovered.'
    : 'Mila legt ihr Handy weg und schlägt ein Buch auf. Aus einem kleinen Einfall wird ein neuer Plan. Sie zeigt Ben, was sie entdeckt hat.';
  async function load() {
    const response = await fetch('/api/voices');
    if (!response.ok) throw new Error('Stimmenauswahl konnte nicht geladen werden.');
    choices = await response.json();
  }
  function render(prefix, config, language, text = '') {
    const matching = choices.filter(v => v.language === language);
    const selected = matching.some(v=>v.id===config.voice_id)?config.voice_id:(language==='de'?'thorsten':'ljspeech');
    const chosen=matching.find(v=>v.id===selected);
    const comparison=matching.filter(v=>v.available&&v.installed&&['qwen_narrator','thorsten','ljspeech'].includes(v.id));
    const speeds = [...new Set([0.85, 1, 1.1, 1.2, 1.25, Number(config.voice_speed || 1)])].sort((a,b) => a-b);
    return `<section class="voice-editor" data-voice-prefix="${prefix}" data-language="${language}">
      <h3>Deine Erzählerstimme</h3><p class="field-hint">Ausgewählt: <strong data-voice-chosen>${escape(chosen?.label||'Stimme fehlt')}</strong>. Die Hörprobe verwendet Tempo, Pausenkürzung und Lautheitsregeln der Produktion. Qwen kann auf einer CPU mehrere Minuten brauchen; Piper ist schneller. Ein Stimmenwechsel erfolgt nur durch deine Auswahl.</p>
      <p class="notice" data-voice-reason ${chosen?.available?'hidden':''}>${escape(chosen?.reason||'Diese Stimme zuerst unter Einstellungen einrichten.')}</p>
      <div class="grid2"><label>Erzählerstimme<select id="${prefix}-voice-id">${matching.filter(v=>v.available||v.id===selected).map(v => `<option value="${v.id}" ${selected === v.id ? 'selected' : ''} ${v.available ? '' : 'disabled'}>${escape(v.label)}${v.quality === 'low' ? ' · geringere Modellqualität' : ''}${v.available ? '' : ' · nicht bereit'}</option>`).join('')}</select></label>
      <label>Sprechtempo<select id="${prefix}-voice-speed">${speeds.map(speed => `<option value="${speed}" ${Number(config.voice_speed || 1) === speed ? 'selected' : ''}>${speed.toLocaleString('de-DE')}×${speed === 1 ? ' · normal' : ''}</option>`).join('')}</select></label></div>
      <details><summary>Stimmen hören und vergleichen</summary><label>Text für den Hörvergleich<textarea data-voice-text rows="3" minlength="3" maxlength="600">${escape(text.slice(0, 600) || sample(language))}</textarea></label>
      <button type="button" class="secondary" data-voice-preview ${chosen?.available?'':'disabled'}>Ausgewählte Stimme anhören</button> <button type="button" class="ghost" data-voice-compare ${comparison.length<2?'disabled':''}>Qwen und Piper vergleichen</button><p class="field-hint">Der Vergleich erzeugt zwei Hörproben mit demselben Text und Tempo, ohne neue Modelle herunterzuladen. Weitere Stimmen wählst du einzeln. Fehlende Stimmen findest du unter ⚙ Einstellungen.</p><div data-voice-progress></div><p class="field-hint" data-voice-status role="status" aria-live="polite"></p><div class="voice-samples" data-voice-samples></div></details></section>`;
  }
  function collect(prefix) {
    const voice_id = document.getElementById(`${prefix}-voice-id`).value;
    if(!choices.some(v=>v.id===voice_id))throw new Error('Die ausgewählte Stimme fehlt. Öffne Einstellungen oder wähle ausdrücklich eine andere Stimme.');
    return {voice_id, voice_provider: choices.find(v => v.id === voice_id)?.provider || 'piper', voice_speed: Number(document.getElementById(`${prefix}-voice-speed`).value)};
  }
  function bind(root = document) {
    root.querySelectorAll('.voice-editor').forEach(studio=>{
      const select=document.getElementById(`${studio.dataset.voicePrefix}-voice-id`);
      select.onchange=()=>{
        const chosen=choices.find(v=>v.id===select.value);
        studio.querySelector('[data-voice-chosen]').textContent=chosen?.label||'Stimme fehlt';
        const reason=studio.querySelector('[data-voice-reason]');
        reason.hidden=Boolean(chosen?.available);
        reason.textContent=chosen?.reason||'Diese Stimme zuerst unter Einstellungen einrichten.';
        studio.querySelector('[data-voice-preview]').disabled=!chosen?.available;
      };
    });
    root.querySelectorAll('[data-voice-compare], [data-voice-preview]').forEach(button => {
      button.onclick = async () => {
        if (ProcessProgress.busy) return;
        const studio = button.closest('.voice-editor');
        const prefix = studio.dataset.voicePrefix;
        const status = studio.querySelector('[data-voice-status]');
        const samples = studio.querySelector('[data-voice-samples]');
        const text = studio.querySelector('[data-voice-text]').value.trim();
        if (text.length < 3) { status.textContent = 'Bitte einen Sprechertext eingeben.'; return; }
        let config;
        try { config=collect(prefix); } catch(error) { status.textContent=error.message; return; }
        const speed = config.voice_speed;
        const selected = config.voice_id;
        const targets = choices.filter(v => v.language === studio.dataset.language && v.available && (button.hasAttribute('data-voice-preview') ? v.id===selected : v.installed&&['qwen_narrator','thorsten','ljspeech'].includes(v.id)));
        if(!targets.length){status.textContent='Die gewählte Stimme zuerst unter Einstellungen einrichten.';return;}
        const controls = [...(studio.closest('form') || root).querySelectorAll('button, input, textarea, select')];
        const disabled = controls.map(item => item.disabled);
        controls.forEach(item => { item.disabled = true; });
        samples.replaceChildren();
        let completed = 0;
        const estimates = targets.map(voice => ProcessProgress.voiceOptions(voice, text, speed));
        const options = targets.length === 1 ? estimates[0] : {label: `${targets.length} Stimmen vergleichen`, key: `voice-compare:${targets.map(v=>v.id).join(',')}:continuous-v2:${speed}`, baseline: estimates.reduce((sum, item) => sum + item.baseline, 0), minimumSample: 20, detail: 'Die Hörproben werden nacheinander erstellt. Gespeicherte Hörproben sind sofort verfügbar.'};
        const progress = ProcessProgress.start(studio.querySelector('[data-voice-progress]'), options);
        studio.querySelector('[data-voice-progress]').scrollIntoView({block: 'nearest'});
        try {
          for (const [index, voice] of targets.entries()) {
            status.textContent = `${index + 1} von ${targets.length} · ${voice.label}: Hörprobe wird erstellt …`;
            try {
              const response = await fetch('/api/voice-previews', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({voice_id:voice.id, text, speed})});
              const result = await response.json();
              if (!response.ok) throw new Error(globalThis.PipelineErrors?.message(result) || (typeof result.detail === 'string' ? result.detail : 'Ungültige Hörprobe.'));
              if(result.voice_id!==voice.id||!/^\/api\/voice-previews\/[0-9a-f]{64}$/.test(result.url))throw new Error('Die Hörprobe passt nicht zur ausgewählten Stimme. Bitte erneut versuchen.');
              const card = document.createElement('div');
              card.className = 'voice-sample';
              card.innerHTML = `<strong>${escape(voice.label)} · ${speed}×</strong><p>${result.speech?`${Number(result.speech.duration_seconds).toFixed(1)} Sekunden · Lautstärke angeglichen · ${result.cached?'gespeicherte Hörprobe':'neu erzeugt'}`:''}</p><audio controls preload="metadata" src="${escape(result.url)}" aria-label="Hörprobe ${escape(voice.label)}"></audio><button type="button" class="ghost">Diese Stimme wählen</button>`;
              card.querySelector('button').onclick = () => {
                if (ProcessProgress.busy) return;
                const select = document.getElementById(`${prefix}-voice-id`);
                select.value = voice.id;
                select.dispatchEvent(new Event('change', {bubbles:true}));
                status.textContent = `${voice.label} ausgewählt. ${prefix === 'job' ? 'Produktionskonfiguration speichern, um die Stimme zu übernehmen.' : 'Gilt für den neuen Auftrag.'}`;
              };
              card.querySelector('button').disabled = true;
              samples.append(card);
              completed++;
            } catch (error) {
              const notice = document.createElement('p');
              notice.className = 'notice error';
              notice.textContent = `${voice.label}: ${error.message}`;
              samples.append(notice);
            }
          }
          const message = completed === targets.length && completed ? 'Hörprobe bereit. Höre sie an und wähle deine Stimme.' : `${completed} von ${targets.length} Hörproben erzeugt. Bitte die angezeigte Fehlermeldung prüfen.`;
          status.textContent = message;
          if (completed === targets.length && completed) progress.finish(message);
          else progress.fail(message);
        } catch (error) {
          progress.fail(error.message);
          status.textContent = error.message;
        } finally {
          controls.forEach((item, index) => { item.disabled = disabled[index]; });
          samples.querySelectorAll('button').forEach(item => { item.disabled = false; });
        }
      };
    });
  }
  function estimateSeconds(words, prefix) {
    const config = collect(prefix);
    const rate = choices.find(voice => voice.id === config.voice_id)?.estimated_words_per_minute || 150;
    return Math.round(words / rate * 60 / config.voice_speed);
  }
  const available=id=>choices.some(v=>v.id===id&&v.available);
  return {load, render, collect, bind, estimateSeconds, available};
})();
