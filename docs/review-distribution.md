# Videoabbruch, Discord-Abnahme und Verteilung

Stand 16.10.2026: implementiert und mit lokalen Prozessfixtures sowie simulierten
Anbieterantworten geprüft. Echte Kontenabnahme nach Einrichtung noch offen.

1. Abbruch je Auftrag, schon während KI-Zeichenplanung, Stimme und Schnitt. Nur
   eigene Prozesse dieses Vorgangs enden. Skripte/fertige Videos bleiben erhalten;
   abgebrochene Teile werden nicht freigegeben oder veröffentlicht. Verspätete
   Ergebnisse dürfen einen Abbruch nicht überschreiben. Kein Film als Routinetest.
2. Einstellungen: Videoordner, Discord-Ziel und erlaubte Freigeber, Plattformkonten
   und API-Zugänge. Neue Geheimnisse im nativen Betriebssystem-Tresor, nie in
   API-Antworten/Logs/Git. Einstellungen nur über bestehenden lokalen Schutz.
3. Discord erhält die fertige Datei mit Video-/Versionsbindung und Knöpfen für
   Freigabe, Änderungswunsch und Ablehnung. Bot-Gateway ausschließlich ausgehend,
   keine öffentlichen Webhooks/Ports. Nur gewählte Server/Kanäle/Nutzer dürfen
   entscheiden. Alte/fremde/doppelte Freigaben dürfen nichts veröffentlichen.
4. Nach Freigabe genau die geprüften Dateien an ausgewählte eingerichtete Ziele
   übertragen. Vorhandene YouTube-/Mastodon-Dispatcher und Idempotenz weiterverwenden;
   Meta/TikTok über offizielle APIs und deren Rechte-/Consent-Voraussetzungen.
   Kein Ersetzen fehlender Anbieterfreigaben durch Login-/CAPTCHA-/Browsertricks.
5. Sichtbarer Zielstatus, Fehler/Fortsetzung ohne blinde Upload-Wiederholung.
   Ohne API-Zugang klares Exportpaket und reguläre Anbieter-Anmeldung. Keine
   Monetarisierungsgarantie; Freigaben und Einnahmeprogramme verwaltet der Anbieter.

Native Windows-Anwendung verwenden. Keine WSL-Chromium-Instanz, fremde Browser,
Portsuche oder Eingriffe in andere laufende Arbeiten. Bereits laufende Nutzer-
produktion erst bei nötigem Neustart berücksichtigen.

Abnahme: echte Prozess-Abbruchfixture ohne Modell/Video, Zustands-/Hash-/Rennfall-
Tests, negative Discord-Berechtigungsfälle, gemockte Hersteller-APIs, UI-Prüfung.
Live-Uploads/Anmeldungen erst nach Einrichtung der eigenen Zielkonten; kein
ungefragtes Veröffentlichen vorhandener Filme.

## So wird es benutzt

1. Unter **Einstellungen → Endvideos und Arbeitsdateien getrennt speichern** einen
   lokalen Endvideoordner wählen, sonst `data/videos/`. Arbeitsdateien liegen in
   `data/jobs/<Auftrag>/v<Version>/`. Den tatsächlichen Endvideoort zeigt jedes
   fertige Video. Bestehende Filme über „Endvideo im Videoordner sichern“ übernehmen.
   [Manuell aufräumen und später weiterbearbeiten](video-storage.md).
