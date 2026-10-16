# Herstellungsmodi und Fehlerdiagnose

Stand 16.10.2026, Etappe B01/B02. Der neue Modus heißt auf Nutzerwunsch **Frame**.

## Bestehende Animation erhalten

Bestehende Aufträge und Skriptversionen erhalten `generation_mode=animated`.
Der vorhandene Text-/Zeichenhash wird dafür nicht verändert. Neue Aufträge speichern
den Modus ausdrücklich; jede Skriptversion übernimmt ihn. Ein gespeicherter Auftrag
kann seinen Modus nicht nachträglich wechseln. Eine abweichende Skriptversion besteht
die Integritäts-/Freigabeprüfung nicht. Es werden keine alten Videos umgerendert.

`frame` ist als zweiter Modus vorbereitet, bleibt aber bis zur Bildanbindung und
Abnahme gesperrt. Frame-Aufrufe starten weder eine Text-KI noch den alten SVG-Renderer.
Die Darstellung/Bewegungen des animierten Renderers bleiben eingefroren; gemeinsame
Sicherheits- und Diagnosekorrekturen gelten weiter. Die zwei Reiter und das Entfernen
überflüssiger Produktionsauswahlen folgen B04, der KI-Bildweg B03.

## Was bei neuen Fehlern sichtbar wird

- Verarbeitungsschritt: Skript, Zeichenplanung, Bilder, Stimme, Schnitt,
  Qualitätsprüfung, Speicherung, Discord oder Veröffentlichung.
- Konkrete Fehlerkategorie, beispielsweise Zeitlimit, Anmeldung, Kontingent,
  fehlende Datei, fehlende Rechte, voller Datenträger oder Prozessabbruch.
- Nächste mögliche Handlung, Auftrags-/Abschnittsbezug soweit vorhanden und eine
  eindeutige Fehler-ID. Veröffentlichung wird nie blind erneut angestoßen.
- **Fehlerdetails kopieren** kopiert nur den öffentlichen Diagnosebericht. Darin
  stehen bei Verfügbarkeit Fehlertyp und betroffene Komponente/Zeile; keine
  vollständigen Dateipfade, Rohantworten, Tokens oder vollständigen Stacktraces.

Die Fehlerkarte bleibt sichtbar, bis sie ausgeblendet oder eine andere Ansicht
geöffnet wird. Beim erneuten Öffnen eines fehlgeschlagenen Auftrags ist sie wieder
verfügbar. Vergangene Fehler werden als **Letzter protokollierter Fehler** kenntlich
gemacht; sie sind kein Beweis für einen aktuell noch bestehenden Fehler.

Während Planung/Rendering liefern die eigenen Worker ihren aktuellen Schritt und,
bei vorhandener Zuordnung, die Abschnitts-ID. Das funktioniert über Dateien im
privaten Operationsordner, ohne zusätzlichen Port oder fremden Browser. Ein
unerwartet beendeter Worker kann dadurch dem zuletzt gemeldeten Schritt zugeordnet
werden. Abbruch durch den Nutzer bleibt ein Abbruchzustand und kein Produktionsfehler.

Neue öffentliche Berichte und begrenzte technische Angaben stehen in der lokalen
Auftragsdatenbank, Tabelle `pipeline_failures`; Aufträge erhalten einen passenden
Verlaufseintrag. Logs nennen dieselbe ID, Schritt, Code und Ausnahmetyp. Meldungen
des Anbieters werden nur zur Klassifikation gelesen und nicht ungeprüft gespeichert
oder zurückgegeben. Falls die Diagnoseablage selbst fehlschlägt, bleiben Fehlerkarte
und Log-ID erhalten; die Ablage wird nicht als erfolgreich behauptet.

Frühere Fehlermeldungen werden nicht nachträglich mit erfundenen Ursachen oder
Fehler-IDs ergänzt. Erwartete Eingabe-/Versionskonflikte behalten ihre vorhandenen
Hinweise. Verbindungs-/Oberflächenfehler vor einer Serverantwort bekommen eine
als lokal erkennbare Diagnose und können naturgemäß nicht im unerreichbaren Server
gespeichert werden. B03–B12 sind weiterhin offen, insbesondere Bildgenerierung,
Bildprüfung und Frame-Erzeugung.

## Nachweise

327 Backend-Tests mit 10 vorgesehenen Plattform-/Optional-Skips und 63 JS-Tests.
Zusätzlich native Windows-Fensterprüfung: sichere Fehlerkarte mit Schritt,
Handlungsempfehlung, Details und ID; eigener Listener ausschließlich 127.0.0.1:8080,
keine eigenen Prozessreste nach Schließen. Testbericht:
`data/desktop/acceptance-normal-1792175752622340900/result.json`.

Negative Fälle: Moduswechsel/Tampering, unberechtigte Frame-Produktion, Timeouts,
Anmeldung, Kontingent, Dateien/Rechte, Speicherplatz, Prozessfehler, ungültige
Ergebnisse, private Zeichenfolgen in Ausnahmen und HTML als Meldungstext.
Ein echter privater Worker überträgt Schritt/ID ohne den Ausnahmeinhalt. Bestehende
Stimmfehler bleiben spezifisch: keine stummen Ersatzvideos oder ungefragten
Anbieterwechsel. Keine neue KI-Inferenz oder Videoerzeugung; nur Prozess-/WAV- und
UI-Fixtures. Keine neuen Pakete, Ports, Konten oder globalen Sicherheitsänderungen.
