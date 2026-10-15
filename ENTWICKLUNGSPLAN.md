# Entwicklungsplan für die Strichmännchen-Pipeline

Stand: 2026-10-16. Vom Nutzer gewünschte Reihenfolge: zuerst die Originalversion fertigstellen, erst danach die Familienversion ohne Pro-Abos. Vorhandene Funktionen werden geprüft und verbessert; andere Videoarten bleiben ausgeblendet.

Aktuelle Ergänzung: Desktop-Start/Stopp, Einzelabbruch, geschützte Kontoeinrichtung,
Videoordner und Discord-Abnahme technisch umgesetzt. Freigabe verteilt über
offizielle Zieladapter; TikTok bleibt eine Inbox-Übergabe mit finalem Posten in der
App. Live-Kontenabnahme offen. [Anleitung und Grenzen](docs/review-distribution.md).

Arbeitsstand: Schritte 1–9 technisch umgesetzt; Schritt 10 als technische
Mehrthemenprüfung mit vier Filmen und allgemeinen Pipelinekorrekturen abgeschlossen.
249 Backend-Tests (1 Skip), 35 Renderer- und 16 JS-Tests sowie TypeScript bestanden;
aktueller npm-Produktionsaudit nach Nutzerfreigabe: 0 bekannte Schwachstellen.
Die persönliche Sicht-/Hörfreigabe bleibt offen. Schritt 11 ist als Kontenübersicht
mit regulärer Herstelleranmeldung und begrenztem kostenlosem Einstieg implementiert.
Schritte 12/13 technisch umgesetzt: Antigravity-Credit-Sperre und vollständiger
manueller Webimport für Text/Überarbeitung/Zeichenplan. 264 Backend- und 18 UI-Tests,
echter Provideraufruf und ein importiertes 25-s-Video geprüft. Externe Abnahme mit
eigenem Free-Tier-Familienkonto und schwächerem Rechner bleibt offen.
[Anleitung und Grenzen](docs/family-paths.md).
Nachweise: [Mehrthemenprüfung](docs/acceptance-10.md), [Konten](docs/accounts.md).

Bestehende Grundlagen aus 2–9:
Bildabdeckung für eine begrenzte Motivgruppe und Textanker/Ziele, gemeinsame
Kontaktpunkte, Besitzwechsel und dauerhafte Tisch-/Koordinatenablage implementiert.
Aktionen bleiben in ihrem Sprachfenster; Figuren- und Gegenstandszustände werden
über Schnitte geprüft und übernommen. Sprachzeiten sind weiterhin Schätzungen.
Schritt 8: Pausengrenzen erhalten, Hörprobe/Produktion gleich normalisieren, gewählten
Anbieter prüfen; kurze echte Qwen-/Piper-Proben erzeugt, Hörabnahme offen. Schritt 9:
aktiver Einrichtungsweg, optionale Alternativen, verlässliche Bereitschaft und
unbestimmter Fortschritt mit erst später messbarer Restzeit; Browser normal/390 px geprüft.
Keine routinemäßigen Testvideos in der UI; echte Videotests übernimmt der Nutzer
später bzw. am Ende. Nur bei zwingendem Prüfbedarf einer konkreten Änderung eine
Videoprobe erzeugen. Die echte Qualitätsabnahme ist dadurch nicht vorweggenommen.

## Originalversion: Schritte 1–10

1. **KI-Zugang zuverlässig machen.** Unter Einstellungen anzeigen, welcher Skriptanbieter und welches Modell tatsächlich genutzt werden, ob die Anmeldung funktioniert und warum ein Zugang eventuell nicht verfügbar ist.
2. **Einfachen Skriptablauf abschließen.** Ein Prompt ergibt einen durchgehenden Sprechertext. Der Nutzer gibt Änderungswünsche, die KI überarbeitet den Text. Nach einer Skriptfreigabe entstehen Bildplanung und Video automatisch, ohne verpflichtende Einzelszenenfreigaben.
3. **Skriptqualität verbessern.** Verständliche Geschichten mit klarer Handlung, passender Länge und natürlichen Formulierungen erzeugen. Änderungswünsche sollen bestehende Vorgaben erhalten.
4. **Handlung vollständig visualisieren.** Zentrale Figuren, Tiere und Gegenstände sichtbar darstellen und die erzählten Aktionen zeigen. Die Prüfung gilt für unterschiedliche Themen; nicht darstellbare Inhalte werden erkannt und verständlich benannt.
5. **Interaktionen verbessern.** Greifen, Tragen, Ablegen und Streicheln nachvollziehbar animieren; Kontaktpunkte zwischen Händen, Figuren und Gegenständen konsistent halten.
6. **Bewegungen zur Erzählung synchronisieren.** Aktionen an der passenden Textstelle zeigen. Bewegungen werden zügiger und bleiben flüssig und verständlich; unnötige Leerlaufzeiten reduzieren.
7. **Kontinuität sichern.** Figuren, Tiere und Gegenstände über Bildwechsel hinweg erkennbar halten. Zustände, Besitz und Ablageorte dürfen nicht ohne erzählte Ursache wechseln.
8. **Stimme und Sprachfluss verbessern.** Qwen und Piper vergleichen, Aussprache und Lautstärke optimieren und unnötige Pausen reduzieren. Tatsächlich verwendete Stimme und Ressourcenbedarf sichtbar machen.
9. **UI selbsterklärend machen.** Notwendige Einrichtung von optionalen Alternativen unterscheiden. Für jeden Prozess Fortschritt und vergangene Zeit anzeigen; eine Restzeit nur nennen, wenn sie belastbar geschätzt werden kann.
10. **Originalversion vollständig prüfen und pushen.** Mehrere unterschiedliche Videos auf Handlung, Bildqualität, Sprache und Bedienung prüfen. Allgemeine Pipeline-Verbesserungen statt Einzelfixes nachweisen, Fehler beheben, Grenzen dokumentieren und geprüfte Änderungen unter der verifizierten GitHub-Identität Abdul7Kader sichern/pushen.

