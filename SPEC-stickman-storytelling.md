# Strichmenschen: gezeichnete Geschichten

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
