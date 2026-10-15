# Prioritäten für die Strichmännchen-Pipeline

Aktualisiert: 2026-10-15. Nutzerentscheidung: erst die eigene Version fertigstellen; die Familienversion kommt ganz am Ende.

Nummerierte Übersicht: [ENTWICKLUNGSPLAN.md](ENTWICKLUNGSPLAN.md).
Detaillierter Plan: [tasks/plan.md](tasks/plan.md); Checkliste: [tasks/todo.md](tasks/todo.md).
Schritte 1–10 schließen die Originalversion ab. Schritte 11–13 betreffen anschließend die Familienversion.

## Aktueller Auftrag vom 16.10.2026: Abbruch und Discord-Verteilung

Auftrag und Grenzen: [docs/review-distribution.md](docs/review-distribution.md).
Desktopabschluss ist lokal als e33143e gesichert; Push weiterhin am Ende.
Abbruch je Auftrag für Zeichenplanung und Rendern implementiert: separater nativer
Worker, eigene Prozessgruppe, sichtbare Zustände, Abbruchknopf schon bei Planung,
Schutz gegen verspätete Erfolge/Fehler. Keine Dateien automatisch gelöscht.
Windows-Renderer akzeptiert ausschließlich native lokale Chrome-/Edge-Dateien;
WSL, UNC-Pfade und bestehende Debug-Endpunkte sind ausgeschlossen.
292 Backend-Tests (10 Skips) und 39 gezielte Workflow-/Abbruchtests bestanden;
zusätzliche Protokoll-/Browser-/UI-Negativtests bestanden. Ein alter Provider-Mock
hatte bei der Workerumstellung unbeabsichtigt eine echte KI-Anfrage gestartet;
sofort nur den eigenen Prüflauf gestoppt, Mockgrenze korrigiert. Kein Testfilm.
Der Nutzer hat den laufenden Feuer-Versuch ausdrücklich abgebrochen: eigener
Desktopwächter beendet, acht eigene Prozesse entfernt, null Überreste; Auftrag
 a5860ef0-a674-5cc2-ab8d-c6d8006ca54b als cancelled gespeichert. Dateien erhalten.
Nächster Schritt: geschützte Kontoeinrichtung/Videoordner, danach Discord-Gateway,
Freigabe-/Änderungs-/Ablehnungsablauf und offizielle soziale Zieladapter. Keine
Anmeldung oder echte externe Veröffentlichung ohne eingerichtete Zielkonten.

## Aktuelle Ergänzung: Desktop für Windows, Linux und macOS

Doppelklick startet UI und eigene Pipeline; Fenster schließen oder die passende
Stoppdatei beendet die eigenen Prozesse. Bei laufender Arbeit: weiterarbeiten,
nach Abschluss beenden oder abbrechen. Vorhandene Texte, Freigaben, Konten und
Videos bleiben erhalten; abgebrochene Renderings starten nicht automatisch neu.

Die Verwaltung ist nativ zugeschnitten: Windows Job Objects; Linux eine temporäre
systemd-Benutzereinheit plus Kernel-Unterprozessüberwachung für Chromiums getrennte
Portalgruppen; macOS eine temporäre launchd-Überwachung mit registrierten
Prozessgruppen. Python, Electron und Profile liegen getrennt nach System/Architektur.
Mac startet erst nach bestandener Prozessprüfung auf dem Zielgerät. Keine dauerhaft
installierten Hintergrunddienste, Autostarts, Firewallfreigaben oder Debugports.
Backend ausschließlich 127.0.0.1; fremde laufende Dienste werden nicht übernommen.

Geprüft: Windows-Backend-Suite (290 Tests, 10 plattformbedingte/optionale Skips), 58 JS-Tests; acht echte Linux-Prozesstests.
Echte Windows- und Linux-Fenster: Zweitstart, Schließen, Abbruch, Electron-Absturz,
Sandbox, Host-/Origin-Sperre und ausschließlich lokale Endpunkte. Keine erfassten
eigenen Prozessreste. Windows-Oberfläche auch als Bild geprüft. Neuer Desktop-
npm-Lockfile: Audit ohne bekannte Befunde. Kein Film und kein KI-Auftrag erzeugt.

Offen: native Mac-/Apple-Silicon-Abnahme, zweite schwache Hardware und signierte
Installationspakete. Dies ist ein startbarer Projektordner. Anleitung und genaue
Grenzen: [docs/desktop-app.md](docs/desktop-app.md).

