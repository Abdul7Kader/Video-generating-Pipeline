# Aktiver Entwicklungsplan: Strichmenschen-Videos

Ergänzung 16.10.2026: Desktop und Einzelabbruch, native Kontotresore/Videoablage,
Discord-Abnahme und offizielle Verteilung implementiert; tatsächliche Konten- und
Uploadabnahme nach Einrichtung offen. TikTok nur Inbox mit finaler App-Freigabe.
Aktueller Ablauf, Schutzbedarf und Prüfungen: [Abnahme und Verteilung](../docs/review-distribution.md).
Neueste Nutzerwahl: Arbeitsdateien **nur manuell** aufräumen. Endvideo getrennt
speichern, Projekt bei Bedarf schützen; Skript-/Planhistorie erhalten, vorhandene
Sprachcaches wiederverwenden. [Speicherablauf und Grenzen](../docs/video-storage.md).

Stand: 2026-10-14. Nummerierter Entwicklungsplan auf Nutzerwunsch.
Zuerst die Originalversion für den Nutzer fertigstellen, erst danach die Familienversion
ohne Pro-Abos. Bereits vorhandene Funktionen gezielt prüfen und verbessern, nicht neu bauen.
Die älteren Ausbaupläne darunter bleiben eingefrorener Verlauf. Aufgaben: `tasks/todo.md`.

Lesbare nummerierte Übersicht: [ENTWICKLUNGSPLAN.md](../ENTWICKLUNGSPLAN.md).
Bearbeitungsstand: [ARBEITSSTAND.md](../ARBEITSSTAND.md) und [STATUS.md](../STATUS.md).

## Entscheidungen und Grenzen

- Ein Prompt → durchgehender Sprechertext → KI-Änderungswünsche → eine Skriptfreigabe → automatische Bildplanung und Produktion → Video prüfen und herunterladen. Keine verpflichtende Einzelszenenfreigabe. Bestehende Veröffentlichungsfreigaben bleiben bestehen.
- Das letzte Katzenadoptionsvideo nutzte Antigravity / `gemini-3.1-pro-high`, lokale Qwen-TTS und SVG / Remotion / FFmpeg. Anbieter und Modell künftig immer tatsächlich ausweisen; der Modellnachweis beweist keinen Abrechnungstarif.
- Fokus ausschließlich Strichmännchen; andere Videoarten bleiben ausgeblendet, bestehende Daten und historische Aufgaben erhalten.
- Ausführung durch die Anwendung ohne Codex oder einen steuernden Coding-Agenten. Für die Originalversion vorhandenen Anbieterzugang prüfen; keine unangekündigten Modellwechsel oder kostenpflichtigen Aktivierungen.
- Schutzbedarf: Skripte, Videos, Kontozugänge und Host-Ressourcen. Browser-/Modellausgaben sind untrusted. Serverseitige Schema-, Pfad-, Herkunfts- und Ressourcenprüfungen; keine Shellbefehle aus Modellausgaben.
- UI und eigene Dienste nur auf Loopback; keine Firewallfreigaben, Tunnel oder globalen Schutzänderungen. Zugangsdaten nur im offiziellen Anmeldedialog bzw. geschütztem lokalen Speicher, nicht in Logs oder Git.
- Aktueller Produktionsaudit am 14.10.2026 nach ausdrücklicher Nutzerfreigabe: `npm audit --omit=dev --ignore-scripts --registry=https://registry.npmjs.org --json`, 0 bekannte Schwachstellen. Der frühere Metadaten-Blocker ist erledigt; keine Paketupdates oder Installationsskripte.
- Neue ausdrückliche Nutzervorgabe: keine routinemäßigen Testvideos über die UI. Echte Videoproben nur bei zwingendem Prüfbedarf einer konkreten Änderung; ansonsten spätere Nutzerabnahme bzw. Schritt 10. Automatisierte Tests zuerst; keine Live-Abnahme vortäuschen.

## Originalversion: Schritte 1–10

