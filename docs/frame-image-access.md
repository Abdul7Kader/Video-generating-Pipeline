# Frame: Bildzugang und Oberfläche · B03/B04

Aktualisierung 17.10.2026: Frame-Medienpipeline B07–B11 ist inzwischen eingebaut.
Echte Bildansicht, positiver/negativer Inhaltskontrast, lokaler Ton und Schnitt
in 16:9/9:16 nachgewiesen. B12 bleibt wegen Google-Bildkontingent und ausstehender
Serien-/Langvideoabnahme teilweise offen. [Aktueller Betriebsumfang](frame-production.md).
Frühere Angaben „gesperrt/folgt später“ darunter beschreiben ältere Entwicklungsstände.

Nachtrag B05/B06: Frame kann inzwischen Texte und Bildpläne vorbereiten.
[Betriebsumfang und Nachweise](frame-text-and-planning.md). Einzelbilder lassen sich
nun separat in den Einstellungen testen; Frame-Videoproduktion bleibt gesperrt.


Stand: 17.10.2026. **B04 umgesetzt; B03 mit zwei Adaptern und Testoberfläche,
vollständiger Bild-/Visionnachweis noch offen.**

**Google-Livebild erfolgreich:**
`data/image-previews/92aff26c56b34f42b23daf238b1334af.png`, 1024×1024 Pixel.
CLI-Anmeldung und Basiskontingent verwendet, Zusatzcredits geprüft und aus.
Entwicklungsseitig angesehen: orange Katze beim Verlassen einer Transportbox,
kniendes Strichmännchen, heller Hintergrund, keine Schrift. Das belegt einen
konkreten Bildaufruf und den sicheren lokalen Export, keine allgemeine Qualität,
Figurenkonsistenz oder automatische Bildinhaltsprüfung. Das eigentliche Bildmodell
wird vom Hersteller nicht gemeldet; `gemini-3.8-flash-high` ist das Brückenmodell.

## Einrichtung und Einzelbildtest

Einstellungen → **Frame · KI-Bilder**:

1. **Cloudflare · FLUX** wählen, Account-ID und Workers-AI-Token eintragen.
   Nur den Workers-Free-Tarif verwenden und bestätigen; die App hat keine
   Berechtigung, den Tarif selbst zu prüfen. Ein bezahltes Konto könnte über
   sein Freikontingent hinaus Kosten verursachen. Token auf das eigene Konto
   und Workers AI begrenzen; im nativen Kontotresor speichern. Leer lassen
   behält den Token, Entfernen löscht ihn aus dem Tresor.
2. Alternativ **Google AI Pro / Antigravity** wählen. Reguläre CLI-Anmeldung und
   angebotenes Skriptmodell verwenden. `Use G1 Credits` muss aus sein. Keine
   separate Gemini-Bild-API, kein API-Schlüssel und kein neues Abo eingerichtet.
3. **Bildanbieter speichern** erzeugt nichts. **Gespeicherten Zugang prüfen**
   liest nur Konfiguration und bei Google die vorhandene Modellliste; das ist
   noch kein erfolgreicher Bildaufruf.
4. Eigenes Motiv beschreiben → **Speichern und ein Testbild erzeugen**. Prompt
   geht nur zum gewählten Anbieter; kein stiller Wechsel oder automatischer
   Wiederholungsversuch. Fortschritt zeigt Laufzeit und unbekannte Restzeit.
   **Testbild abbrechen** beendet nur den eigenen nativen Worker samt Kindern.
5. Erfolgreiches PNG erscheint darunter und liegt unter `data/image-previews`.
   Kein Video, keine Veröffentlichung und keine neue Bildserie werden gestartet.
   Abbruch erstattet bereits verbrauchtes Anbieterkontingent nicht.

Die Motive stammen aus dem eingegebenen Text. Das Katzenmotiv ist ausschließlich
eine Stilprobe und kein eingebautes Muster für andere Ideen.

## Implementierung und Schutzbedarf

Schützenswert: API-Token, Sprecher-/Bildprompts und lokale Ergebnisse. Grenzen:
lokale UI → geschütztes Backend → eigener Worker → Anbieter → untrusted Bild.
Missbrauchsfälle: fremde Webseite, Schlüssel im Fehler, SSRF/Umleitung,
Referenzdatei-Auslesen, Modellbefehle und unbemerkte Zusatzkosten.

