# Spezifikation: Gemini- und NotebookLM-Integration

Stand: 2026-09-17

## Ziel

Die Pipeline soll Inhalte aus Gemini und NotebookLM übernehmen können, ohne den bestehenden versions- und hashgebundenen Freigabeprozess zu umgehen. Das vorhandene Google-AI-Pro-Abo wird über die offiziell unterstützten Gemini-/NotebookLM-Oberflächen genutzt; separat abgerechnete APIs bleiben ausdrücklich optional.

## Verbindliche Annahmen

- Google AI Pro und Gemini API sind getrennte Produkte. Ein Pro-Abo wird nicht als API-Guthaben behandelt.
- Der Consumer-Login von Gemini CLI ist seit Juni 2026 für Google-AI-Pro-/Consumer-Konten nicht mehr verfügbar und wird daher nicht als Integrationsweg eingeplant.
- Consumer-NotebookLM wird nicht automatisiert oder ausgelesen. Audio- und Video-Überblicke werden in der offiziellen Oberfläche erzeugt, dort heruntergeladen und anschließend lokal importiert.
- Jeder externe Inhalt bleibt bis zur zweiten, dateigebundenen Nutzerfreigabe unveröffentlicht.
- Bezahlte Gemini-Medien-APIs bleiben standardmäßig deaktiviert und benötigen später eine separate Kosten- und Datenschutzfreigabe.

## Nutzerablauf

1. Die Pipeline erzeugt oder verwaltet einen Szenenplan.
2. Der Nutzer gibt die aktuelle Skriptversion frei.
3. Der Nutzer erzeugt optional in Gemini oder NotebookLM ein Video, Audio, einen Podcast oder Bilder und lädt die Datei dort herunter.
4. Die Datei wird in den zugehörigen Auftrag importiert. Die Pipeline prüft Format, Streams, Laufzeit und Dateigröße und speichert Herkunft und SHA-256.
5. Das Ergebnis erscheint in der bestehenden Videoprüfung. Veröffentlichung oder Downloadfreigabe erfolgt erst für exakt diese Datei.

## Funktionsumfang

### Phase 1 – externer Videoimport (jetzt)

- MP4-Import aus `Gemini App` oder `NotebookLM` in einen vorhandenen Auftrag.
- Import nur für die aktuell freigegebene Skriptversion und den aktuellen Skripthash.
- Begrenzter, gestreamter Upload; temporäre Datei wird bei Fehlern entfernt.
- Prüfung mit ffprobe: vorhandener Video- und Audiostream, positive Laufzeit und Mindestgröße.
- Unveränderliches Herkunftsmanifest mit Originalname, Quelle, Dateigröße, Laufzeit, Streams, Zeitpunkt und SHA-256.
- Übergang in `video_review`; vorhandene dateigebundene Freigabe und Veröffentlichung werden wiederverwendet.

### Phase 2 – NotebookLM-Audio/Podcast

- Import von WAV/MP3/M4A und technische Prüfung.
- Optionales Transkript und Untertitel.
- Podcast-Renderer mit Wellenform, Cover/Bildern und Sprecherkennzeichnung; Ausgabe wiederum als prüfbares MP4.

### Phase 3 – Bilder und Szenenmedien

- Bild-/Videodateien einzelnen stabilen Szenen-IDs zuordnen.
- Herkunft und Hash pro Asset im Assetmanifest.
- Teil-Neurendering nur für betroffene Szenen.

### Phase 4 – optionale Gemini APIs

- Gemini Interactions für Text/Skript bleibt der bestehende API-Pfad.
- Nano Banana für Bilder, Gemini Omni/Veo für Video und Gemini TTS für Sprache nur mit separatem API-Projekt.
- Kostenschalter, Modellanzeige, geschätzte/angefallene Kosten und explizite Bestätigung vor jedem kostenpflichtigen Auftrag.
- NotebookLM Enterprise Audio Overview API nur als eigener späterer Adapter, falls eine passende Enterprise-Lizenz vorhanden ist.

### Phase 5 – Veröffentlichung

- Bestehende zweite Freigabe bleibt zwingend.
- YouTube zuerst; weitere Plattformen nur als getrennte, widerrufbare Adapter.
- Kein automatisches Posten direkt aus Gemini oder NotebookLM.

## Akzeptanzkriterien Phase 1

- Ein nicht freigegebenes oder zwischenzeitlich geändertes Skript kann keinen Import übernehmen.
- Eine zu große, unvollständige oder technisch ungültige Datei wird verworfen und nicht als fertiges Video angezeigt.
- Ein gültiges MP4 mit Audio und Video wird hashgebunden als `video_review` angezeigt.
- Herkunftsmanifest und Ereignisprotokoll nennen die gewählte Quelle.
- Eine spätere Skriptänderung entwertet auch den importierten Inhalt und alle Freigaben.
- Bestehende lokale Render-, Freigabe- und Veröffentlichungstests bleiben grün.

## Offizielle Grundlagen

- Google AI Pro in Gemini Apps: https://support.google.com/gemini/answer/16275805
- Getrennte Gemini-API-Abrechnung: https://ai.google.dev/gemini-api/docs/billing
- Gemini-CLI-/Code-Assist-Änderung für Consumer-Konten: https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals
- NotebookLM-Audioexport: https://support.google.com/gemininotebook/answer/16212820
- NotebookLM-Videoexport: https://support.google.com/gemininotebook/answer/16454555
- NotebookLM Enterprise Audio Overview API: https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-audio-overview
- Gemini Bild-, Video- und TTS-APIs: https://ai.google.dev/gemini-api/docs/image-generation, https://ai.google.dev/gemini-api/docs/video, https://ai.google.dev/gemini-api/docs/speech-generation
