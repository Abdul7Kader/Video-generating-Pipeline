# Entwicklungsstatus – Video Pipeline V2

Letzte Aktualisierung: 2026-09-18

## Aktiver Auftrag: qualitätsorientierte, auswählbare Produktionsverfahren

### Kurzer Arbeitsplan

1. **Unterbrochenen Sperr-/Idempotenz-Fix sichern und abschließen.** Prüfung: gezielte Regressionstests, Gesamtsuite, Python-/JavaScript-Syntax und Diff-Hygiene.
2. **Antigravity und MoneyPrinterTurbo nachweisen beziehungsweise bewerten.** Prüfung: offizielle Dokumentation, lokal installierte Version und ein minimaler sicherer Automatisierungstest; MoneyPrinterTurbo wird nicht installiert.
3. **Architekturentscheidung zur Freigabe vorlegen.** Prüfung: Skript, Fakten, passende Bilder, Stimme, sichtbare Fehler, Nachbearbeitung, Kosten- und Sicherheitsgrenzen werden getrennt berücksichtigt. **Abgeschlossen: Option A wurde freigegeben.**
4. **Provider-Verträge und Produktionsprofil-Auswahl implementieren.** Das Produktionsverfahren wird im Dropdown gewählt; Skripterstellung, Medienerzeugung, Stimme und Schnitt bleiben getrennte, sichtbar ausgewiesene Komponenten. **Abgeschlossen und geprüft.**
5. **Antigravity als bevorzugten Cloud-Skriptpfad anbinden.** Nur Headless-JSON mit Schema, Sandbox, isoliertem leerem Arbeitsverzeichnis und ohne freigegebene Tools; Qwen nur als letzte Ausweichlösung.
6. **MoneyPrinterTurbo als optionalen Produktionsadapter pilotieren.** Nicht als Ersatz für Freigaben und Provenienz; erst gleicher Testauftrag gegen den bestehenden Remotion-/Stockpfad, dann Qualitätsentscheidung.
7. **Gesamtablauf prüfen und sichern.** Thema → Skript/Szenenplan → Skriptfreigabe → Video → Videofreigabe → Veröffentlichung; keine Kosten oder öffentlichen Zugänge ohne Freigabe.

### Ergebnisse und Fortsetzungspunkt

