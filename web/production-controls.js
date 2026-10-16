/* Aborts only this job; the original long request remains attached until cleanup. */
globalThis.ProductionControls = {
  mount(job, host = document.querySelector('#workspace'), refresh) {
    document.getElementById('production-cancel')?.remove();
    if (!host || !['render_planning', 'render_queued', 'rendering', 'cancelling'].includes(job.status)) return;
    const button = document.createElement('button');
    button.id = 'production-cancel';
    button.type = 'button';
    button.className = 'secondary';
    button.textContent = job.status === 'cancelling' ? 'Eigene Prozesse werden beendet …' : 'Diese Erstellung abbrechen';
    button.disabled = job.status === 'cancelling';
    button.onclick = async () => {
      button.disabled = true;
      button.textContent = 'Erstellung wird beendet …';
      try {
        const response = await fetch(`/api/jobs/${encodeURIComponent(job.id)}/cancel`, {method: 'POST'});
        const result = await response.json();
        if (!response.ok) throw new Error(globalThis.PipelineErrors?.message(result) || result.detail || 'Abbruch konnte nicht angefordert werden.');
        button.textContent = result.status === 'cancelled' ? 'Erstellung abgebrochen' : 'Eigene Prozesse werden beendet …';
        if (refresh) await refresh();
      } catch (error) {
        button.disabled = false;
        button.textContent = error.message;
      }
    };
    host.append(button);
  },
};
