globalThis.ReviewControls = {
  async mount(job, refresh) {
    clearTimeout(this.timer);
    document.getElementById('discord-review-panel')?.remove();
    if (!job.output_path || !['video_review','video_rejected','ready_to_publish','publish_queued','publishing','published','published_partial','publish_failed','publish_pending'].includes(job.status)) return;
    const workspace = document.querySelector('#workspace');
    if (!workspace) return;
    const panel = document.createElement('section');
    panel.className = 'panel';
    panel.id = 'discord-review-panel';
    const heading = document.createElement('h2');
    heading.textContent = 'Video abnehmen und weitergeben';
    panel.append(heading);
    workspace.append(panel);
    async function request(suffix, method='GET', body) {
      const response = await fetch(`/api/jobs/${encodeURIComponent(job.id)}/${suffix}`, {method,
        headers:{'Content-Type':'application/json'},...(body ? {body:JSON.stringify(body)} : {})});
      const value = await response.json();
      if (!response.ok) throw new Error(value.detail || 'Aktion konnte nicht abgeschlossen werden.');
      return value;
    }
    const status = document.createElement('p');
    status.setAttribute('role','status');
    status.setAttribute('aria-live','polite');
    panel.append(status);
    try {
      const value = await request('discord-review');
      if (!panel.isConnected) return;
      const labels = {queued:'Wartet auf Übertragung an Discord',sending:'Video wird an Discord gesendet',sent:'In Discord zur Prüfung bereit',approved:'In Discord freigegeben',rejected:'In Discord abgelehnt',failed:'Abnahmeschritt fehlgeschlagen',unknown:'Übertragung nicht bestätigt – Discord-Kanal vor Wiederholung prüfen',revision_requested:'Änderungswunsch wartet auf die KI',revising:'KI überarbeitet den Text',planning:'Freigegebener Text wird illustriert',render_requested:'Neue Videoerstellung eingereiht',revised:'Text überarbeitet – neue Freigabe erforderlich',superseded:'Diese Abnahme wurde durch eine neuere ersetzt'};
      status.textContent = value.review ? (labels[value.review.state] || value.review.state) + (value.review.error ? ': ' + value.review.error : '') : 'Dieses Video wurde noch nicht an Discord gesendet.';
      const connection = document.createElement('p');
      connection.textContent = value.connection;
      panel.append(connection);
      const location = document.createElement('p');
      location.textContent = 'Original auf diesem Rechner: ' + (value.local_path || job.output_path);
      panel.append(location);
      if (value.review?.message_id) {
        const link = document.createElement('a');
        link.textContent = 'Abnahme in Discord öffnen ↗';
        link.href = 'https://discord.com/channels/' + [value.review.guild_id,value.review.channel_id,value.review.message_id].map(encodeURIComponent).join('/');
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.dataset.discordReview = 'true';
        panel.append(link);
      }
      if (['video_review','video_rejected'].includes(job.status)) {
        const send = document.createElement('button');
        send.type = 'button';
        send.dataset.sendReview = 'true';
        send.className = 'secondary';
        send.textContent = value.review ? 'Erneut zur Discord-Abnahme senden' : 'Zur Discord-Abnahme senden';
        send.disabled = ['queued','sending','deciding','revising','planning','revision_requested','render_requested'].includes(value.review?.state);
        send.onclick = async () => {
          send.disabled = true;
          try {
            await request('discord-review','POST',{expected_version:job.render_version,expected_hash:job.output_sha256});
            status.textContent = 'Zur Discord-Abnahme eingereiht. Alte Freigabeknöpfe werden ungültig; es wurde nichts auf Social Media veröffentlicht.';
          } catch (error) {status.textContent = error.message;send.disabled = false;}
        };
        panel.append(send);
      }
      const archive = document.createElement('button');
      archive.type = 'button';
      archive.className = 'ghost';
      archive.textContent = 'In den gewählten Videoordner kopieren';
      archive.onclick = async () => {
        archive.disabled = true;
        try {const result = await request('archive','POST');status.textContent = 'Gespeichert: ' + result.paths.join(', ');}
        catch (error) {status.textContent = error.message;}
        finally {archive.disabled = false;}
      };
      panel.append(archive);
      const exported = document.createElement('button');
      exported.type = 'button';exported.className = 'ghost';exported.textContent = 'Uploadpaket mit Video und Beschriftung vorbereiten';
      exported.onclick = async () => {
        exported.disabled = true;
        try {const result=await request('export-package','POST',{expected_version:job.render_version,expected_hash:job.output_sha256});status.textContent='Uploadpaket gespeichert: '+result.directory+' · Es wurde nichts hochgeladen.';}
        catch(error){status.textContent=error.message;}
        finally{exported.disabled=false;}
      };
      panel.append(exported);
      if (job.publication_targets?.some(target => target.status === 'awaiting_user')) {
        const confirm = document.createElement('button');
        confirm.type='button';confirm.className='ghost';confirm.textContent='TikTok-Status prüfen · keinen neuen Upload starten';
        confirm.onclick=async()=>{confirm.disabled=true;try{const result=await request('check-publication','POST');status.textContent=result.status;if(refresh)await refresh();}catch(error){status.textContent=error.message;}finally{confirm.disabled=false;}};
        panel.append(confirm);
      }
      const watch = async () => {
        if (!panel.isConnected) return;
        try {
          const latest = await request('discord-review');
          if (!panel.isConnected) return;
          if (latest.job_status !== job.status && refresh) {await refresh();return;}
          status.textContent = latest.review ? (labels[latest.review.state] || latest.review.state) + (latest.review.error ? ': ' + latest.review.error : '') : 'Dieses Video wurde noch nicht an Discord gesendet.';
          connection.textContent = latest.connection;
          const send = panel.querySelector('[data-send-review]');
          if (send) send.disabled = ['queued','sending','deciding','revising','planning','revision_requested','render_requested'].includes(latest.review?.state);
          if (latest.review?.message_id && !panel.querySelector('[data-discord-review]')) {
            const link = document.createElement('a');
            link.dataset.discordReview = 'true';link.textContent = 'Abnahme in Discord öffnen ↗';
            link.href = 'https://discord.com/channels/' + [latest.review.guild_id,latest.review.channel_id,latest.review.message_id].map(encodeURIComponent).join('/');
            link.target = '_blank';link.rel = 'noopener noreferrer';panel.append(link);
          }
        } catch (error) {connection.textContent = error.message;}
        finally {if(panel.isConnected)this.timer=setTimeout(watch,3000);}
      };
      this.timer = setTimeout(watch,3000);
    } catch (error) {status.textContent = error.message;}
  },
};