- **Schritt 1 abgeschlossen:** Identische gleichzeitige Ollama-Anfragen teilen sich einen Modellaufruf; unterschiedliche Aufrufe warten statt mit „erstellt bereits ein Skript“ abgewiesen zu werden. Browser und API verwenden nun für Qwen und Gemini eine stabile `generation_id`; eine Wiederholung erzeugt weder ein zweites Skript noch einen zweiten Auftrag. Das bestehende Gemini-ID-Format bleibt kompatibel. 69/69 Tests bestanden; `compileall`, `node --check web/app.js` und `git diff --check` bestanden.
- **Schritt 2 abgeschlossen:** Antigravity CLI `1.0.2` ist bereits installiert. Offizielle Dokumentation bestätigt Headless-Aufrufe, JSON-/Streaming-Ausgabe, JSON-Schema, Modellwahl, Exitcodes und Sandbox. Ein realer Aufruf mit dem vorhandenen Konto lieferte im Sandbox-Modus `SUCCESS` und die geforderte strukturierte Ausgabe `{status: ok}`. Es wurden keine neuen Kosten, Schlüssel oder öffentlichen Zugänge aktiviert. Der Standardmodus darf nicht direkt im Projektverzeichnis laufen, weil Antigravity dort Lesen/Schreiben automatisch erlauben kann; die spätere Integration muss deshalb ein leeres isoliertes Arbeitsverzeichnis und restriktive Richtlinien erzwingen.
- **MoneyPrinterTurbo-Befund:** API und CLI sind automationsfähig; Stockmedien, generative Clips, mehrere TTS-Anbieter, Untertitel und drei Seitenverhältnisse sind vorhanden. Das Projekt bringt jedoch eigene Orchestrierung, Konfiguration und Anbieterzugänge mit. Im geprüften Quellstand ist kein belastbarer Faktencheck und kein mit dieser Pipeline vergleichbares zweistufiges, versions-/hashgebundenes Freigabegate belegt. Deshalb ist es nur als optionaler Produktionsadapter, nicht als ungeprüfter Ersatz der Pipeline geeignet.
- **Schritt 3 abgeschlossen:** Option A ist freigegeben. Die bestehende Anwendung bleibt Orchestrator und alleinige Freigabe-/Provenienzinstanz; die vier Provider-Slots bleiben getrennt.
- **Schritt 4 abgeschlossen:** Die einfache Auswahl bietet vollständige Produktionsprofile. Erweiterte Einstellungen trennen Skript, Medien, Stimme und Schnitt. Nicht verfügbare Profile/Provider sind sichtbar deaktiviert und nennen den Grund. Die validierte Konfiguration wird am Auftrag und als unveränderlicher Snapshot jeder Skriptversion gespeichert. Eine Konfigurationsänderung erzeugt eine neue Version, entfernt Skript-/Render-/Veröffentlichungsfreigaben und verwirft alte Ausgabezuordnungen. Der Renderpfad prüft zusätzlich, ob Szenenmedien zum gespeicherten Medienanbieter passen; die gespeicherte Stimmenwahl überschreibt korrekt die globale Voreinstellung.
- **Prüfung Schritt 4:** 79/79 Python-Tests bestanden. Python-Compileall, `node --check web/app.js` und `git diff --check` bestanden. Ein isolierter Browser-Smoke-Test bestätigte vollständige Profile, vier getrennte erweiterte Auswahlen, begründete deaktivierte Optionen, responsive Darstellung und null Browserkonsolenfehler/-warnungen. Es wurden keine neuen Abhängigkeiten, Kosten oder öffentlichen Zugänge eingeführt.
- **Fortsetzungspunkt:** Schritt 5 wartet auf ausdrückliche Nutzerfreigabe. Dann wird ausschließlich die bereits nachgewiesene Antigravity-CLI als bevorzugter, schema-validierter Cloud-Skriptpfad hinter dem neuen Provider-Vertrag integriert; Qwen bleibt letzter Fallback.

Offizielle Grundlagen: https://antigravity.google/docs/cli/headless/, https://antigravity.google/docs/cli/install/, https://antigravity.google/docs/plans/, https://github.com/harry0703/MoneyPrinterTurbo/blob/main/README-en.md, https://github.com/harry0703/MoneyPrinterTurbo/blob/main/LICENSE

Git-Status der Dokumentation: `STATUS.md` wird lokal von Git verfolgt und war bei der Prüfung bereits auf GitHub in `origin/main` vorhanden. Diese aktualisierte Fassung gehört zum Branch `codex/gemini-notebooklm-integration`.

## Aktiver Auftrag: Gemini CLI, Profilisolation und NotebookLM

Die geplante Einbindung über Gemini CLI ist für die vorhandenen Google-AI-Pro-Konten extern blockiert: Google hat „Login with Google“ für Gemini Code Assist Individual, Google AI Pro und Google AI Ultra am 18. Juni 2026 eingestellt. Der reale Login auf diesem Rechner authentifizierte zunächst bei Google, wurde anschließend aber von Gemini CLI mit `This client is no longer supported for Gemini Code Assist for individuals` abgewiesen. Laut aktueller offizieller Dokumentation bleibt Gemini CLI nur für Code Assist Standard/Enterprise unterstützt; Consumer-Konten sollen zu Antigravity CLI migrieren. Da der Auftrag ausdrücklich ausschließlich Gemini CLI verlangt, wird nicht eigenmächtig migriert und keine kostenpflichtige API aktiviert. Consumer-NotebookLM bleibt beim kontrollierten Dateiimport, weil die programmatische Audio-Overview-API zu NotebookLM Enterprise gehört.

Aktueller CLI-Stand:

