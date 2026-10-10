# Strichmenschen: gezeichnete Geschichten

Stand: 2026-10-10. Aktueller Nutzerauftrag ersetzt die bisherigen offenen Ausbaupläne.

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
