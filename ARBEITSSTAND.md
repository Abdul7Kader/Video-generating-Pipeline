# Prioritäten für die Strichmännchen-Pipeline

Aktualisiert: 2026-10-14. Nutzerentscheidung: erst die eigene Version fertigstellen; die Familienversion kommt ganz am Ende.

Nummerierte Übersicht: [ENTWICKLUNGSPLAN.md](ENTWICKLUNGSPLAN.md).
Detaillierter Plan: [tasks/plan.md](tasks/plan.md); Checkliste: [tasks/todo.md](tasks/todo.md).
Schritte 1–10 schließen die Originalversion ab. Schritte 11–13 betreffen anschließend die Familienversion.

Dokumentationsstand: Schritte 2–5 technisch abgeschlossen. Schritt 4 prüft neben Tieren auch Bücher, Telefone, Laptops, Dokumente und Futter sowie ausdrücklich erkannte Lese-/Tipp-/Greif-/Trage-/Ablage-/Streichelaktionen mit passenden Textankern und Zielen. Bekannte nicht unterstützte Motive werden vor der Bild-KI benannt. Schritt 5 verbindet Hand und Gegenstand über einen gemeinsamen Kontaktpunkt, unterstützt dauerhafte Ablagekoordinaten oder Tischflächen und prüft Besitzwechsel. Sitzt die Katze, sind Kopf und Körper nun verbunden. Renderer-Version `ink-story-v5` verhindert alte Asset-Zuordnungen.

Prüfstand: 224 Backend-Tests ausgeführt, einer regulär übersprungen; 28 Renderer-Tests, TypeScript, Backend-Syntax und Diff-Prüfung. Zehn lokale PNG-Standbilder in `data/contact-proof/` für Greifen, Lesen, Ablegen und Streicheln in 16:9/9:16 erzeugt und visuell kontrolliert. Kein Testvideo, kein Audio, keine echte KI-Anfrage und kein neuer Produktionsauftrag. Redaktionelle und echte Videoabnahme bleiben offen.

Sicherheit: neue Ablagefelder sind begrenzt und serverseitig geprüft; ungültige, unsichtbare und doppelt gehaltene Ziele werden abgewiesen. Die temporären HTTP-Server der Renderbibliothek werden ausschließlich im Renderprozess auf Loopback begrenzt (`renderer/loopback.mjs`), mit echtem Listener-Test und Standbildrendering geprüft. Keine Firewall-, System- oder Kontoeinstellungen verändert.

**Aktuelle Testregel:** Keine neuen Testvideos in der UI als Routine erzeugen.
Der Nutzer testet Videos selbst bzw. am Ende. Nur bei zwingendem Prüfbedarf einer
konkreten Änderung ein Video erzeugen. In dieser Etappe keine Video-/Audioerzeugung,
keine echten KI-Anfragen und keine neuen Aufträge in der Produktionsdatenbank.

Echte Zugangskontrolle: installierte Antigravity-CLI 1.3.4, Anmeldung bestätigt;
`gemini-3.1-pro-high` fehlt im aktuellen Modellangebot. Angeboten werden
`gemini-3.8-flash-high`, `gemini-3.8-flash-medium` und `gemini-3.8-flash-low`.
Der Nutzer hat Gemini 3.8 Flash (High) bestätigt. Als Skriptmodell lokal gespeichert
und per Einstellungs-API zurückgelesen: `gemini-3.8-flash-high` / Antigravity.
Bestehende Stimmen- und Hardwareauswahl erhalten; keine Anbieter-Credit-Einstellungen
oder Tarife geändert. Das Speichern führte keinen Generierungsauftrag aus.
Nächste Entwicklungsetappe: Schritt 6, Bewegungen mit der Erzählung takten, danach
Schritt 7, Kontinuität über Schnitte. Die Bildprüfung ist ein begrenzter deutscher/
englischer Motivkatalog, keine allgemeine semantische Abnahme. Echter KI-/Videolauf
bleibt für die spätere Nutzerabnahme vorgemerkt und blockiert die Implementierung nicht.

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
