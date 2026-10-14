# Rechner einrichten und die Pipeline selbst bedienen

## Dein aktiver Weg und optionale Alternativen

Oben stehen der tatsächlich aktive Skriptanbieter, das Modell und die Standardstimme.
Für den Antigravity-Weg ist die lokale Ollama-Einrichtung eingeklappt und optional.
Qwen ist bei gewähltem Piper ebenfalls eine optionale Alternative. Beim Wechsel auf
den lokalen Skriptweg öffnet sich dessen Einrichtung; wirksam wird er erst beim Speichern.
Die Bereitschaftsanzeige prüft Skriptzugang, Stimme, Node, Renderer, Browser, FFmpeg
und FFprobe. Ein vorhandener Cloudzugang allein bedeutet noch nicht Produktionsbereitschaft.

## Fortschritt und Zeitangaben

Skript, Hörprobe und Zeichnungs-/Videoerzeugung zeigen laufende Arbeit und vergangene
Zeit. Ohne messbaren Fortschritt bleibt der Balken unbestimmt. Eine ungefähre Restzeit
gibt es erst nach mindestens drei konsistenten lokalen Messungen (letzte fünf Läufe,
Spannweite höchstens 50 % des Medians). Modell, Stimme und Tempo trennen Erfahrungswerte;
schnelle Cache-Antworten und Fehler lernen keine Generierungsdauer. Dauert es länger,
wird dies angezeigt. Prozentwerte erscheinen bei tatsächlichen Downloadangaben oder
nach Abschluss. Gespeichert werden Zeitwerte, keine Sprechertexte.

## Konten und Anmeldungen

Unter Abschnitt 3 stehen kostenloser Google-Einstieg, optionales Pro-/Ultra-Abo,
Kontingent- und Konto-Voraussetzungen sowie die Anmeldung über die offizielle CLI.
Lokaler Skriptweg, Stimmen und Schnitt brauchen kein Konto. Es werden keine
Passwörter oder API-Schlüssel in der Oberfläche verlangt. Quellenstand und genaue
Bedienung: [docs/accounts.md](accounts.md). Web- und zusätzliche API-Adapter
bleiben Schritt 12/13; ein Webseiten-Login allein schaltet sie nicht frei.

## Skriptzugang prüfen und das Modell ausdrücklich wählen

Unter **3 · Skript-KI und Zugang** steht der tatsächlich aktive Anbieter mit
Modell. Eine Auswahl im Formular wird erst mit **Auswahl speichern und verwenden**
aktiv. **Gewählten KI-Zugang prüfen** unterscheidet fehlendes Programm,
Anmeldebedarf, nicht angebotenes Modell, Verbindung/Zeitlimit und
Kontingent-/Kapazitätsfehler. Eine fehlgeschlagene Verbindung wird nicht als
fehlende Anmeldung ausgegeben.

Antigravity bestätigt über die offizielle CLI die Anmeldung und das Modellangebot.
Ein normales Google-Konto oder ein Abo ist keine Garantie für ein bestimmtes Modell.
Die Auswahl zeigt nur tatsächlich angebotene Gemini-Modellnamen. Fehlt das bisherige
Modell, bleibt es bis zur ausdrücklichen Auswahl eines anderen sichtbar; es erfolgt
kein automatischer Ersatz. Beim Speichern wird der ausgewählte Modellzugang erneut
geprüft. Der lokale Weg prüft Dienst und installiertes Modell, nicht nur Konto-Freiheit.

Die reine Modellprüfung bestätigt weder Restkontingent noch Abrechnung. Die Pipeline
aktiviert keine Tarife oder Credits. Bestehende Credit-Einstellungen des Anbieters
sind damit nicht geprüft und können im offiziellen Anbieter überprüft werden.
Bei einer ausdrücklich gespeicherten Antigravity-Auswahl ist ein automatischer
Wechsel zu lokalem Qwen abgeschaltet; der Standard für
`ANTIGRAVITY_FALLBACK_TO_QWEN` ist ebenfalls `false`.

Beim Öffnen von **Neues Video** bleiben Idee, Formate und Abbrechen während der
Zugangsprüfung bedienbar. Erst eine verfügbare, ausdrücklich ausgewählte Herstellung
erlaubt die Skripterstellung. Der Gesundheitsstatus berichtet den gewählten Zugang
auch dann als nicht bereit, wenn eine andere Alternative erreichbar wäre.

