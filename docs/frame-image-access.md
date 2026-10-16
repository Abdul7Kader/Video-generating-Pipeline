# Frame: Bildzugang und Oberfläche · B03/B04

Nachtrag B05/B06: Frame kann inzwischen Texte und Bildpläne vorbereiten.
[Betriebsumfang und Nachweise](frame-text-and-planning.md). Der fehlende Bildzugang
und die weiterhin gesperrte Medienproduktion ändern sich dadurch nicht.


Stand: 16.10.2026. **B04 umgesetzt; B03 teilweise geprüft, nicht abgeschlossen.**

## Vorhandener Zugang

Die lokale Antigravity-CLI wurde über ihre Hilfe und die Modellliste geprüft:
angemeldet, gewähltes `gemini-3.8-flash-high` angeboten, Zusatzcredits aus.
Ein Gemini-API-Schlüssel ist nicht eingerichtet (nur Vorhandensein geprüft).
Keine Zugangsdaten, Kontonamen, Kontingentwerte oder vollständigen Antworten gespeichert.
Keine echte Bild-/Visionanfrage und keine Videoerzeugung durchgeführt.

Google dokumentiert Bildgenerierung als eingebautes Agentenwerkzeug. Ein offizielles
SDK-Beispiel begrenzt die Fähigkeiten auf `GENERATE_IMAGE`; damit ist ein fester
Aufruf technisch dokumentiert, intern bleibt es eine Agentenlaufzeit. Ein sicherer
Bildadapter für diese App ist dadurch noch nicht nachgewiesen. Die bisherige CLI-Anbindung
bleibt beim begrenzten strukturierten Skriptweg; keine Freigabe allgemeiner Werkzeuge,
kein `dangerously-skip-permissions`, keine Konto- oder Schutzänderung.
Die direkte Gemini-Bild-API ist ein separater Zugang ohne kostenlosen Bildtarif;
Google-AI-Pro-Anmeldung und API-Abrechnung sind nicht gleichzusetzen.

Nutzerentscheidung: **keine zusätzlichen Kosten**, bevorzugt vorhandenes Abo;
Antigravity/CLI oder Browser dürfen als Bildweg untersucht werden. Ohne Abo
soll eine kostenlose Alternative möglich sein. Das ist keine Freigabe für neue
Tarife, Zusatzcredits oder das Umgehen von Kontingenten. B03 bleibt bis zum
technischen Nachweis offen. Kein neuer Bildanbieter, API-Schlüssel, SDK, Modell
oder Bezahltarif wurde eingerichtet. Der echte Adapter und eine
notwendige Stil-/Visionprobe sind ausdrücklich **noch nicht umgesetzt/nachgewiesen**.

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

**Empfohlene Reihenfolge, noch keine Implementierung:** vorhandenes Antigravity
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

- Einstellungen → **Frame · KI-Bilder** erklärt den fehlenden Zugang und seine Bedingungen.
- „Vorhandenen Zugang prüfen“ ruft nur die vorhandene Modellliste ab; lokale
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

Herstellerquellen, geprüft am 16.10.2026:
- [Antigravity SDK: Bildgenerierung als Werkzeug](https://www.antigravity.google/blog/introducing-google-antigravity-sdk)
- [Antigravity: Werkzeugberechtigungen](https://antigravity.google/docs/settings)
- [Gemini Bild-API](https://ai.google.dev/gemini-api/docs/image-generation)
- [Gemini API: Preise und fehlender kostenloser Bildtarif](https://ai.google.dev/gemini-api/docs/pricing)
- [Offizielles Antigravity-SDK: Bildbeispiel mit eingeschränkten Fähigkeiten](https://github.com/google-antigravity/antigravity-sdk-python/blob/main/examples/getting_started/multimodal.py)
- [SDK-Werkzeugregeln](https://antigravity.google/docs/sdk/policies/), [CLI-Hooks](https://www.antigravity.google/docs/hooks), [CLI-Änderungen](https://www.antigravity.google/docs/changelog?tab=cli)
- [Antigravity-Pläne](https://antigravity.google/docs/plans), [Zusatzcredits](https://antigravity.google/docs/cli/credits)
- [Cloudflare: Freikontingent und Begrenzung](https://developers.cloudflare.com/workers-ai/platform/pricing/), [FLUX.1 schnell](https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/), [REST-Zugang](https://developers.cloudflare.com/workers-ai/get-started/rest-api/)
- [Gemini: aktuelle Nutzungslimits](https://support.google.com/gemini/answer/16275805?hl=de)
- [Flow: Bildmodelle](https://support.google.com/flow/answer/16352836?hl=en-0)
- [Qwen-Image](https://github.com/QwenLM/Qwen-Image), [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)

## Prüfung

Simulierte Konto-/UI-Antworten: Skriptanmeldung ist kein Bild-/Visionnachweis;
fremder Origin und fehlender Setup-Token erreichen den Prüfer nicht. Keine privaten
Anbietermetadaten in der Antwort. Reiterfilter, Legacy-Aufträge, offene Änderungen,
späte Antworten, unveränderte Produktionsauswahl und sichere Textausgabe geprüft.

329 Backend-Tests (10 Plattform-/Umgebungs-Skips), 69 JavaScript-Tests bestanden.

Native Windows-Abnahme: `data/desktop/acceptance-normal-1792176971397096100/result.json`.
Beide Reiter, schmales Fenster, bestehende Einstellungen und regulärer Start/Stopp;
nur `127.0.0.1:8080`, keine eigenen Prozessreste. Isolierte Daten, kein Film.
Der erste Versuch startete wegen einer bereits offenen eigenen App keine zweite
Instanz; nach bestätigtem Leerlauf regulär geschlossen und isoliert geprüft.

Offen: technische Anbieterauswahl nach obiger Kostenentscheidung, echter Bildadapter, Einrichtung falls nötig,
Live-Stilprobe und echter Vision-Nachweis. Keine Sicherheitsgarantie und keine
Behauptung einer bereits funktionsfähigen Frame-Videoproduktion.
