# Desktop-App: Einrichtung und Betrieb

Stand: 15.10.2026. Vorhandene Strichmännchen-UI und Pipeline als Electron-Fenster.
Windows und Linux wurden hier mit echten Fenstern geprüft. macOS ist implementiert;
eine native Mac-Abnahme steht aus. Kein signierter Installer: gestartet wird aus
dem Projektordner, ohne Codex oder einen steuernden Agenten.

## Starten und beenden

| System | Einmal einrichten | Starten | Beenden |
|---|---|---|---|
| Windows | Desktop-Einrichten.cmd | Start-Desktop.cmd | Stop-Desktop.cmd |
| Linux | Desktop-Einrichten.sh | Start-Desktop.sh oder Video-Pipeline.desktop | Stop-Desktop.sh oder Video-Pipeline-beenden.desktop |
| macOS | Desktop-Einrichten.command | Start-Desktop.command | Stop-Desktop.command |

1. Auf jedem Zielgerät die passende Einrichtung ausführen. Benötigt werden
   natives Python ab 3.11 und Node.js LTS ab 22.12 mit npm. Die Einrichtung fragt
   vor fehlenden Python-Paketen und installiert diese im Projekt. Electron 44.7.2
   ist festgelegt; allgemeine npm-Installationsskripte sind deaktiviert. Nur der
   geprüfte Herstellerinstaller lädt Electron mit Prüfsummenprüfung herunter.
2. Startdatei öffnen. Modelle, Stimmen und Konten unter **Einstellungen** einrichten.
   Bestehende Einstellungen bleiben erhalten. Ein zweiter Start fokussiert das
   vorhandene Fenster. Ein separat gestartetes Browser-Backend vorher beenden.
3. Fenster schließen, **Anwendung → Beenden** oder Stoppdatei verwenden. Ohne
   laufende App startet die Stoppdatei kein Backend.

Bei Arbeit stehen **Weiter geöffnet lassen**, **Nach Abschluss beenden** und
**Abbrechen und beenden** zur Wahl. Beim Warten bleibt das Fenster sichtbar;
weitere Produktions-/Schreibanfragen werden abgelehnt und kein nächster Auftrag
beansprucht. Erneutes Schließen erlaubt den Abbruch. Gespeicherte Skripte,
Freigaben und fertige Videos bleiben erhalten. Ungespeicherte Eingaben und laufende
Generierungsantworten können beim Abbruch verloren gehen. Unterbrochene
Desktop-Renderings werden beim Neustart als unterbrochen angezeigt und nicht
ungefragt erneut gestartet. Wartende Aufträge bleiben gespeichert.

## Zuschnitt je Betriebssystem

**Windows:** Ein natives Job Object umfasst Electron und dessen Kinder schon vor
dem ersten ausgeführten Befehl. Beim Ende/Absturz des äußeren Starters schließt
Windows die Gruppe mit Kill-on-close. Eine fehlgeschlagene Zuweisung verhindert
den Start. Die vorhandene lokale Windows-Python-Umgebung wird weiterverwendet.

**Linux:** Normale grafische Anmeldung mit erreichbarer systemd-Benutzersitzung,
`systemd-run`, `systemctl`, `/proc` und Kernel-Pidfd-Unterstützung erforderlich.
Kein sudo-/Root-Start. Eine eindeutige temporäre Benutzereinheit besitzt die
Prozesse; KillMode bleibt control-group. Chromium kann für Desktop-Portale in eine
andere Gruppe wechseln. Deshalb übernimmt ein Kernel-Subreaper verwaiste Kinder
und beendet/reapt auch diese anhand ihrer tatsächlichen Abstammung und Pidfds.
Die normale Portalintegration und Chromium-Sandbox bleiben aktiv. Die Einheit wird
anschließend entfernt; kein dauerhafter Systemdienst oder Login-Autostart.
Fehlen die Voraussetzungen, startet keine unüberwachte Ersatzinstanz.
Die Einrichtung erzeugt zwei lokale .desktop-Dateien. Manche Dateimanager verlangen
„Start erlauben“; alternativ die .sh-Dateien im Terminal ausführen. Für fehlende
GTK-/NSS-/Audio-/Grafikbibliotheken die regulären Distributionspakete verwenden.
Keine Sandbox-Abschaltung, Setuid-Änderung oder globale AppArmor-Ausnahme verwenden.

**macOS:** Native x64-/Apple-Silicon-Laufzeit und reguläre grafische Anmeldung,
kein sudo. Die .command-Dateien lassen sich im Finder öffnen. Ein nur für diese
Sitzung registrierter launchd-Wächter und geschützte Prozessregistrierungen
überwachen auch absichtlich getrennte Worker und den Zeichenbrowser. Konfiguration
wird über einen privaten Unix-Socket übertragen; keine Zugangsdaten in Plist oder
Kommandozeile. Nach einem Wächterfehler bereinigt der Wiederanlauf ausschließlich
und startet keine unbeaufsichtigte Produktion. Kein Eintrag in Library/LaunchAgents.
Vor dem ersten Start und nach Änderungen an System/Python/Wächter muss eine lokale
Prüfung normale Beendigung, Starterabsturz, getrennte Kinder und das Überleben
eines fremden Kontrollprozesses bestätigen. Sonst bleibt der Desktopstart gesperrt.
Diese Prüfung ersetzt keine vollständige native Mac-/Zeichenbrowser-Abnahme.
Gatekeeper, Sandbox und andere globale Schutzmechanismen nicht umgehen.

