# Familienwege: automatische KI und manueller Webimport

Stand: 14.10.2026. Schritte 12/13 sind technisch implementiert. Der persönliche
Free-Tier-Familienkonto-Test und ein Test auf einem schwächeren physischen Rechner
stehen noch aus. Ein geprüftes Modellangebot beweist keinen bestimmten Kontotarif.

## Automatisch: eigenes Google-Konto in Antigravity

1. Unter **⚙ Einstellungen → Skript-KI und Zugang** die offizielle
   Antigravity-Installation und Konto-Voraussetzungen öffnen.
2. `agy` in einem leeren Ordner starten und im Herstellerdialog mit dem eigenen
   berechtigten Google-Konto anmelden. Ein Pro-Abo ist für den begrenzten
   kostenlosen Individual-Einstieg nicht vorgeschrieben.
3. In `agy` unter `/config` **Use G1 Credits ausschalten**. Unter Einstellungen
   Antigravity wählen, Zugang prüfen, ein angebotenes Modell ausdrücklich wählen
   und speichern. Es werden keine Google-Passwörter oder Tokens in die UI eingetragen.
4. **Neues Video → Sprecher-Skript erstellen**. Änderungswünsche werden automatisch
   verarbeitet. Nach der Textfreigabe plant die Anwendung die Zeichnungen und rendert lokal.

Vor jedem CLI-Aufruf liest die Pipeline ausschließlich die notwendige
Credit-Einstellung aus `~/.gemini/antigravity-cli/settings.json`. `useG1Credits=true`,
ein ungültiger Typ oder eine nicht lesbare/zu große Konfiguration blockieren den
Aufruf. Eine fehlende Einstellung verwendet den dokumentierten Herstellerdefault
`false`. Globale Kontoeinstellungen werden nicht überschrieben. Die CLI bekommt
keine API-/Vertex-Schlüssel oder fremden Agentenvariablen aus der Umgebung.
Anmeldung, Modelle und tatsächliche Basiskontingente verwaltet der Hersteller.
Die lokale Prüfung bestätigt weder Tarif noch verbleibendes Kontingent und ist
keine Abrechnungsgarantie bei extern geänderten Kontoeinstellungen.

Bei Anmelde-, Kontingent- oder Konfigurationsfehlern bleiben gespeicherte Aufträge,
Textversionen und Freigaben erhalten. Neue fehlgeschlagene Entwürfe erzeugen keinen
Teilauftrag; die Idee bleibt im geöffneten Dialog. Der gespeicherte UI-Zugang hat
keinen Qwen-Fallback. Eine Credit-Sperre darf auch einen ausdrücklich konfigurierten
Legacy-Fallback nicht auslösen. Für die Bedienung ist kein steuernder Coding-Agent nötig.

**Quellenentscheidung:** Die allgemeine Gemini-CLI-Anmeldung und Quota-Seite nennt
weiterhin Consumer-Zugänge. Googles spezifische, am 09.10.2026 aktualisierte
Abkündigung erklärt dagegen, dass diese seit 18.06.2026 eingestellt sind.
Deshalb wird Gemini CLI hier nicht als kostenloser Familienzugang angeboten.
Der historische Profilpool bleibt eingefroren; es werden keine Konten zur Limitumgehung gewechselt.

