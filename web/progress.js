// Opaque processes stay indeterminate. ETA needs several consistent local measurements.
window.ProcessProgress = (() => {
  let active = 0;
  const storageKey = 'pipeline-process-times-v2';
  const formatTime = seconds => {
    seconds = Math.max(0, Math.ceil(seconds));
    return seconds < 60 ? `${seconds} Sek.` : `${Math.floor(seconds / 60)} Min. ${seconds % 60} Sek.`;
  };
  function readTimes() {
    try {
      const value = JSON.parse(localStorage.getItem(storageKey) || '{}');
      return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    } catch { return {}; }
  }
  function estimate(key, baseline) {
    const saved = readTimes()[key];
    const samples = Array.isArray(saved) ? saved.filter(value=>Number.isFinite(value)&&value>=.05&&value<=100).slice(-5) : [];
    const sorted = [...samples].sort((a,b)=>a-b);
    const median = sorted[Math.floor(sorted.length/2)];
    const reliable = samples.length>=3 && (sorted.at(-1)-sorted[0])/median<=.5;
    return {samples,seconds:reliable?baseline*median:null};
  }
  function scriptOptions(provider, duration = 60, singleScene = false, revision = false) {
    return {
      label: singleScene ? 'Sprechertext und Zeichnungen der Szene überarbeiten' : revision ? 'Sprecher-Skript überarbeiten' : 'Sprecher-Skript schreiben',
      key: `script:${provider}:${window.PipelineScriptModel || 'unconfirmed'}:${singleScene ? 'scene' : 'full'}`,
      baseline: (provider === 'qwen' ? 420 : 120) + Number(duration || 60) * (singleScene ? 0.5 : 2),
      minimumSample: 15,
      detail: 'Die KI schreibt einen durchgehenden Sprechertext und eine Bildidee. Zeichnungen und Video entstehen nach deiner Freigabe.'
    };
  }
  function voiceOptions(voice, text, speed = 1) {
    const words = text.trim().split(/\s+/u).length;
    return {
      label: `${voice.label}: Hörprobe erzeugen`,
      key: `voice:${voice.id}:continuous-v2:${speed}`,
      baseline: voice.provider === 'qwen_tts' ? 80 + words / (voice.estimated_words_per_minute || 156) * 60 * 8 : (voice.installed === false ? 30 : 4) + words * 0.08,
      minimumSample: voice.provider === 'qwen_tts' ? 20 : 2,
      detail: 'Die Stimme wird erzeugt und lange Sprechpausen werden gekürzt. Bereits gespeicherte Hörproben sind sofort verfügbar.'
    };
  }
  function start(host, options) {
    const baseline = Math.max(1, Number(options.baseline) || 1);
    const history = estimate(options.key, baseline), total=history.seconds;
    const started = performance.now() - Math.max(0, Number(options.elapsedSeconds) || 0) * 1000;
    const panel = document.createElement('section');
    panel.className = 'process-progress';
    panel.setAttribute('aria-busy', 'true');
    const title = document.createElement('strong');
    title.textContent = options.label;
    const bar = document.createElement('progress');
    bar.max = 100;
    bar.removeAttribute('value');
    bar.setAttribute('aria-label', `${options.label} – läuft, Fortschritt noch nicht messbar`);
    const timing = document.createElement('p');
    timing.className = 'process-timing';
    const state = document.createElement('p');
    state.className = 'field-hint';
    state.setAttribute('role', 'status');
    state.textContent = options.waiting ? 'Der Auftrag wartet auf den Produktionsplatz. Die Restzeit ist noch nicht messbar.' : `${total===null?'Restzeit noch nicht messbar. Erst mehrere ähnliche Läufe liefern einen Erfahrungswert.':`Erfahrungswert aus ${history.samples.length} ähnlichen Läufen: ca. ${formatTime(total)}.`} ${options.detail || ''}`;
    panel.append(title, bar, timing, state);
    host.replaceChildren(panel);
    let stopped = false, overdue = false;
    if (options.blocking !== false) active++;
    const stop = () => {
      if (stopped) return false;
      stopped = true;
      clearInterval(timer);
      if (options.blocking !== false) active--;
      panel.setAttribute('aria-busy', 'false');
      return true;
    };
    const update = () => {
      if (!panel.isConnected) { stop(); return; }
      const elapsed = (performance.now() - started) / 1000;
      if (options.waiting) { timing.textContent = `Wartezeit bisher: ${formatTime(Math.floor(elapsed))}`; return; }
      const remaining = total===null?null:Math.ceil(Math.max(0,total-elapsed)/5)*5;
      timing.textContent = `Vergangen: ${formatTime(Math.floor(elapsed))} · ${total===null?'Restzeit noch nicht messbar':elapsed<total?`Erfahrungswert: noch ca. ${formatTime(remaining)}`:'Dauert länger als geschätzt'}`;
      bar.setAttribute('aria-valuetext', `Läuft. ${timing.textContent}`);
      if (total!==null && elapsed >= total && !overdue) {
        overdue = true;
        state.textContent = 'Der Vorgang läuft weiter. Die geschätzte Wartezeit wurde überschritten; bitte auf das Ergebnis warten.';
      }
    };
    const timer = setInterval(update, 1000);
    update();
    return {
      attach(nextHost) { nextHost.replaceChildren(panel); update(); },
      dispose: stop,
      finish(message = 'Fertig') {
        if (!stop()) return;
        const elapsed = (performance.now() - started) / 1000;
        bar.value = 100;
        bar.setAttribute('aria-label', `${options.label || 'Vorgang'} – abgeschlossen`);
        bar.setAttribute('aria-valuetext', 'Fertig: 100 Prozent');
        timing.textContent = `Gesamtdauer: ${formatTime(elapsed)}`;
        state.textContent = message;
        panel.classList.add('complete');
        // Ignore cache hits and idempotent retries when learning generation times.
        if (options.key && elapsed >= (options.minimumSample ?? 2)) {
          const times = readTimes();
          const sample = elapsed / baseline;
          if(!Number.isFinite(sample)||sample<.05||sample>100)return;
          times[options.key] = [...history.samples,sample].slice(-5);
          try { localStorage.setItem(storageKey, JSON.stringify(times)); } catch {}
        }
      },
      fail(message) {
        if (!stop()) return;
        panel.classList.add('error');
        timing.textContent = `Nach ${formatTime((performance.now() - started) / 1000)} beendet`;
        bar.setAttribute('aria-valuetext', 'Fehlgeschlagen');
        bar.hidden = true;
        state.textContent = message;
      }
    };
  }
  return {start, scriptOptions, voiceOptions, get busy() { return active > 0; }};
})();