Laufzeiten sind getrennt: `.runtime/python/<system>-<arch>` und
`.runtime/desktop/<system>-<arch>`; Electron-Profile entsprechend unter
`.runtime/electron-profile`. Systeme: win32/linux/darwin; Architekturen: x64/arm64.
Laufzeiten, native Pakete und Modelle auf dem jeweiligen Gerät einrichten, keine
fertigen virtuellen Umgebungen zwischen Betriebssystemen kopieren. Vorhandene
Browserstarter bleiben erhalten. Daten/Konten werden nicht automatisch migriert.

## Sicherheitsgrenzen

Schützenswert sind lokale Projekte, Kontozugänge und das Hostsystem. Vertrauensgrenzen:
fremde Webseiten/Modellantworten, lokale HTTP-Anfragen und Prozessstarts. Gegen
fremde Webanfragen, URL-/Befehlsmissbrauch und verwaiste Produktion gelten:

- Backend fest auf **127.0.0.1** (Standard 8080; APP_PORT wählt einen anderen lokalen
  Port). Fremde Origin-/Host-Anfragen werden abgelehnt. Eine schon laufende
  Projektinstanz wird auch auf anderem Port erkannt und nicht übernommen.
- Steuerung über private Prozesspipes bzw. macOS-Unix-Socket. Keine Debugports,
  Firewallregeln, Tunnel, Hintergrundablage oder Autostarts. Eigene temporäre
  Render-HTTP-Server und ausdrücklich eingerichtetes Ollama bleiben auf Loopback.
- Electron mit Sandbox, Context Isolation und Web Security; keine Node-Rechte,
  System-IPC-Brücke oder Webviews in der UI. Fenster lädt nur die eigene lokale UI.
  Geräte-/Leseberechtigungen bleiben verweigert; eigene Hauptseite darf Text
  über bestehende Kopierknöpfe in die Zwischenablage schreiben.
- Nur feste Hersteller-/Hilfedomänen öffnen als HTTPS-Link im normalen Browser.
  Keine neue automatische Anmeldung oder Tarifaktivierung. Fremde bestehende
  Dienste werden beim Beenden nicht angefasst; öffentlich erreichbare eigene
  Ports sind für den Desktopbetrieb nicht nötig.
- Wiederverwendete Prozess-IDs werden über Betriebssystem und Prozessgeburt
  unterschieden. Keine breit gefassten Abschüsse nach Programmnamen.

Diagnose lokal: `data/desktop/backend.log`, unter Linux auch `lifecycle.log`.
Testnachweise: `data/desktop/acceptance-*` und `linux-acceptance-*`. Laufzeiten,
Profile, lokale Konfiguration und Nachweise sind nicht versioniert. Betriebssystem-
eingriffe, kompromittierte gleichberechtigte Programme und fremde Dienste liegen
außerhalb dieser Lebenszyklusverwaltung; keine absolute Sicherheitsgarantie.

## Geprüft und offen

- Windows-Backend-Suite: 290 Tests mit 10 regulären optionalen/Plattform-Skips; 58 UI-/Desktop-/Renderer-JS-Tests bestanden.
- Windows: echte Start-/Stoppdateien, Doppelstart, Dialogauswahl, Abbruch und
  Electron-/Starterabsturz. Erfasste eigene Kinder/Enkel entfernt, fremder
  Kontrollprozess erhalten. Native Oberfläche als Screenshot geprüft.
- Ubuntu 24.04 unter WSLg: acht native Prozessprüfungen bestanden, einschließlich
  getrennten Sitzungen und ausgelagerten systemd-Scopes. Echtes Electron-Fenster,
  Zweitstart, normales Ende, Abbruch und Electron-Absturz erfolgreich geprüft.
- Tatsächliche eigene Endpunkte in beiden GUI-Abnahmen ausschließlich lokal:
  Windows 127.0.0.1:8080, Linux 127.0.0.1:18183. Keine erfassten Prozessreste.
  Host-/Origin-Fremdanfragen 403, neue Schreibanfragen während des Beendens 503.
- Desktop-npm-Audit: 0 bekannte Befunde. Keine neuen Filme, Modelle oder
  kostenpflichtigen KI-Anfragen für diese Entwicklung.

Optionale GUI-Abnahme mit eingerichtetem Projekt-Python, bei vorher geschlossener
App: `python tests/check_desktop_runtime.py` unter Windows oder
`python tests/check_linux_desktop_runtime.py` unter Linux. Diese öffnen echte
Testfenster und erzeugen keine Videos. Native Mac-Prozessprüfung:
`python -m unittest tests.test_macos_desktop` innerhalb einer Mac-GUI-Sitzung.

Offen: native Mac-Abnahme (Intel/Apple Silicon und Zeichenbrowser), andere Linux-
Desktops/Architekturen, vollständige frische Installation und Leistung auf einem
schwachen zweiten physischen Rechner, signierte Installationspakete. Zusätzliche
Electron-Speichernutzung bleibt; eine unveränderte Rendergeschwindigkeit wird ohne
Leistungsmessung auf Zielhardware nicht behauptet.

Quellen: [Electron-Sicherheit](https://www.electronjs.org/docs/latest/tutorial/security),
[Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[systemd-KillMode](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html),
[Chromium-Portalgruppen](https://github.com/chromium/chromium/blob/main/components/dbus/xdg/systemd.cc),
[Apple-Prozessinformationen](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/proc_info.h).
