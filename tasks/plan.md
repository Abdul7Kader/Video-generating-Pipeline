# Implementierungsplan Gemini/NotebookLM

Stand: 2026-09-17

1. Produktgrenzen dokumentieren: Consumer-Abo/Dateiübergabe, getrennte Gemini API, optionales NotebookLM Enterprise.
2. Tests für die erste vertikale Scheibe schreiben: Importprüfung, Größenlimit, Skriptbindung, Provenienz und Freigabeentwertung.
3. Backend für gestreamten MP4-Import, ffprobe-Prüfung und Herkunftsmanifest implementieren.
4. Datenbankworkflow ergänzen, sodass ein geprüfter Import an die aktuelle freigegebene Skriptversion gebunden in `video_review` landet.
5. Oberfläche um Quellenwahl und MP4-Dateiauswahl erweitern.
6. Unit-, Syntax- und Browser-Smoke-Tests ausführen; Ergebnisse in `STATUS.md` dokumentieren.
7. Danach Audio/Podcast, szenenweise Bilder/Videos und erst zuletzt kostenpflichtige API-Adapter in separaten, überprüfbaren Scheiben umsetzen.

## Multi-Channel-Erweiterung

1. Offizielle Plattformwege und Einschränkungen dokumentieren.
2. Additiven Plattformkatalog und `target_platforms`-API-Vertrag definieren.
3. Zielstatus je Plattform mit atomarer Beanspruchung und ohne blinde Wiederholung implementieren.
4. Vorhandenen YouTube-Upload auf den Multi-Target-Dispatcher umstellen.
5. Mastodon als zweiten echten automatischen Adapter implementieren.
6. Mehrfachauswahl und Einzelstatus in der Oberfläche darstellen.
7. Qualitätsprofile/Ausgabevarianten und Podcast-RSS in den nächsten vertikalen Scheiben ergänzen.

## Qualitätsgrenzen

- Kein automatisierter Consumer-Login und kein Scraping von Gemini/NotebookLM.
- Keine stillschweigende API-Abrechnung.
- Kein Import ohne aktuelle Skriptfreigabe.
- Kein Überspringen der zweiten Veröffentlichungsfreigabe.
- Kein vollständiges Einlesen großer Dateien in den Arbeitsspeicher.