### 1. Verlässlichen Produktionszugang prüfen
Zwischenstand: implementiert; automatisierte Tests und echte Anmeldung-/Modelllistenprüfung bestanden. Gemini 3.1 Pro wird vom vorhandenen Konto derzeit nicht angeboten. Der Nutzer hat Gemini 3.8 Flash (High) bestätigt; `gemini-3.8-flash-high` ist lokal als aktives Skriptmodell gespeichert. Stimmen- und Hardwareauswahl erhalten; keine Anbieter-Credit-Einstellungen oder Tarife geändert. Eine reale Skriptanfrage bleibt für die spätere Nutzerabnahme vorgemerkt.

Den aktuell verwendeten Skriptanbieter mit tatsächlichem Modellstatus in der Oberfläche erklären; Installation, Anmeldung, Modellzugang und ausgeschöpftes Kontingent getrennt darstellen.
- Abnahme: vorhandener Zugang ermöglicht eine echte Skriptanfrage; fehlender Zugang liefert eine verständliche Ursache und passenden nächsten Schritt. Keine automatische Kostenaktivierung oder stille Anbieterumschaltung.
- Prüfung: gezielte Provider-/Einstellungstests plus reale Anfrage nur bei verfügbarem, ausdrücklich gewähltem Zugang.
- Abhängigkeiten: keine. Umfang M; `backend/antigravity.py`, `backend/setup.py`, `web/settings.js`, `tests/test_antigravity.py`, `tests/test_settings_api.py`.

### 2. Einfachen Skript-Freigabeablauf abschließen
Technisch abgeschlossen und automatisiert geprüft: Text-/Bildidee, Schutz nicht angewendeter Änderungswünsche, atomare Freigabe/Render-Einreihung und Fortsetzung nach Renderfehlern. Überarbeitung von Storyboards wird serverseitig als Fließtextablauf erkannt, auch ohne Clientflag. Änderungen ausschließlich an sachlichen Hinweisen werden als neue Version akzeptiert. Live-/Videoabnahme auf ausdrücklichen Nutzerwunsch bis zum Ende verschoben.

Den bestehenden Fließtextablauf vom Prompt bis zur Produktion durchgängig prüfen und verbleibende Szenenpflichten aus dem Bedienweg nehmen.
- Abnahme: KI-Änderungswünsche erzeugen eine neue Skriptversion; genau der freigegebene Sprechertext wird produziert. Doppelaufrufe und veraltete Freigaben erzeugen keinen falschen Render.
- Prüfung: `python -m unittest tests.test_story_workflow tests.test_workflow`; echter Browser-/Videoablauf bei der späteren Nutzerabnahme, jetzt keine Testvideoerstellung.
- Abhängigkeiten: 1. Umfang M; `backend/story.py`, `backend/main.py`, `web/app.js`, `tests/test_story_workflow.py`, `tests/test_workflow.py`.

### 3. Skriptqualität über verschiedene Themen verbessern
Technisch abgeschlossen und mit Textfixtures für Tieradoption, Informatik und Kochen, Deutsch/Englisch sowie 30/60/90 Sekunden geprüft. Stimme und Tempo beeinflussen das Wortbudget. Höchstens ein Korrekturversuch, danach Fehler statt ungültiger Speicherung. Vorherige Bildidee und Hinweise werden in den Überarbeitungskontext aufgenommen. Faktische/semantische und redaktionelle Qualität werden damit nicht als verifiziert ausgegeben.

Sprechertexte auf klare Handlung, gute Verständlichkeit, passende Länge und überprüfbare Aussagen ausrichten; Änderungswünsche ohne Verlust vorheriger Vorgaben umsetzen.
- Abnahme: mehrere unterschiedliche Themen liefern verständliche Texte innerhalb des gewählten Zeitbudgets; Änderungen erhalten zentrale Figuren und Handlung. Unsichere Fakten werden nicht als geprüft ausgegeben.
- Prüfung: gezielte Story-/Planner-Tests und Textfixtures ohne echte KI-Anfragen; Vergleich realer Entwürfe durch den Nutzer bzw. in Schritt 10.
- Abhängigkeiten: 2. Umfang M; `backend/story.py`, `backend/planner.py`, `tests/test_story_workflow.py`, `tests/test_planner.py`.

