# Ein Sprecher-Skript, danach automatisch Bildplanung und Video

## Verlässliche Freigabe und Wiederholung

Eingegebene Änderungswünsche müssen zuerst über **KI verbessert das Skript**
angewendet oder aus dem Feld entfernt werden. Solange sie noch nicht angewendet
sind, ist die Freigabe gesperrt und ein Seitenwechsel verwirft sie nicht unbemerkt.
Bei fehlendem Skriptzugang erklärt die Oberfläche den nächsten Einrichtungsschritt;
vorhandene Texte bleiben lesbar. Der tatsächlich verwendete Anbieter und das Modell
stehen direkt am Sprechertext.

Nach erfolgreicher Bildplanung speichert eine Datenbanktransaktion die neue
Bildplanversion, die hashgebundene Freigabe und den Renderauftrag gemeinsam.
Schlägt einer dieser Schreibschritte fehl, bleiben ursprünglicher Text und Version
erhalten. Veraltete Versionen, veränderte Wörter und konkurrierende Änderungen
werden vor der Produktion abgewiesen; Änderungen können einen bereits eingereihten
oder laufenden Render nicht überschreiben.

Eine wiederholte identische Freigabe startet keine zweite Bildplanung. Nach einem
Renderfehler verwendet ein erneuter Aufruf den gespeicherten freigegebenen Bildplan,
auch nach einem Neuladen der UI. Dafür ist kein weiterer KI-Aufruf erforderlich.
Die Freigabe zur Veröffentlichung wird dadurch nicht erteilt.

Neue Strichmännchen-Aufträge in der UI verwenden `script_mode=story`. Die erste
KI-Anfrage liefert einen zusammenhängenden Sprechertext und eine kurze Bildidee.
Die UI zeigt den Text zum Lesen, ein Feld für Änderungswünsche an die KI sowie
**Freigeben & Video erzeugen**. Einzelne Szenen, Sekundenfelder und technische
Zeichenregie gehören nicht mehr zum Nutzerablauf. Stimme und Herstellung bleiben
in einem aufklappbaren Bereich erreichbar.

Die KI überarbeitet auf Wunsch das ganze Skript. Jede Überarbeitung bleibt als
neue Version erhalten und hebt ältere Freigaben auf. Bereits vorhandene Aufträge
werden ebenfalls als durchgehender Text angezeigt; ihre alten Versionen und
Videodateien werden nicht migriert oder gelöscht.

Die Freigabe sendet aktuelle Version und Inhaltshash an
`POST /api/jobs/{id}/approve-and-render`. Erst dann erzeugt die KI die konkrete
Bildplanung. Sie darf den freigegebenen Text nur an natürlichen Handlungs- und
Satzgrenzen auf interne Einstellungen verteilen. Die zusammengefügten Texte
müssen bis auf Leerraum exakt übereinstimmen, einschließlich Satzzeichen.
Titel und Beschreibung bleiben erhalten. Bildidee und Änderungswünsche fließen
in die Planung ein. Erst ein valider, zum Text passender Plan wird versioniert,
freigegeben und eingereiht. Der Nutzer benötigt dafür keinen zweiten Knopf.

Der interne Schnitt dient der Illustration; er ist kein gleichmäßiges Raster
aus Fünf-Sekunden-Erklärungen. Die fertigen Zeiten folgen weiterhin der Stimme.
Der Text bleibt zusammenhängend lesbar, unabhängig von der Zahl der Einstellungen.

## Sichtbare Tiere und konkrete Handlungen

Der frühere Zeichenkatalog enthielt keine Tierfiguren. Deshalb konnte ein Plan
zur Katzenadoption einen Korb, ein menschliches Bett oder ein Herz enthalten und
trotzdem strukturell gültig sein. Der Katalog enthält nun Katzen und Hunde als
eigenständige Figuren mit stabiler ID und animierten Bewegungen. Sie können
laufen, sitzen, schnuppern und schlafen. Menschen können ein bestimmtes Tier
streicheln; Interaktionsziele werden auf vorhandene Figuren geprüft.
Steht ein Mensch dabei zu weit entfernt, nähert er sich zum gesprochenen
Streichelmoment automatisch auf Berührungsabstand. Das gilt auch im Hochformat.

Transportbox, flaches Tierbett, Napf, Katzenklo, Kratzbaum und Dokument haben
eigene Zeichnungen. Sprachanker steuern auch das Erscheinen und Verschwinden
von Tieren, etwa beim Einsteigen in eine Transportbox. Die Modellanweisung
fordert wiederkehrende Tiere, echte Interaktionen und sichtbare Folgen.

Eine deterministische Motivprüfung erkennt deutsche und englische Bezeichnungen
für Katzen, Hunde und diesen Tierbedarf. Ein genanntes Tier muss als Tierfigur
vorkommen; ein ähnliches Möbelstück oder Symbol genügt nicht. Bei einem Fehler
darf die Bild-KI einmal korrigieren. Bleibt der Text verändert oder fehlt das
Motiv weiterhin, wird keine Produktion gestartet und das gelesene Skript bleibt
erhalten. Diese Prüfung ersetzt keine allgemeine semantische oder künstlerische
Bewertung: weitere Tiere und Gegenstände benötigen passende Katalogeinträge.

## Sicherheit und Prüfung

Die KI liefert ausschließlich begrenzte JSON-Zeichendaten. Fremdes SVG, Code,
Dateipfade oder Werkzeugaufrufe werden nicht zugelassen. Der neue Textaufruf
verwendet dieselbe Werkzeugbegrenzung wie die bisherige Skript-KI. Version und
Hash werden serverseitig geprüft; ein paralleler Textwechsel während der
Bildplanung verhindert die Freigabe. Doppelte Planung wird begrenzt; eine
wiederholte identische Freigabe eines eingereihten Films startet keinen neuen
Modelllauf. Es kommen keine neuen kostenpflichtigen Dienste hinzu.

Tests prüfen den neuen Entwurf, KI-Überarbeitung, unveränderte Freigabe,
veraltete Hashes/Versionen, parallele Änderungen, doppelte Starts, fehlende
Tiermotive und die tatsächlichen SVG-Zeichnungen. Die kurze Zeichenprobe liegt
in `examples/cat-adoption-demo.json`; sie lässt sich mit
`scripts/render_stickman_demo.py` rendern. Für schnelle Bildprüfungen kann Piper
verwendet werden, während die Nutzerkonfiguration die Qwen-Stimme behält.
