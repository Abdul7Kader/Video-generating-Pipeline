# Frame · lange Sprechertexte und inhaltliche Bildplanung

Aktualisierung 17.10.2026: Frame-Medienpipeline B07–B11 ist inzwischen eingebaut.
Echte Bildansicht, positiver/negativer Inhaltskontrast, lokaler Ton und Schnitt
in 16:9/9:16 nachgewiesen. B12 bleibt wegen Google-Bildkontingent und ausstehender
Serien-/Langvideoabnahme teilweise offen. [Aktueller Betriebsumfang](frame-production.md).
Frühere Angaben „gesperrt/folgt später“ darunter beschreiben ältere Entwicklungsstände.

Stand: 16.10.2026. **B05/B06 implementiert und mit Fixtures geprüft.**
Nachtrag 17.10.: [Separate Bildanbieter und Einzelbildtest](frame-image-access.md)
eingebaut; Google-Livebild erfolgreich. Bildserien im Auftrag (B08), Tonspur/Bildzeiten (B07), Bildinhaltsprüfung
(B09), Zusammensetzen (B10) und reale Langvideo-Abnahme (B12) bleiben offen.

## Bedienung

1. Reiter **Frame** → **Frame-Skript vorbereiten**.
2. **Idee** oder **Eigener Sprechertext** wählen. Für eigenen Text ist der Titel optional.
3. Zieldauer mit Minuten/Sekunden setzen; Vorschläge 1/5/10/20/30 Minuten.
4. Den zusammenhängenden Sprechertext lesen. Änderungswunsch eingeben und
   **KI verbessert das Skript** wählen; danach die neue Fassung lesen.
5. **Text freigeben & Bildplan vorbereiten** bindet die Bildaussagen an den
   freigegebenen Wortlaut. Eine Einzelbild-/Szenenfreigabe ist nicht nötig.

Aktuell entstehen dabei **Skript und Bildplan**, noch keine Frame-Mediendateien.
Eigener Text kann ohne KI übernommen werden. Für KI-Entwurf, Überarbeitung und
Bildplanung ist der eingerichtete automatische Antigravity-/Ollama-Skriptzugang
nötig. Manueller Webimport bleibt beim bestehenden Animationsverfahren.

## Inhalt folgt der jeweiligen Idee

Frame verwendet keinen festen Tier-/Möbelkatalog und keine animierte Gestenfolge.
Der Entwurf soll die für das Thema passende Erzähl- oder Erklärstruktur wählen;
keinen fiktiven Helden, festen Dreisatz oder immer gleiche Einleitung erzwingen.
Literal gezeigte Handlung, Gegenstandsbild, Raum, Vergleich und Diagramm sind
gleichberechtigte Bildarten. Ein abstraktes Thema darf eine passende konkrete
Visualisierung bekommen. Der Zeichenstil bleibt einheitlich, der Inhalt variiert.

Pro Bild werden Umgebung, Handlung, sichtbare Zustandsänderung und die tatsächlich
abzubildenden Personen/Tiere/Gegenstände/Konzepte geplant. Textbelege verbinden
diese Motive mit dem jeweiligen Sprecherabschnitt. Zubehör ersetzt kein Hauptmotiv.
Ein zusätzlicher KI-Prüfaufruf prüft den **Plan** auf solche Inhaltsfehler und generische
Ersatzgesten. Höchstens eine Korrekturrunde; danach sichtbarer Fehler statt Ersatzplan.
Diese Modellprüfung ist kein Beweis semantischer Richtigkeit und keine Pixelprüfung.
Der tatsächliche Bildinhalt muss später in B09 geprüft werden.

## Dauer und lange Texte

- Frame-Ziel: 15–1800 Sekunden, sekundengenau. Animationsgrenze bleibt 600 Sekunden;
  die Animationsgestaltung wurde nicht geändert.
- Eigener Sprechertext: 20–80000 Zeichen, Wortlaut und Absätze bleiben erhalten.
  Die Zieldauer kürzt oder streckt ihn nicht. Überarbeitung erfolgt nur auf Anforderung;
  ausdrücklich verlangte starke Kürzungen bleiben möglich.
- Zielzeit, geschätzte Sprechzeit und später gemessene Dauer bleiben getrennt.
  Stimmen-/Tempoänderung erzeugt eine neue Version und aktualisiert die Schätzung.
- Lange Entwürfe und Revisionen verwenden intern begrenzte Textportionen, etwa
  300 Wörter/5000 Zeichen. Das sind keine Bild- oder Zeitvorgaben. Zur Freigabe
  liegt ein Fließtext vor; Wiederholungen werden auch über Abschnittsgrenzen geprüft.
- Folgeabschnitte erhalten die Idee, ihre Position, vorherigen Text und bei Revisionen
  den jeweiligen Originalabschnitt samt Änderungswunsch. Kein neuer Standardanfang
  je Abschnitt. Nachträgliche Bildplanung darf keinen Sprechertext umschreiben.