### 4. Erzählte Handlung in sichtbare Bildaktionen übersetzen
Technisch umgesetzt: zusätzlicher Motivkatalog für Bücher, Telefone, Laptops, Dokumente und Futter; Prüfung erkannter read/work/pick/carry/place/pet-Aktionen gegen Textanker und tatsächliche Ziele. Einfache Objektpronomen verfolgen das zuletzt ausdrücklich genannte Motiv, auch über Bildabschnitte. Bekannte nicht unterstützte Motive (Pferd, Vogel, Fisch, Auto, Fahrrad, Flugzeug, Pfanne) stoppen bereits vor der Bild-KI. Fehlende Aktionen dürfen einmal korrigiert werden, danach bleibt der ursprüngliche Entwurf ungequeued. Prüfung mit Tieradoption, Lesen, Tippen und englischen Telefonhandlungen; keine allgemeine semantische oder Faktenprüfung behauptet.
Die vorhandene Bildabdeckung über Katze/Hund hinaus für eine begrenzte erste Motivgruppe ausbauen. Figuren, Tiere, wichtige Gegenstände und konkrete Handlungen im Plan mit den darstellbaren Zeichenbausteinen abgleichen.
- Abnahme: Adoption zeigt das Tier und die relevante Interaktion; weitere Testthemen zeigen ihre zentralen Handlungen. Nicht unterstützte Motive werden vor einem irreführenden Erfolgsresultat benannt.
- Prüfung: `python -m unittest tests.test_visual_coverage tests.test_story_workflow`; Vergleich Erzähltext/Bildplan bei unterschiedlichen Themen.
- Abhängigkeiten: 3. Umfang M; `backend/visual_coverage.py`, `backend/story.py`, `backend/stickman.py`, `tests/test_visual_coverage.py`, `tests/test_story_workflow.py`.

Prüfpunkt nach 1–4: Text-/Bildplanverträge automatisch prüfen, einschließlich Thema ohne Katze. Der echte Auftrag von Idee und Textänderung bis zum Bildplan bleibt Bestandteil der späteren Nutzerabnahme; keine routinemäßigen Testvideos während des Baus.

### 5. Handkontakt und Gegenstandsinteraktion verbessern
Technisch umgesetzt und anhand echter PNG-Standbilder geprüft: Hand und gehaltenes Objekt verwenden denselben Griffpunkt, einschließlich Größe, Blickrichtung und Körperbewegung. Greifen und Ablegen nähern die Figur nötigenfalls an; erreichte Position bleibt erhalten. Ablage bleibt an neuen Koordinaten oder passt auf eine ausdrücklich referenzierte Tischfläche. Besitzwechsel dürfen nicht doppelt erfolgen; die Ablage endet vor dem nächsten gesprochenen Greifanker. Streicheln berührt den tatsächlichen Tierkopf; sitzende Katze/Hund haben einen verbundenen Hals. Renderer-Version erhöht. Temporäre Render-HTTP-Server sind im Renderprozess auf Loopback begrenzt und getestet. 224 Backend-Tests (ein regulärer Skip), 28 Renderer-Tests, TypeScript/Syntax sowie zehn Standbilder; Film-/Audioabnahme auf Nutzerwunsch später.
Greifen, Tragen, Ablegen und Streicheln anhand bestehender Bewegungen verbessern; Kontaktpunkte zwischen Figuren und Objekten konsistent halten.
- Abnahme: Hand und Gegenstand bleiben während der Aktion nachvollziehbar verbunden; Objektbesitz und Ablage wechseln zum vorgesehenen Zeitpunkt.
- Prüfung: Renderer-/Stickman-/Sprachanker-Tests und PNG-Standbilder mit Greifen/Lesen/Ablegen/Tierkontakt; kurze Filmproben bei der späteren Nutzerabnahme.
- Abhängigkeiten: 4. Umfang M; `renderer/src/ink.tsx`, `backend/stickman.py`, `tests/test_stickman.py`, `renderer/ink.test.mjs`.

