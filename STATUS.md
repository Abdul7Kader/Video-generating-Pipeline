# Entwicklungsstatus – Video Pipeline V2

Letzte Aktualisierung: 2026-09-15

## Aktiver Auftrag: vollständig lokale Skripterstellung

Handyzugang und Cloud-Anbieter sind zurückgestellt. Der lokale Ausbau erfolgt in vier überprüfbaren Etappen:

1. Ollama ausschließlich auf `127.0.0.1` installieren, Qwen3.5 9B Q4_K_M laden und Hardware-/Speicherreserve messen. Einen größeren Kandidaten nur testen, wenn Modell, KV-Cache, Anwendung und Renderreserve ohne dauerhaften Swap in 22 GiB RAM passen.
2. Zwei identische deutsche Skriptaufgaben plus eine Revision mit festem JSON-Schema benchmarken; Laufzeit, RAM, Formatzuverlässigkeit und redaktionelle/visuelle Qualität dokumentieren und den besten Entwurf sichern.
3. Den Gewinner ohne Cloud- oder Template-Fallback als begrenzten Ollama-Adapter integrieren: ein Modellaufruf gleichzeitig, begrenzter Kontext/Ausgabe, verständliche Fehler und Entladen vor dem Rendern.
4. Echten lokalen API-Ablauf Thema → Entwurf → Revision → Freigabe testen; vollständigen Videoauftrag erst nach Nutzerfreigabe mit vorhandenem Material rendern.

Aktueller Befund: Kein Ollama/llama.cpp vorhanden; 22 GiB RAM, rund 18 GiB aktuell verfügbar, 8 GiB unbenutzter Swap, 146 GiB freier Speicher und keine nutzbare GPU. Qwen3.5 9B Q4_K_M benötigt laut offizieller Ollama-Registry 6,6 GB und ist der Erstkandidat. Qwen3.5 27B Q4_K_M benötigt bereits 17 GB Modellgewicht; GLM-4.7-Flash Q4_K_M 19 GB. Beide lassen auf diesem Rechner keine belastbare Laufzeit- und Renderreserve und werden deshalb nicht vorsorglich heruntergeladen. Quellen: https://ollama.com/library/qwen3.5/tags, https://ollama.com/library/glm-4.7-flash

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

Status: **erledigt**

### 3. Reale visuelle Produktion pro Stil

Ergebnis: `stickman` bleibt eine bewusste Option. Erklärvideo, Social Clip und Podcast nutzen jeweils passende echte Layouts/Assets; `generated` nutzt einen separaten Bild-/Video-Adapter. Eine visuelle Anweisung erscheint nie als Ersatzbild im Film.

Prüfung: Für jede angebotene Videoart ein kurzer Render-Smoke-Test und eine Asset-Manifestauswertung; nicht verfügbare Adapter werden in der UI deaktiviert statt vorgetäuscht.

Status: **teilweise erledigt** – Strichmännchen und reale Pexels-Stockfotos/-videos sind implementiert; Live-Pexels-Test wartet auf kostenlosen Schlüssel. Generierte Bilder/Videos sowie verifizierte Motion-Graphics-/Podcast-Renderer bleiben gesperrt.

### 4. Stimme, Schnitt, Untertitel und Qualitäts-Gate

Ergebnis: Natürliche Stimme, szenengenaue Timings, Schnitt/Übergänge und eingebrannte oder zuschaltbare Untertitel. Fehlende/defekte Stimme, fehlende Assets, leere Frames oder starke Laufzeitabweichung führen zu `quality_failed`, nicht zu Erfolg.

Prüfung: `ffprobe`-Checks für Audio/Video/Dauer, Untertitelprüfung, Asset-Vollständigkeit und stichprobenartige Frame-Prüfung gegen Skript/Plan.

Status: **teilweise erledigt** – lokale Piper-Stimme, szenengenaue eingeblendete Untertitel/SRT und hartes technisches Qualitäts-Gate funktionieren. Optionales natürliches Gemini TTS ist implementiert, aber ohne bewusst freigegebenen Cloudzugang nicht live bewertet. Semantische Bild-gegen-Plan-Prüfung bleibt offen.