- Cloudflare: festes HTTPS-REST-Ziel, FLUX.1 schnell, vier Schritte; keine
  beliebigen Modelle/URLs, Weiterleitungen oder übernommenen Proxy-Einstellungen.
  Free-Quotenfehler pausieren ohne Upgrade. Die Tarifbestätigung ersetzt keine
  Anbieterabrechnungsprüfung; andere Kontonutzung zählt zum gemeinsamen Limit.
- Google: private CLI-Konfiguration mit eigenem Hauptagenten, ausschließlich
  `generate_image`, keine Unteragentenfreigabe. Vor Ausführung deny-by-default
  Hook für sämtliche Werkzeuge, ein Bildaufruf mit festem Prompt/Namen, keine
  Referenzdateien, Shell, Browser oder beliebigen Dateizugriffe. Credits vor
  CLI-Start und vor dem Bildwerkzeug prüfen. Geladene Hooks und ausgeführter
  Startschutz sind zwingend. Keine globalen Regeln verändert.
- Eigene native Prozessgruppen wie beim Rendern; Abbruch, Timeout und App-Ende
  beenden die eigenen Prozesse. Kein neuer Listener, keine WSL-Browser.
- Nur begrenzte PNG/JPEG-Bytes; bestehendes FFprobe/FFmpeg prüft Pixelmaße und
  Dekodierung, entfernt Metadaten, schreibt ein neues PNG ohne Überschreiben.
  Google-Quelldatei muss zur eigenen Hersteller-Sitzung und zum eigenen Bildnamen
  gehören. Cloudflare-Bild-URLs werden nicht nachgeladen.
- Lokale Token-/Origin-Prüfung, begrenzte Eingaben, keine Secret-Rückgabe und
  bestehende Diagnose-ID mit Schritt `image`. Bildtests sperren parallele
  Einrichtung/Produktion. Kein neues Python-/npm-Paket erforderlich.
- Die CLI speichert herstellereigene Sitzungsartefakte im regulären eigenen
  Sitzungsordner. App-Hilfsdateien sind temporär; Antworten werden nicht als
  dauerhafte App-Logs geführt. Keine fremden Sitzungen werden durchsucht.

## Vorhandener Zugang

Die lokale Antigravity-CLI wurde über ihre Hilfe und die Modellliste geprüft:
angemeldet, gewähltes `gemini-3.8-flash-high` angeboten, Zusatzcredits aus.
Ein Gemini-API-Schlüssel ist nicht eingerichtet (nur Vorhandensein geprüft).
Keine Zugangsdaten, Kontonamen, Kontingentwerte oder vollständigen Antworten gespeichert.
Vor dem Adapterbau gab es keine echte Bild-/Visionanfrage. Inzwischen wurden
notwendige eigene Google-Bildproben durchgeführt; kein Testvideo erzeugt.

Google dokumentiert Bildgenerierung als eingebautes Agentenwerkzeug. Ein offizielles
SDK-Beispiel begrenzt die Fähigkeiten auf `GENERATE_IMAGE`; damit ist ein fester
Aufruf technisch dokumentiert, intern bleibt es eine Agentenlaufzeit. Ein sicherer
Bildadapter für diese App ist dadurch allein nicht nachgewiesen. Der neue Bildweg
verwendet die vorhandene CLI; der bisherige strukturierte Skriptweg bleibt erhalten.
Keine Freigabe allgemeiner Werkzeuge,
kein `dangerously-skip-permissions`, keine Konto- oder Schutzänderung.
Die direkte Gemini-Bild-API ist ein separater Zugang ohne kostenlosen Bildtarif;
Google-AI-Pro-Anmeldung und API-Abrechnung sind nicht gleichzusetzen.

Nutzerentscheidung: **keine zusätzlichen Kosten**, bevorzugt vorhandenes Abo;
Antigravity/CLI oder Browser dürfen als Bildweg untersucht werden. Ohne Abo
soll eine kostenlose Alternative möglich sein. Das ist keine Freigabe für neue
Tarife, Zusatzcredits oder das Umgehen von Kontingenten. B03 bleibt bis zum
technischen Nachweis offen. Cloudflare-Adapter und Google-CLI-Adapter sind eingebaut;
kein neues Konto, Token, SDK, lokales Modell oder Bezahltarif wurde eingerichtet.
Cloudflare benötigt noch Nutzereinrichtung und Live-Abnahme; der vollständige
Stil-/Visionnachweis ist weiterhin offen.

## Recherche: Bildwege ohne zusätzliche Kosten