### 6. Bewegung passend zur Erzählung takten
Technisch umgesetzt: Wortzeitdaten auf Anzahl, Reihenfolge, Endzeiten und endliche Werte geprüft. Aktionen dauern höchstens bis zum nächsten Anker/Abschnittsende, maximal 1,2 Sekunden für Laufwege und 0,9 Sekunden für andere Bewegungen. Sprachfenster steuern das Gestenende; richtungsloses Marschieren stoppt. Alte Laufziele werden an erkannte Bewegungswörter gebunden, statt bei Bildbeginn loszulaufen. Sehr enge Anker werden abgewiesen. Wortzeiten bleiben Schätzungen aus Sprachenergie und Wortgewichten; echte Sprach-/Filmabnahme später.
Die vorhandenen Sprachanker für Aktionsbeginn, Tempo und Abschluss nutzen; unnötig lange Leerlaufbewegungen vermeiden, kurze Aktionen lesbar halten.
- Abnahme: die Hauptaktion erscheint während der entsprechenden Erzählstelle; Laufwege und Gesten sind zügig, flüssig und verständlich statt beliebig beschleunigt.
- Prüfung: `python -m unittest tests.test_speech_motion`; Renderer-Tests und Filmvergleich mit zugehörigem Audio.
- Abhängigkeiten: 5. Umfang M; `backend/speech.py`, `backend/rendering.py`, `renderer/src/ink.tsx`, `tests/test_speech_motion.py`.

### 7. Kontinuität zwischen Bildabschnitten sichern
Technisch umgesetzt: stabile Gegenstands-IDs und begrenzter Anfangsbesitz; Figurenart/Kleidung/Größe und Objekttyp/Größe/Beschriftung werden über Wiederauftritte geprüft. Besitzwechsel benötigen Ablage, gehaltene Objekte bleiben beim Träger, Ruhe-/Schlafzustände bis zur nächsten Aktion erhalten. Ablage bleibt im selben Schauplatz erhalten. Der Renderer übernimmt tatsächliche Endpositionen inklusive automatischer Annäherung und setzt die Bewegungsphase fort; gehaltene Objekte verschwinden mit ihrem Träger. Normalisierung erfolgt vor Speicherung des neuen Bildplans und vor dem Rendern bestehender Pläne, ohne Änderungen am Sprechertext oder gespeicherten Altversionen. 234 Backend-Tests (ein Skip), 31 Renderer-Tests, TypeScript/Syntax und acht Schnitt-Standbilder aus vier Abschnitten in beiden Formaten geprüft; kein Testvideo. Begrenzter Zustandsvertrag, keine allgemeine Ursachen-/Spracherkennungsprüfung. Absichtliche Merkmalswechsel sind derzeit nicht unterstützt.
Figurenidentität, Tiermerkmale, gehaltene Gegenstände und erzählte Zustände über Schnitte hinweg erhalten.
- Abnahme: dieselbe Figur/dasselbe Tier bleibt erkennbar; wichtige Gegenstände und Zustandsänderungen verschwinden oder wechseln nicht ohne erzählte Ursache.
- Prüfung: mehrteilige Filmprobe und gezielte Tests für Figuren-/Objektzustände; Bildabschnitte vor und nach Schnitten vergleichen.
- Abhängigkeiten: 6. Umfang M; `backend/story.py`, `backend/visual_coverage.py`, `renderer/src/ink.tsx`, `tests/test_visual_coverage.py`, `tests/test_stickman_studio.py`.

Prüfpunkt nach 5–7: technische Prüfungen und Schnitt-Standbilder bestanden; Filmproben für Bild-/Tonabnahme auf Nutzerwunsch später.

