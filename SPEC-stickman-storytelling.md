# Strichmenschen: gezeichnete Geschichten

## Erweiterung 2026-10-11: Stimmenstudio und gezielte Skriptarbeit

Die Oberfläche zeigt ausschließlich Strichmenschen-Aufträge und zugehörige Erstellung,
Stimme, Skript, Zeichenregie und Downloads. Andere Daten und Adapter bleiben erhalten;
die Darstellung wird reduziert, keine Bereinigung oder Migration bestehender Aufträge.

- Lokaler Hörvergleich mit identischem Text und Tempo: Thorsten klar, Thorsten lebhaft
  (Emotions-Sprecher-ID 0), Kerstin; LJ für Englisch. Kerstins niedrigere Modellqualität
  bleibt sichtbar. Modellwahl ist eine feste Liste, keine nutzerdefinierten Pfade/URLs.
- Stimme/Tempo sind Teil der versionierten Produktionskonfiguration und des Audio-
  Cache-Fingerprints. Eine Änderung entwertet die Freigabe; alte Konfigurationen werden
  ohne Änderung ihrer gespeicherten Inhalte weiterhin gelesen.
- Skript-Wortbudget und Editor-Sprechzeit verwenden eine grobe lokale Kalibrierung
  je Stimme (deutscher Vergleich: 25 Wörter / 7,05, 8,38, 8,02 Sekunden). Thema, Satzbau
  und Aussprache beeinflussen die tatsächliche Länge. Keine zugesicherte Zieldauer.
- KI-Überarbeitung optional auf stabile Szenen-ID begrenzt. Server übernimmt nur diese
  Szene samt Sprechertext/Zeichenregie; andere Szenen, Titel und Dauern bleiben erhalten.
  Fehlende Szene/ID, ungültige Textanker und konkurrierende Versionen werden abgewiesen.
- Redaktionelle Prompts verlangen verbundene Erzählung, Ursache/Wirkung und Gegenstands-
  Kontinuität. Presets sind bearbeitbare Anweisungen, keine automatischen KI-Aufrufe.
- Ungespeicherte Eingaben schützen Freigaben und Auftragswechsel. Laufende Änderungen
  sperren doppelte Aktionen; Fehler erhalten den Entwurf. Sachprüfungsnotizen bleiben
  bei manuellen Änderungen sichtbar und müssen weiterhin redaktionell geprüft werden.

Schutzbedarf: Entwürfe, lokale Hörproben, Medien und vorhandene Anbieterzugänge.
Sprechertexte werden lokal synthetisiert; Downloads gehen ausschließlich über den
vorhandenen Piper-Downloader. Keine neuen Cloud-Dienste/Kosten oder Zugangsdatenänderungen.
Hörproben: max. 600 Zeichen, endliches Tempo 0,85–1,25, eine gleichzeitige Anfrage,
atomarer Cache mit 128-MB-Schwelle, private Audioantworten und streng geprüfte Hash-IDs.
Der lokale Piper-Zugriff ist serialisiert. KI-Ausgabe bleibt untrusted und wird validiert.

Offen: subjektive Stimmenqualität, menschliche Faktenprüfung und approximative Wort-
Synchronisierung. Ein Hörvergleich ersetzt keine Beurteilung längerer Erzählungen.

Nachweis dieser Erweiterung: echte drei deutsche Hörproben; echte Antigravity-
Überarbeitung einer Szene mit unverändertem Titel und unveränderten übrigen Szenen;
Browserprüfung von Stimmen-/Tempowahl, Versionswechsel und Schutz ungespeicherter
Eingaben. Anschließende Full-HD-Probe mit Thorsten lebhaft bei 1,1×: 13,62 Sekunden,
automatisches Qualitäts-Gate bestanden. 151 Python-Tests bestanden, ein optionaler
Render-Test übersprungen; 14 Renderer-Tests und TypeScript-Prüfung bestanden.
Sicherheitsnachweis: ungültige Stimm-/Medien-IDs, nicht endliches Tempo, falsche
Sprache, konkurrierende Vorschauanfragen und veraltete Szenenversionen abgewiesen;
Stimmenwechsel entwertet Freigaben und trennt Audio-Caches. Keine Sicherheitsgarantie.