- Offizielle Gemini CLI `0.60.0` global installiert.
- `primary` und `secondary` liegen getrennt unter `%LOCALAPPDATA%\VideoPipeline\gemini-profiles` und verwenden je ein offiziell dokumentiertes `GEMINI_CLI_HOME`.
- Windows-ACLs geprüft: Vererbung deaktiviert; Zugriff nur für das aktuelle Windows-Konto und `SYSTEM`.
- Profile besitzen eine CLI-Deny-All-Policy; die Pipeline übergibt Prompts nur über stdin und startet die CLI in einem leeren Profil-Arbeitsordner.
- Tokens, Cookies und Sitzungsdateien liegen weder in SQLite noch im Repository. Persistiert werden nur Profilname, kategorisierter Status, letzter Erfolg/Fehler und Cooldown.
- Pooltests beweisen identische Eingabe beim Profilwechsel, Retry-After-Cooldown, Neustartpersistenz und das Nicht-Überschreiben CLI-verwalteter Authentifizierungseinstellungen.
- Der reguläre interaktive Google-Login für `primary` wurde mit der bewusst gewählten Ordneroption „Don't trust“ vollständig bis zur Google-Authentifizierung getestet. Der nachgelagerte Gemini-CLI-Dienst verweigert dieses Consumer-/Pro-Konto aufgrund der offiziellen Einstellung. Deshalb wurden weder `primary` aktiviert noch `secondary` unnötig angemeldet.
- Die fünfschrittige, persistente Skriptproduktion ist implementiert: Briefing, Struktur, Sprecher-Skript, Szenenplan und Qualitätsprüfung werden mit vollständiger strukturierter Eingabe/Ausgabe, Hashes, Modell, Profil und Prompt-Version in SQLite gespeichert. Abgeschlossene Schritte werden nach Fehler oder Neustart nicht wiederholt; eine stabile `generation_id` verhindert doppelte Endaufträge.
- Die Oberfläche erlaubt pro Auftrag die Wahl zwischen lokalem Qwen und Gemini CLI, zeigt Profil-/Fehler-/Cooldown-Status sowie das verwendete Profil und erkannte Qualitätsprobleme. Gemini bleibt bis zum bestandenen Live-Profiltest deaktiviert.

Umsetzungsplan:

1. **Jetzt:** heruntergeladene Gemini-/NotebookLM-MP4s gestreamt importieren, mit ffprobe prüfen, Herkunft und SHA-256 manifestieren und an die aktuelle freigegebene Skriptversion binden.
2. NotebookLM-Audio/Podcasts importieren und mit Wellenform, Bildern, Transkript und Untertiteln zu einem prüfbaren Video zusammensetzen.
3. Gemini-Bilder und -Videoclips einzelnen stabilen Szenen zuordnen und in das vorhandene Teil-Neurendering übernehmen.
4. Optionale Gemini-Medien-APIs für Bild, Video und TTS nur hinter expliziter Kostensperre, Modell-/Kostenanzeige und separatem API-Projekt ergänzen.
5. Alle externen Ergebnisse durchlaufen weiterhin die bestehende zweite, dateihashgebundene Freigabe vor einem Online-Posting.

Status: **Phase 1 implementiert** – In der Skriptansicht kann nach der Skriptfreigabe ein offiziell heruntergeladenes MP4 aus Gemini oder NotebookLM gewählt werden. Der Server schreibt den Upload begrenzt und gestreamt, verlangt Audio- und Videostream sowie eine positive Laufzeit, speichert ein Herkunfts-/Hashmanifest und übernimmt nur eine weiterhin aktuelle freigegebene Skriptversion in `video_review`. Die vorhandene zweite Freigabe bleibt unverändert zwingend. Phasen 2–5 sind geplant, aber noch nicht implementiert.

Vollständige Spezifikationen: `SPEC-gemini-cli-pool.md` und `SPEC-gemini-notebooklm-integration.md`; ausführbarer Plan: `tasks/plan.md`; Arbeitsliste: `tasks/todo.md`.

Offizielle Grundlagen: https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals, https://antigravity.google/docs/cli/gcli-migration, https://geminicli.com/docs/get-started/authentication/, https://geminicli.com/docs/reference/configuration/, https://geminicli.com/docs/cli/headless/, https://geminicli.com/docs/reference/policy-engine/, https://support.google.com/gemininotebook/answer/16212820, https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-audio-overview

