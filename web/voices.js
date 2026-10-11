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
    const selected = config.voice_id || (language === 'de' ? 'thorsten' : 'ljspeech');
    const speeds = [...new Set([0.85, 1, 1.1, 1.2, 1.25, Number(config.voice_speed || 1)])].sort((a,b) => a-b);
    return `<section class="voice-editor" data-voice-prefix="${prefix}" data-language="${language}">
      <h3>Stimmenstudio · lokal</h3><p class="field-hint">Vergleiche denselben Text. Die Hörprobe verwendet das Tempo und die Pausenkürzung der Produktion. Fehlende Modelle werden beim ersten Hören geladen.</p>
      <div class="grid2"><label>Erzählerstimme<select id="${prefix}-voice-id">${matching.map(v => `<option value="${v.id}" ${selected === v.id ? 'selected' : ''} ${v.available ? '' : 'disabled'}>${escape(v.label)}${v.quality === 'low' ? ' · geringere Modellqualität' : ''}${v.available ? '' : ' · nicht installiert'}</option>`).join('')}</select></label>
      <label>Sprechtempo<select id="${prefix}-voice-speed">${speeds.map(speed => `<option value="${speed}" ${Number(config.voice_speed || 1) === speed ? 'selected' : ''}>${speed.toLocaleString('de-DE')}×${speed === 1 ? ' · normal' : ''}</option>`).join('')}</select></label></div>
      <details><summary>Stimmen hören und vergleichen</summary><label>Text für den Hörvergleich<textarea data-voice-text rows="3" minlength="3" maxlength="600">${escape(text.slice(0, 600) || sample(language))}</textarea></label>
      <button type="button" class="secondary" data-voice-compare>Alle verfügbaren Stimmen vergleichen</button><p class="field-hint" data-voice-status role="status" aria-live="polite"></p><div class="voice-samples" data-voice-samples></div></details></section>`;
  }
  function collect(prefix) {
    return {voice_id: document.getElementById(`${prefix}-voice-id`).value, voice_speed: Number(document.getElementById(`${prefix}-voice-speed`).value)};
  }
  function bind(root = document) {
    root.querySelectorAll('[data-voice-compare]').forEach(button => {
      button.onclick = async () => {
        const studio = button.closest('.voice-editor');
        const prefix = studio.dataset.voicePrefix;
        const status = studio.querySelector('[data-voice-status]');
        const samples = studio.querySelector('[data-voice-samples]');
        const text = studio.querySelector('[data-voice-text]').value.trim();
        if (text.length < 3) { status.textContent = 'Bitte einen Sprechertext eingeben.'; return; }
        const speed = collect(prefix).voice_speed;
        button.disabled = true;
        samples.replaceChildren();
        for (const voice of choices.filter(v => v.language === studio.dataset.language && v.available)) {
          status.textContent = `${voice.label}: Hörprobe wird erstellt …`;
          try {
            const response = await fetch('/api/voice-previews', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({voice_id:voice.id, text, speed})});
            const result = await response.json();
            if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Ungültige Hörprobe.');
            const card = document.createElement('div');
            card.className = 'voice-sample';
            card.innerHTML = `<strong>${escape(voice.label)} · ${speed}×</strong><audio controls preload="metadata" src="${escape(result.url)}" aria-label="Hörprobe ${escape(voice.label)}"></audio><button type="button" class="ghost">Diese Stimme wählen</button>`;
            card.querySelector('button').onclick = () => {
              const select = document.getElementById(`${prefix}-voice-id`);
              select.value = voice.id;
              select.dispatchEvent(new Event('change', {bubbles:true}));
              status.textContent = `${voice.label} ausgewählt. ${prefix === 'job' ? 'Produktionskonfiguration speichern, um die Stimme zu übernehmen.' : 'Gilt für den neuen Auftrag.'}`;
            };
            samples.append(card);
          } catch (error) {
            const notice = document.createElement('p');
            notice.className = 'notice error';
            notice.textContent = `${voice.label}: ${error.message}`;
            samples.append(notice);
          }
        }
        status.textContent = 'Vergleich abgeschlossen. Höre die Proben an und wähle deine Stimme.';
        button.disabled = false;
      };
    });
  }
  function estimateSeconds(words, prefix) {
    const config = collect(prefix);
    const rate = choices.find(voice => voice.id === config.voice_id)?.estimated_words_per_minute || 150;
    return Math.round(words / rate * 60 / config.voice_speed);
  }
  return {load, render, collect, bind, estimateSeconds};
})();
