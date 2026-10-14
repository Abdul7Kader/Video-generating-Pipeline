# Mehrthemenprüfung: Strichmännchen-Pipeline

Stand: 14.10.2026. Technische Prüfung und menschliche Qualitätsfreigabe werden
getrennt dokumentiert. Keine Veröffentlichung, keine neue kostenpflichtige API.
Die vier kurzen fiktionalen Beispiele nutzen den gewählten Antigravity-Zugang,
`gemini-3.8-flash-high` mit hoher Denkstufe und die lokale Piper-Stimme Thorsten.
Eine Tarif-/Restkontingentbestätigung ist damit nicht verbunden.

| Beispiel | Echter Produktionsweg | Ergebnis |
| --- | --- | --- |
| Katzenadoption, 9:16 | Echter KI-Text und KI-Bildplan; danach explizite Testplan-Korrektur für Regal und Abgang, Sprechertext identisch | Version 5 fertig; Katze, Regal, Streicheln und Box mit Weggehen in Filmframes geprüft; 33,75 s |
| Informatik lernen, 16:9 | Ein Prompt → KI-Fließtext → Freigabe → automatische Bildplanung/Render; derselbe unveränderte KI-Plan nach Haltehöhenfix als Version 3 wiederverwendet | Version 3 fertig, 19,11 s; Regal, Buchaufnahme, Lesen und sichtbare Reaktion geprüft. Gesicht frei; ursprüngliche Version 2 erhalten |
| Buch auf Tisch ablegen und durch Ben aufnehmen, 16:9 | Ein Prompt → KI-Fließtext → normale Freigabe/Produktion; Renderer nach Rundungsfix mit gleichem Plan/Sprache wiederholt | Version 2 fertig, 16,09 s; gezielte Ablage-/Aufnahme-/Leseframes zeigen dasselbe Buch und freien Gesichtsausdruck |
| Soziale Geschichte mit einem gemeinsamen Plan, 16:9 | KI-Fließtext, echte UI-Überarbeitung mit Änderungswunsch → erneute Freigabe → automatische Bildplanung/Render | Version 3 fertig, 16,45 s. Früherer doppelter Besitz korrekt blockiert; konkretisierte gemeinsame Lektüre hält einen Besitzer und zeigt beide Figuren mit demselben Dokument |

Die Katzenprobe allein ist kein Beleg einer fehlerfreien automatischen Planung.
Die allgemeinen Änderungen sind im gemeinsam verwendeten Code und durch
Regressionsfälle für unterschiedliche Figuren, Gegenstände und Formate verankert.

## Gemeinsame Korrekturen

- Fehlerhafte Szenendaten erreichen die bestehende begrenzte KI-Korrektur statt
  fälschlich als Anbieterausfall zu enden. Rückmeldung enthält begrenzte Feldregeln,
  keine abgewiesenen Pydantic-Eingaben. Sprechertext und Freigabebindung bleiben strikt.
- Ein allgemeiner Anbieterfehler erhält höchstens einen Wiederholungsversuch;
  Anmeldung, Kontingent, Zeitlimit, ungültiges Protokoll und Tool-Verstöße werden
  dabei nicht erneut angefragt. Kein stiller Anbieter-/Modellwechsel.
- Wörtliche Regale sind ein eigener Zeichengegenstand. Ein Kratzbaum kann ein
  genanntes Holzregal nicht ersetzen. Physisches Verlassen erfordert eine passend
  erzählte sichtbare Laufbewegung; bloßes Tragen genügt nicht.
- Bewegungen übernehmen die tatsächlich erreichte Höhe über Schnitte und wechseln
  beim erzählten Gehen zum gewünschten Bodenniveau. Box und Haltegriff teilen einen
  Kontaktpunkt; gehaltene Gegenstände liegen im Vordergrund. Bücher/Dokumente bleiben
  unter dem Kinn. Neuer Cache-Stand `ink-story-v9`; Katze Version 5 noch `v8`.
- Eine alte Serverinstanz hatte nach Schließen ihres Listeners weiter Aufträge
  abgeholt und mit aktuellem Code konkurriert. Identität, vorhandenes Stopsignal,
  fehlender Listener und fehlende Unterprozesse wurden vor ihrem Beenden geprüft.
  Stop signalisiert dem Worker jetzt sofort, keine weiteren Jobs abzuholen;
  ein Neustart wird bei noch lebender registrierter Vorgängerinstanz abgewiesen.
- Lange Ideen bleiben aufklappbar; Hauptüberschrift nutzt den Skripttitel.
  Auftragskarten und Grid-Spalten begrenzen lange Inhalte statt Seitenüberlauf.