### 5. Gezielte Überarbeitung

Ergebnis: Sprechertext, Voiceover, Asset oder Schnitt einer einzelnen Szene können neu erzeugt werden; unveränderte Artefakte werden wiederverwendet. Jede Ausgabe erhält eine neue, nachvollziehbare Renderrevision.

Prüfung: Test zeigt, dass bei einer Szenenänderung nur deren Artefakte und der finale Zusammenschnitt neu entstehen.

Status: **erledigt** – einzelne Szenen können separat als neue Planversion gespeichert werden. Medien- und Sprachsegmente besitzen szenenweise Inhaltsfingerprints und Datei-Hashes; unveränderte, intakte Artefakte werden in die neue Renderrevision übernommen. Nur geänderte Segmente werden neu erzeugt, der finale Schnitt wird zur eindeutigen neuen Ausgabe erneut gebaut.

### 6. Sicherer Handyzugang und kontrollierte Veröffentlichung

Ergebnis: Nach gemeinsamer Auswahl privater Zugang für ausdrücklich zugelassene Personen, Rollen für Anfrage/Freigabe/Download, TLS, Widerruf und Audit-Log. Keine öffentliche Erreichbarkeit und kein Plattformupload ohne separate Entscheidung/Freigabe.

Prüfung: Nicht zugelassener Zugriff scheitert; Freigabe und Download funktionieren mobil; Upload bleibt ohne eigene Freigabe technisch gesperrt.

Status: wartet bewusst auf gemeinsame Zugangsentscheidung

## Werkzeug- und Kostenentscheidung (Stand 2026-09-15)

- Für den ersten kostenlosen, leistungsfähigen Skriptpfad ist die Gemini Developer API mit einem aktuellen stabilen Flash-Modell technisch geeignet: strukturierte JSON-Ausgabe und ein begrenztes kostenloses Kontingent sind dokumentiert. Wichtig: Im Free Tier dürfen Inhalte laut Anbieter zur Produktverbesserung verwendet werden. Für sensible Inhalte ist daher ein bezahlter, datenschutzgeeigneter Tarif oder ein genügend gutes lokales Modell vorzuziehen.
- OpenAI-API-Modelle unterstützen strukturierte Ausgaben und bieten hohe Qualität, haben laut aktueller offizieller Modellübersicht aber kein kostenloses API-Kontingent. Ein ChatGPT/Codex-Abo deckt API-Kosten ausdrücklich nicht ab. Deshalb wird kein OpenAI-Aufruf ohne separat bereitgestellten API-Schlüssel und Kostenentscheidung aktiviert.
- OpenRouter bleibt als expliziter Adapter möglich, wird aber wegen wechselnder Gratis-Modelle nicht als Qualitätsstandard voreingestellt.
- Quellen: https://ai.google.dev/gemini-api/docs/models, https://ai.google.dev/gemini-api/docs/pricing, https://ai.google.dev/gemini-api/docs/structured-output, https://developers.openai.com/api/docs/models/compare, https://help.openai.com/en/articles/9039756-managing-your-work-in-the-api-platform-with-projects
- Für den privaten Handyzugang ist Tailscale technisch die bevorzugte Option: freigegebene Geräte bleiben laut Dokumentation außerhalb des öffentlichen Internets, und Zugriffsregeln können Personen auf den Web-Port begrenzen. Der Personal-Tarif ist für nicht-kommerzielle Nutzung mit bis zu sechs Personen kostenlos; kommerzielle Nutzung benötigt nach aktuellem Preismodell einen bezahlten Tarif. Cloudflare Private Network wäre die zweite private Variante, erfordert aber ebenfalls einen Client auf den Endgeräten. Quellen: https://tailscale.com/pricing, https://tailscale.com/kb/1084/sharing, https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/private-net/

## Bisherige Tests

