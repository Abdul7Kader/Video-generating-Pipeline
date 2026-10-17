# Frame-Produktion · Stand 17.10.2026

## Bedienung

1. Unter **Einstellungen → Frame · KI-Bilder** den vorhandenen Google-/Antigravity-
   Zugang wählen und speichern. Alternativ Cloudflare-Free mit Account-ID und
   Workers-AI-Token einrichten. Beide Bildwege benötigen die vorhandene Google-
   Anmeldung zusätzlich für die automatische Prüfung des tatsächlichen Bildinhalts.
2. Eine installierte lokale Stimme wählen: Piper oder Qwen3-TTS. Es wird keine
   kostenpflichtige Gemini-Sprach- oder Bild-API automatisch eingesetzt.
3. Im Reiter **Frame** ein Video mit Idee oder eigenem Sprechertext anlegen.
   Zieldauer: 15 Sekunden bis 30 Minuten. Bei eigenem Text bestimmt dessen
   tatsächliche Sprechzeit das Ergebnis; die Pipeline kürzt keine Wörter heimlich.
4. Text lesen, bei Bedarf Änderungswünsche eingeben und **KI verbessert das Skript**
   wählen. **Text freigeben & Video erstellen** startet den gesamten Medienablauf.
   Einzelne Szenen oder Bilder müssen nicht zusätzlich freigegeben werden.
5. Der Verlauf nennt den aktuellen Schritt und Bildabschnitt. **Diese Erstellung
   abbrechen** beendet ausschließlich die eigenen Produktionsprozesse. Über
   **Frame-Produktion fortsetzen** werden gültige Ergebnisse wiederverwendet.
6. Fertiges Video lokal prüfen oder über die bereits eingerichtete Discord-Abnahme
   freigeben, verändern lassen oder ablehnen. Veröffentlichung verwendet dieselben
   versions- und dateigebundenen Zieladapter wie bisher. Ohne eingerichtete Konten
   wird nichts gepostet; TikTok bleibt beim vorhandenen Inbox-/Bestätigungsweg.

## Umgesetzt

- **B07:** Freigegebene Textstellen werden unverändert an die lokale Stimme gegeben.
  Interne Sprachabschnitte sind cachebar; begrenzte Sprechpausen werden wie bisher
  gekürzt. Ein zusammenhängendes Mono-PCM-WAV mit 48 kHz ist die gemeinsame Uhr.
  Bildwechsel liegen an gemessenen Sprachabschnittsgrenzen. Keine geschätzten
  Wortzeiten, keine zusätzlich eingefügten Abschnittspausen. Lautheit wird auf den
  bestehenden Sprachstandard normalisiert. Maximal 60 Minuten gemessene Tonspur
  dienen als technische Obergrenze, ohne Text abzuschneiden.
- **B08:** Serielle Bildgenerierung, inhaltsspezifische Motive und ein gemeinsames
  Figurenregister. Echte lokale PNGs, Anbieter-/Prompt-/Modellnachweise und SHA-256
  pro Datei. Jedes angenommene Bild und jeder Sprachabschnitt erhält sofort einen
  atomaren Cacheeintrag. Bei vorübergehend fehlender Bildprüfung bleibt auch das
  bereits erzeugte, noch nicht angenommene Bild zur erneuten Prüfung erhalten.
- **B09:** Google sieht die tatsächlichen Pixel über ein auf eigene private PNG-
  Kopien begrenztes `view_file`. Hauptmotive, Handlung, Ergebnis und Zeichenstil
  werden gegen den zugehörigen Text geprüft. Das erste angenommene Bild dient
  zusätzlich als Stil-/Identitätsreferenz. Ein Prompt oder Dateiname reicht nicht
  als Bildbeweis. Maximal eine korrigierte Neuerzeugung je abgelehntem Bild; danach
  sichtbarer Qualitätsfehler mit Abschnitt und konkreten Prüfbefunden in der UI.
- **B10:** Vorhandenes natives FFmpeg hält die Bilder passend zur Erzählspur.
  30 fps, H.264/AAC, 1280×720 bzw. 720×1280/720×720. Vollständiges Motiv durch
  Einpassen auf Weiß, kein Abschneiden oder Pflichtgesten. Weitere Formate nutzen
  dieselben angenommenen Bilder und Audiodateien. Qualitätsbericht verlangt
  Audio-/Videoende innerhalb von 100 ms, unabhängig von der Gesamtlänge.
  Eine separate SRT enthält ganze Bildabschnitte mit gemessenen Grenzen; keine
  vorgetäuschte Wortgenauigkeit oder automatisch eingebrannten Untertitel.
- **B11:** Aktuelle Textfreigabe und passender Bildplan sind beim Einreihen und beim
  Rendern erforderlich. Bearbeitung erzeugt neue Versionen und entwertet alte
  Freigaben. Unveränderte Cacheinhalte können aus früheren Versionen desselben
  Auftrags übernommen werden. Abbruch, endgültige Ablage, manuelle Bereinigung,
  Discord und Veröffentlichung verwenden die bestehenden gemeinsamen Dienste.
  Arbeitsdateien bleiben standardmäßig erhalten; `work_retention_days=0` bleibt
  unverändert. Endvideos liegen separat im eingestellten Videoordner.

## Prüfung und verbleibende Abnahmen

- Synthetische WAVs für 1, 10 und 30 Minuten: samplegenau zusammengefügt, kein
  aufsummierter Versatz durch gerundete Bildzeiten.
- Simulierter Abbruch bei Bild 7 von 20: sechs angenommene Bilder bleiben erhalten;
  Wiederaufnahme erzeugt nur fehlende Bilder. Beschädigte Dateien werden verworfen;
  eine geänderte Bildaussage erzeugt nur deren neuen Inhalt.