- Ein realer Auftrittsanker wurde wegen eines Float-Rundungsfehlers von
  1,11 × 10⁻¹⁶ s abgewiesen. Nur numerisches Rauschen bis 10⁻⁹ s wird toleriert;
  tatsächlich zu frühe Aktionen und verschwindende Interaktionsziele bleiben gesperrt.

## Prüfungen und Sicherheit

249 Backend-Tests ausgeführt, einer regulär übersprungen; 35 Renderer-Tests,
16 JS-Tests, TypeScript und JS-Syntax bestanden. Der reguläre Skip betrifft einen
zusätzlichen optionalen Doppel-Render, während hier tatsächliche Abnahmeclips laufen.
Negative Fälle prüfen unter anderem Tool-Verstöße, Kontingent-/Anmeldefehler,
Schema-/Textanker-/Besitzregeln, Versionskonflikte, Origin/Host/Setup-Token und
abgewiesene Eingaben ohne Rohdaten in Meldungen.

Nach ausdrücklicher Nutzerfreigabe ausgeführt:
`npm audit --omit=dev --ignore-scripts --registry=https://registry.npmjs.org --json`.
Ergebnis: 0 bekannte Produktionsschwachstellen; keine Paketupdates oder Installationsskripte.
Dies ist keine allgemeine Sicherheitsgarantie oder Prüfung sämtlicher Laufzeitpakete.

Katzenfilm: H.264/AAC; Player lädt ohne Fehler. Der über die UI heruntergeladene
Film hat denselben SHA-256 wie die Produktionsdatei. Audiopeak -1,5 dBFS, Clipping 0,
längste innere Pause 0,15 s. Lernfilm: ebenfalls Qualitätsgate bestanden,
Audiopeak -1,5 dBFS, Clipping 0, längste innere Pause 0,23 s.
Übergabe-/Sozialfilm: Qualitätsgate bestanden, Peak jeweils -1,5 dBFS,
Clipping 0, längste innere Pause jeweils 0,20 s. Alle Filme haben H.264/AAC;
Katze 1080 × 1920, übrige drei 1920 × 1080. Sprachzeiten und erzählte Handlung
wurden mit gezielten Frames verglichen; diese Prüfung ersetzt keine menschliche Hörsichtung.

Der neue Stop-/Startweg wurde nach allen Clips tatsächlich ausgeführt: alter
Workerprozess vollständig beendet, Listener geschlossen, genau eine neue
registrierte Instanz auf 127.0.0.1:8080 gestartet. Die aktuellen Jobs bleiben erhalten.
Browser: echte KI-Überarbeitung, unveränderte Freigabe, Player und Download sowie
Kontenübersicht geprüft. Lange Aufträge erzeugten zunächst Seitenüberlauf; nach
Grid-/Kartenkorrektur passt die Seite in den tatsächlich gemessenen schmalen
Viewport von 845 px. Der erneute 390-px-Override wurde vom Browserwerkzeug nicht
angewendet; eine neue 390-px-Abnahme wird daher nicht behauptet. Frühere 390-px-Prüfung
aus Schritt 9 bleibt ein historischer Nachweis.

Oberfläche und eigene Renderer-Listener bleiben auf Loopback. Keine neuen
Firewallfreigaben, Tunnel, Kontoeinstellungen, Credits oder Zugangsdaten.
Lokale Testmedien und Metadaten liegen ignoriert unter `data/acceptance-10/` und
`data/jobs/`; sie sind weder im Git-Commit noch veröffentlicht.

## Offen

Die technische Mehrthemenprüfung ist abgeschlossen. Die abschließende
Sicht-/Hörfreigabe durch den Nutzer bleibt offen.
Hörgeschmack, vollständige Aussprache, allgemeine Semantik und echtes physikalisches
Verhalten werden nicht aus Audioenergie oder einzelnen Bildern abgeleitet.
Wortzeiten bleiben energiegestützte Schätzungen; Motiv-/Handlungsprüfung ist ein
begrenzter Katalog. Bestehender Katzen-Sprechertext enthält noch eine Wangenbewegung,
die nicht als eigene präzise Animation modelliert ist. Auch das Aufklappen eines
Buchs ist keine eigene Animation; das Buch wird als offen dargestellt. Neue frei erfundene Details
werden in den Schreibanweisungen stärker auf darstellbare Aktionen begrenzt.
Ein echter Free-Tier-Familienkonto-Test erfolgt durch dessen Inhaber. Schritt 12/13
(zusätzlicher kostenloser Adapter bzw. Webimport) ist noch nicht beauftragt/integriert.