- 2026-09-15: V1-Datenbank-Workflow: 3/3 Tests bestanden.
- 2026-09-15: Python-Bytecodeprüfung des Backends bestanden.
- 2026-09-15: Neuer Skriptplaner: 5/5 Tests für fehlende Konfiguration, Stilverzweigung, Revision, strukturiertes Gemini-Ergebnis/Provenienz und gesperrten Template-Fallback bestanden; zusammen 8/8 Python-Tests grün.
- 2026-09-15: Python-Compileall, JavaScript-Syntaxcheck, TypeScript-`tsc --noEmit` und `git diff --check` bestanden.
- 2026-09-15: Direkter Funktions-/API-Ablauf in isoliertem temporärem Datenverzeichnis bestanden: Auftrag, Revision auf Version 2, Freigabe und erwartete Sperre des noch nicht realen Erklärvideo-Renderers.
- 2026-09-15: Migration einer Kopie der bestehenden V1-Datenbank bestanden; 6 vorhandene Skriptversionen blieben erhalten und erhielten kompatible leere Metadaten.
- 2026-09-15: Remotion-Smoke-Render eines vorhandenen kurzen Auftrags nach Entfernung der Bildanweisungs-Textkarte bestanden (`/tmp/video-pipeline-step1-smoke.mp4`, 468 Frames, 1,8 MB). Der erste Versuch scheiterte erwartbar an der Socket-Sandbox; der freigegebene lokale Testlauf war erfolgreich.
- 2026-09-15: Etappe 2: 15/15 Tests bestanden, darunter kanonische Hashes, Szenen-ID-/Dauer-Normalisierung, falsche Freigabehashes, manipulierte gespeicherte Pläne und falsche Video-Dateihashes.
- 2026-09-15: V1-Migrationsprüfung auf einer Datenbankkopie erneut bestanden: 6 Skriptversionen erhalten, alle mit gültigem nachgetragenem Inhaltshash; keine bestehende Datei verändert.
- 2026-09-15: Isolierter API-Funktionstest bestanden: exakte hashgebundene Freigabe, Sperre nicht implementierter Renderer und Ablehnung einer vom Testadapter nur vorgetäuschten, inhaltlich unveränderten Revision.
- 2026-09-15: Etappe 3: 18/18 Tests bestanden. Neue Tests prüfen fehlende Assetanbieter, Pexels-Hochformatwahl sowie versionsgebundene Quelle, Urheber, Lizenz-URL und Asset-SHA-256 im Manifest.
- 2026-09-15: Neuer Remotion-Medienpfad mit echtem lokalem Bild und echtem lokalem MP4 jeweils über 60 Frames erfolgreich gerendert; Range-Requests für Videodateien funktionieren.
- 2026-09-15: Etappe 4: 24/24 Tests bestanden. Neue Tests prüfen Caption-Timing/SRT, nicht-stummes Audio, Audio-/Videostream und Dauer, Ablehnung stiller Ausgabe, Cloud-TTS-Kostensperre sowie korrekt verpacktes Gemini-PCM.
- 2026-09-15: Vollständiger isolierter Produktionslauf bestanden: Szenenplan, lokale Piper-Stimme, Untertitel, Remotion-Render und 8/8 Qualitätschecks. Ausgabe und alle Testartefakte lagen ausschließlich unter `/tmp`.
- 2026-09-15: Etappe 5: 28/28 Tests bestanden. Geprüft sind gezielte Szenenänderung mit neuer Version, Ablehnung wirkungsloser Änderungen sowie Wiederverwendung unveränderter Stock- und Sprachsegmente ohne erneuten Anbieteraufruf.
- 2026-09-15: Vollständiger Zwei-Szenen-Render mit getrennten Piper-Sprachsegmenten, neu zusammengesetzter Audiospur, Untertiteln und 9/9 Qualitätschecks bestanden. Die Testartefakte lagen ausschließlich unter `/tmp`.
- 2026-09-15: Python-Compileall, JavaScript-Syntaxcheck, TypeScript-`tsc --noEmit` und `git diff --check` nach Etappe 5 bestanden.

## Offene Probleme/Risiken