## Familienversion: erst nach Abschluss von Schritt 10

11. **Kostenlose Anmeldeoptionen ergänzen.** Unter Einstellungen erklären, welche offiziell unterstützten Wege mit einem normalen Google-Konto funktionieren und welche ein optionales Abo benötigen. Anmeldung beim Anbieter und Verbindungsprüfung verständlich zugänglich machen.
12. **Kostenlosen automatischen KI-Zugang integrieren.** Einen zu diesem Zeitpunkt verfügbaren und geprüften API- oder CLI-Zugang mit dem eigenen Konto des Familienmitglieds nutzen. Bei ausgeschöpften Limits den Auftrag behalten und informieren; keine automatische kostenpflichtige Nutzung.
13. **Webversionen als Alternative ermöglichen.** Zunächst Prompt und Ergebnis durch Kopieren/Einfügen übernehmen und validieren. Automatische Browserbedienung anschließend gesondert auf Zulässigkeit und Zuverlässigkeit prüfen. Den Familienablauf auf einem schwächeren Rechner testen; Anmeldung oder Limits nicht durch neue Fenster umgehen.

## Geltende Grenzen

- Die Anwendung läuft ohne Codex oder einen steuernden Coding-Agenten.
- Oberfläche und eigene Dienste bleiben lokal auf Loopback; keine unnötigen Ports, Firewallfreigaben oder Tunnel.
- Zugangsdaten werden nicht im Klartext angezeigt, protokolliert oder versioniert. Modellausgaben erhalten keine Systemrechte.
- Keine automatische Tarif-/Credit-Aktivierung und kein unangekündigter Anbieterwechsel. Kostenlose Angebote und Modellzugänge vor Integration anhand aktueller offizieller Angaben prüfen.
- Vorhandene Daten und Veröffentlichungsfreigaben bleiben erhalten. Allgemeine perfekte Bildabdeckung und garantierte Laufzeiten werden nicht behauptet.

## Zugehörige Arbeitsdateien

Zusätzlicher Nutzerauftrag vom 15.10.2026: bestehende UI als Electron-Anwendung
unter Windows starten; beim Schließen sämtliche eigenen Pipelineprozesse beenden,
bei laufender Arbeit Abschluss/Abbruch anbieten und ausschließlich Loopback nutzen.
[Umsetzung und Abnahme](docs/desktop-app.md). Die nummerierten Videopipeline-Schritte
1–13 bleiben als bisherige Reihenfolge erhalten.

- [Detaillierter Implementierungsplan mit Abnahmebedingungen und Prüfungen](tasks/plan.md)
- [Aufgabencheckliste](tasks/todo.md)
- [Arbeitsstand und Prioritäten](ARBEITSSTAND.md)
- [Entwicklungsstatus und historische Prüfergebnisse](STATUS.md)

Diese Datei beschreibt die vereinbarte Reihenfolge. Sie ist kein Nachweis, dass offene Schritte bereits umgesetzt oder abgenommen sind. Bearbeitungsstatus und Abnahme werden in der Checkliste und im Entwicklungsstatus gepflegt.

## Desktop-Ergänzung

Vom Nutzer freigegeben: Windows, Linux und macOS mit eigenen Start-/Stoppdateien,
gemeinsamem Lebenszyklus für UI und Pipeline, ausschließlich lokalen Ports und
getrennten Systemlaufzeiten. Windows und Linux nativ geprüft; macOS mit
verbindlicher Prozessprüfung auf dem Zielgerät vorbereitet, native Mac-Abnahme
ausstehend. [Einrichtung und Nachweise](docs/desktop-app.md). Keine neuen Testfilme.
