# Aktueller Auftrag: Strichmenschen-Videos

Stand: 2026-10-13. Nummern, Abnahmebedingungen, Abhängigkeiten und Prüfungen in `tasks/plan.md`.
Vorhandene Implementierung ist Ausgangspunkt; offen bedeutet hier noch zu prüfen/verbessern und abzunehmen.

Nummerierte Übersicht: [ENTWICKLUNGSPLAN.md](../ENTWICKLUNGSPLAN.md).
Die Familienetappe startet erst nach Abnahme der Originalversion in Schritt 10.

Zwischenstand 1–2: Zugangsanzeige/Modellauswahl und abgesicherter Fließtextablauf
sind implementiert und automatisch getestet. Die echte CLI-/Browserprüfung
bestätigt Anmeldung und fehlendes bisheriges Pro-Modell. Der komplette neue
KI-/Videolauf bleibt bis zur ausdrücklichen Modellwahl offen; Schritte 1 und 2
werden deshalb noch nicht als vollständig abgenommen markiert.

- [x] Installation, Anmeldung, Modellangebot und Verbindungsfehler getrennt anzeigen
- [x] Modell nur ausdrücklich speichern; kein automatischer Anbieterersatz
- [x] Änderungswünsche vor versehentlicher Freigabe schützen
- [x] Bildplan, Freigabe und Renderauftrag atomar speichern; Render-Wiederholung ohne neue KI-Planung
- [ ] Vollständiger Echtlauf mit ausdrücklich gewähltem verfügbarem Skriptmodell

- [ ] 1. Tatsächlichen Skriptanbieterzugang prüfen und verständlich anzeigen
- [ ] 2. Prompt → Fließtext → KI-Überarbeitung → Skriptfreigabe → Produktion abschließen
- [ ] 3. Skriptqualität über unterschiedliche Themen verbessern
- [ ] 4. Zentrale erzählte Figuren, Motive und Handlungen sichtbar abdecken
- [ ] Prüfpunkt 1–4: echter Skriptablauf und Bildplan, einschließlich Thema ohne Katze
- [ ] 5. Handkontakt und Gegenstandsinteraktion verbessern
- [ ] 6. Bewegungstempo mit Erzählung synchronisieren
- [ ] 7. Figuren- und Gegenstandskontinuität zwischen Bildabschnitten sichern
- [ ] Prüfpunkt 5–7: Filmproben für Kontakt, Aktionstakte und Kontinuität
- [ ] 8. Stimmqualität und Sprachfluss fertigstellen
- [ ] 9. Verständliche UI, Einrichtung und ehrliche Fortschrittsanzeige abschließen
- [ ] 10. Originalversion mit mehreren Videos abnehmen, dokumentieren, prüfen und sichern/pushen
- [ ] Prüfpunkt 8–10: Originalversion abgeschlossen; Grenzen und Prüfergebnisse dokumentiert

Erst nach Abschluss von 10:

- [ ] 11. Konten und offiziell unterstützte kostenlose Anmeldewege unter Einstellungen erklären
- [ ] 12. Kostenlosen automatischen Skriptweg mit eigenem Familienzugang ergänzen
- [ ] 13. Webversion als validierten Prompt-/Ergebnisimport ergänzen; zulässige Automation gesondert bewerten
- [ ] Abschlussprüfpunkt: echter Familienablauf ohne Pro-Pflicht oder versteckte Kosten; Review und autorisierter Push

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