## Vorherige Etappe: Schritte 12 und 13

Technisch umgesetzt: automatischer Antigravity-Zugang mit eigenem berechtigtem
Google-Konto, Credit-Sperre vor jedem Aufruf und begrenztem Herstellerkontingent;
Pro ist optional. Der aktuelle Google-Consumer-Abkündigungshinweis hat Vorrang vor
widersprechenden allgemeinen Gemini-CLI-Anleitungen. Gemini CLI wird nicht als
Familien-Gratiszugang angeboten. Keine Tarif-/Kontoschalter überschrieben.

Webimport vollständig: Prompt und Antwort für Fließtext, KI-Änderungswünsche und
Zeichenplan übertragen. Textfreigabe bleibt an Version/Hash gebunden; Bildplan und
Renderanspruch atomar gespeichert. Wörter bleiben unverändert. Schema-, Motiv-,
Sprachanker-, Medien- und Kontinuitätsgates erhalten; keine Szenen-Einzelfreigabe.
Neue Scriptoption unter Einstellungen, klare manuelle UI und Fortschritt während
lokaler Prüfungen. Keine Browserautomation, keine Kontingentumgehung.

Sicherheit: Zusatzcredits an/nicht prüfbar blockieren die CLI; keine fremden
API-/Agentenvariablen vererbt. Loopback-, Origin- und Hostprüfung jetzt auf der
gesamten Pipeline, auch Lese-/Importendpunkten. Bounded JSON, kein Modellcode,
keine fremden Medienpfade, keine neuen Ports/Firewallregeln oder Pakete.

Geprüft: Provider-/Negativtests, 264 Backend-Tests (1 regulärer Skip), 18 UI-Tests,
Syntax/Diff; danach 21 gezielte Import-/Qwen- und 6 Startertests bestanden. Echter Antigravity-Test mit dem bestätigten Flash-High-Modell und
neuem Umgebungsfilter erfolgreich. Genau ein notwendiger Webimport-Film: Auftrag
`d8bdb271-6a21-51bb-8083-f941dad22f27`, v3, 25,02 s, Full HD, H.264/AAC,
Qualitätsgate bestanden, Clipping 0, längste innere Pause 0,24 s. Browserimport,
Überarbeitung, Fehlermeldungen und Player ohne Konsolenfehler geprüft. Testfixture,
keine behauptete neue Web-KI-/Gratis-Familienkontoantwort.

Offen bleibt die externe Abnahme mit dem eigenen kostenlosen Familienkonto,
einer ausgewählten Web-KI und einem schwächeren physischen Rechner. Der vorhandene
Nutzerzugang bestätigt keinen Kontotarif. [Einrichtung, Quellen, API und Nachweise](docs/family-paths.md).
Code/Dokumentation geprüft und unter Abdul7Kader gesichert; Branch
`codex/gemini-notebooklm-integration`. Laufende UI auf 127.0.0.1:8080,
ursprünglicher Antigravity-/Piper-Standard erhalten. Keine weiteren Testvideos.

## Vorherige Etappe: Schritt 10 und 11

Schritt 11 ist als Kontenübersicht unter Einstellungen implementiert: reguläre
Google-Anmeldung, begrenzter kostenloser Einstieg, optionale Abos, Modellprüfung
und lokale Alternativen. Quellen und Grenzen: [docs/accounts.md](docs/accounts.md).
Ein eigener Free-Tier-Familienkonto-Test und die Adapter von 12/13 bleiben offen.

Schritt 10 technisch abgeschlossen: 249 Backend-Tests (1 regulärer Skip), 35 Renderer-Tests, 16 JS-Tests
und TypeScript bestanden. Der npm-Produktionsaudit wurde nach ausdrücklicher
Nutzerfreigabe erneut ausgeführt: 0 bekannte Schwachstellen. Keine Pakete geändert.
Allgemeine Fixes betreffen Zeichenplan-Korrekturen, wörtliche Regale, erzählte
Abgänge, Höhenwechsel, Boxgriff, Gesichtsfreiraum beim Lesen und Vordergrundzeichnung (`ink-story-v9`).
Eine alte, bereits gestoppte Serverinstanz hatte weiterhin Jobs angenommen.
Sie wurde nach Identitäts-/Leerlaufprüfung beendet; Start und Stop verhindern
nun Weiterarbeiten einer herunterfahrenden Instanz bzw. vorzeitigen Neustart.

