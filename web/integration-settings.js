globalThis.IntegrationSettings = {
  async mount(parent, token) {
    if (parent.querySelector('#integration-settings')) return;
    const section = document.createElement('section');
    section.id = 'integration-settings';
    section.className = 'settings-section';
    section.textContent = 'Videoordner und Kanäle werden geladen …';
    parent.append(section);
    const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
    async function api(suffix = '', method = 'GET', value) {
      const response = await fetch('/api/settings/integrations' + suffix, {method,
        headers:{'Content-Type':'application/json', 'X-Setup-Token':token},
        ...(value ? {body:JSON.stringify(value)} : {})});
      const result = await response.json();
      if (!response.ok) throw new Error(globalThis.PipelineErrors?.message(result) || result.detail || 'Kontoeinstellung konnte nicht geladen werden.');
      return result;
    }
    try {
      const state = await api(), preferences = state.preferences;
      if (!section.isConnected) return;
      const text = (name, label, hint = '') => `<label>${escape(label)}<input data-integration="${name}" value="${escape(preferences[name])}" autocomplete="off">${hint ? `<small>${escape(hint)}</small>` : ''}</label>`;
      const flag = (name, label) => `<label class="check"><input type="checkbox" data-integration="${name}" ${preferences[name] ? 'checked' : ''}> ${escape(label)}</label>`;
      const secret = (name, label) => `<label>${escape(label)}<input type="password" data-credential="${name}" autocomplete="new-password" maxlength="1200" placeholder="${state.secrets_present[name] ? 'Gespeichert – leer lassen, um ihn zu behalten' : 'Noch nicht gespeichert'}" ${state.vault_ready ? '' : 'disabled'}></label><button type="button" class="ghost" data-clear-credential="${name}" ${state.secrets_present[name] ? '' : 'disabled'}>Gespeicherten Zugang entfernen</button>`;
      const platform = (id, label, enabled, fields, guide, hint) => `<details class="setup-tool"><summary>${label}</summary><p>${hint}</p>${flag(enabled, 'API-Zugang für ' + label + ' aktivieren')}${fields}<p><a href="${guide}" target="_blank" rel="noopener noreferrer">Offizielle Einrichtung und Anmeldung ↗</a></p><label class="check"><input type="checkbox" data-publish-target="${id}" ${preferences.publish_targets.includes(id) ? 'checked' : ''}> Nach Freigabe auf ${label} veröffentlichen</label></details>`;
      section.innerHTML = `<h2>4 · Videos, Discord und Veröffentlichung</h2>
        <p>Erst ansehen, dann entscheiden. Die Freigabe gilt für die konkrete Videoversion und die darunter gewählten Ziele. Ein Anbieterzugang allein startet keinen Upload.</p>
        <h3>Endvideos und Arbeitsdateien getrennt speichern</h3><p>Endvideos: <code>${escape(state.final_directory)}</code>. Arbeitsdateien: <code>${escape(state.working_directory)}</code>.</p>
        ${text('archive_directory', 'Ordner für fertige Videos', 'Leer lassen: data/videos im Projekt. Neue Endvideos werden getrennt abgelegt. Bestehende Videos über „Endvideo im Videoordner sichern“ übernehmen; frühere externe Ablagen bleiben erhalten.')}
        <button type="button" id="choose-video-folder" class="ghost" ${state.native_picker ? '' : 'disabled'}>Ordner auswählen …</button>
        <label>Arbeitsdateien automatisch aufräumen<select data-integration="work_retention_days">${[0,30,90,180,365,...([0,30,90,180,365].includes(preferences.work_retention_days)?[]:[preferences.work_retention_days])].map(days=>`<option value="${days}" ${preferences.work_retention_days===days?'selected':''}>${days===0?'Automatik aus':days+' Tage nach letzter Bearbeitung'}</option>`).join('')}</select></label><p>Die Bereinigung läuft nur bei geöffneter Anwendung und löscht abgelaufene Ton-/Bild-Arbeitsdateien. Endvideos, Skripte und Qualitätsnachweise bleiben. Laufende/vorgemerkte Aufträge und „Projekt behalten“ sind geschützt. Ohne erreichbares geprüftes Endvideo wird nichts bereinigt. Nach der Bereinigung müssen Zwischenmaterialien für spätere Änderungen neu erzeugt werden.</p>
        <h3>Abnahme auf deinem Discord-Server</h3><p>Fertige Videos gehen an den gewählten Kanal. Nur eingetragene Discord-Nutzer dürfen freigeben, Änderungswünsche senden oder ablehnen. Die Verbindung geht ausschließlich nach außen; dein Rechner braucht dafür keinen öffentlichen Port.</p>
        ${flag('discord_enabled', 'Neue fertige Videos an Discord zur Prüfung senden')}
        ${secret('discord_bot_token', 'Discord Bot-Token')}
        ${text('discord_guild_id', 'Discord Server-ID')}${text('discord_channel_id', 'Discord Kanal-ID')}
        <label>Erlaubte Freigeber · Discord Nutzer-IDs, mit Komma getrennt<input id="discord-approvers" value="${escape(preferences.discord_approver_ids.join(', '))}" autocomplete="off"></label>
        <details><summary>Wo bekomme ich diese Angaben?</summary><p>Im Discord Developer Portal eine eigene Anwendung und einen Bot anlegen. Den Bot nur mit Kanal ansehen, Nachrichten senden, Dateien anhängen und Verlauf lesen einladen. In Discord den Entwicklermodus aktivieren; danach Server, Kanal und deinen Nutzer rechts anklicken und die jeweilige ID kopieren. Kein Discord-Passwort oder persönlicher Nutzertoken.</p><a href="https://discord.com/developers/applications" target="_blank" rel="noopener noreferrer">Discord Bot einrichten ↗</a></details>
        <label>Dateigrenze deines Discord-Servers in MB<input type="number" min="1" max="500" data-integration="discord_upload_mb" value="${preferences.discord_upload_mb}"></label><p>Standard: 10 MB. Nur entsprechend der tatsächlichen Servergrenze erhöhen. Zu große Dateien werden nicht ungeprüft übertragen.</p>
        <button type="button" id="discord-check" class="ghost">Bot prüfen und Einladungslink anzeigen</button><p id="discord-check-result" role="status"></p><h3>Wohin soll eine Freigabe veröffentlichen?</h3><p>Jeden gewünschten Kanal ausdrücklich auswählen. Fehlende App-Rechte oder Anbieterprüfungen werden als Einrichtungsbedarf angezeigt. Ein Pro-Abo oder Einnahmen werden nicht zugesichert.</p>
        ${platform('youtube', 'YouTube / Shorts', 'youtube_enabled', text('youtube_client_id', 'Google OAuth Client-ID') + secret('youtube_client_secret', 'Google OAuth Client-Secret') + '<button type="button" id="youtube-connect" class="ghost">Mit YouTube verbinden …</button><button type="button" class="ghost" data-clear-credential="youtube_refresh_token">YouTube-Anmeldung entfernen</button><p id="youtube-connect-status" role="status"></p><label>Sichtbarkeit<select data-integration="youtube_privacy">' + ['private','unlisted','public'].map(value => `<option value="${value}" ${preferences.youtube_privacy === value ? 'selected' : ''}>${({private:'Privat',unlisted:'Nicht gelistet',public:'Öffentlich'})[value]}</option>`).join('') + '</select></label>', 'https://console.cloud.google.com/apis/credentials', 'Eine eigene Google-Entwickleranwendung mit YouTube Data API und OAuth-Desktopzugang ist nötig. Erst speichern, dann verbinden. Ungeprüfte Upload-Anwendungen können auf private Videos beschränkt sein.')}
        ${platform('facebook_reels', 'Facebook Reels', 'facebook_enabled', text('facebook_page_id', 'Facebook Seiten-ID') + secret('facebook_token', 'Seiten-Zugriffstoken'), 'https://developers.facebook.com/apps/', 'Veröffentlichung auf einer eigenen Facebook-Seite über die Reels-API. Eine Meta-Entwickleranwendung und passende Seitenberechtigungen sind nötig.')}
        ${platform('instagram_reels', 'Instagram Reels', 'instagram_enabled', text('instagram_account_id', 'Instagram Professional Konto-ID') + '<label>Zugangstyp<select data-integration="instagram_login"><option value="instagram" ' + (preferences.instagram_login === 'instagram' ? 'selected' : '') + '>Instagram Login · professionelles Konto</option><option value="facebook" ' + (preferences.instagram_login === 'facebook' ? 'selected' : '') + '>Facebook Login · verknüpftes Konto</option></select></label>' + secret('instagram_token', 'Instagram Zugriffstoken'), 'https://developers.facebook.com/docs/instagram-platform/', 'Ein unterstütztes professionelles Instagram-Konto, Entwickleranwendung und Veröffentlichungsrechte sind nötig. Lokale Videos werden hochgeladen; dein Rechner wird kein öffentlicher Videoserver.')}
        ${platform('tiktok', 'TikTok · Entwurf zur App', 'tiktok_enabled', text('tiktok_client_id', 'TikTok Client Key') + secret('tiktok_client_secret', 'TikTok Client Secret') + secret('tiktok_access_token', 'TikTok OAuth Zugriffstoken') + secret('tiktok_refresh_token', 'TikTok Refresh-Token'), 'https://developers.tiktok.com/', 'Die offizielle Upload-API benötigt eine Entwickleranwendung und OAuth-Zugang mit video.upload-Recht. Nach Freigabe geht das Video als Entwurf in deine TikTok-Benachrichtigungen. Dort Beschriftung, Sichtbarkeit und endgültige Veröffentlichung selbst bestätigen. Für diese private Pipeline wird kein Direct-Post-Zugang behauptet; Login-Skripte umgehen keine Anbieterprüfung.')}
        <p class="notice">${escape(state.vault_message)} Schlüssel werden nie wieder im Formular angezeigt. Ein leeres Schlüsselfeld behält den vorhandenen Zugang.</p>
        <button type="button" id="integration-save" class="secondary">Videoordner und Kanäle speichern</button>
        <p id="integration-message" role="status" aria-live="polite"></p>`;
      const message = section.querySelector('#integration-message');
      section.querySelector('#choose-video-folder').onclick = async event => {
        event.target.disabled = true;
        try {
          const result = await api('/folder', 'POST');
          if (result.directory) section.querySelector('[data-integration="archive_directory"]').value = result.directory;
        } catch (error) { message.textContent = error.message; }
        finally { event.target.disabled = false; }
      };
      section.querySelector('#integration-save').onclick = async event => {
        event.target.disabled = true;
        const updated = {...preferences}, secrets = {};
        section.querySelectorAll('[data-integration]').forEach(input => {
          updated[input.dataset.integration] = input.type === 'checkbox' ? input.checked : input.type === 'number' || input.dataset.integration === 'work_retention_days' ? Number(input.value) : input.value.trim();
        });
        updated.discord_approver_ids = section.querySelector('#discord-approvers').value.split(/[\s,;]+/).filter(Boolean);
        updated.publish_targets = [...section.querySelectorAll('[data-publish-target]:checked')].map(input => input.dataset.publishTarget);
        section.querySelectorAll('[data-credential]').forEach(input => {if (input.value.trim()) secrets[input.dataset.credential] = input.value.trim();});
        try {
          const result = await api('', 'PUT', {preferences:updated, secrets});
          Object.assign(preferences, result.preferences);
          section.querySelectorAll('[data-credential]').forEach(input => {input.value = ''; input.placeholder = result.secrets_present[input.dataset.credential] ? 'Gespeichert – leer lassen, um ihn zu behalten' : 'Noch nicht gespeichert';});
          message.textContent = 'Gespeichert. Automatik: '+(result.preferences.work_retention_days?'Arbeitsdateien nach '+result.preferences.work_retention_days+' Tagen bereinigen.':'aus · nur manuell aufräumen.')+' Es wurde nichts veröffentlicht.';
        } catch (error) { message.textContent = error.message; }
        finally { event.target.disabled = false; }
      };
      section.querySelectorAll('[data-clear-credential]').forEach(button => {button.onclick = async () => {
        button.disabled = true;
        try {
          const result = await api('', 'PUT', {preferences, clear_secrets:[button.dataset.clearCredential]});
          Object.assign(preferences, result.preferences);
          const input = section.querySelector('[data-credential="' + button.dataset.clearCredential + '"]');
          if (input) {input.value = '';input.placeholder = 'Noch nicht gespeichert';}
          message.textContent = 'Gespeicherter Zugang entfernt. Beim Anbieter kannst du die App-Berechtigung zusätzlich widerrufen.';
        } catch (error) {message.textContent = error.message;button.disabled = false;}
      };});
      section.querySelector('#discord-check').onclick = async event => {
        event.target.disabled = true;
        const host = section.querySelector('#discord-check-result');
        host.textContent = 'Gespeicherten Bot und Kanal prüfen …';
        try {
          const result = await api('/discord-check','POST');
          host.textContent = result.bot_name + (result.channel_ready ? ' · Zugriff auf den gewählten Server/Kanal bestätigt. ' : ' · Bot noch einladen oder Kanalrechte prüfen. ');
          const link = document.createElement('a');
          link.href = result.invite_url;link.target = '_blank';link.rel = 'noopener noreferrer';link.textContent = 'Eigenen Bot einladen ↗';host.append(link);
        } catch (error) {host.textContent = error.message;}
        finally {event.target.disabled = false;}
      };
      section.querySelector('#youtube-connect').onclick = async () => {
        const host = section.querySelector('#youtube-connect-status');
        host.textContent = 'Reguläre Google-Anmeldung wird vorbereitet …';
        try {
          let result = await api('/youtube-connect', 'POST');
          host.textContent = result.message;
          while (result.status === 'running' && document.getElementById('settings-dialog')?.open) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            result = await api('/youtube-connect');
            host.textContent = result.message;
          }
          if(result.status === 'connected')Object.assign(preferences,(await api()).preferences);
        }
        catch (error) { host.textContent = error.message; }
      };
      document.getElementById('settings-dialog')?.addEventListener('close', () => {
        section.querySelectorAll('[data-credential]').forEach(input => {input.value = '';});
      }, {once:true});
    } catch (error) { section.textContent = error.message; }
  },
};