- [Google: Consumer-Abkündigung, einschließlich Gemini CLI](https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals)
- [Antigravity: berechtigte Konten und Pläne](https://antigravity.google/docs/plans)
- [Antigravity: kostenlose Individual-Option](https://www.antigravity.google/pricing)
- [CLI-Anmeldung und Installation](https://antigravity.google/docs/cli/install)
- [Credit-Schalter](https://antigravity.google/docs/cli/credits/)
- [Konfigurationspfad](https://antigravity.google/docs/cli/features/)
- [CLI-Defaults](https://antigravity.google/docs/cli/reference/)

## Manuell: Web-KI ohne installierten Skriptdienst

1. Unter Einstellungen **Web-KI · manuell kopieren und einfügen** speichern.
   Alternativ nur für diesen Auftrag unter **Neues Video → Stimme und Herstellung
   ändern → Produktionsprofil** auswählen. Piper und Schnittwerkzeuge müssen bereit sein.
2. Idee und Länge eingeben, **Web-Prompt vorbereiten** wählen. Prompt kopieren,
   in der gewünschten Web-KI ausführen und die vollständige JSON-Antwort zurückkopieren.
   Dann **Antwort prüfen und Skript übernehmen**. Du liest weiterhin nur den Fließtext.
3. Für Änderungen beschreiben, was verbessert werden soll, und **KI verbessert das
   Skript** wählen. Den neuen Prompt und die neue Antwort genauso übertragen.
   Eine ungültige Antwort ersetzt die bisherige Textfassung nicht.
4. **Text freigeben & Zeichenprompt öffnen**. Den bereitgestellten Zeichenprompt
   in der Web-KI ausführen und die vollständige Antwort einfügen. **Zeichenantwort
   prüfen & Video erzeugen** startet nach erfolgreicher Prüfung die lokale Produktion.
   Eine Kontrolle/Freigabe einzelner Szenen ist nicht nötig.
5. Das fertige Video prüfen und herunterladen.

Anmeldungen und Limits gelten auf der gewählten Webseite. Der Prompt enthält den
eigenen Text; nur Inhalte übertragen, die dort verarbeitet werden dürfen. Keine
automatische Webseitenbedienung, Captcha-Lösung, Anmeldung oder Limitumgehung.
Dieser Weg ist ausdrücklich manuell und eröffnet keinen neuen lokalen Netzwerkdienst.

## Prüfgrenzen und API-Vertrag

Webtexte erhalten keine Werkzeuge oder Systemrechte. Nur ein JSON-Objekt oder ein
einzelner JSON-Codeblock wird akzeptiert. Doppelte Schlüssel, NaN/Infinity, übermäßige
Verschachtelung, Zusatzfelder, fremder Modellcode sowie externe Medienpfade werden
abgewiesen. Bestehende Wortbudget-, Text-, Zeichen-, Motiv-, Sprachanker- und
Kontinuitätsprüfungen bleiben aktiv. Sprecherwörter und Interpunktion im Zeichenplan
müssen genau der aktuellen freigegebenen Fassung entsprechen.

| POST-Endpunkt | Eingabe / Wirkung |
|---|---|
| `/api/jobs/web-prompt` | `request` mit `JobCreate`; nur Textprompt, kein KI-Aufruf |
| `/api/jobs/web-import` | derselbe `request` mit UUID `generation_id`, plus `response`; versionierter Entwurf, idempotent |
| `/api/jobs/{id}/web-revision-prompt` | `expected_version`, `expected_hash`, `instructions`; Überarbeitungsprompt |
| `/api/jobs/{id}/web-revision-import` | dieselben Felder plus `response`; neue Fassung, alte Freigaben entwertet |
| `/api/jobs/{id}/web-board-prompt` | `expected_version`, `expected_hash`; aktuelle Textfreigabe und Zeichenprompt |
| `/api/jobs/{id}/web-board-import` | dieselben Felder plus `response`; geprüfter Bildplan und Renderanspruch atomar gespeichert |

Nur `web_import` mit dem aktiven Strichmenschen-Verfahren ist erlaubt. Textantworten
sind auf 100.000, Zeichenantworten auf 300.000 Zeichen, HTTP-Bodies auf 1,5 MB begrenzt.
HTTP 422: ungültige Inhalte; 409: veraltete Version/fehlende Freigabe/belegter Auftrag;
413: zu großer Body; 403: fremde Origin/Host/Clients. Gleiche Wiederholungen erzeugen
keinen zweiten Auftrag/Render; abweichende Inhalte derselben Importkennung werden abgewiesen.
Eine spätere Veröffentlichung behält ihre eigene Freigabe.

## Nachweis dieser Umsetzung

- Provider- und Negativtests für Credit-Schalter, fremde Umgebungsschlüssel,
  Anmelde-/Quotenfehler, Schema-/Motivfehler und Versions-/Freigabebindung.
- Echte Antigravity-CLI 1.3.4, bestätigtes `gemini-3.8-flash-high`: strukturierte
  Testantwort erfolgreich mit dem neuen Umgebungsfilter und geprüftem
  `useG1Credits=false`. Kein Konto-/Credit-Schalter geändert; der vorhandene
  Nutzerzugang beweist keinen kostenlosen Familienkontotarif.
- Echter Browserablauf: ungültige Antwort korrigierbar, Textimport, Änderungswunsch,
  neue Textversion, blockierte Textänderung im Bildplan, Sprachankerprüfung,
  lokale Produktion und Player. Keine Browser-Konsolenfehler.
- Genau ein notwendiges Import-Abnahmevideo: Auftrag
  `d8bdb271-6a21-51bb-8083-f941dad22f27`, Version 3, 25,02 s, 1920×1080,
  H.264/AAC, Qualitätsgate bestanden, Peak −1,5 dBFS, Clipping 0,
  längste innere Pause 0,24 s. Die Antwort war eine ausdrücklich gekennzeichnete
  Testfixture; keine neue Web-KI-Antwort oder Familienanmeldung wird behauptet.
  Nachweise liegen ignoriert unter `data/acceptance-12-13/`.
- Fremde Webseiten und DNS-Rebinding-Hostnamen werden jetzt für die gesamte
  lokale Pipeline abgewiesen. Keine Firewall-/Port-/Tarifänderungen oder neuen Pakete.
- Zwei bestehende Qwen-Worker-/Timeouttests verwenden ein festes simuliertes
  RAM-Budget; Produktions-RAM-Sperre und deren Negativtest bleiben unverändert.
- Ein Windows-Verbindungsreset hielt die eigene, bereits leerlaufende Serverinstanz
  im Shutdown fest. Nach Prüfung von PID, Starterregister und Auftragsstatus beendet.
  Der Starter begrenzt jetzt das Drain von HTTP-Verbindungen auf 30 s; der laufende
  Renderworker wird weiterhin über seinen bestehenden geordneten Abschluss behandelt.

Offen: tatsächlicher Free-Tier-Lauf mit dem eigenen Familienkonto, Test der
ausgewählten Web-KI durch deren Nutzer sowie Laufzeit/Hörabnahme auf einem
schwächeren physischen Rechner. Die Quellenprüfung und simulierte Geräteprüfung
ersetzen diese Abnahme nicht.