2. Discord-Bot im [Developer Portal](https://discord.com/developers/applications)
   anlegen. Bot-Token, Server-ID, Kanal-ID und ausdrücklich erlaubte Nutzer-IDs
   eintragen. IDs lassen sich im Discord-Entwicklermodus kopieren. Bot prüfen und
   über den angezeigten Link einladen. Er braucht Kanal ansehen, Nachrichten senden,
   Dateien anhängen und Nachrichtenverlauf lesen; keine Administratorrechte und
   keinen privilegierten Message-Content-Intent. Persönliche Nutzertokens werden
   nicht unterstützt. Dateigrenze passend zum tatsächlichen Server einstellen.
3. Gewünschte Plattformen einrichten und als Ziele **nach Freigabe** auswählen.
   Erst speichern, dann eine neue Abnahme senden. Änderungen von Konten, Zielen oder
   Sichtbarkeit machen alte Abnahmeknöpfe ungültig. Während eingereihter/laufender
   Veröffentlichungen bleiben Kontoeinstellungen gesperrt.
4. Neues Video wie bisher über Textfreigabe erzeugen. **Erstellung abbrechen**
   beendet nur dessen Planung/Sprach-/Renderprozesse; fertige Dateien bleiben.
   Das fertige Video wird bei aktiviertem Discord automatisch gesendet. Bereits
   vorhandene fertige Videos lassen sich ausdrücklich zur Discord-Abnahme senden.
5. In Discord anschauen und **Freigeben**, **Ändern** oder **Ablehnen** wählen.
   Änderungen erzeugen zuerst einen überarbeiteten Text zur erneuten Freigabe,
   dann ein neues Video zur erneuten Videoabnahme. Ablehnung veröffentlicht nichts.
   Freigabe gilt nur für die gezeigte Version, Datei und Zielauswahl. Ohne gewählte
   Ziele bleibt das Video lokal. Die Anwendung muss für Bot und Uploads geöffnet sein.

| Ziel | Erforderlicher Zugang | Verhalten nach Freigabe |
|---|---|---|
| YouTube | Eigenes Google-Konto/Kanal; OAuth-Desktopclient mit Client-ID und Secret, YouTube Data API | Offizieller Upload; Sichtbarkeit in Einstellungen, Standard privat. Anmeldung über Google, kein Google-Passwort in der Pipeline. |
| Facebook Reels | Meta-Entwickleranwendung, Seiten-ID, Seitentoken mit erforderlichen Veröffentlichungsrechten | Offizieller Reels-Upload auf eine Facebook-Seite; bestätigter Plattformstatus wird gespeichert. |
| Instagram Reels | Professionelles Konto, Konto-ID, autorisierter Token; Instagram Login oder Facebook Login für verknüpftes Konto | Lokaler Datei-Upload und offizielle Veröffentlichung; kein öffentlich erreichbarer Videoserver nötig. |
| TikTok | Entwickleranwendung und OAuth-Token mit `video.upload`; optional Client Secret/Refresh-Token | Übergabe an TikTok-Inbox. Beschriftung, Sichtbarkeit und endgültiges Posten in TikTok bestätigen. Statusprüfung lädt nichts erneut hoch. |

Meta/TikTok-Zugänge werden als autorisierte Tokens eingetragen; ein eigener
vollständiger OAuth-Anmeldeassistent für diese Anbieter ist noch nicht vorhanden.
Bei YouTube gibt es einen Anmeldeknopf. API-Zulassung, Quoten, Kosten und
Monetarisierungsprogramme richten sich nach dem Anbieter/Konto; die Anwendung
aktiviert keinen Bezahltarif. TikTok Direct Post wird für dieses private Werkzeug
nicht zugesichert. Fehlende Freigaben werden nicht mit Browser-/Login-Skripten
umgangen. **Uploadpaket vorbereiten** legt verifizierte MP4s, Beschriftung und
Dateiprüfsummen für manuelle Übergabe ab; dabei wird nichts hochgeladen.

## Fehler, Speicherung und Sicherheit

- Der gezeigte Antigravity-Timeout trat bei der Bildplanung nach rund zehn Minuten
  auf, bevor dieser Versuch ein Video erzeugt hatte. Vorhandene ältere Filme und
  Skripte werden dadurch nicht gelöscht. Der ausdrücklich abgebrochene neue
  Feuer-Versuch ist gespeichert und startet nicht automatisch erneut.
- Neue Endvideos: gewählter Videoordner, sonst `data/videos/`. Noch nicht übernommene
  ältere Filme: `data/jobs/`. Arbeitsdateien werden standardmäßig nur manuell
  bereinigt. Uploadpakete:
  dessen Unterordner `Uploadpakete`, sonst `data/exports/Uploadpakete`.
- Neue API-Schlüssel/Refresh-Tokens: Windows-Anmeldeinformationsverwaltung,
  macOS-Schlüsselbund oder Linux Secret Service, ohne Klartextfallback. Nichtgeheime
  Optionen stehen in `data/integrations.json`. Der Tresor ist an Betriebssystemnutzer
  und Projektpfad gebunden; nach Projektumzug gegebenenfalls neu verbinden.
- Der Videoordner ist kein verschlüsseltes Backup. Für vertrauliche Videos einen
  durch das Betriebssystem verschlüsselten Datenträger wählen. Bewusste Übertragung
  an Discord/Plattformen unterliegt deren Speicherung und Zugriffsrechten.
- Ausschließlich eigene native Windows-Browser für den Windows-Renderer; keine
  WSL-Browser, fremden Browserinstanzen oder Debug-Endpunkte. Backend nur Loopback;
  Discord über ausgehendes HTTPS/WSS, keine öffentlichen Callbackports. Nur die
  offizielle Google-Anmeldung nutzt vorübergehend einen zusätzlichen Loopbackport.
- Fremde/alte/doppelte Discord-Aktionen werden serverseitig abgewiesen. Änderungen
  der Datei stoppen die Freigabe. Unsichere Upload-URLs werden abgewiesen.
  Unterbrochene, möglicherweise schon erfolgte Uploads heißen **Status unbekannt**
  und werden nicht blind wiederholt. Vor erneutem Senden den Plattformstatus prüfen.

## Nachweise und offene Abnahme

311 Backend-Tests (10 vorgesehene Skips) und 60 JS-Tests bestanden. Negative
Discord-Berechtigungen, Versions-/Dateibindung, genau einmal beanspruchte Aktionen,
nativer Abbruch mit Unterprozess, Betriebssystem-Tresor, Ordnerwahl und simulierte
offizielle Uploads geprüft. TikTok-Inbox bleibt bis zur API-Bestätigung ausdrücklich
unveröffentlicht; Statusabfrage erzeugt keinen neuen Upload. Kopien überschreiben
keine fremden Dateien; fehlgeschlagene Kopien entfernen ihre eigene Teildatei.
Keine neuen Testfilme. Ein beim Umbau unbeabsichtigt gestarteter KI-Prüfaufruf wurde
beendet und seine Mockgrenze korrigiert. Live-Discord, echte OAuth-Konten und reale
Veröffentlichungen stehen nach Einrichtung noch aus. Mac-/schwacher-PC-Abnahme
und signierte Installationspakete bleiben separat offen.

Eigene native Windows-Fensterprüfung: Einstellungen und private Ordnerauswahl,
Abnahmepanel mit Fixture, Sandbox, Zweitstart und Schließen bestanden. Nur
127.0.0.1:8080, keine eigenen UDP-Endpunkte und keine eigenen Prozessreste nach
Schließen. Die optionale Einstellungsdialog-Aufnahme war technisch nicht verfügbar;
die Funktionsprüfung und Aufnahme des Hauptfensters waren erfolgreich.

Offizielle Grundlagen: [Discord Gateway](https://docs.discord.com/developers/events/gateway),
[Discord Interaktionen](https://docs.discord.com/developers/interactions/receiving-and-responding),
[Meta Reels-Beispiel](https://github.com/fbsamples/reels_publishing_apis),
[Facebook Reels-Beispiel](https://github.com/fbsamples/Facebook-Reels-Publishing-API-Postman-Collection),
[TikTok Upload](https://developers.tiktok.com/doc/content-posting-api-reference-upload-video),
[TikTok Status](https://developers.tiktok.com/doc/content-posting-api-reference-get-video-status),
[TikTok Freigabegrenzen](https://developers.tiktok.com/doc/content-sharing-guidelines).
