# Prioritäten für die Strichmännchen-Pipeline

Aktualisiert: 2026-10-13. Nutzerentscheidung: erst die eigene Version fertigstellen; die Familienversion kommt ganz am Ende.

Nummerierte Übersicht: [ENTWICKLUNGSPLAN.md](ENTWICKLUNGSPLAN.md).
Detaillierter Plan: [tasks/plan.md](tasks/plan.md); Checkliste: [tasks/todo.md](tasks/todo.md).
Schritte 1–10 schließen die Originalversion ab. Schritte 11–13 betreffen anschließend die Familienversion.

Dokumentationsstand: Übersicht, Detailplan, Checkliste, README und STATUS sind auf diese Reihenfolge abgestimmt. Bearbeitung von 1 und 2 begonnen: Zugangsanzeige und ausdrücklich bestätigte Modellauswahl sowie abgesicherter Text-/Freigabeablauf sind implementiert und getestet. Noch keine vollständige Abnahme: Der neue KI-/Videolauf wartet auf die Modellwahl. Die übrigen Schritte bleiben geplant.

Echte Zugangskontrolle: installierte Antigravity-CLI 1.3.4, Anmeldung bestätigt;
`gemini-3.1-pro-high` fehlt im aktuellen Modellangebot. Angeboten werden
`gemini-3.8-flash-high`, `gemini-3.8-flash-medium` und `gemini-3.8-flash-low`.
Die Frage nach Gemini 3.8 Flash (High) als Testmodell ist noch offen. Keine
gespeicherten Geräteeinstellungen oder Anbieter-Credit-Einstellungen geändert.
Nächster Schritt: ausdrücklich gewähltes Modell verwenden und einen echten
Fließtext-/Überarbeitungs-/Freigabe-/Videoablauf prüfen.

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