## Aktiver Auftrag: Multi-Channel-Produktion und Veröffentlichung

Die Pipeline erhält eine additive Mehrfachziel-Auswahl und einen Zielstatus pro Plattform. YouTube bleibt ein echter automatischer Adapter; Mastodon wird als zweiter direkter Adapter ergänzt. TikTok, Meta, LinkedIn, X und Bluesky werden nur dann automatisch aktiviert, wenn die jeweils vorgeschriebenen Entwickler-Apps, OAuth-Rechte und Plattformprüfungen eingerichtet sind. Podcastziele folgen über einen öffentlich gehosteten RSS-Feed; Spotify Music und Apple Music benötigen für unabhängige Musikveröffentlichungen einen Distributor. Die Oberfläche wird diese Unterschiede sichtbar machen und keinen Export als Veröffentlichung ausgeben.

Status: **erste Multi-Channel-Scheibe implementiert** – Aufträge akzeptieren mehrere Ziele, die Datenbank migriert ältere Einzelziele additiv und führt je Plattform einen eigenen Status. Ein einziger Freigabeschritt reiht alle vollständig konfigurierten automatischen Ziele ein. Die Beanspruchung ist atomar; Fehler werden nicht automatisch wiederholt und ein Neustart während einer Übertragung erzeugt den sichtbaren Status `unknown`. YouTube läuft über den neuen Dispatcher, Mastodon ist als zweiter echter Adapter mit gestreamtem Medienupload, privater Standardsichtbarkeit und Idempotency-Key implementiert. Alle anderen Ziele bleiben bis zu ihrer offiziellen Einrichtung als Setup/RSS/Distributor gekennzeichnet.

Qualitätsausbau: Jede Plattform erhält ein Formatprofil. In der nächsten Scheibe erzeugt die Pipeline freigabebindbare 9:16-, 16:9- und 1:1-Varianten sowie Podcast-Audio mit Loudness-Prüfung. Eine echte Songproduktion bleibt ein eigener Adapter und wird nicht durch Sprach-TTS simuliert.

Bereits umgesetzt ist eine produktionsweite Lautheitsnormalisierung der Sprecher-Audiospur auf -16 LUFS mit -1,5 dB True-Peak-Reserve. Damit startet jedes neue lokale Rendering mit konsistenterer, plattformtauglicher Lautstärke.

Vollständige Spezifikation: `SPEC-multichannel-publishing.md`.

## Aktiver Auftrag: vollständig lokale Skripterstellung

Handyzugang und Cloud-Anbieter sind zurückgestellt. Der lokale Ausbau erfolgt in vier überprüfbaren Etappen:

1. Ollama ausschließlich auf `127.0.0.1` installieren, Qwen3.5 9B Q4_K_M laden und Hardware-/Speicherreserve messen. Einen größeren Kandidaten nur testen, wenn Modell, KV-Cache, Anwendung und Renderreserve ohne dauerhaften Swap in 22 GiB RAM passen.
2. Zwei identische deutsche Skriptaufgaben plus eine Revision mit festem JSON-Schema benchmarken; Laufzeit, RAM, Formatzuverlässigkeit und redaktionelle/visuelle Qualität dokumentieren und den besten Entwurf sichern.
3. Den Gewinner ohne Cloud- oder Template-Fallback als begrenzten Ollama-Adapter integrieren: ein Modellaufruf gleichzeitig, begrenzter Kontext/Ausgabe, verständliche Fehler und Entladen vor dem Rendern.
4. Echten lokalen API-Ablauf Thema → Entwurf → Revision → Freigabe testen; vollständigen Videoauftrag erst nach Nutzerfreigabe mit vorhandenem Material rendern.

Etappenstatus: **1 abgeschlossen**, **2 in Arbeit**, Adapter aus Etappe 3 bereits implementiert und testgedeckt, Etappe 4 wartet auf den bestandenen realen Benchmark.

