// Providers return a completed result, so time and progress are explicitly estimated.
window.ProcessProgress = (() => {
  let active = 0;
  const storageKey = 'pipeline-process-times-v1';
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
    const factor = readTimes()[key];
    return baseline * (typeof factor === 'number' && Number.isFinite(factor) && factor >= 0.25 && factor <= 4 ? factor : 1);
  }
  function scriptOptions(provider, duration = 60, singleScene = false, revision = false) {
    return {
      label: singleScene ? 'Sprechertext und Zeichnungen der Szene überarbeiten' : revision ? 'Sprecher-Skript überarbeiten' : 'Sprecher-Skript schreiben',
      key: `script:${provider}:${singleScene ? 'scene' : 'full'}`,
      baseline: (provider === 'qwen' ? 420 : 120) + Number(duration || 60) * (singleScene ? 0.5 : 2),
      minimumSample: 15,
      detail: 'Die KI schreibt einen durchgehenden Sprechertext und eine Bildidee. Zeichnungen und Video entstehen nach deiner Freigabe.'
    };
  }
  function voiceOptions(voice, text) {
    const words = text.trim().split(/\s+/u).length;
    return {
      label: `${voice.label}: Hörprobe erzeugen`,
      key: `voice:${voice.id}`,
      baseline: voice.provider === 'qwen_tts' ? 80 + words / (voice.estimated_words_per_minute || 156) * 60 * 8 : (voice.installed === false ? 30 : 4) + words * 0.08,
      minimumSample: voice.provider === 'qwen_tts' ? 20 : 2,
      detail: 'Die Stimme wird erzeugt und lange Sprechpausen werden gekürzt. Bereits gespeicherte Hörproben sind sofort verfügbar.'
    };
  }
  function start(host, options) {
    const baseline = Math.max(1, Number(options.baseline) || 1);
    const total = estimate(options.key, baseline);
    const started = performance.now() - Math.max(0, Number(options.elapsedSeconds) || 0) * 1000;
    const panel = document.createElement('section');
    panel.className = 'process-progress';
    panel.setAttribute('aria-busy', 'true');
    const title = document.createElement('strong');
    title.textContent = options.label;
    const bar = document.createElement('progress');
    bar.max = 100;
    bar.value = 0;
    if (options.waiting) bar.removeAttribute('value');
    bar.setAttribute('aria-label', `${options.label} – geschätzter Fortschritt`);
    const timing = document.createElement('p');
    timing.className = 'process-timing';
    const state = document.createElement('p');
    state.className = 'field-hint';
    state.setAttribute('role', 'status');
    state.textContent = options.waiting ? 'Der Auftrag wartet auf den Produktionsplatz. Die Restzeit wird nach Produktionsstart geschätzt.' : `Geschätzte Wartezeit: ca. ${formatTime(total)} ${options.detail || ''}`;
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
      const fraction = elapsed / total;
      // Reserve completion for the actual server response, including overdue runs.
      bar.value = fraction < 1 ? fraction * 90 : 90 + 5 * (1 - Math.exp(1 - fraction));
      const remaining = Math.ceil(Math.max(0, total - elapsed) / 5) * 5;
      timing.textContent = `Vergangen: ${formatTime(Math.floor(elapsed))} · ${fraction < 1 ? `Noch ca. ${formatTime(remaining)}` : 'Dauert länger als geschätzt'}`;
      bar.setAttribute('aria-valuetext', `Geschätzt ${Math.floor(bar.value)} Prozent. ${timing.textContent}`);
      if (fraction >= 1 && !overdue) {
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
        bar.setAttribute('aria-valuetext', 'Fertig: 100 Prozent');
        timing.textContent = `Gesamtdauer: ${formatTime(elapsed)}`;
        state.textContent = message;
        panel.classList.add('complete');
        // Ignore cache hits and idempotent retries when learning generation times.
        if (options.key && elapsed >= (options.minimumSample ?? 2)) {
          const times = readTimes();
          const sample = Math.max(0.25, Math.min(4, elapsed / baseline));
          times[options.key] = (total / baseline + sample) / 2;
          try { localStorage.setItem(storageKey, JSON.stringify(times)); } catch {}
        }
      },
      fail(message) {
        if (!stop()) return;
        panel.classList.add('error');
        timing.textContent = `Nach ${formatTime((performance.now() - started) / 1000)} beendet`;
        bar.setAttribute('aria-valuetext', 'Fehlgeschlagen');
        state.textContent = message;
      }
    };
  }
  return {start, scriptOptions, voiceOptions, get busy() { return active > 0; }};
})();