Quellen für Anmeldung und Kontingente:
[offizielle CLI-Anmeldung](https://www.antigravity.google/docs/cli/install),
[Pläne](https://www.antigravity.google/docs/plans),
[Credit-Einstellungen](https://www.antigravity.google/docs/cli/credits/).

Die Oberfläche hat ein Zahnrad **Einstellungen**. Dort stehen Rechnerprüfung,
passende lokale Modelle, Download-Schritte, Standardstimme und optionale
Anmeldungen. Die tägliche Produktion benötigt keinen Coding-Agenten: Ein Prompt
liefert den Sprechertext, Änderungswünsche gehen an die Skript-KI, die Freigabe
startet Bildplanung und Video automatisch.

## Erster Start

Windows: `Start-Pipeline.cmd`. Linux und macOS: `./Start-Pipeline.sh`.
Eine vorhandene lokale Python-Laufzeit wird verwendet. Fehlen die Python-Pakete,
fragt der Starter, ob er die festgelegten Pakete in `.runtime/pipeline-python`
installieren darf. System-Python und globale Einstellungen werden nicht geändert.
Python 3.11 oder neuer muss bereits vorhanden sein; empfohlen ist Python 3.12.
Fehlt Python selbst, zeigt der Starter den offiziellen Download. Eine nicht
gestartete Python-Anwendung kann ihre eigene Einstellungsseite noch nicht öffnen.
Docker wird vom Starter nicht mehr automatisch gestartet oder mit großen Modellen
befüllt; der bestehende manuelle Compose-Weg bleibt gesondert verfügbar.

In den Einstellungen:

1. Rechnerwerte und Empfehlung lesen. Bei unbekannten Angaben RAM, CPU-Threads
   und optional separaten Grafikspeicher ergänzen. Keine Seriennummern oder
   persönlichen Daten eingeben.
2. Fehlende Programme über ihre Herstellerseiten installieren: Node.js LTS,
   Ollama, Chrome/Edge/Chromium. Danach die Pipeline neu starten, falls ein neuer
   PATH-Eintrag nötig ist. **Schnittwerkzeuge einrichten** installiert die
   festgelegten npm-Pakete im Projekt, ohne Installationsskripte auszuführen.
3. Das angebotene Skriptmodell herunterladen und die passende Stimme einrichten.
   Der Fortschritt zeigt vergangene Zeit; bei Ollama auch den aktuellen
   Downloadabschnitt und eine daraus geschätzte Restzeit. Paketinstallationen
   ohne messbaren Fortschritt erfinden keine Fertigstellungszeit.
4. **Auswahl speichern und verwenden**. Modell und Stimme gelten für neue
   Aufträge. Vorhandene Skripte, Videos und gewählte Stimmen bleiben erhalten. Eine neue
   KI-Überarbeitung verwendet das aktuell gewählte Skriptmodell.

Die UI speichert ausschließlich begrenzte Geräteoptionen in
`.runtime/machine-settings.json`, nicht in einer allgemeinen `.env`-Bearbeitung.
Diese Datei ist nicht versioniert. Sie setzt den Skriptdienst fest auf Loopback
und überschreibt nur Skriptmodell, lokale oder
optionale Cloud-Skripterstellung, Standardstimme und begrenzte Leistungsparameter.
Die Einstellungs-UI zeigt keine Anmeldetokens oder bestehenden `.env`-Schlüssel.
Beim nächsten Start wird die Modellwahl erneut an den verfügbaren Speicher
angepasst; bei unklarer oder unzureichender Kapazität bleibt lokale Produktion
gesperrt, bis die Gerätewerte geprüft sind. Eine kleinere gewählte Modellgröße
wird nicht ungefragt erhöht.

## Leistungswahl und Grenzen

Modelle: Qwen 3.5 mit 0,8B, 2B, 4B, 9B, 9B Q8 und 27B. Die Auswahl betrachtet
Gesamt-RAM, freien RAM, CPU-Threads, freien Plattenplatz und sicher erkannte
Nvidia-VRAM beziehungsweise Apple-Silicon-Speichernutzung. Ein 27B-Modell wird
nur mit 64 GB RAM und geeigneter Beschleunigung angeboten. RAM-Werte dürfen
um bis zu 0,5 GB unter der nominellen Ausstattung liegen; die Mindestwerte für
freien Speicher bleiben unverändert. Die Budgets in `backend/device.py` sind
konservative Anwendungsheuristiken, kein Benchmark oder Qualitätsversprechen.
Kleine Modelle können eher an der validierten Bildplanung scheitern; die Pipeline
gibt weiterhin kein erfundenes Ersatzvideo aus.

Piper ist die sparsame Stimme. Qwen wird ab nominell 24 GB RAM und mindestens
12 GB aktuell freiem RAM angeboten; die Einrichtung benötigt 20 GB freien
Plattenplatz. Qwen prüft verfügbaren RAM auch vor der Audioerzeugung. Die
automatische isolierte Qwen-CPU-Installation verwendet den vorhandenen Lockstand
für Python 3.12 auf Windows/Linux x64. macOS x64/ARM64 verwendet dieselben
Torch-Versionen als macOS-Wheels ohne den +cpu-Suffix; alle übrigen Paketversionen
bleiben festgelegt. Andere Architekturen nutzen Piper. Die Windows-Laufzeit ist
physisch erprobt; die macOS-Variante braucht zusätzlich eine reale Geräteprüfung.
Browser- und FFmpeg-Erkennung berücksichtigen Windows, macOS und Linux. Das ist
kein Nachweis einer physischen Prüfung auf jedem Betriebssystem oder Gerät.

## Lokale Sicherheit und Konten

Die Web-UI bindet ausschließlich `127.0.0.1`. Ein von der Pipeline gestartetes
Ollama bindet ebenfalls ausschließlich `127.0.0.1:11434`, deaktiviert Cloud und
verarbeitet höchstens ein Modell gleichzeitig. Bereits laufende Ollama-Dienste
werden nur genutzt, wenn die lokale Listenerprüfung reine Loopback-Adressen
bestätigt. Unbekannte oder belegte Ports werden nicht umgangen. Es entstehen
keine Firewallregeln, Tunnel, Routerfreigaben oder zusätzlichen Ausweichports.

Einrichtung ist nur über Loopback-Host und Loopback-Client erlaubt. Schreibaufrufe
benötigen einen pro Serverstart erzeugten CSRF-Token; fremde Origins und
Cross-Site-Aufrufe werden verworfen. Anfragen sind auf 8192 Bytes begrenzt.
Die API akzeptiert feste Aktions- und Modellnamen, keine Shellbefehle,
Installationsskripte, Zielpfade oder Download-URLs. Downloads erfolgen über
festgelegte Hersteller/Registries mit normaler Zertifikatsprüfung. Große Modelle,
Paket-Caches und temporäre Installationsdaten bleiben im Projektordner. Ein fremder
Ollama-Dienst wird nicht umkonfiguriert; neue Downloads brauchen den von der
Pipeline gestarteten Dienst. Vorhandene Modelle können lokal weiter genutzt werden. Konfiguration
und Downloads sind mit laufender Produktion gegenseitig gesperrt. Beim Stoppen
werden ausschließlich die selbst gestarteten Einrichtungsvorgänge und der
selbst gestartete Ollama-Prozess beendet; fremde Dienste bleiben erhalten.
Unterbrochene Stimmeninstallationen werden nicht als bereit angezeigt. Der
gleiche Download-Knopf repariert die isolierte Laufzeit beziehungsweise lädt die
Piper-Dateien erneut; eine beschädigte Stimme wird nicht still ersetzt.

Der lokale Weg benötigt kein Konto, keinen API-Schlüssel und keinen Agenten.
Das bisher vorhandene Antigravity-Cloudprofil ist optional. Seine reguläre
Herstelleranmeldung bleibt außerhalb der Pipeline; die UI verlinkt die
Anmeldedokumentation und prüft den vorhandenen Zugang. Die Pipeline baut keine
eigene Passwortverwaltung und liest keine Anmeldetokens aus. Für diesen
optionalen Weg werden Sprechertexte an den Anbieter gesendet.

Offizielle Quellen für Katalog und Verbindungseinstellungen:
[Qwen-Modelle](https://ollama.com/library/qwen3.5/tags),
[Ollama lokal betreiben](https://docs.ollama.com/faq),
[Modell-Download](https://docs.ollama.com/api/pull),
[Node.js LTS](https://nodejs.org/en/download),
[Antigravity-Anmeldung](https://antigravity.google/docs/cli/install).

Prüfungen: `python -m unittest tests.test_device_setup`, vollständige bestehende
Backend-Suite und `node --test renderer/browser.test.mjs renderer/ink.test.mjs`.
Tests decken Gerätebudgets, dauerhafte Konfiguration, unerlaubte Payloads,
fremde Origins/Hosts, fehlende CSRF-Tokens sowie parallele Einrichtung ab.