Aktueller Befund: Ollama läuft mit deaktivierter Cloud-/Verlaufsfunktion ausschließlich auf `127.0.0.1:11434`. Der Nutzer hat die stärkere Quantisierung `qwen3.5:9b-q8_0` installiert (Ollama-ID `441ec31e4d2a`, 10 GB); Konfiguration, Compose und lokale Startskripte verwenden jetzt genau dieses Modell. Der Live-Healthcheck der Pipeline meldete `ready=true`, Anbieter `ollama`, Modell `qwen3.5:9b-q8_0`. Die früheren Q4-Benchmarkdateien bleiben als historische Messdaten unverändert.

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

Status: **lokaler Adapter erledigt; Live-Benchmark läuft** – Qwen3.5 9B ist Standard, Fehler verwenden weder Textvorlagen noch Cloudmodelle. Der reale Modell-/API-Test folgt unmittelbar nach abgeschlossenem Modelldownload.

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

- 2026-09-17: Qwen-Q8-Bindung live bestanden: Ollama nur auf localhost gestartet; `/api/health` meldete `ollama / qwen3.5:9b-q8_0` bereit.
- 2026-09-17: Gemini-CLI-Profilpool: offizielle CLI 0.60.0 installiert; Profil-ACLs für `primary` und `secondary` verifiziert. Acht Pooltests prüfen Namen/Traversal, tool-lose Policy, stdin/isoliertes Home, Rate-Limit-Failover mit identischer Eingabe, Statuspersistenz ohne Credentials, CLI-Fehlercode 41, Consumer-Deprecation und Erhalt CLI-verwalteter Authentifizierung.
- 2026-09-17: Realer `primary`-Login: leeres Workspace ausdrücklich nicht vertraut, Google-OAuth erfolgreich, anschließend offizielle serverseitige Ablehnung des Consumer-/Pro-Zugangs. Keine Umgehung, kein API-Schlüssel und kein zweites Konto verwendet. Gemini bleibt deaktiviert; Qwen bleibt bereit.
- 2026-09-17: Persistenter Gemini-Workflow: drei Tests belegen fünf schema-validierte Schritte, Wiederaufnahme exakt am ersten offenen Schritt, keine erneute Erzeugung fertiger Schritte, unveränderliche Auftrags-IDs und Ablehnung ungültiger Teilausgaben. Gesamtsuite 63/63 bestanden; Compileall, JavaScript-Syntax und `git diff --check` bestanden.
- 2026-09-17: Lokaler Dienst nach Neustart ausschließlich auf `127.0.0.1:8080`: Qwen Q8 bereit, `primary` sichtbar als `access_denied`, `secondary` unangemeldet, Gemini bewusst inaktiv. Frischer Browser-Smoke-Test zeigt Anbieterwahl und Profilstatus; Browserkonsole ohne Fehler oder Warnungen.
- 2026-09-17: Multi-Channel-Scheibe: 48/48 Python-Tests bestanden. Neue Tests prüfen Mehrfachziel-Normalisierung, Plattformmodi, Konfigurationsstatus ohne Secret-Leak, unabhängige Zielzustände, atomare Beanspruchung, Teilfehler, Neustartstatus `unknown`, Mastodon-HTTPS-/Payload-/Idempotenzregeln und -16-LUFS-Normalisierung.
- 2026-09-17: Echte lokale FFmpeg-Loudness-Normalisierung erfolgreich geprüft: 1,0 s Eingang ergab 1,0 s, 48 kHz und eine valide WAV-Ausgabe. Python-Compileall, JavaScript-Syntax und `git diff --check` bestanden. Laufender Dienst meldet FFmpeg/ffprobe bereit und 15 Plattformprofile. Browser-Smoke-Test zeigte die Mehrfachauswahl und alle Setup-/Formatangaben ohne Konsolenfehler.
- 2026-09-17: Gemini-/NotebookLM-Phase 1: 39/39 Python-Tests bestanden. Neue Tests prüfen Uploadlimit und Entfernung von Teildateien, Audio-/Videostream-Pflicht, Herkunftsmanifest, unbekannte Quellen, aktuelle Skriptfreigabe sowie den vollständigen API-zu-`video_review`-Ablauf.
- 2026-09-17: Python-Compileall, JavaScript-Syntax und `git diff --check` bestanden. Laufender Dienst nach Neustart gesund; Windows-ffprobe erkannt und Importendpunkt im OpenAPI-Schema vorhanden. Die lokale Oberfläche lädt die neue `app.js` ohne Browserwarnungen oder -fehler.

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
- 2026-09-16: Ollama 0.34.1 projektlokal gestartet; Bindung auf `127.0.0.1:11434`, `OLLAMA_NO_CLOUD=1`, `OLLAMA_NOHISTORY=1`, maximal ein geladenes Modell und ein paralleler Modellaufruf verifiziert.
- 2026-09-16: Interner Compose-Betrieb ergänzt und mit `docker compose config --quiet` geprüft: kein veröffentlichter Ollama-Port, gepinntes Image, internes Modell-Init und gehärtete Containeroptionen.
- 2026-09-16: 31/31 Python-Tests sowie Python-Compileall, JavaScript-Syntaxcheck, TypeScript-`tsc --noEmit` und `git diff --check` mit lokalem Ollama-Standard bestanden.
- 2026-09-16: Qwen3.5 `qwen3.5:9b-q4_K_M` vollständig geladen und von Ollama per SHA-256 verifiziert; Modellliste meldet ID `6488c96fa5fa` und 6,6 GB. Socket erneut ausschließlich auf `127.0.0.1:11434` bestätigt; vor Inferenz 19 GiB RAM verfügbar und 0 Byte Swap belegt.
- 2026-09-16: 32/32 Python-Tests bestanden. Ein zweiter gleichzeitiger Modellaufruf schlägt nun sofort verständlich fehl, statt die Anwendungsthreads hinter dem aktiven Lauf aufzustauen.
- 2026-09-16: Erster realer Benchmarkversuch korrekt als fehlgeschlagen gewertet: Moor 470,705 s und Schlaf 451,000 s, beide Antworten wegen `accent="de_DE"` beziehungsweise `accent="de"` in allen Szenen nicht schema-valide; Revision daher nicht vorgetäuscht, sondern übersprungen. Spitzenreserve mindestens 12,66 GiB verfügbarer RAM, Swap stets 0 Byte. Rohmessung: `benchmarks/qwen3.5-9b-q4_K_M-attempt1-invalid.json`.
- 2026-09-16: Ursache des Formatfehlers behoben: Das an Ollama übermittelte JSON-Schema erzwingt für `accent` nun eine feste Hex-Farbpalette; der Prompt grenzt das Feld zusätzlich ausdrücklich gegen Sprache/Locale ab. Zugehöriger Adaptertest bestanden.
- 2026-09-16: Zweiter realer Benchmark: Moor-Entwurf schema-valide in 419,200 s, Schlaf-Entwurf nach 600,101 s am bisherigen Timeout abgebrochen, Moor-Revision schema-valide in 475,022 s. Revision bewahrte Szenen-IDs und nicht adressierte Szenen, setzte die Schwamm-Analogie aber wissenschaftlich zu wörtlich um. Messung: `benchmarks/qwen3.5-9b-q4_K_M-attempt2-timeout.json`.
- 2026-09-16: Daraufhin Ausgabe gezielt gestrafft und gehärtet: technische Quellenfelder werden deterministisch aus dem Medientyp abgeleitet, Beschreibungen besitzen Schema-Längenlimits, `visual` darf kein bloßer Enumwert sein, Fakt-/Analogie-/CTA-Regeln wurden verschärft. Ausgabelimit sinkt von 3072 auf 2048 Tokens; CPU-Zeitlimit steigt moderat von 600 auf 720 s. 32/32 Tests sowie Compileall und `git diff --check` bestanden.
- 2026-09-16: Dritter Benchmark technisch 3/3 schema-valide (Moor 491,725 s, Schlaf 484,206 s, Moor-Revision 481,649 s), aber redaktionell nicht freigegeben: unbelegte Mengen-/Waldvergleiche, fachlich irreführende Schwamm-Erklärung, generische Follow-Karte, Grammatikfehler und `%s`-Platzhalter in Faktenhinweisen. Messung: `benchmarks/qwen3.5-9b-q4_K_M-attempt3-quality-fail.json`.
- 2026-09-16: Redaktionelle Regeln erneut verschärft: ungesicherte Mengen/Ranglisten/Vergleiche müssen aus Sprechertext und Visuals entfernt werden, Faktenhinweise erlauben keine unsichere Behauptung im Text, generische Follow-/Teaser-Karten sind verboten, Grammatik-Selbstprüfung gefordert. Die Schwamm-Revision begrenzt die Analogie ausdrücklich auf den Wasserhaushalt; ein neuer harter Guard lehnt `%s`, `TODO` und Templatevariablen ab. 33/33 Tests bestanden.