Herstellerangaben vom 16.10.2026; keine Anmeldung, Bildgenerierung oder Installation
für diese Recherche. Kontingente können sich ändern. Kein geprüfter Dienst
verspricht hier unbegrenzte kostenlose Bilder.

| Weg | Zugang/Kosten | Eignung für Frame |
| --- | --- | --- |
| Antigravity | Vorhandenes Google-Konto/Abo, planabhängige Limits; Zusatzcredits müssen aus bleiben. | Bevorzugter Prüfkandidat. Offizielles SDK mit Bildwerkzeug; konkrete Konto-, Laufzeit- und Kostenkontrolle noch offen. |
| Cloudflare Workers AI / FLUX.1 schnell | Eigenes Konto, Account-ID und API-Token. Free: 10.000 Neurons/Tag; bei Erschöpfung Fehler statt bezahlter Mehrnutzung. | Offizielle REST-API als kostenlose automatische Alternative. Keine öffentliche lokale Portfreigabe nötig. Bildstil und Figurenkonsistenz noch ungeprüft; keine feste Bilderzahl aus dem Rechenkontingent ableiten. |
| Gemini / Flow im Browser | Google-Anmeldung; kostenlose und Abo-Zugänge mit Limits. Flow dokumentiert Nano Banana 2 Lite als kostenlosen Bildmodus. | Manueller Kandidat. Aktives Modell/Kosten prüfen; automatischer Hintergrundbetrieb nicht nachgewiesen. |
| Lokales Qwen-Image oder Z-Image-Turbo | Offene Modellgewichte (Apache 2.0), keine Anbietergebühr pro Aufruf; eigene Rechenleistung, Speicher und Strom nötig. | Automatisierbar, aber zuerst Hardware und tatsächlichen Downloadbedarf prüfen. Kein Modell heruntergeladen. |

**Ursprüngliche Empfehlung vom 16.10., inzwischen Adapter eingebaut:** vorhandenes Antigravity
auf einen ausschließlich auf Bilder begrenzten Zugang prüfen; Cloudflare-Free als
API-Alternative vorsehen; lokale Modelle bei geeigneter Hardware. Browser bleibt
eine mögliche Ergänzung. Kein stiller Anbieterwechsel: Prompts verlassen dabei
jeweils den Rechner zum gewählten Anbieter. Zugangsdaten gehören in den OS-Tresor.

Vor einem Antigravity-Probelauf: Werkzeuge bereits vor Ausführung sperren, nur den
benötigten Bildweg zulassen; feste eigene Arbeits-/Ausgabeverzeichnisse, begrenzte
Versuche und Abbruch. Aktuelle CLI-Versionen können intern einen Bild-Unteragenten
verwenden; eine allgemeine Agenten-/Shell-/Browserfreigabe ist kein Ersatz für
diesen Nachweis. SDK-Verhalten bei ausgeschalteten Zusatzcredits separat prüfen;
die vorhandene CLI-Einstellung allein beweist das nicht. Die App steuert weiterhin
die feste Pipeline. Kontingentfehler müssen sichtbar pausieren, ohne Tarifwechsel,
Credit-Zukauf oder Konto-/Sitzungswechsel zur Limitumgehung.

## Einstellungen und Bedienung

- Einstellungen → **Frame · KI-Bilder** bietet die beiden oben beschriebenen Zugänge.
- „Gespeicherten Zugang prüfen“ liest Konfiguration und ggf. die Modellliste; lokale
  Token-/Origin-Prüfung, begrenzte öffentliche Statusfelder, keine Bildgenerierung.
- Skript-Anmeldung, Bildbereitschaft und Vision-Nachweis werden nicht verwechselt.
- Zwei Reiter **Animierte Strichmännchen** / **Frame**, Aufträge je Modus gefiltert.
  Altaufträge ohne Modus bleiben animiert. Keine Aufträge oder Dateien gelöscht.
- Frame zeigt den Aufbauzustand. Produktion bleibt im Backend wie zuvor gesperrt,
  bis die späteren Bild-/Audio-/Schnittschritte einschließlich B10 funktionieren.
- Erstellungsdialog verwendet die gespeicherten Einstellungen. Profil-/Cloud-/Stock-/
  Podcast-/MoneyPrinter-Menüs entfallen; technische gespeicherte Konfiguration bleibt
  für bestehende Versionen erhalten. Stimmenänderungen verändern nicht heimlich den
  Skriptanbieter. Unverfügbare alternative Stimmen sind aus der Auswahl entfernt;
  eine bereits gewählte fehlende Stimme bleibt mit Einrichtungsgrund sichtbar.