- Positiver und negativer echter Google-Visionnachweis:
  `data/frame-vision-proof.json`. Das tatsächliche Katzenbild wird passend akzeptiert
  und für die falsche Zug-/Elefanten-Erzählung abgelehnt. Zusatzcredits aus.
  `data/frame-vision-post-proof.json` bestätigt zusätzlich die neue verpflichtende
  erfolgreiche PostToolUse-Pixelansicht (`frame-pixels-v2`).
- Native Windows-UI und Start/Stopp:
  `data/desktop/acceptance-normal-1792253219637271800/result.json`;
  nur 127.0.0.1:8080, keine eigenen Prozessreste. Veralteter UI-Cache bei Appupdates
  behoben, ohne Cookies, Anmeldungen oder fremde Browser zu löschen.
- Expliziter sparsamer echter Kurztest: `tests/check_frame_runtime.py`, eigene
  Testdatenbank unter `data/frame-acceptance`. Der finale Laufnachweis wird erst
  nach bestandener Medienprüfung in `result.json` geschrieben. **Dieser vollständige
  neue Serienlauf ist derzeit nicht bestanden:** Google meldet für das Bildmodell
  `gemini-3.1-flash-image` ein erschöpftes Kontingent, beim Test etwa vier Stunden
  Wartezeit. Es wird kein zusätzlich bezahlter Zugang aktiviert. Plan und echte
  Piper-Tonabschnitte bleiben zur Wiederaufnahme erhalten.
- Tatsächlicher Schnitt-/Sprachnachweis mit dem vorhandenen, real geprüften
  Google-Bild: `tests/check_frame_composition.py` und
  `data/frame-composition-proof/result.json`. 16:9 und 9:16, identische Tonspur,
  4,356 Sekunden gemessene Sprache; Qualitätsprüfung und Bildkontrolle bestanden.
  **Dies ist ausdrücklich keine neue KI-Bildserie.** Kein externer Aufruf dafür.
- Nativer Zweibild-Schnitt mit synthetischen Farbflächen und vorhandener Tonspur:
  `data/frame-boundary-proof/result.json`, Wechsel bei Frame 78, rund 6,7 ms
  Abweichung von der gemessenen Samplegrenze. Keine KI-/Stimmgenerierung dafür.
- **B12 bleibt bis zur realen Langvideo- und Nutzerabnahme teilweise offen.**
  Synthetische Zeitlinien ersetzen keine qualitative Langvideoabnahme. Cloudflare
  kann ohne Account-ID/Token nicht live geprüft werden. Discord-/Social-Konten
  brauchen weiterhin ihre eigenen Berechtigungen und Live-Abnahmen. Linux-/Mac-
  Hardwareabnahmen werden durch einen Windows-Test nicht ersetzt.

## Schutzgrenzen

Schützenswert sind Sprechertexte, Bilder, Videos und Zugangsdaten. Fremde Prompts,
Modellausgaben, Rasterdateien und API-Antworten bleiben untrusted. Lokale HTTP-
Zugriffe, native Worker, Anbieter und Dateisystem sind getrennte Vertrauensgrenzen.

- Keine neuen Listener, öffentlichen Ports, allgemeinen Modellwerkzeuge oder
  automatischen Browserlogins. Google läuft intern in seiner Agentenlaufzeit;
  die App begrenzt diese pro Aufruf auf Bildgenerierung oder eigene Pixelansicht.
- Session-, PreToolUse- und PostToolUse-Hooks, feste Werkzeuge, Dateien, Prompt-/Dateinamen und
  ausgeschaltete Zusatzcredits. `AspectRatio` wird, falls vom installierten CLI
  mitgegeben, auf das feste quadratische Masterbild überschrieben. Andere
  unbekannte Werkzeugparameter werden abgelehnt.
- Bildprüfung darf nur eigene geprüfte private PNG-Kopien öffnen. Keine Shell,
  URLs, fremden Projektdateien oder Delegation. Erforderliche Bildansichten müssen
  erfolgreich abgeschlossen sein, bevor ein formal passender Prüfbefund angenommen
  wird. Werkzeugfehler werden getrennt vom möglicherweise erfolgreichen CLI-
  Gesamtergebnis klassifiziert. Als begrenzter Fallback werden ausschließlich die
  Runtime-Fehlerdatensätze der eigenen verifizierten Sitzung gelesen; keine fremden
  Sitzungen und keine Ausgabe ihrer Inhalte. Kontingentfehler werden damit nicht
  als unverständlicher Bildexportfehler ausgegeben.
- Bilddecoder und Prozesse sind begrenzt. FFmpeg bekommt ausschließlich die selbst
  geschriebene Wiedergabeliste mit regexgeprüften relativen SHA-256-PNG-Namen.
  Die für feste Bildraten benötigte ffconcat-Option `safe=0` erlaubt hier keine
  Anbieterpfade oder URLs; Protokolle bleiben auf file/pipe begrenzt.
- Keine Secrets in Cache-/Workerdateien. Cloudflare-Token im OS-Tresor; Google-
  Anmeldung verwaltet der Hersteller. Öffnen/Speichern startet keine Inferenz.
  Anbieterlimits führen zum sichtbaren Stopp, niemals zum stillen Bezahltarif oder
  Ersatzanbieter. Das tatsächliche Google-Bildmodell ist weiterhin nicht gemeldet;
  das konfigurierte Gemini-Modell wird ausdrücklich nur als Brückenmodell erfasst.

Herstellergrundlagen: [CLI](https://antigravity.google/docs/cli/headless/),
[Hooks](https://www.antigravity.google/docs/hooks),
[Cloudflare-Modell](https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/).
Eine KI-Bildprüfung reduziert Fehler, garantiert aber keine fehlerfreien Bilder.