Stand: 2026-10-10. Aktueller Nutzerauftrag ersetzt die bisherigen offenen Ausbaupläne.

Erweiterung 2026-10-10: Strichmenschenfilme folgen der tatsächlichen Sprechdauer,
ohne auf die Wunschlänge aufgefüllte Stille. Überlange stille TTS-Abschnitte kürzen,
kurze Atem-/Wortpausen und hörbare Sprache erhalten. Konkrete Textanker steuern
mehrere zügige Handlungen einer Figur je Szene, inklusive Bezug zu Requisiten.
Der Editor erlaubt diese Regieschritte. Wortpositionen werden lokal aus Text und
Sprachenergie geschätzt; es wird keine exakte Spracherkennung behauptet.
Prüfung: echte PCM-Samples vor/nach Kürzung, unbekannte Textanker/Zielobjekte,
deterministische Bewegungswechsel, Requisiten-Interaktion und erneuter Echtrender.

Referenz: https://www.youtube.com/watch?v=49_Ph2q6uIM (Ink Explainer).
Im Browser gesichtet: Wecker-Nahaufnahme, Gegenüberstellung moderner/steinzeitlicher Figur,
Feldarbeit. Ziel ist die Bildsprache, kein Kopieren von Figuren, Bildern oder Sprechertext.

## Ergebnis und Grenzen

- Weißer Zeichenhintergrund, schwarze organische Konturen, sparsame flache Farben.
- Geschichten mit mehreren ausdrucksstarken Figuren, Requisiten und Schauplätzen;
  kein wiederkehrender Präsentator mit Szenennummer, Fortschrittsbalken oder Verlauf.
- Strukturierte Regie steuert Schauplatz, Bildausschnitt, Figurenpositionen, Kleidung,
  Emotionen, Posen, Bewegungen, Requisiten und deren zeitlichen Auftritt.
- Harte Schnitte als Standard, steuerbare Blenden/Wischblenden/Zooms. Untertitel bleiben
  lesbar, Sprecherstimme und Freigaben bestehen.
- KI erzeugt ausschließlich validiertes JSON aus einem begrenzten Zeichenbaukasten.
  Keine fremden SVGs, Skripte, URLs oder Dateipfade im Zeichenplan.
- Neue Aufträge bieten ausschließlich Strichmenschenproduktion. Andere Profile bleiben
  lesbar und im Code erhalten, werden als eingefroren gesperrt. Bestehende Videos bleiben zugänglich.
- Standardformat 16:9 wie die Referenz; Hochformat und Quadrat bleiben möglich.
- Alte Szenen ohne Zeichenplan bleiben lesbar. Beim Rendern braucht es einen expliziten
  Zeichenplan; die Oberfläche erlaubt dessen Ergänzung. Kein stiller Rückfall zur alten Figur.
- Keine neuen Dienste, Abhängigkeiten, Kosten oder automatischen Veröffentlichungen.

## Umsetzung und Prüfung

1. Datenvertrag und KI-Prompt für ausführbare Zeichenregie; negative Schema-/Grenztests.
2. SVG-Szenenrenderer mit Figuren, Requisiten, Schauplätzen und deterministischer Animation.
3. Szenenplan im Editor bearbeitbar; neue Auswahl auf Strichmenschen begrenzen.
4. Eigenes Beispiel mit Piper und Remotion wirklich rendern, Bilder ansehen und Audio/MP4 prüfen.
5. Gesamtsuite, TypeScript/JavaScript, Review und Git-Hygiene; Commit/Push als Abdul7Kader.

