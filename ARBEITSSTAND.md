# Prioritäten für die Strichmännchen-Pipeline

Aktualisiert: 2026-10-14. Nutzerentscheidung: erst die eigene Version fertigstellen; die Familienversion kommt ganz am Ende.

Nummerierte Übersicht: [ENTWICKLUNGSPLAN.md](ENTWICKLUNGSPLAN.md).
Detaillierter Plan: [tasks/plan.md](tasks/plan.md); Checkliste: [tasks/todo.md](tasks/todo.md).
Schritte 1–10 schließen die Originalversion ab. Schritte 11–13 betreffen anschließend die Familienversion.

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
