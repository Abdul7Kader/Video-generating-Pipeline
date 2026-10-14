# Konten und Anmeldungen

Quellenstand: 14.10.2026. Angaben des Anbieters können sich ändern.

| Weg | Anmeldung | Abo und Grenzen |
| --- | --- | --- |
| Antigravity CLI für Skripte | Eigenes berechtigtes persönliches Google-Konto | Kostenloses begrenztes Basiskontingent; Pro/Ultra optional. Ohne Abo wöchentliche Grenzen. Modelle werden pro Konto geprüft. |
| Ollama für lokale Skripte | Keine | Kein Abo; Modellinstallation, ausreichend RAM und Rechenzeit nötig. |
| Piper/Qwen für Sprache | Keine | Lokal; kein Cloud-TTS-Abo. Modellinstallation und passende Hardware nötig. |
| Remotion/FFmpeg für Zeichnung und Schnitt, lokaler Download | Keine Anbieteranmeldung | Lokal. Remotion kostenlos für Einzelpersonen/Firmen bis 3 Personen; größere Firmen benötigen eine Lizenz. |

In **Einstellungen → 3 · Skript-KI und Zugang → Konten und Anmeldungen** stehen
die tatsächlich eingebauten Wege. Google verlangt derzeit mindestens 18 Jahre
und eine unterstützte Region; Workspace-Konten können abweichen. Deutschland
steht in der unterstützten Länderliste. Ein Pro-Abo ist keine Voraussetzung
für den Einstieg und garantiert umgekehrt kein bestimmtes verfügbares Modell.

Antigravity über die Herstelleranleitung installieren, `agy` im eigenen Terminal
in einem leeren Ordner starten und die Google-Anmeldung im Herstellerfenster abschließen. Danach in
der Pipeline Antigravity auswählen, **Gewählten KI-Zugang prüfen**, eines der
angebotenen Modelle wählen und **Auswahl speichern und verwenden** drücken.
Es erfolgt keine automatische Modell-/Kontoumschaltung.

**Bereit** bedeutet bestätigte Anmeldung und Modellangebot, keine Prüfung von
Tarif, Restkontingent oder kostenloser Abrechnung. Das Restkontingent beim
Anbieter mit `/usage` ansehen. Für einen Weg ohne Zusatzkosten dort
**AI Credit Overages: Never / Use AI Credits: off** wählen. Die Pipeline
ändert diese Kontoeinstellung nicht und kauft keine Credits. Bei ausgeschöpftem
Kontingent bleibt die Arbeit erhalten; Grenzen werden nicht durch weitere
Fenster oder Kontowechsel umgangen.

Passwörter, OAuth-Codes und Schlüssel werden nicht in Pipeline-Formulare
eingetragen. Die offizielle CLI verwaltet ihre eigene Sitzung über den
Betriebssystem-Schlüsselspeicher. Die Pipeline zeigt weder E-Mail-Adressen noch
Anmeldetokens an. Der automatische Skriptlauf nutzt einen isolierten temporären
Ordner mit dem Ausgabeschema; die reguläre Anmeldung sollte ebenfalls nicht in
einem privaten Dokument-/Projektordner begonnen werden. Für Antigravity werden die jeweiligen Skript-/Bildplanprompts
an Google übertragen. Ollama, Stimme und Rendering bleiben lokal.

Gemini-Webimport und zusätzliche Free-Tier-API-Adapter sind **Schritt 12/13**.
Eine Anmeldung auf einer Webseite verbindet diese nicht mit der Pipeline.
Ein echter Test mit dem kostenlosen Familienkonto erfolgt durch dessen Inhaber;
der vorhandene Zugang auf diesem Rechner belegt keinen bestimmten Kontotarif.

Offizielle Quellen:

- [Antigravity: Kontingente und optionale Abos](https://antigravity.google/docs/plans)
- [Antigravity: Individual ohne Abo](https://www.antigravity.google/pricing)
- [CLI-Installation und reguläre Anmeldung](https://antigravity.google/docs/cli/install)
- [Konto-, Alters- und Regionsvoraussetzungen](https://antigravity.google/docs/faq)
- [Kontingentanzeige](https://antigravity.google/docs/cli/commands/usage/)
- [Credit-Einstellung](https://www.antigravity.google/docs/cli/credits/)
- [Remotion-Lizenz und Firmengröße](https://www.remotion.dev/docs/license/pricing)