## Offene Probleme/Risiken

- Die Docker-CLI ist in dieser Windows-Sitzung nicht installiert beziehungsweise nicht im PATH; `docker compose config --quiet` konnte deshalb im finalen Durchgang nicht erneut ausgeführt werden. Der projektlokale FastAPI-/Ollama-Betrieb und alle automatisierten Tests funktionieren unabhängig davon.
- Die CPU-Laufzeit liegt bei etwa acht Minuten je Entwurf und die Speicherreserve ist gut. Die Struktur ist inzwischen zuverlässig, aber der dritte Lauf fiel am redaktionellen Qualitätsgate durch. Die nochmals verschärften Regeln müssen daher in einem letzten vollständigen Wiederholungslauf belegt werden.
- V1-Nutzdaten und bereits gerenderte Videos werden erhalten und nicht migriert oder gelöscht.
- Die tatsächliche Medienstrategie pro Stil und mögliche generative Videokosten werden vor Aktivierung kostenpflichtiger Adapter konkret verglichen.
- Die lokale Maschine (Intel i5-8400, 6 CPU-Kerne, 22 GiB RAM) besitzt aktuell keinen nutzbaren NVIDIA-Treiber. Hochwertige lokale Diffusions-/Videomodelle sind daher technisch nicht sinnvoll; generatives Video benötigt voraussichtlich einen externen Bezahladapter.

