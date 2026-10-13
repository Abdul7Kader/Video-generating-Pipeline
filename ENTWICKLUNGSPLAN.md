# Entwicklungsplan für die Strichmännchen-Pipeline

Stand: 2026-10-13. Vom Nutzer gewünschte Reihenfolge: zuerst die Originalversion fertigstellen, erst danach die Familienversion ohne Pro-Abos. Vorhandene Funktionen werden geprüft und verbessert; andere Videoarten bleiben ausgeblendet.

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

- [Detaillierter Implementierungsplan mit Abnahmebedingungen und Prüfungen](tasks/plan.md)
- [Aufgabencheckliste](tasks/todo.md)
- [Arbeitsstand und Prioritäten](ARBEITSSTAND.md)
- [Entwicklungsstatus und historische Prüfergebnisse](STATUS.md)

Diese Datei beschreibt die vereinbarte Reihenfolge. Sie ist kein Nachweis, dass offene Schritte bereits umgesetzt oder abgenommen sind. Bearbeitungsstatus und Abnahme werden in der Checkliste und im Entwicklungsstatus gepflegt.