### 8. Erzählerqualität und Sprachfluss fertigstellen — technisch umgesetzt (2026-10-14)
Qwen als vorhandene natürliche Stimmoption und Piper als ausdrücklich wählbare schnelle Alternative vergleichen; Aussprache, Lautheit und unnötige Pausen verbessern.
- Abnahme: ausgewählte Stimme ist die tatsächlich verwendete; unnötige lange Pausen werden reduziert, Satzgrenzen bleiben verständlich. Fehlendes Audio ist ein Fehler; Zeit-/Ressourcenbedarf wird ehrlich angezeigt.
- Prüfung: `python -m unittest tests.test_qwen_voice tests.test_quality`; dieselben kurzen Texte mit beiden Stimmen anhören, Wellenform und Audiozeit prüfen.
- Abhängigkeiten: 2; für gemeinsamen Bild-/Tonvergleich 6. Umfang M; `backend/speech.py`, `backend/qwen_tts.py`, `web/voices.js`, `tests/test_qwen_voice.py`, `tests/test_quality.py`.

### 9. UI und Einrichtung für die Originalversion abschließen — umgesetzt (2026-10-14)
Nur relevante Produktionswege im Hauptablauf zeigen; notwendige Einrichtung von optionalen Alternativen unterscheiden. Fortschritt, Fehler und nächster Bedienungsschritt sind verständlich.
- Abnahme: ein neuer Nutzer findet Einrichtung, Prompt, Änderungswunsch, Freigabe und Download ohne Szenenwissen. Laufende Prozesse zeigen Fortschritt/vergangene Zeit und nur eine tatsächlich belastbare Restzeitschätzung.
- Prüfung: echter Browser-Smoke-Test in schmaler und normaler Ansicht; `node --test tests/settings-ui.test.cjs tests/process-progress.test.cjs` und UI-Guidance-Tests.
- Abhängigkeiten: 1, 2, 8. Umfang M; `web/app.js`, `web/settings.js`, `web/styles.css`, `tests/test_ui_guidance.py`, `tests/settings-ui.test.cjs`.

Umsetzungsnachweis 8–9: `continuous-v2` erhält beide Ränder gekürzter stiller Lücken;
Hörproben nutzen die Produktions-Lautheitsregel und liefern begrenzte WAV-Messwerte.
Gewählte Anbieter müssen übereinstimmen; stille/abgeschnittene Cache-Dateien werden
nicht wiederverwendet. Installation allein aktiviert Qwen nicht. Tatsächliche
freie RAM-Werte begrenzen dessen Verfügbarkeit. Vergleich: Piper 15,44 s Rechenzeit
für 3,153 s Audio; Qwen 211,50 s für 3,67 s. Keine übersteuerten Samples; längste
innere Pause 0,08/0,10 s. Menschliche Hör-/Ausspracheabnahme bleibt Schritt 10.
Die UI zeigt den aktiven Weg und klappt dessen Alternativen ein. Modell-/Stimmen-/
Tempo-Erfahrungswerte benötigen drei konsistente Messungen, liefern keine erfundenen
Prozentwerte. 238 Backend-Tests (1 übersprungen), 16 JS-Tests, JS-Syntax und
Browser normal/390 px geprüft. Kein Video und kein neuer Produktionsauftrag.

