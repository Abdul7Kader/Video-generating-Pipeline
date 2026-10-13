# Ein Sprecher-Skript, danach automatisch Bildplanung und Video

## Textprüfung vor dem Speichern

Skripterstellung und KI-Überarbeitung verwenden dieselben Prüfungen für alle
unterstützten Skriptanbieter. Das Wortbudget berücksichtigt gewünschte Länge,
ausgewählte Stimme und Sprechtempo. Akzeptiert werden 65–110 % des geschätzten
Zielwortbudgets; der Prompt zielt auf die volle gewünschte Länge. Das ist eine
Sprechzeitschätzung, keine Garantie für die spätere Audiodauer.

Szenenüberschriften, Aufzählungen, Zeitstempel, Markdown, Regieanweisungen,
wortgleiche längere Satzwiederholungen und Platzhalter werden erkannt. Die Prüfung
erfasst auch Platzhalter in der Bildidee und den sachlichen Hinweisen. Für einen
ungültigen Entwurf gibt es höchstens einen zusätzlichen Korrekturversuch. Bleibt
er ungültig, wird er nicht gespeichert; ein vorhandener Text bleibt erhalten.
Schemafehler geben keine unbearbeiteten Modellausgaben in Fehlermeldungen zurück.

Überarbeitungen erhalten den bisherigen Titel, die Beschreibung, den gesamten
Sprechertext, die Bildidee und die sachlichen Hinweise als Kontext. Die KI soll
nur gewünschte Änderungen vornehmen und frühere Verbesserungen erhalten. Reine
Änderungen der Bildidee oder sachlicher Hinweise lassen sich ebenfalls speichern.
Auch nach einer Bildplanung oder einem Renderfehler bleibt die Überarbeitung
beim Text-zuerst-Ablauf, ohne Einzelszenensteuerung.

Prüfversion, Wortbudget, geschätzte Sprechzeit und Anzahl der Versuche werden mit
dem Skript gespeichert. Die Prüfung bestätigt keine Fakten und garantiert weder
sprachliche Qualität noch semantische Bildabdeckung; diese redaktionellen Punkte
gehören weiterhin zur späteren Nutzerabnahme.

Aktuelle Entwicklungsregel des Nutzers: keine neuen Testvideos in der UI als
Routine erzeugen. Zuerst automatisierte Text-, Schema- und Workflowtests verwenden.
Eine echte Videoprobe nur dann, wenn eine konkrete Änderung sie zwingend benötigt;
ansonsten übernimmt der Nutzer die Videotests später.

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

Die begrenzte Bildprüfung umfasst nun auch Bücher, Telefone, Laptops, Dokumente
und Futter. Erkannte Wörter für Lesen, Tippen, Greifen, Tragen, Ablegen und
Streicheln brauchen eine entsprechende Aktion mit Textanker und passendem Ziel.
Ein bloßes Zeigen oder Sprechen ersetzt sie nicht. Einfache Objektpronomen folgen
dem zuletzt ausdrücklich genannten Motiv. Bekannte nicht unterstützte Motive
(Pferd, Vogel, Fisch, Auto, Fahrrad, Flugzeug, Pfanne) werden bereits vor der
Bild-KI benannt; der freigegebene Text wird deshalb nicht heimlich umgeschrieben.
Andere Motive und freie Formulierungen sind keine allgemeine semantische Prüfung.

Greifen, Tragen, Lesen und Ablegen benutzen einen gemeinsamen Hand-/Objektkontakt.
`place_x` und `place_y` definieren gemeinsam eine neue dauerhafte Ablageposition.
Alternativ referenziert `place_surface` einen vorhandenen `desk`; der Objektboden
liegt dann auf der Tischplatte. Flächen und freie Koordinaten dürfen nicht zugleich
angegeben werden. Pro Figur ist ein gehaltenes Objekt erlaubt; vor einem neuen
Besitzer muss es abgelegt werden. Neue Ablagefelder und Zielindizes sind begrenzt.
Die tatsächliche Sprachzeit begrenzt die Ablage vor dem nächsten Greifanker.
Nach der Sprachzeitberechnung müssen Ziele während ihrer Aktion sichtbar bleiben,
auch bei prozentualen Auftritts-/Abgangszeiten; andernfalls stoppt der Renderpfad.
Diese Regeln gelten innerhalb eines Bildabschnitts; Kontinuität über Schnitte
bleibt eine eigene Entwicklungsetappe.

Die Renderbibliothek bindet temporäre HTTP-Server standardmäßig an alle
Schnittstellen. Der prozesslokale Schutz in `renderer/loopback.mjs` beschränkt
ihre Listener auf `127.0.0.1` und weist fremde Bind-Adressen ab. Er verändert keine
Firewall, Systemkonfiguration oder installierten Abhängigkeiten. Ein echter
HTTP-Test sowie lokale Standbildrenderings prüfen den Ausführungspfad.

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