Echte Mehrthemen-Prüfung mit dem bestätigten Antigravity-Modell High und
Piper abgeschlossen: Katze Version 5 (33,75 s), Lernen Version 3 (19,11 s),
Buchübergabe Version 2 (16,09 s), soziale Geschichte Version 3 (16,45 s).
Alle Medien-/Audiogates bestanden; gezielte Filmframes und UI geprüft.
Gemeinsame Lektüre hält nur einen Dokumentbesitzer. Ein Rundungsfehler am gesprochenen
Auftritt wurde allgemein korrigiert. Stop/Start mit vollständigem Prozessende geprüft.
Die Katzenprobe verwendet den echten
KI-Plan mit explizit dokumentierter Testplan-Korrektur; sie beweist allein keine
automatische Planungsgarantie. Menschliche Hör-/Filmabnahme bleibt offen.
Nachweise lokal/ignoriert: `data/acceptance-10/`; keine Veröffentlichung.
Bericht: [docs/acceptance-10.md](docs/acceptance-10.md). Nächster Prüfpunkt ist
die menschliche Sicht-/Hörfreigabe; Schritt 12/13 bleibt ein späterer Auftrag.
Git-Branch: `codex/gemini-notebooklm-integration`; verifizierter Autor/Committer
Abdul7Kader mit GitHub-Noreply-Adresse. Geprüfte Änderungen werden zum Abschluss gepusht.

## Historischer Stand bis Schritt 9

Dokumentationsstand: Schritte 2–9 technisch umgesetzt; echte Hör-/Filmabnahme bleibt Schritt 10. Schritt 6 begrenzt Aktionen auf verfügbare Sprachfenster und lässt Gesten auslaufen; Laufwege mit altem `end_x` bekommen einen erkannten gesprochenen Bewegungsanker. Schritt 7 prüft wiederkehrende Figuren-/Objektmerkmale, übergibt Besitz über stabile Gegenstands-IDs bzw. eindeutige Typen und erhält Ablage- und Ruhe-/Schlafzustände. Der Renderer übernimmt tatsächliche Endpositionen im selben Schauplatz einschließlich Haltegriff und Bewegungsphase. Renderer-Version `ink-story-v6` verhindert alte Asset-Zuordnungen.

Prüfstand 6–7: 234 Backend-Tests ausgeführt, einer regulär übersprungen; 31 Renderer-Tests, TypeScript, Backend-Syntax und Diff-Prüfung. Acht PNG-Standbilder vor/nach Schnitten aus vier Abschnitten in `data/continuity-proof/` (16:9/9:16) visuell kontrolliert. Früherer Stand 4–5: 224 Backend-/28 Renderer-Tests und zehn PNGs unter `data/contact-proof/`. Kein Testvideo, kein echtes Audio, keine KI-Inferenz und kein neuer Produktionsauftrag. Redaktionelle und echte Videoabnahme bleiben offen.

Grenzen: Sprachzeiten bleiben energiegestützte Wortschätzungen. Stabile Merkmale werden strikt geprüft; absichtliche Kleidungs-/Objekttypwechsel werden aktuell abgewiesen. Ohne Objekt-ID wird ein eindeutiger tragbarer Typ als dasselbe Objekt interpretiert; mehrere gleichartige tragbare Objekte brauchen IDs. Gleicher Schauplatz erhält Positionen, Szenen-/Auftrittswechsel erlauben neue Aufstellung. Das ist keine allgemeine semantische Ursachenprüfung.

Sicherheit: neue Ablagefelder sind begrenzt und serverseitig geprüft; ungültige, unsichtbare und doppelt gehaltene Ziele werden abgewiesen. Die temporären HTTP-Server der Renderbibliothek werden ausschließlich im Renderprozess auf Loopback begrenzt (`renderer/loopback.mjs`), mit echtem Listener-Test und Standbildrendering geprüft. Keine Firewall-, System- oder Kontoeinstellungen verändert.

**Aktuelle Testregel:** Keine neuen Testvideos in der UI als Routine erzeugen.
Der Nutzer testet Videos selbst bzw. am Ende. Nur bei zwingendem Prüfbedarf einer
konkreten Änderung ein Video erzeugen. In Schritt 8–9 nur zwei kurze lokale Hörproben; keine Videos,
keine Skript-KI-Inferenz und keine neuen Aufträge in der Produktionsdatenbank.