### 10. Originalversion mit mehreren Videos abnehmen und sichern
Technische Mehrthemenprüfung abgeschlossen: vier Clips und allgemeine Fixes,
249 Backend-/35 Renderer-/16 JS-Prüfungen, TypeScript, UI/Download und freigegebener
npm-Produktionsaudit. [Nachweis und Grenzen](../docs/acceptance-10.md).
Menschliche Sicht-/Hörfreigabe ist weiterhin ein offener Abnahmepunkt.
Repräsentative Beispiele statt eines Einzelfixes verwenden: Tieradoption, Lernen, Gegenstandshandlung und eine einfache soziale Geschichte. Einrichtungs- und Produktionsfehler ebenfalls prüfen.
- Abnahme: alle Beispiele zeigen wesentliche erzählte Akteure und Handlungen; Skriptfreigaben, Stimme, Audiofluss und Download stimmen. Grenzen und offene Risiken sind dokumentiert; Originalversion ist vor Start der Familienetappe abgeschlossen.
- Prüfung: Backend-/Renderer-Tests, TypeScript-Prüfung, Browserablauf, reale Film-/Hörsichtung und Sicherheits-Negativfälle. Nur bei neuer Grundlage weitere Tests wiederholen.
- Abhängigkeiten: 3–9. Umfang M; bestehende Testläufe und Filmproben, `docs/story-workflow.md`, `docs/device-settings.md`, `STATUS.md`. Commit/Push nur unter verifizierter Identität Abdul7Kader; bestehende Push-Autorisierung beachten.

Prüfpunkt nach 8–10: Originalversion erfüllt alle Abnahmen; Testergebnisse und offene Einschränkungen sind dokumentiert und Änderungen geprüft/gesichert.

## Familienversion: erst danach, Schritte 11–13

### 11. Konten und kostenlose Anmeldewege erklären
Implementiert und geprüft als Kontenübersicht mit Herstelleranmeldung,
Verbindungsprüfung, kostenlosem Basiskontingent und optionalen Abos.
[Quellen und Voraussetzungen](../docs/accounts.md); eigener Familienkonto-Test offen.
Die zu diesem Zeitpunkt offiziell unterstützten kostenlosen Gemini-/Antigravity-Zugänge prüfen und unter Einstellungen klar darstellen: normales Konto, optionales Abo, Modellzugang und Limits.
- Abnahme: kostenlose Konten werden nicht pauschal wegen eines fehlenden Pro-Abos ausgeschlossen; Herstelleranmeldung und Verbindungsprüfung sind verständlich. Keine Zugangsdaten in Logs, Browser-URLs oder Git.
- Prüfung: offizielle Dokumentation, gezielte Einstellungs-/Provider-Tests und regulärer Anmeldetest durch den Kontoinhaber.
- Abhängigkeiten: 10. Umfang M; `backend/setup.py`, `web/settings.js`, `tests/test_settings_api.py`, `tests/settings-ui.test.cjs`, `docs/device-settings.md`.

### 12. Kostenlosen automatischen Skriptweg ergänzen
Technisch umgesetzt: offiziell unterstützter Antigravity-Individual-Zugang,
Credit-Einstellung vor jedem Aufruf geprüft, API-/Agentenvariablen ausgeschlossen,
Fehler ohne Teilauftrag/Versionsverlust. Gemini CLI wegen aktueller Consumer-
Abkündigung verworfen. Echter bestehender Providerzugang geprüft; eigener
Free-Tier-Familienkonto-Test bleibt externe Abnahme. [Nachweise](../docs/family-paths.md).
Nach Verfügbarkeits- und Konditionenprüfung einen offiziell unterstützten Free-Tier-API- oder CLI-Weg auswählen. Jeder nutzt den eigenen Zugang; Stimme und Renderer bleiben Teil der bestehenden Pipeline.
- Abnahme: kostenloser Zugang erzeugt und überarbeitet Skripte ohne steuernden Coding-Agenten; Limit-/Anmeldefehler behalten den Auftrag. Keine automatische Tarif-/Credit-Aktivierung und keine unangekündigte Anbieterumschaltung.
- Prüfung: Provider-Vertrags- und Negativtests für fehlenden Zugang, Kontingent und ungültige Antworten; echter Familien-End-to-End-Test mit dem gewählten Zugang.
- Abhängigkeiten: 11. Umfang M; `backend/planner.py`, `backend/setup.py`, `web/settings.js`, `tests/test_planner.py`, `tests/test_settings_api.py`.

