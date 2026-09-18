# Aktueller Auftrag: Qualitätsorientierte Produktionsverfahren

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
