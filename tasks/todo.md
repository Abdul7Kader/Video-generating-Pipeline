# Aktueller Auftrag: Strichmenschen-Videos

Stand: 2026-10-14. Nummern, Abnahmebedingungen, Abhängigkeiten und Prüfungen in `tasks/plan.md`.
Vorhandene Implementierung ist Ausgangspunkt; offen bedeutet hier noch zu prüfen/verbessern und abzunehmen.

Nummerierte Übersicht: [ENTWICKLUNGSPLAN.md](../ENTWICKLUNGSPLAN.md).
Die Familienetappe startet erst nach Abnahme der Originalversion in Schritt 10.

Stand 2–3: Implementierung und automatisierte Prüfung abgeschlossen. Schritt 2
bleibt nach Bildplanung/Renderfehlern beim Fließtext; Bildidee und sachliche Hinweise
können separat überarbeitet werden. Schritt 3 prüft Stimme/Zeitbudget, Textformat,
Wiederholungen und Platzhalter mit höchstens einem zusätzlichen Korrekturversuch.
209 Backend-Tests ausgeführt, ein optionaler echter Rendertest ausgelassen.

Stand 4–5: technisch implementiert und geprüft. Begrenzte Motiv-/Aktionsprüfung
für Tieradoption, Lesen, Tippen und Telefonhandlungen; fehlende Ziele/Aktionen
stoppen die Freigabe. Gemeinsame Hand-/Objektkontakte, dauerhafte Ablage auf Tisch
oder Koordinaten, Besitzwechsel und Tierkopfkontakt. 224 Backend-Tests ausgeführt,
ein regulärer Skip; 28 Renderer-Tests, TypeScript/Syntax und zehn echte PNG-
Standbilder in 16:9/9:16 geprüft. Keine Video-/Audio-/KI-Erzeugung oder neuen
Produktionsaufträge. Render-HTTP-Server auf Loopback begrenzt. Live-/Filmabnahme
und allgemeine semantische Bildbewertung bleiben offen.

Stand 6–7: technisch implementiert. Aktionen enden vor dem nächsten Sprachanker;
Gesten beruhigen sich nach ihrem Abschnitt. Stabile Figuren-/Objektmerkmale,
Besitz, Ablage- und Ruheposen sowie tatsächliche Endpositionen im selben Schauplatz
werden über Schnitte erhalten. 234 Backend-Tests (ein regulärer Skip), 31 Renderer-
Tests und acht echte Schnitt-Standbilder in 16:9/9:16 geprüft. Kein Testvideo oder
echter Sprach-/KI-Aufruf. Wortzeiten bleiben geschätzt; Film-/Audioabnahme folgt später.

Nutzervorgabe: keine routinemäßigen Testvideos in der UI. Echte KI-/Video- und
redaktionelle Abnahme durch den Nutzer bzw. am Ende in Schritt 10; jetzt nur eine
Videoprobe, wenn eine konkrete Änderung sie zwingend braucht. Die technische
Erledigung von 2–7 ist keine Behauptung einer bestandenen Live-/Qualitätsabnahme.

- [x] Installation, Anmeldung, Modellangebot und Verbindungsfehler getrennt anzeigen
- [x] Modell nur ausdrücklich speichern; kein automatischer Anbieterersatz
- [x] Bestätigtes Gemini 3.8 Flash (High) lokal als aktives Skriptmodell speichern und zurücklesen
- [x] Änderungswünsche vor versehentlicher Freigabe schützen
- [x] Bildplan, Freigabe und Renderauftrag atomar speichern; Render-Wiederholung ohne neue KI-Planung
- [x] Vollständiger Echtlauf mit ausdrücklich gewähltem verfügbarem Skriptmodell; native Lern-/Übergabe-/Sozialplanung und Film geprüft

- [x] 1. Tatsächlichen Skriptanbieterzugang prüfen und verständlich anzeigen; Anmeldung/Modellangebot und echte High-Skripte nachgewiesen
- [x] 2. Fließtext-/Überarbeitungs-/Freigabeablauf technisch abschließen und automatisiert prüfen
- [x] 3. Skriptqualität durch Kontext, Wortbudget und Textprüfungen verbessern; Themen-/Längenfixtures prüfen
- [x] 4. Begrenzte Motivgruppe und zentrale erkannte Handlungen sichtbar abdecken, automatisiert prüfen
- [x] Prüfpunkt 1–4 technisch: Text-/Bildplanverträge einschließlich Thema ohne Katze prüfen; echter Lauf bleibt später vorgemerkt
- [x] 5. Handkontakt, dauerhafte Ablage und Gegenstandsbesitz verbessern; Tests und Standbilder prüfen
- [x] 6. Aktionen auf Sprachfenster begrenzen, Gesten beruhigen und Bewegungsanker prüfen
- [x] 7. Figuren-/Gegenstandsidentität, Besitz, Ablage und Ruheposen über Schnitte sichern
- [x] Prüfpunkt 5–7 technisch: Kontakt, Aktionstakte und Schnittzustände testen; Film-/Audioabnahme bleibt später
- [x] 8. Stimmqualität und Sprachfluss technisch verbessern; zwei kurze echte Hörproben, Aussprache-/Geschmacksabnahme in 10
- [x] 9. Verständliche UI, aktive Einrichtung und ehrliche Fortschrittsanzeige; Browser normal/390 px geprüft
- [x] 10. Technische Mehrthemenprüfung, allgemeine Fixes, Dokumentation und Sicherung/Push; menschliche Sicht-/Hörfreigabe bleibt offen
- [ ] Prüfpunkt 8–10: Originalversion abgeschlossen; Grenzen und Prüfergebnisse dokumentiert