### 13. Webversion als Alternative prüfen und integrieren
Technisch umgesetzt und im Browser bis zum geprüften Video nachgewiesen:
Fließtext, Änderungswünsche und Zeichenplan mit Version/Hash validiert importieren.
Ein notwendiges 25-s-Testvideo, keine Webautomation. Eigene Web-KI-Anmeldung und
schwächerer physischer Rechner bleiben externe Abnahme. [Anleitung](../docs/family-paths.md).
Zunächst einen verständlichen Prompt-/Ergebnisimport vorsehen. Automatische Browserbedienung nur bei offiziell erlaubtem und nachgewiesen zuverlässigem Zugang als gesonderte Erweiterung bewerten.
- Abnahme: kopierter Webtext lässt sich validieren, bearbeiten und freigeben; Modellausgaben erhalten keine Systemrechte. Anmeldungen, Captchas und Limits werden nicht durch Fenster-/Kontowechsel umgangen; ein manueller Import wird nicht als vollautomatisch beworben.
- Prüfung: Import-Schema- und Negativtests, Browser-Smoke-Test sowie kompletter Videoablauf aus einem importierten Text; Geräteprüfung auf einem schwächeren Rechner.
- Abhängigkeiten: 12. Umfang M; `backend/schemas.py`, `backend/story.py`, `web/app.js`, `tests/test_story_workflow.py`, `docs/story-workflow.md`. Neue Browserautomation ggf. separat planen, um diese Scheibe klein zu halten.

Abschlussprüfpunkt nach 11–13: Familienablauf mit eigenem Zugang, unveränderten Freigabegates und ohne versteckte Kosten nachgewiesen; Dokumentation, Review und autorisierter Push abschließen.

## Risiken und überprüfbare Grenzen

- Allgemeine perfekte Bildabdeckung ist mit endlichen SVG-Bausteinen nicht zugesichert: Motive schrittweise ausbauen und nicht darstellbare Handlungen melden.
- Geräteempfehlungen belegen keine garantierte Render-/TTS-Geschwindigkeit: reale Laufzeiten messen; keine erfundenen Restzeiten.
- Anbieterzugänge und Gratislimits können wechseln: aktuelle offizielle Konditionen vor der Familienetappe verifizieren; Webseite ist kein automatischer API-Ersatz.
- Echte Qualitätsabnahme umfasst Film- und Hörproben; reine Schema-/Unit-Tests reichen dafür nicht.

## Erhaltene Etappe vom 2026-10-11

1. [x] Stimmenstudio und gezielte Szenenüberarbeitung.
2. [x] Weiche Laufwege, kontinuierliche Richtungswechsel und mitgeführte Requisiten.
3. [x] Bewegungsprobe mit Piper, Sichtprüfung und Qualitätsgate.
4. [x] Diff-Prüfung und Sicherung unter verifizierter Identität.

---

# Bisheriger Implementierungsplan: Qualitätsorientierte Produktionsverfahren

Stand: 2026-09-19

1. [x] Unterbrochenen Sperr- und Idempotenz-Fix abschließen und vollständig prüfen.
2. [x] Antigravity-Automatisierung praktisch nachweisen und MoneyPrinterTurbo quellenbasiert bewerten.
3. [x] Modulare Architekturentscheidung vom Nutzer freigeben lassen (Option A).
4. [x] Provider-Verträge und Produktionsprofil-Dropdown implementieren; Skript, Medien, Stimme und Schnitt getrennt ausweisen. Die Konfiguration wird auf Auftrag und Skriptversion gespeichert; Änderungen erzeugen eine neue Version und entwerten vorhandene Freigaben. Nicht verfügbare Profile und Provider bleiben sichtbar, aber deaktiviert und begründet.
5. [x] Antigravity als bevorzugten schemavalidierten Cloud-Skriptpfad integrieren; Qwen nur als letzten, sichtbar dokumentierten Fallback erhalten. Tatsächlicher Anbieter und Modell werden am Auftrag und an jeder Skriptversion gespeichert und angezeigt; Fehler erzeugen keine Teil- oder Doppelaufträge.
6. [ ] MoneyPrinterTurbo isoliert als optionalen Produktionsadapter pilotieren und mit dem vorhandenen Pfad anhand desselben Auftrags vergleichen. **Teilstand:** Adapter, sichere Grenzen, Providerauswahl, technische Vergleichsansicht und automatisierte Tests sind implementiert; der echte Vergleichslauf bleibt offen, weil MoneyPrinterTurbo lokal nicht installiert/konfiguriert und kein Pexels-Schlüssel vorhanden ist.
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