Schutzbedarf: unveröffentlichte Skripte, lokale Medien und Anbieterzugänge. Vertrauensgrenzen:
KI-JSON → Pydantic → fest implementierte React/SVG-Elemente; lokale API → versionierte
Freigaben → Renderprozess. Missbrauch: übergroße Pläne, ungültige Koordinaten, Code-/SVG-
Injection und Umgehung eingefrorener Profile. Schema begrenzt Listen, Werte und Identifikatoren;
Text wird von React/HTML-Escaping kodiert. Bestehende Kontrollen bleiben aktiv.

Technische Grundlagen: https://www.remotion.dev/docs/use-current-frame und
https://docs.pydantic.dev/latest/concepts/fields/.

Qualitätsgrenze: Der Zeichenbaukasten ist erweiterbar, aber erzeugt keine beliebige
handgezeichnete Illustration aus Freitext. Nicht vorhandene Requisiten werden nicht erfunden.
Sichtprüfung des Beispiels und spätere redaktionelle Freigabe sind notwendig.

Abschlussnachweis: Umsetzung 1–4 durchgeführt; echte Full-HD-Stilprobe mit Piper-Stimme,
MP4-/Untertitelprüfung und Sichtprüfung. Finaler KI-Vertrag live mit Antigravity validiert.
133 bestandene Python-Tests plus separat bestandener optionaler Mehrformat-Echtrender,
zehn Node-Tests, TypeScript-/Syntaxprüfungen. Browser bestätigt versionierte Zeichenregie.
Sicherheit geprüft: begrenzte Zeichenwerte, Text-Encoding, Planhash, eingefrorene API-Wege,
unzulässige Antigravity-Tools und ungültige Abgangszeiten. Keine zusätzlichen Dienste oder Pakete.

Nachweis der Erweiterung: künstliches Auffüllen auf die geplante Szenenlänge entfernt;
lange stille PCM-Abschnitte gekürzt, hörbare Testsamples unverändert und kurze Wortpausen erhalten.
Audio-Cache nach Sprachrichtlinie versioniert, Wortschätzungen wiederverwendet. Textanker,
Requisitenindizes und Reihenfolge werden serverseitig geprüft; ungültige Änderungen ergeben 422
und verändern den gespeicherten Plan nicht. Die UI schützt verwendete Requisiten vor versehentlichem
Entfernen und hält die Nummerierung gültig. Aufheben, Ablegen, Lesen, Tragen und kurze Laufwege
sind ausführbar; dieselbe Requisite folgt der Figur und kann im nächsten Bild abgelegt werden.

Geprüft: 141 bestandene Python-Tests, ein optionaler Integrationstest übersprungen; 14 Node-Tests,
TypeScript-/Syntaxprüfung, echte Piper-/Full-HD-Probe samt Qualitätsgate und Bildsichtung.
Die Bewegungsprobe dauert rund 11,8 Sekunden statt 22 Sekunden geplanter Szenenlänge;
gemessene stille Abschnitte höchstens rund 0,20 Sekunden. Browserprüfung mit separater
Testdatenbank: Regieschritte speichern, Skriptfreigabe, Rendern und Videovorschau erfolgreich,
keine Console-Fehler. Live-KI-Prüfung: Antigravity erzeugt vier gültige Szenen mit acht Textankern
und passenden pick/place/read-Handlungen. Die erste Antwort im engeren Testzeitfenster war ungültig;
der abschließende Test nutzt die unveränderte reguläre Anbieterzeitgrenze.

Offen als Qualitätsgrenze: Wortzeiten bleiben eine Schätzung, keine erkannten Wortgrenzen;
natürliche kurze Sprachabstände bleiben bestehen. Die Zeichenregie braucht redaktionelle Prüfung,
insbesondere bei neuen Themen und Requisiten. Keine weiteren Dienste oder Abhängigkeiten ergänzt.