Echte Zugangskontrolle: installierte Antigravity-CLI 1.3.4, Anmeldung bestätigt;
`gemini-3.1-pro-high` fehlt im aktuellen Modellangebot. Angeboten werden
`gemini-3.8-flash-high`, `gemini-3.8-flash-medium` und `gemini-3.8-flash-low`.
Der Nutzer hat Gemini 3.8 Flash (High) bestätigt. Als Skriptmodell lokal gespeichert
und per Einstellungs-API zurückgelesen: `gemini-3.8-flash-high` / Antigravity.
Bestehende Stimmen- und Hardwareauswahl erhalten; keine Anbieter-Credit-Einstellungen
oder Tarife geändert. Das Speichern führte keinen Generierungsauftrag aus.
Nächste Entwicklungsetappe: Schritt 10, gemeinsame Hör-/Filmabnahme mit dem Nutzer. Die Bildprüfung ist ein begrenzter deutscher/
englischer Motivkatalog, keine allgemeine semantische Abnahme. Echter KI-/Videolauf
bleibt für die spätere Nutzerabnahme vorgemerkt und blockiert die Implementierung nicht.

Prüfstand 8–9: 238 Backend-Tests (1 übersprungen), 16 JS-Tests, JS-Syntax und
Browser normal/390 px geprüft. Zwei lokale Proben: Piper 15,44 s Erzeugung/3,153 s
Audio, Qwen 211,50 s/3,67 s. Keine übersteuerten Samples, längste innere Pausen
0,08/0,10 s. Messdaten `data/voice-quality-proof.json`, UI-Bilder
`data/ui-quality-proof/`; lokale Artefakte werden nicht eingecheckt. Keine subjektive
Hörabnahme oder universelle Ausspracheprüfung behauptet. Gewählte globale Konfiguration
weiter Antigravity `gemini-3.8-flash-high` / Piper. Host-Listener bleibt 127.0.0.1:8080;
keine Installationen, Firewalländerungen oder neuen Zugangsdaten.

## Aktueller Schwerpunkt

- Die bestehenden Originalfunktionen für die eigene Nutzung fertigstellen: Idee → durchgehender Sprechertext → KI-Überarbeitung → Skriptfreigabe → automatische Bildplanung und Videoerzeugung.
- Qualität von Skripten, sichtbarer Handlung, Strichmännchen-Bewegungen und Erzählerstimme verbessern; die UI verständlich machen.
- Andere Videoarten bleiben ausgeblendet. Die Familienversion erweitert den aktuellen Auftrag vorerst nicht.
- Das letzte in der Hauptdatenbank gespeicherte Katzenadoptionsvideo verwendete Antigravity mit `gemini-3.1-pro-high`, lokale Qwen-TTS und den bestehenden SVG-/Remotion-/FFmpeg-Renderer. Der gespeicherte Modellnachweis enthält keinen Abrechnungstarif.

## Spätere Etappe: Familie ohne Pro-Abos

Erst nach Fertigstellung der Originalfunktionen bearbeiten:

- Unter **Einstellungen → Konten und Anmeldungen** klar erklären, welcher Anbieter welchen Zugang benötigt: normales Konto, kostenloses Kontingent, optionales Abo oder API-Zugang. Offizielle Anmeldung verlinken und Verbindungsstatus prüfen; Passwörter und Tokens nicht im Klartext anzeigen oder versionieren.
- Kostenlose Zugänge mit einem normalen Google-Konto prüfen, einschließlich der dann offiziell unterstützten Gemini-/Antigravity-CLI- und API-Optionen. Ein Pro-Abo nicht pauschal als Voraussetzung darstellen; aktuelle Modellverfügbarkeit, Limits und Konditionen vor Implementierung verifizieren.
- Eine Nutzung von LLM-Webversionen als weitere Alternative prüfen: manueller Prompt-/Ergebnisimport und, soweit offiziell erlaubt und zuverlässig, Browserintegration. Keine Anmeldung oder Kontingentgrenzen durch neue Fenster umgehen.
- Die Pipeline soll auf dem Familienrechner ohne Codex oder einen steuernden Coding-Agenten funktionieren. Lokale Stimmen und Videoerzeugung bleiben nutzbar; KI-Zugänge sind ausdrücklich auswählbar.
- Keine automatische Aktivierung kostenpflichtiger Tarife oder Credits. Bei fehlendem Zugang oder ausgeschöpftem Kontingent verständlich informieren, Arbeit behalten und auf einen verfügbaren, ausdrücklich gewählten Weg warten.

Für diese spätere Etappe wurden mit dieser Notiz keine neuen Anmeldeoptionen oder Browseradapter implementiert und keine Kontoeinstellungen verändert.