Prüfung Schritt 4: 79/79 Python-Tests, Python-Compileall, `node --check web/app.js` und `git diff --check` bestanden. Ein isolierter Browser-Smoke-Test bestätigte die Profil- und Providerauswahl, deaktivierte Optionen mit Gründen, responsive Darstellung und eine fehlerfreie Browserkonsole.

Prüfung Schritt 5: Offizielle Antigravity CLI `1.2.7`, Modell `gemini-3.1-pro-high`. Ein echter isolierter Browserablauf mit abgeschaltetem Qwen-Fallback erzeugte Version 1 über Antigravity und überarbeitete sie über Antigravity zu Version 2. Schema, unterschiedliche Inhaltshashes, Anbieter-/Modellprovenienz, Neustartpersistenz und fehlerfreie Browserkonsole wurden geprüft. 93/93 Python-Tests, Compileall, JavaScript-/TypeScript-Syntax, Diff-Prüfung und npm-Audit (0 bekannte Produktionsabhängigkeits-Schwachstellen) bestanden. Fortsetzungspunkt ist Schritt 6; Beginn erst nach erneuter Nutzerfreigabe.

Teilprüfung Schritt 6: Der kontrollierte Pilot tauscht ausschließlich den Schnitt aus und verwendet dasselbe freigegebene Antigravity-Skript, dieselben Pexels-Medien und dieselbe Piper-Stimme. Der abgeschaltete Adapter akzeptiert nur eine feste externe Installation samt eigener Python-Umgebung, startet ausschließlich die offizielle Batch-CLI ohne Webserver, übergibt keine Geheimnisse, prüft Aufgabenkennung und Ausgabepfad, speichert Hash-Provenienz und veröffentlicht nichts. Die Oberfläche zeigt Verfügbarkeit sowie – nur bei identischem Skript-Hash – Remotion- und MoneyPrinterTurbo-Ausgabe nebeneinander. Die öffentliche CLI kann die geprüfte SRT nicht übernehmen; dieser Nachteil wird ausdrücklich angezeigt. 103/103 Python-Tests, Compileall, JavaScript-/TypeScript-Syntax, Diff-Prüfung und npm-Audit (0 bekannte Produktionsabhängigkeits-Schwachstellen) bestanden. Ein Echttest wurde nicht vorgetäuscht: MoneyPrinterTurbo, Docker und `uv` sind auf diesem Rechner nicht vorhanden, und `PEXELS_API_KEY` ist nicht konfiguriert. Kein Fremdcode wurde installiert oder ausgeführt. Fortsetzung innerhalb Schritt 6: separat geprüfte MoneyPrinterTurbo-Laufzeit und Pexels konfigurieren, zuerst Remotion und danach bei unverändertem Skript-Hash den Pilot rendern und redaktionell vergleichen.

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

# Desktop-Ergänzung (15.10.2026)

Vom Nutzer freigegeben: vorhandene UI als Electron-Anwendung unter Windows, Linux und macOS,
ein gemeinsamer Lebenszyklus für Fenster und eigene Pipeline. Doppelklick-Dateien,
bei aktiver Arbeit Abschluss/Abbruch, keine versteckten Restprozesse und nur
Loopback. Anforderungen, Sicherheitsgrenzen und Abnahme sind in
[docs/desktop-app.md](../docs/desktop-app.md) dokumentiert. Die Video- und
Modellproduktion wird wiederverwendet; kein neuer Testfilm für diese Änderung.
