# Entwicklungsstatus – Video Pipeline V2

Letzte Aktualisierung: 2026-09-15

## Ziel

Aus einem Thema entsteht zuerst ein inhaltlich belastbares, zum gewählten Stil passendes Skript mit konkretem Szenenplan. Nach versionsgebundener Freigabe erzeugt die Pipeline reale visuelle Assets beziehungsweise bewegte Szenen, natürliche Sprache, Schnitt und Untertitel. Einzelne Szenen sollen später gezielt überarbeitet werden können. Handyzugang und Plattformveröffentlichung bleiben bis zu einer ausdrücklichen Entscheidung beziehungsweise separaten Freigabe deaktiviert.

## Bestandsaufnahme V1

### Brauchbar und zu erhalten

- FastAPI, SQLite und der lokale Web-Workflow sind klein und nachvollziehbar.
- Skript-, Render- und Veröffentlichungsfreigaben sind bereits an Versionsnummern gebunden; Skriptänderungen entwerten alte Freigaben.
- Der Render-Worker serialisiert Aufträge und stellt unterbrochene Renderjobs wieder her.
- Remotion/FFmpeg, Piper und lokale Artefaktordner liefern einen funktionierenden technischen Grundpfad.
- Container-Härtung: localhost-Bindung, read-only Container, Capability-Drop und `no-new-privileges`.
- Veröffentlichungen sind standardmäßig deaktiviert; abgebrochene Uploads werden nicht blind wiederholt.

### Wesentliche Lücken

- `SCRIPT_PROVIDER=template` ist der Standard. Dadurch entsteht unabhängig vom Thema fast derselbe allgemeine Text.
- Der Szenenvertrag besteht im Kern aus `narration`, einer eingeblendeten `visual`-Beschreibung und Strichmännchen-Aktionen.
- Alle Videoarten laufen durch dieselbe Strichmännchen-Komposition. Es gibt keine Asset-Erzeugung oder Auswahl passender Bilder/Videos.
- Bildanweisungen werden als Textkarte angezeigt statt umgesetzt.
- Die Piper-Ersatzspur darf stumm sein und wird trotzdem als fertig gerendertes Video behandelt.
- Es fehlen Untertitel, szenenweise Artefakte, Qualitätsprüfungen und Teil-Neurendering.
- Änderungen sind nur als manuelle Feldbearbeitung möglich; ein KI-gestützter Änderungswunsch fehlt.
- Für den späteren Handyzugang fehlen Identität, Rollen und ein sicherer privater Transportweg.

## Umsetzungsplan

### 1. Echte KI-Skripterstellung und Änderungswünsche

Ergebnis: Ohne konfigurierten leistungsfähigen Anbieter wird kein generisches Vorlagenskript erzeugt. Ein strukturierter Prompt liefert themenspezifischen Sprechertext und einen produktionsfähigen Szenenplan; Änderungswünsche erzeugen eine neue Version und entwerten alte Freigaben. Anbieter und Modell werden ohne Schlüssel in Status/Provenienz ausgewiesen.

Prüfung: Unit-Tests für Anbieterwahl, strukturiertes Ergebnis, Stilverzweigung, Revision und Fehler bei fehlender Konfiguration; bestehende Workflow-Tests bleiben grün.

Status: **erledigt (Implementierung und kostenfreie Mock-/Workflowtests); Live-Modelltest wartet auf bewusst bereitgestellten Zugang**

### 2. Versionsgebundener Produktionsplan

Ergebnis: Jede Szene besitzt stabile ID, Dauer, visuellen Medientyp, Prompt/Quelle, Kamera/Bewegung, Einblendungen und Übergang. Die Freigabe bindet einen kanonischen Hash von Skript und Plan; nachträgliche Änderungen sind erkennbar.

Prüfung: Datenbankmigration sowie Konflikt-, Hash- und Freigabetests; UI zeigt den Plan verständlich und vollständig.

Status: offen

### 3. Reale visuelle Produktion pro Stil

Ergebnis: `stickman` bleibt eine bewusste Option. Erklärvideo, Social Clip und Podcast nutzen jeweils passende echte Layouts/Assets; `generated` nutzt einen separaten Bild-/Video-Adapter. Eine visuelle Anweisung erscheint nie als Ersatzbild im Film.

Prüfung: Für jede angebotene Videoart ein kurzer Render-Smoke-Test und eine Asset-Manifestauswertung; nicht verfügbare Adapter werden in der UI deaktiviert statt vorgetäuscht.

Status: offen

### 4. Stimme, Schnitt, Untertitel und Qualitäts-Gate

Ergebnis: Natürliche Stimme, szenengenaue Timings, Schnitt/Übergänge und eingebrannte oder zuschaltbare Untertitel. Fehlende/defekte Stimme, fehlende Assets, leere Frames oder starke Laufzeitabweichung führen zu `quality_failed`, nicht zu Erfolg.

Prüfung: `ffprobe`-Checks für Audio/Video/Dauer, Untertitelprüfung, Asset-Vollständigkeit und stichprobenartige Frame-Prüfung gegen Skript/Plan.

Status: offen

### 5. Gezielte Überarbeitung

Ergebnis: Sprechertext, Voiceover, Asset oder Schnitt einer einzelnen Szene können neu erzeugt werden; unveränderte Artefakte werden wiederverwendet. Jede Ausgabe erhält eine neue, nachvollziehbare Renderrevision.

Prüfung: Test zeigt, dass bei einer Szenenänderung nur deren Artefakte und der finale Zusammenschnitt neu entstehen.