- Tabwechsel schützt offene Änderungen; verspätete Jobantworten überschreiben nicht
  den inzwischen geöffneten anderen Reiter. Tastatursteuerung und schmale Fenster.

## Quellen

Herstellerquellen, geprüft am 16./17.10.2026:
- [Antigravity SDK: Bildgenerierung als Werkzeug](https://www.antigravity.google/blog/introducing-google-antigravity-sdk)
- [Antigravity: Werkzeugberechtigungen](https://antigravity.google/docs/settings)
- [Gemini Bild-API](https://ai.google.dev/gemini-api/docs/image-generation)
- [Gemini API: Preise und fehlender kostenloser Bildtarif](https://ai.google.dev/gemini-api/docs/pricing)
- [Offizielles Antigravity-SDK: Bildbeispiel mit eingeschränkten Fähigkeiten](https://github.com/google-antigravity/antigravity-sdk-python/blob/main/examples/getting_started/multimodal.py)
- [SDK-Werkzeugregeln](https://antigravity.google/docs/sdk/policies/), [CLI-Hooks](https://www.antigravity.google/docs/hooks), [CLI-Änderungen](https://www.antigravity.google/docs/changelog?tab=cli)
- [Antigravity-Pläne](https://antigravity.google/docs/plans), [Zusatzcredits](https://antigravity.google/docs/cli/credits)
- [CLI: eigene Agenten mit eingeschränkten Werkzeugen](https://antigravity.google/docs/subagents/)
- [Cloudflare: Freikontingent und Begrenzung](https://developers.cloudflare.com/workers-ai/platform/pricing/), [FLUX.1 schnell](https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/), [REST-Zugang](https://developers.cloudflare.com/workers-ai/get-started/rest-api/)
- [Gemini: aktuelle Nutzungslimits](https://support.google.com/gemini/answer/16275805?hl=de)
- [Flow: Bildmodelle](https://support.google.com/flow/answer/16352836?hl=en-0)
- [Qwen-Image](https://github.com/QwenLM/Qwen-Image), [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)

## Prüfung

Simulierte Konto-/UI-Antworten: Skriptanmeldung ist kein Bild-/Visionnachweis;
fremder Origin und fehlender Setup-Token erreichen den Prüfer nicht. Keine privaten
Anbietermetadaten in der Antwort. Reiterfilter, Legacy-Aufträge, offene Änderungen,
späte Antworten, unveränderte Produktionsauswahl und sichere Textausgabe geprüft.

Aktuell: 354 Backend-Tests (10 Plattform-/Umgebungs-Skips), 74 JavaScript-Tests
bestanden. Darunter native Rasterdekodierung, Token-/Origin-/Schema-Prüfung,
SSRF-/Redirect-Gegenfälle, sichere Google-Quelldateiauswahl, JSON-/Metadaten-
Varianten der Hooks, unerlaubte Werkzeuge, Doppelaufruf und Abbruch ohne Film.

Native Windows-Abnahme: `data/desktop/acceptance-normal-1792250783779202100/result.json`.
Beide Reiter, schmales Fenster, bestehende Einstellungen und regulärer Start/Stopp;
nur `127.0.0.1:8080`, keine eigenen Prozessreste. Isolierte Daten, kein Film.

Bei notwendigen Google-Proben wurden Windows-Hook-Aufrufe mit Leerzeichen im
Pfad korrigiert; CLI-Anzeigefelder `toolAction`/`toolSummary` werden begrenzt
behandelt. Der eigene Hauptagent stellt ausschließlich das Bildwerkzeug bereit.
Die CLI kann ohne `structured_output` erfolgreich enden; deshalb verwendet der
Export den eigenen Bildnamen im eigenen Sitzungsordner, keine Freitextpfade.
Unerlaubte Shell-Versuche wurden im Liveversuch vor Ausführung blockiert. Eigene
temporäre Rohlogs aus den abgebrochenen Entwicklungsversuchen wurden entfernt;
fremde Sitzungen, Nutzerjobs und Medien blieben erhalten.

Offen: Cloudflare-Token und Live-Abnahme, Bildserien/Stilkonsistenz, echter
Vision-Nachweis in der App und native Linux-/Mac-Bildtests. Keine Sicherheitsgarantie und keine
Behauptung einer bereits funktionsfähigen Frame-Videoproduktion.