- Vorhandene Modell-/Kontextbudgets werden nicht hochgesetzt. Native Gesamt-Timeouts
  berücksichtigen Textumfang und konfigurierte Einzellimits, maximal zwölf Stunden.
  Lokale Rechenleistung und gewähltes Modell begrenzen die praktische Qualität/Laufzeit.
  Ein realer 30-Minuten-Lauf auf jeder Hardware wurde nicht behauptet.

## Vertrag und Versionierung

`backend/frame.py` enthält begrenzte Datenmodelle und die festen Planeraufrufe.
`POST /api/jobs` mit `generation_mode=frame` und `input_kind=idea|narration`
bereitet den Text vor; `narration` nur bei eigener Texteingabe.
`POST /api/jobs/{id}/revise-script` überarbeitet den Fließtext.
`POST /api/jobs/{id}/approve-frame-plan` benötigt aktuelle Version und Inhaltshash.
Der klassische Szeneneditor ist für Frame ausdrücklich gesperrt.

`frame_plans` speichert den Bildplan separat nach Auftrag und Skriptversion;
der freigegebene Text wird dabei nicht zur neuen animierten Szenenfassung umgebaut.
Nach Text-/Stimmenänderung wird kein alter Plan für die neue Version ausgegeben.
Historische Fassungen bleiben erhalten. Ein bestehender gültiger Plan wird bei
wiederholter identischer Freigabe ohne erneuten KI-Aufruf zurückgegeben.

Planfelder: Skriptversion/-hash, exakter Texthash, Stil, Figurenregister,
Bild-IDs, Textanfang/-ende und Bildbeschreibungen; zusätzlich Plan-Prüfsumme.
Textoffsets sind **Python-Unicode-Codepoints**, Ende exklusiv; keine UTF-16-Indizes.
Die Bereiche decken jedes Zeichen einschließlich Zwischenräumen lückenlos und in
Reihenfolge ab. IDs werden aus Skripthash und Textbereich berechnet und überprüft.
Unbekannte Motive, fehlende Belege, veränderte Texte, doppelte Bilder und manipulierte
Bereiche/Hashes werden abgewiesen. Maximal 600 Bildabschnitte/256 Motive je Auftrag.
Keine erfundenen Sekunden oder Wortzeitmarken; Zeitbasis steht auf „Audio ausstehend“.

## Sicherheit und Grenzen

Schutzbedarf: privater Sprechertext, lokale Projekte und wirksame Freigaben.
Vertrauensgrenzen: lokale Formulare/API, Modellantworten, Workerdatei und Datenbank.
KI-Ausgaben sind Daten, keine Werkzeuge, Befehle, Dateipfade oder freigegebenen URLs.
Feste bestehende Skriptanbieter, kein stiller Anbieterwechsel und keine Zusatzcredits;
vorhandene Antigravity-Credit-Prüfung bleibt wirksam. Keine neue Abhängigkeit.

Anfragen sind begrenzt, bei neuer Textanlage maximal 1,5 MB. Betriebssystem-Prozessgruppen,
lokaler Server, Fehler-IDs und die bestehende Abbruchverwaltung werden weiterverwendet.
Render-/Uploadfreigabe für Frame bleibt gesperrt. Wiederaufnahme nach Abbruch und
inkrementelle Medienbearbeitung gehören zur späteren Frame-Integration B11.
Browser-Wiederholungskennung speichert nur einen Payload-Hash statt des Sprechertextes.
Keine WSL-Browser, fremden Prozesse, zusätzlichen Ports oder globalen Kontoeinstellungen.

## Nachweise

- 343 Backend-Tests bestanden, davon 10 Plattform-/Umgebungs-Skips; 73 JS-Tests bestanden.
- 1-/10-/30-Minuten-Entwürfe und lange Revisionen mit simulierten Modellantworten;
  große eigene Texte über die echte API, exakte Absätze, Wortbudgets und Grenzwerte.
- Katze, Feuer, Vorher/Nachher und abstrakter Zusammenhang: unterschiedliche Motive
  und Bildarten; Negativfälle für Zubehörersatz, generische Gesten, Lücken, Reihenfolge,
  Prüfsummen, alte Freigaben und fehlende Textbelege. Kein Live-Qualitätsnachweis.
- Echter privater Worker übernimmt eigenen Sprechertext ohne Provideraufruf.
- Windows-App: `data/desktop/acceptance-normal-1792179078647168900/result.json`:
  Reiter, schmale Fenster, eigener Sprechertext mit Absätzen und 30-Minuten-Ziel,
  Freigabeschaltfläche, Einstellungen, Loopback und vollständiger eigener Prozessstopp.
- Bei dieser UI-Prüfung ein bestehender Fehler im gemeinsamen Erstellungsdialog behoben:
  Zugriff auf undefiniertes `path` vor dem API-Aufruf. Kein Zeichen-/Renderalgorithmus geändert.
- Tests arbeiten isoliert. Ein durch eine alte Testannahme entstandener auftragsloser
  Test-Diagnoseeintrag wurde eindeutig identifiziert und entfernt; keine Nutzeraufträge verändert.

Keine neuen Testbilder, Hörproben oder Testfilme und keine echte Modellinferenz erzeugt.