## Erledigter Zwischenstand

- Standard ist jetzt `SCRIPT_PROVIDER=ollama` mit `qwen3.5:9b-q8_0`; ohne erreichbares lokales Modell entsteht kein Schein-Skript.
- Der Ollama-Adapter erzwingt strukturiertes JSON, begrenzt Kontext und Ausgabe, serialisiert Modellaufrufe und entlädt das Modell vor einem Render. Nicht-lokale Ollama-Adressen werden abgewiesen.
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

Für den qualitätsorientierten Skriptpfad ist Option A entschieden. Als Nächstes folgt nach ausdrücklicher Freigabe Schritt 5: Antigravity wird über den neuen Provider-Vertrag bevorzugt angebunden, ausschließlich headless, schemavalidiert, sandboxed und in einem leeren isolierten Arbeitsverzeichnis; Qwen bleibt letzter Fallback. Bis dahin bleibt die in Schritt 4 eingeführte Antigravity-Auswahl sichtbar deaktiviert. Der nicht mehr unterstützte Gemini-CLI-Consumerpfad bleibt deaktiviert.

Für Multi-Channel als Nächstes aus einem freigegebenen Master hashgebundene 9:16-, 16:9- und 1:1-Ausgaben sowie ein Podcast-Audioartefakt erzeugen. Erst wenn ein valider Feed samt öffentlichem Hosting konfiguriert ist, darf ein Podcastziel von `setup_required` auf export- oder veröffentlichungsbereit wechseln. Danach folgen – jeweils nur mit offiziellen Entwicklerrechten – weitere direkte Social-Adapter. Eine Songproduktion bleibt getrennt und benötigt einen echten Musikgenerator sowie einen Distributor.

Für den lokalen Skriptpfad bleibt parallel der vollständige Drei-Lauf-Benchmark mit strengem redaktionellem Prompt und Platzhalter-Guard offen. Ein Video wird weiterhin erst nach Nutzerfreigabe gerendert oder veröffentlicht; Handyzugang bleibt zurückgestellt.
