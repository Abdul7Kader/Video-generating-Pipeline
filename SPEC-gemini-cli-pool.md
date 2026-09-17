# Capability Map: Gemini-CLI-Skriptproduktion

| Modul | Verantwortung | Abhängigkeit |
|---|---|---|
| `profile-isolation` | Offizielle CLI, getrennte `GEMINI_CLI_HOME`-Verzeichnisse, restriktive Rechte, keine Secrets in App/DB/Git | — |
| `cli-runner` | Tool-loser Headless-Aufruf, JSON-Ausgabe, Timeout, Fehlerklassifikation und Cooldown | `profile-isolation` |
| `checkpoint-workflow` | Fünf persistente, hashgebundene Produktionsschritte und Wiederaufnahme | `cli-runner` |
| `profile-status-ui` | Nicht-sensitive Zustände und Schrittergebnisse in API/Oberfläche | `checkpoint-workflow` |

Build-Reihenfolge: `profile-isolation` → `cli-runner` → `checkpoint-workflow` → `profile-status-ui`.

# Spezifikation: Gemini-CLI-Profilpool

## Ziel

Die Pipeline darf hochwertige Skripte über die offizielle Gemini CLI 0.60.x erzeugen, wenn ein offiziell unterstütztes Profil regulär und interaktiv angemeldet werden kann. Bereits abgeschlossene Schritte werden nicht wiederholt. Das lokale Qwen3.5 9B Q8 bleibt jederzeit der offline verfügbare Standard und Ersatz.

Aktuelle Produktgrenze (Live-Test 2026-09-17): Google hat Gemini-CLI-Consumerzugang für Gemini Code Assist Individual, Google AI Pro und Google AI Ultra am 18. Juni 2026 eingestellt. Der vorhandene Pro-Login wird serverseitig mit `This client is no longer supported for Gemini Code Assist for individuals` abgewiesen. Gemini CLI bleibt für Code Assist Standard/Enterprise unterstützt; für Consumer-Konten nennt Google Antigravity CLI als Nachfolger. Eine Migration dorthin ist nicht Teil dieser Spezifikation und braucht eine neue ausdrückliche Entscheidung.

Der Pool ist für Verfügbarkeit autorisierter Profile gedacht, nicht zum Behaupten unbegrenzter Tokens oder zum Umgehen von Schutzmechanismen. Eine exakte Restquote wird nur angezeigt, falls die CLI sie künftig zuverlässig und dokumentiert liefert; aktuell wird sie nicht behauptet.

## Offizielle Schnittstellen

- Installation: `npm install -g @google/gemini-cli`
- Interaktive Anmeldung: `gemini` und „Sign in with Google“.
- Profilisolation: je Profil ein eigenes, offiziell dokumentiertes `GEMINI_CLI_HOME`; die CLI legt darin `.gemini` an.
- Verarbeitung: Headless-JSON über stdin und `--output-format json`; vorhandene gecachte Anmeldung darf laut offizieller Authentifizierungsdokumentation verwendet werden.
- Sicherheit: Benutzer-Policy verweigert alle CLI-Tools. Der Arbeitsordner ist ein leeres, profilspezifisches Verzeichnis und nicht das Projekt.

Quellen:

- https://geminicli.com/docs/get-started/authentication/
- https://geminicli.com/docs/reference/configuration/
- https://geminicli.com/docs/cli/headless/
- https://geminicli.com/docs/reference/policy-engine/
- https://geminicli.com/docs/cli/enterprise/
- https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals

## Profilvertrag

- Zulässige Profilnamen: `[a-z0-9][a-z0-9_-]{0,31}`.
- Profilnamen kommen ausschließlich aus `GEMINI_CLI_PROFILES`; Tokens und Cookies niemals.
- Profildaten liegen standardmäßig unter `%LOCALAPPDATA%\VideoPipeline\gemini-profiles\<profil>` und niemals im Repository.
- Das Profilverzeichnis erhält unter Windows eine ACL ausschließlich für den aktuellen Benutzer und `SYSTEM`.
- UI/API geben nur Profilname, Status, letzten Erfolg, kategorisierten letzten Fehler und Cooldown-Zeit aus.
- Die Auswahl ist atomar. Ein Profil kann höchstens einen aktiven Modellaufruf besitzen.
- Authentifizierungsfehler deaktivieren das Profil bis zur manuellen Neuanmeldung. Temporäre Kapazitäts-/Ratenfehler respektieren eine dokumentierte Abkühlung; andernfalls wird eine begrenzte konservative Abkühlung verwendet.

## Verarbeitungsschritte

1. `briefing`: Themenbriefing.
2. `outline`: Skriptstruktur.
3. `narration`: vollständiges Sprecher-Skript.
4. `scene_plan`: Szenen- und Medienplan im vorhandenen Skriptschema.
5. `quality_review`: strukturierte Qualitätsprüfung und abschließende Schema-Prüfung.

Jeder abgeschlossene Schritt speichert: kanonischen Eingabehash, strukturierte Ausgabe, Ausgabehash, Modell, Profilname, Prompt-Version und Zeitstempel. Ein Kontowechsel ändert keine vorhandene Ausgabe und damit keine Freigabe. Erst eine inhaltlich neue Endausgabe erzeugt eine neue Skriptversion.

## Wiederaufnahme und Idempotenz

- Derselbe Auftragsschlüssel und Schritt dürfen nur einmal erfolgreich gespeichert werden.
- Ein beim Neustart als `running` vorgefundener Schritt wird `interrupted`; seine gespeicherte Eingabe bleibt unverändert und darf mit einem anderen Profil neu gestartet werden.
- Nur vollständig parse- und schema-validierte Antworten werden als abgeschlossen gespeichert.
- Nach `quality_review` entsteht genau eine Skriptversion. Videoerzeugung bleibt durch die bestehende hashgebundene Benutzerfreigabe gesperrt.

## Befehle

- Tests: `.\.runtime\windows-python\Scripts\python.exe -m unittest discover -s tests -q`
- Python-Syntax: `.\.runtime\windows-python\Scripts\python.exe -m compileall -q backend`
- JavaScript-Syntax: `node --check web\app.js`
- CLI-Version: `gemini --version`

## Grenzen

- Keine Browserautomatisierung, Cookie-Kopie, API-Schlüssel-Rotation oder kostenpflichtige Gemini API.
- Keine Passwörter/Tokens in Browser, App-Konfiguration, SQLite, Logs oder Git.
- Kein Shell-, Datei-, Browser-, MCP- oder anderer Toolzugriff für den von der Pipeline gestarteten Gemini-Prozess.
- Keine öffentlichen Ports.
- Reguläre Google-Anmeldungen erfolgen ausschließlich durch den Benutzer im interaktiven CLI-Fenster.

## Abnahmekriterien

- Qwen Q8 ist in `/api/health` bereit und kann unabhängig von Gemini verwendet werden.
- Ein angemeldetes Profil liefert eine schema-valide Testantwort über den tool-losen Runner.
- Zwei simulierte Profile beweisen: Fehler/Cooldown von Profil A, identische Eingabe und Fortsetzung mit Profil B, kein Wiederholen abgeschlossener Schritte.
- Neustart setzt nur unvollständige Schritte fort; doppelte Endversionen/Freigaben entstehen nicht.
- Gesamttests, Syntaxprüfungen, Secret-Prüfung, Commit und Push des Feature-Branches sind erfolgreich.
