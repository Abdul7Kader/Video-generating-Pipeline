# Spezifikation: Multi-Channel-Produktion und Veröffentlichung

Stand: 2026-09-17

## Ziel

Ein einmal freigegebener Inhalt kann für mehrere ausgewählte Ziele vorbereitet und – nur bei vollständig eingerichteten offiziellen Adaptern – aus einem einzigen Freigabevorgang veröffentlicht werden. Jede Zielplattform besitzt einen eigenen Status, eine unveränderliche Idempotenzbindung und ein sichtbares Qualitätsprofil.

## Sicherheits- und Produktgrenzen

- Die zweite Freigabe bindet weiterhin exakt die geprüfte Ausgabedatei und startet erst danach externe Übertragungen.
- Geheimnisse liegen nur in `.env` oder OAuth-Dateien, nie in Datenbank, API-Antwort, Ereignistext oder Git.
- Jeder Zieladapter wird einzeln beansprucht. Ein Fehler wird nicht automatisch wiederholt, weil ein Timeout nach einem externen Upload einen unbekannten Ausgang haben kann.
- Unterbrochene Übertragungen erhalten `unknown`, nicht fälschlich `failed` oder `published`.
- Ein Ziel ohne eingerichteten offiziellen Adapter oder ohne bereits erzeugtes Zielartefakt wird als `setup_required` angezeigt und niemals als veröffentlicht beziehungsweise exportbereit ausgegeben.
- Plattformen, deren API eine App-Prüfung oder zusätzliche Nutzerzustimmung verlangt, werden erst nach dieser Einrichtung automatisch aktiviert.

## Plattformkatalog

### Video und soziale Netzwerke

- YouTube/YouTube Shorts: vorhandener automatischer OAuth-Adapter.
- Mastodon: neuer automatischer Adapter über Medien- und Status-API, nur mit fester HTTPS-Instanz und Zugriffstoken.
- TikTok, Instagram Reels, Facebook Reels, LinkedIn, X und Bluesky: Ziel- und Qualitätsprofile; automatische Adapter folgen nach OAuth-/App-Einrichtung. Bis dahin klare Einrichtungs- oder Exportanzeige.

### Podcasts

- Spotify Podcasts, Apple Podcasts, Amazon Music Podcasts und weitere Verzeichnisse werden über einen öffentlich gehosteten, validen RSS-Feed beliefert.
- Die Pipeline erzeugt zunächst RSS-/Audio-Exportartefakte. Ein Hostingziel muss separat eingerichtet werden; localhost ist kein öffentlicher Podcastfeed.

### Audio und Musik

- SoundCloud erhält einen geplanten direkten Adapter.
- Spotify Music und Apple Music nehmen unabhängige Musikveröffentlichungen über Labels beziehungsweise Distributoren entgegen. Die Pipeline erzeugt dafür später Releasepakete (Master, Cover, Credits, Metadaten), behauptet aber keinen direkten Plattformupload.
- Eine echte Songerzeugung ist ein eigener Produktionsadapter und wird nicht durch Sprach-TTS vorgetäuscht.

## Phasen

1. **Jetzt:** additive Mehrfachziel-Auswahl, Plattformkatalog, eigener Zielstatus, atomare Beanspruchung, idempotente Veröffentlichungsabsicht und bestehender YouTube-Adapter im neuen Dispatcher.
2. **Jetzt:** automatischer Mastodon-Adapter, sofern Instanz und Token konfiguriert sind.
3. Qualitätsprofile und Ausgabevarianten: 9:16, 16:9, 1:1, H.264/AAC sowie Podcast-MP3 mit Loudness-Prüfung. Jede Variante erhält Hash und eigene Vorschau/Freigabebindung.
4. RSS-Feed und Podcast-Hostingadapter; anschließende Verteilung an Spotify/Apple/Amazon und Podcastverzeichnisse.
5. TikTok/Meta/LinkedIn/X/Bluesky/SoundCloud nach offizieller App-/OAuth-Einrichtung.
6. Musik-Releasepakete und optionaler Distributoradapter; separater Songproduktionsadapter.

## API-Vertrag Phase 1

- `GET /api/publication-platforms` liefert Plattform-ID, Kategorie, Liefermodus, Konfigurationsstatus und empfohlenes Format – niemals Geheimnisse.
- `POST /api/jobs` akzeptiert additiv `target_platforms`; `target_platform` bleibt für ältere Clients erhalten.
- `GET /api/jobs/{id}` enthält `publication_targets` mit je eigenem Status, Fehler und öffentlicher Remote-URL.
- `POST /api/jobs/{id}/approve-video` legt für jedes Ziel genau eine Veröffentlichungsabsicht für Job, Renderhash und Plattform an.

## Akzeptanzkriterien Phase 1/2

- Ein Auftrag kann mehrere unterschiedliche Ziele enthalten; Duplikate werden entfernt und unbekannte IDs an der API-Grenze abgelehnt.
- Ein einziger Freigabeklick reiht alle eingerichteten automatischen Ziele ein.
- Zielaufträge werden atomar und höchstens einmal beansprucht.
- Erfolg oder Fehler eines Ziels überschreibt nicht den Status der anderen Ziele.
- Neustart nach einer laufenden externen Übertragung führt zu `unknown` und keiner automatischen Wiederholung.
- Nicht konfigurierte Plattformen werden nicht kontaktiert.
- Bestehende Ein-Ziel-Aufträge und Datenbanken bleiben kompatibel.

## Offizielle Grundlagen

- TikTok Content Posting API: https://developers.tiktok.com/docs/en/content-posting-api-get-started
- LinkedIn Videos/Posts APIs: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/videos-api und https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
- Mastodon Media/Status APIs: https://docs.joinmastodon.org/methods/media/ und https://docs.joinmastodon.org/methods/statuses/
- Bluesky Posting: https://docs.bsky.app/docs/tutorials/creating-a-post
- Spotify Podcast RSS: https://support.spotify.com/creators/article/your-rss-feed/
- Apple Podcasts RSS: https://podcasters.apple.com/support/897-submit-a-show
- Apple Music Distribution: https://artists.apple.com/support/1108-get-your-next-release-on-apple-music
