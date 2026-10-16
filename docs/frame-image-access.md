# Frame: Bildzugang und Oberfläche · B03/B04

Stand: 16.10.2026. **B04 umgesetzt; B03 teilweise geprüft, nicht abgeschlossen.**

## Vorhandener Zugang

Die lokale Antigravity-CLI wurde über ihre Hilfe und die Modellliste geprüft:
angemeldet, gewähltes `gemini-3.8-flash-high` angeboten, Zusatzcredits aus.
Ein Gemini-API-Schlüssel ist nicht eingerichtet (nur Vorhandensein geprüft).
Keine Zugangsdaten, Kontonamen, Kontingentwerte oder vollständigen Antworten gespeichert.
Keine echte Bild-/Visionanfrage und keine Videoerzeugung durchgeführt.

Google dokumentiert Bildgenerierung als eingebautes Agentenwerkzeug. Daraus folgt
kein fester, agentenfreier Bildadapter für diese App. Die bisherige CLI-Anbindung
bleibt beim begrenzten strukturierten Skriptweg; keine Freigabe allgemeiner Werkzeuge,
kein `dangerously-skip-permissions`, keine Konto- oder Schutzänderung.
Die direkte Gemini-Bild-API ist ein separater Zugang ohne kostenlosen Bildtarif;
Google-AI-Pro-Anmeldung und API-Abrechnung sind nicht gleichzusetzen.

Die Anbieterentscheidung wurde beim Nutzer angefragt: kostenlos/offen lassen,
direkte API erst nach eigener Einrichtung, oder lokales Bildmodell prüfen.
Bis zur Entscheidung bleibt B03 offen. Kein neuer Bildanbieter, API-Schlüssel,
SDK, Modell oder Bezahltarif wurde eingerichtet. Der echte Adapter und eine
notwendige Stil-/Visionprobe sind ausdrücklich **noch nicht umgesetzt/nachgewiesen**.

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

Offen: Anbieterentscheidung, echter Bildadapter, Anmeldung/Kostenfreigabe falls nötig,
Live-Stilprobe und echter Vision-Nachweis. Keine Sicherheitsgarantie und keine
Behauptung einer bereits funktionsfähigen Frame-Videoproduktion.