- Noch kein KI-Schlüssel im Projekt konfiguriert; Live-Qualität kann daher erst nach einer bewussten Anbieter-/Datenschutzentscheidung geprüft werden. Tests verwenden keine externen Kosten.
- V1-Nutzdaten und bereits gerenderte Videos werden erhalten und nicht migriert oder gelöscht.
- Die tatsächliche Medienstrategie pro Stil und mögliche generative Videokosten werden vor Aktivierung kostenpflichtiger Adapter konkret verglichen.
- Die lokale Maschine (Intel i5-8400, 6 CPU-Kerne, 22 GiB RAM) besitzt aktuell keinen nutzbaren NVIDIA-Treiber. Hochwertige lokale Diffusions-/Videomodelle sind daher technisch nicht sinnvoll; generatives Video benötigt voraussichtlich einen externen Bezahladapter.

## Erledigter Zwischenstand

- Standard ist jetzt `SCRIPT_PROVIDER=auto`; ohne bewusst konfigurierten Schlüssel entsteht kein Schein-Skript.
- Aktuelle strukturierte Gemini-`interactions`-Integration, OpenAI-kompatibler Adapter und expliziter OpenRouter-Adapter sind vorhanden.
- Visuelle Regie ist je Stil getrennt und umfasst realen Medientyp, sichtbare Einstellung, Asset-Prompt, Kamera, bewusste Texteinblendung und Übergang.
- KI-Änderungswünsche erzeugen eine neue Version; Modell/Anbieter und Hinweise zur Faktenprüfung werden gespeichert und angezeigt.
- Nicht implementierte Videoarten werden vorläufig gesperrt statt als Strichmännchenvideo ausgegeben. Bildanweisungen werden nicht mehr als sichtbare Textkarte gerendert.
- Jede neue Szene besitzt eine stabile ID, eine geplante Dauer und eine konkrete Quellenstrategie; Dauern werden exakt auf die Zielvideolänge normalisiert.
- Skript-/Szenenfreigaben speichern den kanonischen SHA-256-Hash des Plans. Renderaufträge müssen Version und Hash treffen; Manipulationen werden erkannt.
- Fertige Videos erhalten einen Datei-SHA-256. Prüfung, Freigabe und ein eventueller Upload sind an genau diese unveränderte Datei gebunden.
- Stockfotos und -videos werden passend zu Format und Suchbegriff über Pexels ausgewählt, lokal gespeichert und einschließlich Herkunft, Urheber, Lizenz und Datei-Hash manifestiert. Fehlende Assets brechen die Produktion ab.
- Reale Bilder erhalten kontrollierte Kamerabewegung; reale Videos werden bildfüllend geschnitten. Bildanweisungen selbst werden weiterhin nicht eingeblendet.
- Stumme Ersatzvideos sind entfernt. Fehlende oder lautlose Sprache, fehlende Untertitel/Assets, falsche Asset-Hashes, fehlende Audio-/Videostreams oder relevante Laufzeitabweichung verhindern den Status `video_review`.
- Ein natürlicherer Gemini-TTS-Adapter für Deutsch/Englisch ist vorhanden, bleibt aber hinter `ALLOW_CLOUD_TTS=0`, bis Kosten und Datenschutz bewusst akzeptiert wurden.
- Jede Szene kann in der Oberfläche separat gespeichert werden. Das erzeugt eine neue, hashgebundene Planversion und entwertet frühere Freigaben.
- Stockmedien und Voiceover werden pro stabiler Szenen-ID und Inhalt gefingert. Bei einer Teiländerung werden nur betroffene Segmente neu beschafft beziehungsweise gesprochen; vorhandene Dateien werden vor Wiederverwendung per SHA-256 geprüft.

## Nächster konkreter Arbeitsschritt

Etappe 6 benötigt die vereinbarte Nutzerentscheidung zum privaten Handyzugang, bevor ein Dienst erreichbar gemacht wird. Empfohlen ist Tailscale mit eigener Benutzer-/Gerätefreigabe, weil die Anwendung dabei nicht öffentlich ins Internet gestellt werden muss. Alternative: Cloudflare Access mit öffentlicher URL hinter Identitätsprüfung. Parallel bleiben für echte Qualitätsbewertung ein bewusst bereitgestellter KI-Schlüssel und für Stockmaterial ein kostenloser Pexels-Schlüssel offen.
