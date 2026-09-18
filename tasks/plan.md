# Aktiver Implementierungsplan: Qualitätsorientierte Produktionsverfahren

Stand: 2026-09-18

1. [x] Unterbrochenen Sperr- und Idempotenz-Fix abschließen und vollständig prüfen.
2. [x] Antigravity-Automatisierung praktisch nachweisen und MoneyPrinterTurbo quellenbasiert bewerten.
3. [x] Modulare Architekturentscheidung vom Nutzer freigeben lassen (Option A).
4. [x] Provider-Verträge und Produktionsprofil-Dropdown implementieren; Skript, Medien, Stimme und Schnitt getrennt ausweisen. Die Konfiguration wird auf Auftrag und Skriptversion gespeichert; Änderungen erzeugen eine neue Version und entwerten vorhandene Freigaben. Nicht verfügbare Profile und Provider bleiben sichtbar, aber deaktiviert und begründet.
5. [ ] Antigravity als bevorzugten schemavalidierten Cloud-Skriptpfad integrieren; Qwen nur als letzten Fallback erhalten.
6. [ ] MoneyPrinterTurbo isoliert als optionalen Produktionsadapter pilotieren und mit dem vorhandenen Pfad anhand desselben Auftrags vergleichen.
7. [ ] Gesamtablauf mit beiden Freigabegates prüfen, dokumentieren, committen und pushen.
8. [ ] Quellenbasierte Recherche und unabhängige Faktenprüfung mit belegbarer Quellenprovenienz integrieren.
9. [ ] Freigegebene Bild- und Videogeneratoren als szenenweise Adapter mit Kosten-, Datenschutz- und Rechtekontrollen integrieren.
10. [ ] Hochwertige Rendererprofile für Erklärvideo, Social Clip, Podcast/Wellenform, Motion Graphics und bei nachgewiesenem Bedarf 3D/Manim ergänzen.
11. [ ] Stimmenqualität um Aussprachewörterbuch, Emotion, Mehrsprecherbetrieb und einen nachvollziehbaren Anbieterbenchmark erweitern.
12. [ ] Semantische Qualitätsprüfung für Skript-Bild-Passung, Artefakte, Text, Gesichter, Kontinuität und fehlerhafte Frames samt gezielter Nachproduktion ergänzen.
13. [ ] Plattformgerechte Ausgabevarianten und weitere offizielle Veröffentlichungsadapter vollständig implementieren.
14. [ ] Eigenständige Podcast-, Audio- und Song-Pipelines einschließlich RSS- beziehungsweise Distributor-Paketen ergänzen; Sprach-TTS nicht als Musikgenerator ausgeben.
15. [ ] Repräsentativen Qualitätsbenchmark über Themen und Produktionsverfahren sowie Lizenz-, Urheberrechts-, Moderations- und Kostenkontrollen abschließen.

Architekturentscheidung: Option A ist freigegeben. Die bestehende FastAPI-/SQLite-Anwendung bleibt Orchestrator sowie Freigabe- und Provenienzinstanz. Produktionsprofile kombinieren vier getrennte Provider-Slots. Antigravity soll nur headless, schemavalidiert, sandboxed und in einem leeren Arbeitsverzeichnis laufen. MoneyPrinterTurbo wird nicht übernommen, sondern hinter einem Adapter gegen den vorhandenen Produktionspfad getestet.

Prüfung Schritt 4: 79/79 Python-Tests, Python-Compileall, `node --check web/app.js` und `git diff --check` bestanden. Ein isolierter Browser-Smoke-Test bestätigte die Profil- und Providerauswahl, deaktivierte Optionen mit Gründen, responsive Darstellung und eine fehlerfreie Browserkonsole. Fortsetzungspunkt ist Schritt 5; Beginn erst nach erneuter Nutzerfreigabe.

---

# Bisheriger Implementierungsplan Gemini/NotebookLM

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