Erst nach Abschluss von 10:

Stand 10–11: vier kurze Filme geprüft; 249 Backend-Tests (1 Skip), 35 Renderer-
und 16 JS-Tests, TypeScript, UI/Download und npm-Produktionsaudit (0 bekannte
Schwachstellen nach Nutzerfreigabe). [Abnahmebericht](../docs/acceptance-10.md).
Schritt 11 als Informations-/Anmeldebereich auf ausdrücklichen Auftrag umgesetzt;
12/13 sind technisch umgesetzt; die gesonderte externe Familienabnahme bleibt offen.
264 Backend-/18 UI-Tests, echter Antigravity-Aufruf mit Credit-Sperre und ein
Webimport-Video (25,02 s) geprüft. [Anleitung/Nachweise](../docs/family-paths.md).

- [x] 11. Konten und offiziell unterstützte kostenlose Anmeldewege unter Einstellungen erklären; eigener Familienkonto-Test bleibt offen
- [x] 12. Kostenlos unterstützten automatischen Antigravity-Weg mit Credit-Sperre technisch ergänzen; eigener Familienkonto-Test gesondert offen
- [x] 13. Vollständigen manuellen Webimport für Text/Überarbeitung/Zeichnung ergänzen und bis zum Video prüfen; keine Browserautomation
- [ ] Externer Abschlussprüfpunkt: echter Familienablauf mit eigenem Gratiszugang; technische Umsetzung, Review und autorisierter Push abgeschlossen

Erhaltene erledigte Etappe:

- [x] Stimmenstudio und gezielte Szenenüberarbeitung
- [x] Weiches Anlaufen/Abbremsen und Richtungswechsel mit getragenen Gegenständen
- [x] Regressionstests und reale Full-HD-Probe mit lokaler Stimme

Maßgeblicher Stand: `STATUS.md` und `tasks/plan.md`. Die älteren Aufgaben bleiben
als eingefrorener Verlauf erhalten und stellen keinen aktiven Ausbauauftrag dar.

---

# Bisheriger Auftrag: Qualitätsorientierte Produktionsverfahren

- [x] Unterbrochenen Sperr-/Idempotenz-Fix abschließen
- [x] 69/69 Tests sowie Syntax- und Diff-Prüfungen bestehen
- [x] Antigravity-Headless-Automatisierung mit strukturiertem JSON real nachweisen
- [x] MoneyPrinterTurbo ohne Installation quellenbasiert bewerten
- [ ] Nutzerfreigabe für die dokumentierte Architekturentscheidung einholen
- [ ] Provider-Verträge und Produktionsprofil-Dropdown implementieren
- [ ] Antigravity-Skriptadapter sicher und testgetrieben integrieren
- [ ] MoneyPrinterTurbo-Adapter als isolierten Pilot implementieren und qualitätsbasiert vergleichen
- [ ] End-to-End-Freigaben prüfen, Abschluss dokumentieren, committen und pushen

Fortsetzungspunkt: Schritt 3, Architekturfreigabe. Vor der Freigabe keine Umsetzung von Schritt 4.

---

# Bisherige Aufgaben

- [x] Offizielle Produktgrenzen und unterstützte Wege prüfen
- [x] Spezifikation und Phasenplan erstellen
- [x] Tests für externen Videoimport ergänzen
- [x] Importmodul und ffprobe-Prüfung implementieren
- [x] Datenbankworkflow für importiertes Video implementieren
- [x] API-Endpunkt implementieren
- [x] Importoberfläche implementieren
- [x] Vollständige Tests und Browser-Smoke-Test ausführen
- [x] `STATUS.md` mit Prüfergebnissen aktualisieren
- [ ] Phase 2: NotebookLM-Audio/Podcast
- [ ] Phase 3: szenenweise Gemini-Bilder/-Videos
- [ ] Phase 4: optionale, kostenkontrollierte Gemini-Medien-APIs

## Multi-Channel

- [x] Offizielle Veröffentlichungswege und Plattformgrenzen prüfen
- [x] Multi-Channel-Spezifikation und API-Vertrag erstellen
- [x] Plattformkatalog und Mehrfachziel-Schema implementieren
- [x] Zielstatus und atomaren Dispatcher implementieren
- [x] YouTube in den Dispatcher übernehmen
- [x] Mastodon-Adapter implementieren
- [x] Mehrfachauswahl und Zielstatus in der UI implementieren
- [x] Tests, Migration und Browser-Smoke-Test ausführen
- [ ] Qualitätsvarianten und Podcast-RSS als nächste Scheibe implementieren

## Gemini-CLI-Profilpool

- [x] Offizielle Anmeldung, Headless-Modus, Profilisolation und Tool-Policies prüfen
- [x] Qwen3.5 9B Q8 als lokalen Standard binden und Live-Health prüfen
- [x] Offizielle Gemini CLI installieren und Version prüfen
- [x] Getrennte Profilverzeichnisse mit restriktiven ACLs und Deny-All-Policy einrichten
- [x] Tool-losen CLI-Runner mit Fehlerklassen und Cooldown testgetrieben implementieren
- [x] Fünfstufige persistente, idempotente Skripterstellung implementieren
- [x] Profil- und Schrittstatus ohne Secrets in API und UI anzeigen
- [ ] Erstes Profil interaktiv anmelden und real vollständig testen
- [ ] Zweites Profil interaktiv anmelden; Ausfall/Fortsetzung nachweisen
- [ ] Gesamttests, Secret-Prüfung, Commit und Push ausführen

- [ ] Externe Abnahme 12/13: eigenes kostenloses Familienkonto, ausgewählte Web-KI und schwächerer physischer Rechner