Status: offen

### 6. Sicherer Handyzugang und kontrollierte Veröffentlichung

Ergebnis: Nach gemeinsamer Auswahl privater Zugang für ausdrücklich zugelassene Personen, Rollen für Anfrage/Freigabe/Download, TLS, Widerruf und Audit-Log. Keine öffentliche Erreichbarkeit und kein Plattformupload ohne separate Entscheidung/Freigabe.

Prüfung: Nicht zugelassener Zugriff scheitert; Freigabe und Download funktionieren mobil; Upload bleibt ohne eigene Freigabe technisch gesperrt.

Status: wartet bewusst auf gemeinsame Zugangsentscheidung

## Werkzeug- und Kostenentscheidung (Stand 2026-09-15)

- Für den ersten kostenlosen, leistungsfähigen Skriptpfad ist die Gemini Developer API mit einem aktuellen stabilen Flash-Modell technisch geeignet: strukturierte JSON-Ausgabe und ein begrenztes kostenloses Kontingent sind dokumentiert. Wichtig: Im Free Tier dürfen Inhalte laut Anbieter zur Produktverbesserung verwendet werden. Für sensible Inhalte ist daher ein bezahlter, datenschutzgeeigneter Tarif oder ein genügend gutes lokales Modell vorzuziehen.
- OpenAI-API-Modelle unterstützen strukturierte Ausgaben und bieten hohe Qualität, haben laut aktueller offizieller Modellübersicht aber kein kostenloses API-Kontingent. Ein ChatGPT/Codex-Abo deckt API-Kosten ausdrücklich nicht ab. Deshalb wird kein OpenAI-Aufruf ohne separat bereitgestellten API-Schlüssel und Kostenentscheidung aktiviert.
- OpenRouter bleibt als expliziter Adapter möglich, wird aber wegen wechselnder Gratis-Modelle nicht als Qualitätsstandard voreingestellt.
- Quellen: https://ai.google.dev/gemini-api/docs/models, https://ai.google.dev/gemini-api/docs/pricing, https://ai.google.dev/gemini-api/docs/structured-output, https://developers.openai.com/api/docs/models/compare, https://help.openai.com/en/articles/9039756-managing-your-work-in-the-api-platform-with-projects

## Bisherige Tests

- 2026-09-15: V1-Datenbank-Workflow: 3/3 Tests bestanden.
- 2026-09-15: Python-Bytecodeprüfung des Backends bestanden.
- 2026-09-15: Neuer Skriptplaner: 5/5 Tests für fehlende Konfiguration, Stilverzweigung, Revision, strukturiertes Gemini-Ergebnis/Provenienz und gesperrten Template-Fallback bestanden; zusammen 8/8 Python-Tests grün.
- 2026-09-15: Python-Compileall, JavaScript-Syntaxcheck, TypeScript-`tsc --noEmit` und `git diff --check` bestanden.
- 2026-09-15: Direkter Funktions-/API-Ablauf in isoliertem temporärem Datenverzeichnis bestanden: Auftrag, Revision auf Version 2, Freigabe und erwartete Sperre des noch nicht realen Erklärvideo-Renderers.
- 2026-09-15: Migration einer Kopie der bestehenden V1-Datenbank bestanden; 6 vorhandene Skriptversionen blieben erhalten und erhielten kompatible leere Metadaten.
- 2026-09-15: Remotion-Smoke-Render eines vorhandenen kurzen Auftrags nach Entfernung der Bildanweisungs-Textkarte bestanden (`/tmp/video-pipeline-step1-smoke.mp4`, 468 Frames, 1,8 MB). Der erste Versuch scheiterte erwartbar an der Socket-Sandbox; der freigegebene lokale Testlauf war erfolgreich.

## Offene Probleme/Risiken

- Noch kein KI-Schlüssel im Projekt konfiguriert; Live-Qualität kann daher erst nach einer bewussten Anbieter-/Datenschutzentscheidung geprüft werden. Tests verwenden keine externen Kosten.
- V1-Nutzdaten und bereits gerenderte Videos werden erhalten und nicht migriert oder gelöscht.
- Die tatsächliche Medienstrategie pro Stil und mögliche generative Videokosten werden vor Aktivierung kostenpflichtiger Adapter konkret verglichen.

## Erledigter Zwischenstand

- Standard ist jetzt `SCRIPT_PROVIDER=auto`; ohne bewusst konfigurierten Schlüssel entsteht kein Schein-Skript.
- Aktuelle strukturierte Gemini-`interactions`-Integration, OpenAI-kompatibler Adapter und expliziter OpenRouter-Adapter sind vorhanden.
- Visuelle Regie ist je Stil getrennt und umfasst realen Medientyp, sichtbare Einstellung, Asset-Prompt, Kamera, bewusste Texteinblendung und Übergang.
- KI-Änderungswünsche erzeugen eine neue Version; Modell/Anbieter und Hinweise zur Faktenprüfung werden gespeichert und angezeigt.
- Nicht implementierte Videoarten werden vorläufig gesperrt statt als Strichmännchenvideo ausgegeben. Bildanweisungen werden nicht mehr als sichtbare Textkarte gerendert.

## Nächster konkreter Arbeitsschritt

Etappe 2 beginnen: stabile Szenen-IDs und geplante Dauern ergänzen, kanonischen Skript-/Plan-Hash in der Datenbank speichern und Freigaben an genau diesen Hash binden; anschließend Konflikt-, Hash-, Migrations- und UI-Tests ausführen.
