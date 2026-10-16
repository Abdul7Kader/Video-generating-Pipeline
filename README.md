# Lokale Video Pipeline

**Neu:** Laufende Erstellung einzeln abbrechen. Unter **⚙ Einstellungen** den
zusätzlichen Videoordner, Discord-Freigeber und Plattformzugänge einrichten.
Fertige Videos in Discord anschauen, freigeben, ändern lassen oder ablehnen;
erst nach Freigabe an ausgewählte eingerichtete Ziele übertragen. TikTok erhält
einen Entwurf zur endgültigen Veröffentlichung in TikTok. Neue Endvideos liegen
getrennt im gewählten Videoordner, sonst `data/videos/`; Arbeitsdateien unter
`data/jobs/`. Aufräumen ist standardmäßig **nur manuell**. Beim fertigen Video
„Arbeitsdateien jetzt bereinigen“ wählen; Video und Skript bleiben erhalten.
[Speicherung und Weiterbearbeitung](docs/video-storage.md),
[Abnahme und Voraussetzungen](docs/review-distribution.md).

**Desktop-App für Windows, Linux und macOS:** Die passende Einrichtung einmal
starten, danach die Startdatei öffnen. Schließen oder die Stoppdatei beendet auch
die eigene Pipeline. Bei laufender Arbeit kannst du warten oder abbrechen.

| System | Einmal einrichten | Starten | Beenden |
|---|---|---|---|
| Windows | `Desktop-Einrichten.cmd` | `Start-Desktop.cmd` | `Stop-Desktop.cmd` |
| Linux | `Desktop-Einrichten.sh` | `Start-Desktop.sh` / erzeugte `.desktop`-Datei | `Stop-Desktop.sh` / Beenden-Datei |
| macOS | `Desktop-Einrichten.command` | `Start-Desktop.command` | `Stop-Desktop.command` |

Linux benötigt eine reguläre systemd-Benutzersitzung; macOS prüft die
Prozessbereinigung auf dem Zielgerät vor dem ersten Start. Native Mac-Abnahme
steht hier noch aus. Ein separat gestartetes Browser-Backend zuerst beenden.
[Einrichtung, Verhalten und Sicherheitsgrenzen](docs/desktop-app.md).

Eine lokale Videoproduktion mit Startern für Windows, Linux und macOS. Aktueller Schwerpunkt sind gezeichnete Strichmenschen-Geschichten mit Remotion, SVG, Piper und FFmpeg. FastAPI und SQLite speichern Auftrag, Versionen, Fehler und beide verbindlichen Freigaben.

Die weitere Entwicklung folgt dem [nummerierten Entwicklungsplan](ENTWICKLUNGSPLAN.md):
zuerst die Originalversion fertigstellen (Schritte 1–10), danach die Familienversion
ohne Pro-Abos (Schritte 11–13). [Arbeitsstand](ARBEITSSTAND.md),
[Abnahmebedingungen](tasks/plan.md) und [Aufgabencheckliste](tasks/todo.md)
halten Prioritäten und Bearbeitungsstatus fest.

Kurze Werkzeugübersicht mit Anmeldung/Abo: [Technologiestech.md](Technologiestech.md).
Aktuelle Anmeldung, kostenloses Google-Basiskontingent und optionale Abos:
[Konten und Anmeldungen](docs/accounts.md), direkt unter ⚙ Einstellungen.
Skripte erhalten eine begrenzte Textprüfung vor dem Speichern; Details und Grenzen:
[Skript- und Freigabeablauf](docs/story-workflow.md). Während der Entwicklung werden
keine routinemäßigen Testvideos in der UI erzeugt. Die technische Mehrthemenprüfung
ist [dokumentiert](docs/acceptance-10.md); die persönliche Sicht-/Hörfreigabe bleibt offen.

Bildpläne prüfen eine begrenzte Gruppe erzählter Tiere, Gegenstände und Handlungen.
Hände und gehaltene Gegenstände teilen einen Kontaktpunkt; abgelegte Gegenstände
bleiben am neuen Ort oder auf einer referenzierten Tischfläche. Temporäre
Render-HTTP-Server lauschen ausschließlich auf Loopback.
Aktionen folgen begrenzten Sprachfenstern; Figurenmerkmale, Besitz und Ablageorte
werden über Schnitte geprüft. Die Wortzeiten sind Schätzungen, die Filmabnahme folgt später.

## Einrichtung auf diesem Rechner

**⚙ Einstellungen** bündelt die lokale Rechnerprüfung, passende Skriptmodelle,
Downloads, Standardstimme und optionale Anmeldungen. Kleine Geräte bekommen kleinere
Modelle und Piper, stärkere Geräte können größere Modelle und Qwen wählen. Die
Empfehlung berücksichtigt auch freien RAM und Plattenplatz. Bei unklarer Erkennung
kann der Nutzer technische Geräteangaben ergänzen. Es werden keine Hardwaredaten
an einen Anbieter geschickt und keine Firewall- oder Routerfreigaben eingerichtet.

Der normale lokale Betrieb braucht keinen Coding-Agenten, kein Konto und keine
manuelle `.env`-Bearbeitung. **Auswahl speichern und verwenden** aktiviert begrenzte,
gerätelokale Optionen für neue Aufträge. Installationen starten mit eigenen Knöpfen;
Systemprogramme öffnen ihre offiziellen Downloadseiten. Details, Plattformgrenzen
und Sicherheitsprüfungen: [docs/device-settings.md](docs/device-settings.md).

## Strichmenschen-Geschichten

Seit 2026-10-10 ist ausschließlich die Strichmenschenproduktion aktiv. Stockmedien, MoneyPrinterTurbo, Podcast und andere Videoarten sind eingefroren; ihre vorhandenen Daten und Adapter bleiben erhalten. Die nachfolgenden Beschreibungen dieser Wege dokumentieren den bisherigen Stand.

Seit 2026-10-11 blendet die Oberfläche auch andere Produktionsprofile, Stockfelder,
externe Videoimporte, Renderer-Vergleiche und Veröffentlichung aus. Die Auftragsliste
zeigt Strichmenschen; bestehende andere Aufträge und Backend-Adapter werden nicht gelöscht.

**Stimmen ausprobieren:** Unter **Stimme und Herstellung ändern · optional → Stimmen hören und vergleichen**
einen kurzen Testtext eingeben und **Qwen und Piper vergleichen** wählen.
Deutsch bietet Qwen · tiefer Erzähler, Thorsten · klar, Thorsten · lebhaft und Kerstin; Englisch LJ.
Die Player verwenden denselben Text und dasselbe gewählte Tempo (0,85–1,25×).
**Diese Stimme wählen** übernimmt die Auswahl. Bei bestehenden Aufträgen anschließend
**Produktionskonfiguration speichern** und das Skript erneut freigeben.
Die ausgewählte Qwen-Stimme läuft kostenlos lokal in einer separaten Laufzeit;
Einrichtung und kurze UI-Anleitung stehen in [docs/qwen-voice.md](docs/qwen-voice.md).
**Ausgewählte Stimme anhören** erzeugt eine einzelne Probe. Neue Aufträge behalten
die gespeicherte Standardstimme; ein installiertes Qwen ersetzt Piper nicht automatisch.
Der Vergleich verwendet nur bereits installierte, verfügbare Qwen-/Piper-Stimmen. Die übrigen
Stimmen werden lokal mit Piper erzeugt; fehlende feste Modelle werden bei
aktiviertem `PIPER_AUTO_DOWNLOAD` einmalig heruntergeladen. Es wird kein Cloud-TTS aktiviert.
Kerstins Modell ist als niedrige Qualität gekennzeichnet; eine andere Stimme ist nicht
automatisch besser. Wortbudget und Sprechzeitschätzung berücksichtigen Stimme und Tempo,
bleiben aber Näherungen auf Basis einer kurzen lokalen Vergleichspassage.

**Skripte verbessern:** Die UI zeigt einen durchgehenden Sprechertext und eine Bildidee.
Unter **Was soll die KI verbessern?** einen Änderungswunsch eingeben und
**KI verbessert das Skript** wählen. Die nächste Version erneut lesen und dann
**Freigeben & Video erzeugen** drücken. Bildplanung und Rendern entstehen automatisch,
ohne Einzelszenen-Kontrolle. Die Bildplanung muss den freigegebenen Sprechertext
unverändert übernehmen. Details: [docs/story-workflow.md](docs/story-workflow.md).

Quellen für den lokalen Stimmenvergleich: [Piper Python API](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md),
[Thorsten emotional](https://huggingface.co/rhasspy/piper-voices/blob/main/de/de_DE/thorsten_emotional/medium/MODEL_CARD),
[Kerstin](https://huggingface.co/rhasspy/piper-voices/blob/main/de/de_DE/kerstin/low/MODEL_CARD),
[LJ Speech](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/high/MODEL_CARD).
Die Modellkarten nennen CC0 für die deutschen Trainingsdatensätze und Public Domain für LJ Speech.
Lizenzpflichten der Piper-Laufzeit bestehen unabhängig davon.

Die Bildsprache orientiert sich an [Ink Explainer](https://www.youtube.com/watch?v=49_Ph2q6uIM): heller Zeichenhintergrund, schwarze Konturen, wenige flache Farben, Mimik, Kleidung, Requisiten und wechselnde Schauplätze. Standardformat ist 16:9. Ein ausführbarer `stickman`-Zeichenplan steuert bis zu vier Figuren und acht Requisiten pro Szene, Posen, Gefühle, Positionen, Laufwege, zeitliche Auftritte, Ausschnitt und Kamerabewegung. Die KI darf nur den validierten Zeichenbaukasten verwenden; sie erzeugt keine beliebigen Illustrationen aus Freitext.

Für einen ersten Test: **Neues Video** öffnen, eine Idee eingeben, Länge und
Videoformat wählen und **Sprecher-Skript erstellen** drücken. Die Stimme und
Herstellung verwenden die Rechnereinstellungen; eine andere Stimme ist optional.
Den Fließtext lesen, bei Bedarf einen KI-Änderungswunsch eingeben und schließlich
**Freigeben & Video erzeugen** wählen. Das fertige Video ansehen und herunterladen.

Beispielthema: „Eine Figur legt ihr Handy weg, nimmt ein Buch, liest darin und zeigt
einer zweiten Figur ihre Idee. Zeige die gesprochenen Handlungen mit passenden
Bewegungen und tatsächlichen Gegenständen.“

Strichmenschen-Videos folgen jetzt der tatsächlichen Stimme statt künstlich auf die geplante Szenenlänge zu warten. Lange stille TTS-Abschnitte werden gekürzt; kurze Wortabstände bleiben erhalten. Bewegungen, Gegenstandswechsel und Untertitel nutzen lokal geschätzte Wortzeiten aus Sprachsignal und Text. Diese Zuordnung ist keine wortgenaue Spracherkennung. Bestehende Entwürfe brauchen passende Regieschritte oder eine neue KI-Überarbeitung, um mehrere erzählte Handlungen zu zeigen.

Die eigene Stilprobe liegt in `examples/stickman-demo.json`. Mit eingerichtetem Piper, Remotion und FFmpeg lässt sie sich ohne KI-Anfrage oder Veröffentlichung erzeugen:

```bash
python scripts/render_stickman_demo.py
```

Die MP4, Untertitel sowie Stimmen-, Asset- und Qualitätsnachweise liegen anschließend in `data/style-preview`. Der Film ist eine Stilprobe, kein recherchierter Geschichtsbeitrag. Anforderungen und Sicherheitsgrenzen stehen in `SPEC-stickman-storytelling.md`.

Die neue Bewegungsprobe verwendet zusammenhängende Erzählung und textgebundene Regieschritte:

```powershell
python scripts/render_stickman_demo.py --script examples/stickman-motion-demo.json --output data/motion-preview
```

Laufwege starten und bremsen weich ab. Bei einem Richtungswechsel dreht sich die Figur
kurz in die neue Laufrichtung; getragene Gegenstände folgen dieser Drehung ohne Sprung.
Nach der Ankunft endet die Laufbewegung. Die Blickrichtung im Editor gilt weiterhin
für Figuren ohne Laufweg. Eine eigene Probe mit Hinweg, Rückweg und getragenem Buch:

```powershell
python scripts/render_stickman_demo.py --script examples/stickman-turn-demo.json --output data/turn-preview
```

## Start

Direkt im Projektordner liegen Starter und Stopper:

- **Windows:** `Start-Pipeline.cmd` doppelklicken. Das sichtbare Konsolenfenster zeigt den Server; mit `Strg+C` wird er beendet. Die vorhandene `.runtime/windows-python`-Umgebung wird bevorzugt, andernfalls eine bereits eingerichtete System-Python-Umgebung. Fehlende Python-Pakete können nach Rückfrage ausschließlich in einer projektlokalen Umgebung installiert werden.
- **Linux/macOS:** `./Start-Pipeline.sh` ausführen. Der Starter nutzt vorhandenes Python oder die projektlokale Laufzeit und fragt vor deren Einrichtung. Docker und große Modelle werden nicht automatisch gestartet oder geladen.
- **Stoppen:** Unter Windows `stop.cmd` ausführen, unter Linux `./stop.sh`. Beide stoppen nur die durch diese Projekt-Starter verwalteten lokalen Server. Unter Linux stoppt `stop.sh` zusätzlich den Compose-Webdienst dieses Projekts, falls er läuft; Ollama und Datenvolumes bleiben erhalten. Ein manuell mit `uvicorn` gestarteter Server wird nicht beendet – dort `Strg+C` verwenden.

Beide Starter binden die Weboberfläche ausschließlich an `127.0.0.1`. Im lokalen Python-Betrieb wird sie nach dem Gesundheitscheck im Browser geöffnet; ohne grafischen Browser steht die Adresse im Terminal. Eine bereits laufende Pipeline wird erkannt und nicht doppelt gestartet. Lokale Einstellungen können in einer nicht versionierten `.env` stehen. Für den Qwen-Fallback muss Ollama separat laufen; Antigravity benötigt keinen gestarteten Ollama-Dienst.

`start_pipeline.py` ist der gemeinsame lokale Starter hinter den Windows- und Linux-Dateien: Er lädt `.env`, prüft Port und Gesundheitsstatus, startet FastAPI/Uvicorn und öffnet die Oberfläche. Die `.cmd`-/`.sh`-Dateien wählen die passende Laufzeit; `setup_pipeline.py` kann nach Rückfrage eine fehlende lokale Python-Umgebung anlegen. Der Starter schreibt eine kleine, nicht versionierte Prozesskennung nach `.runtime`; `stop_pipeline.py` fordert damit ohne Port-Freigabe ein sauberes Herunterfahren an. Optional stoppt `stop_pipeline.py --port 8080` nur eine bestimmte lokale Instanz.

Der bisherige Docker-Befehl bleibt ebenfalls möglich:

```bash
cp .env.example .env
docker compose up --build -d
```

Danach ist die Oberfläche ausschließlich lokal unter <http://127.0.0.1:8080> erreichbar. Compose startet Ollama nur im internen Containernetz und lädt beim ersten Start `qwen3.5:9b-q8_0` in ein lokales Volume. Das Piper-Stimmenmodell liegt ebenfalls lokal. Fehlende Modelle oder Stimmen brechen den Auftrag verständlich ab; stumme oder generische Ersatzresultate gelten nicht als Erfolg.

Auf diesem Rechner liegt zusätzlich eine verifizierte projektlokale Testlaufzeit unter `.runtime`. Solange Docker wegen fehlender Socket-Berechtigung noch nicht nutzbar ist, startet die bereits installierte Fassung so im Vordergrund:

```bash
# Terminal 1
./scripts/ollama_local.sh serve

# einmalig in Terminal 2
./scripts/ollama_local.sh pull qwen3.5:9b-q8_0

# anschließend in Terminal 2
./scripts/run_local.sh
```

## Bedienung

1. Unter **Neues Video** die Idee, Sprache, Länge und Videoformate wählen. Es entsteht ein zusammenhängender Sprechertext.
2. Lesen, bei Bedarf Änderungswünsche an die KI geben und **Freigeben & Video erzeugen** drücken.
3. Bildplanung und Videoproduktion abwarten. Der Rechner bearbeitet einen Renderauftrag gleichzeitig.
4. Jedes fertige Format ansehen und herunterladen. **Skript bearbeiten** führt zurück zum Entwurf. Veröffentlichungsfunktionen sind derzeit ausgeblendet.

Das **i** im Seitenkopf öffnet die Bedienhilfe. Felder und Aktionen erklären sich zusätzlich beim Darüberfahren mit der Maus oder beim Fokussieren mit der Tab-Taste.

Änderungen am Skript erzeugen eine neue Version und löschen automatisch alte Skript-, Render- und Veröffentlichungsfreigaben. Wiederholte Renderaufrufe derselben Version werden nicht doppelt gestartet. Die Weboberfläche ist zunächst an `127.0.0.1` gebunden.

## Gemini- und NotebookLM-Inhalte importieren

Nach der Skriptfreigabe erscheint unter dem Szenenplan der Bereich **„Video aus Gemini oder NotebookLM übernehmen“**:

1. Video in der offiziellen Gemini- oder NotebookLM-Oberfläche erzeugen und dort als MP4 herunterladen.
2. Quelle und MP4 in der Pipeline auswählen und **Video importieren** drücken.
3. Die Pipeline prüft Audio, Video, Laufzeit und Dateigröße, speichert Herkunft und SHA-256 und zeigt das Ergebnis unter **Video prüfen**.
4. Erst die bestehende zweite Freigabe erlaubt den weiteren Veröffentlichungsablauf.

Der Dateiimport verwendet keine Gemini API und verursacht daher in der Pipeline keine API-Kosten. Google AI Pro ist kein Gemini-API-Guthaben; Bild-, Video- oder TTS-API-Aufrufe benötigen ein separates API-Projekt und bleiben standardmäßig deaktiviert. Das Importlimit lässt sich mit `EXTERNAL_IMPORT_MAX_MB` einstellen (Standard: 500 MB).

## KI-Skripterstellung

Die Pipeline erzeugt absichtlich **kein** allgemeines Vorlagenskript mehr. Standard ist die vollständig lokale Erzeugung mit Ollama und `qwen3.5:9b-q8_0`. Ollama lauscht beim projektlokalen Start nur auf `127.0.0.1`; in Compose besitzt der Dienst keinen veröffentlichten Port. Cloud-Funktionen und Verlauf sind deaktiviert.

```dotenv
SCRIPT_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:9b-q8_0
OLLAMA_NUM_CTX=8192
OLLAMA_NUM_PREDICT=4096
OLLAMA_TIMEOUT_SECONDS=720
```

Das lokale Modell bearbeitet höchstens eine Skripterstellung gleichzeitig. Vor einem aufwendigen Render wird es aus dem Arbeitsspeicher entladen. Ist Ollama nicht erreichbar, liefert die Oberfläche einen verständlichen Fehler; es gibt weder einen Vorlagen- noch einen Cloud-Ersatzpfad.

Die vorhandenen Cloudadapter bleiben ausschließlich für eine spätere ausdrücklich gewählte Konfiguration erhalten. Sie werden nicht automatisch verwendet.

### Kostenloser automatischer Zugang und Webimport

Unter **⚙ Einstellungen → Skript-KI und Zugang** stehen Antigravity mit dem
berechtigten eigenen Google-Konto, lokale Ollama-Modelle und der manuelle Webimport.
Der automatische Antigravity-Weg verlangt kein Pro-Abo; der Anbieter begrenzt das
Basiskontingent und Modellangebot. Vor jedem Aufruf prüft die Pipeline, dass
Zusatzcredits ausgeschaltet sind. Sie aktiviert keine Tarife und überschreibt keine
Kontoeinstellungen. Zugangsdaten bleiben im Herstellerdialog/-Schlüsselspeicher.

Für **Web-KI · manuell kopieren und einfügen** sind zwei Übertragungen nötig:
Sprechertext importieren und lesen/überarbeiten; nach Textfreigabe die Zeichenantwort
importieren. Danach entstehen Stimme und Video lokal. Kein automatischer Weblogin,
keine Einzelszenenfreigabe und kein Umgehen von Limits. Eine ungültige oder veraltete
Antwort ersetzt keine gespeicherte Fassung. [Kurzanleitung und geprüfte Grenzen](docs/family-paths.md).

**Gemini CLI ist kein aktueller Consumer-Gratiszugang:** Googles spezielle
[Abkündigung](https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals)
(aktualisiert 09.10.2026) gilt seit 18.06.2026 auch für Gemini CLI. Allgemeine ältere
CLI-Anleitungen widersprechen dem. Der frühere Profilpool in `SPEC-gemini-cli-pool.md`
bleibt eingefrorener Verlauf und wird in der aktiven UI nicht angeboten.
Ein echter Test mit dem eigenen kostenlosen Familienkonto und einem schwächeren
Rechner bleibt gesonderte Abnahme; der vorhandene Nutzerzugang beweist keinen Tarif.

Beispiel für eine ausdrückliche spätere Cloud-Auswahl:

```dotenv
SCRIPT_PROVIDER=gemini
GEMINI_API_KEY=...
```

Alternativ mit separat abgerechneter OpenAI API:

```dotenv
SCRIPT_PROVIDER=openai
OPENAI_API_KEY=...
```

oder mit einem ausdrücklich gewählten OpenRouter-Modell:

```dotenv
SCRIPT_PROVIDER=openrouter
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=anbieter/modell
```

Schlüssel gehören nur in `.env`; die Datei wird nicht versioniert. Ein ChatGPT-/Codex-Abo umfasst keine OpenAI-API-Nutzung. Beim Gemini-Free-Tier ist außerdem zu beachten, dass übermittelte Inhalte laut Anbieter zur Produktverbesserung verwendet werden können. Diese Cloudwege sind im lokalen Standard vollständig unbeteiligt.

Der KI-Entwurf enthält neben dem Sprechertext einen konkreten Produktionsplan pro Szene (visueller Medientyp, sichtbare Einstellung, Asset-Prompt, Kamera, bewusste Texteinblendung und Übergang). Über das Feld „Änderungswunsch an die KI“ entsteht eine neue Skriptversion; alte Freigaben werden dabei ungültig.

Eine einzelne Szene kann separat gespeichert werden. Auch das erzeugt eine neue, hashgebundene Planversion. Beim nächsten Render werden unveränderte Stockmedien und Voiceover-Segmente nach Prüfung ihres SHA-256 wiederverwendet; nur betroffene Szenen werden neu beschafft beziehungsweise gesprochen. Der finale Film wird immer neu zusammengesetzt und als eigene Renderrevision geprüft.

Aktuell ist ausschließlich der Strichmenschenpfad freigeschaltet. Andere visuelle Typen und Produktionsprofile sind auch bei vollständiger Anbieterkonfiguration serverseitig eingefroren.

## Reale Stockmedien

Für lizenzierte reale Fotos und Videos ist ein Pexels-Adapter vorhanden. Pexels stellt Inhalte und API kostenlos bereit, verlangt für API-Aufrufe aber einen Kontoschlüssel und eine sichtbare Verlinkung. Der Schlüssel bleibt ausschließlich in `.env`:

```dotenv
PEXELS_API_KEY=...
```

Jede Auswahl wird mit Suchbegriff, Pexels-Seite, Urheber, Lizenz-URL, lokaler Datei und SHA-256 im versionsgebundenen `asset-manifest.json` gespeichert. Fehlt der Schlüssel oder ein Asset, bricht der Renderauftrag ab; es erscheint kein Platzhalter als vermeintlich fertiges Video. Kostenpflichtige generative Medien bleiben zusätzlich durch `ALLOW_PAID_MEDIA=0` gesperrt.

## Optionaler MoneyPrinterTurbo-Schnittpilot

MoneyPrinterTurbo ersetzt weder Skripterstellung noch Freigaben, Provenienz oder Veröffentlichung. Der Pilot tauscht ausschließlich den Schnitt aus und erhält dasselbe freigegebene Antigravity-Skript, dieselben bereits geladenen Pexels-Medien und dieselbe normalisierte Piper-Stimme wie der Remotion-Pfad. Damit bleibt der Vergleich aussagekräftig.

Das Fremdprojekt wird nicht in dieses Repository installiert. Es muss separat mit eigener Python-Umgebung vorhanden sein. Danach wird der standardmäßig abgeschaltete Adapter lokal konfiguriert:

```dotenv
MONEYPRINTER_ENABLED=1
MONEYPRINTER_ROOT=C:\Tools\MoneyPrinterTurbo
MONEYPRINTER_PYTHON=C:\Tools\MoneyPrinterTurbo\.venv\Scripts\python.exe
MONEYPRINTER_TIMEOUT_SECONDS=1800
```

Die Pipeline nutzt ausschließlich die offizielle Batch-CLI, startet keine Weboberfläche und öffnet keinen Port. Der freigegebene Text liegt nicht in der Prozesszeile. Der Unterprozess erhält eine bereinigte Umgebung ohne API-Schlüssel, darf keine externe Veröffentlichung auslösen und seine Ausgabedatei wird nur aus dem eigenen `storage/tasks/<task-id>` akzeptiert. Rohdiagnosen werden nicht protokolliert. MoneyPrinterTurbo kann über seine öffentliche CLI unsere geprüfte SRT-Datei nicht übernehmen; im kontrollierten Pilot ist deshalb seine eigene Untertitelerzeugung deaktiviert. Diese sichtbare Qualitätsgrenze gehört in den Vergleich und ist kein stiller Ersatz.

Diese Prozessgrenzen sind keine Betriebssystem-Sandbox: Separat installierter MoneyPrinterTurbo-Code läuft weiterhin mit den Rechten des angemeldeten Windows-Benutzers. Die Pipeline installiert oder startet das Fremdprojekt deshalb nicht selbst. Vor einem Echttest muss dessen Quellstand separat geprüft und die isolierte Laufzeit bewusst eingerichtet werden.

Für den Vergleich wird ein Stock-Auftrag zuerst mit „Cloud-Qualität · Stockvideo“ gerendert. Danach wird bei unverändertem Inhalt das Profil „MoneyPrinterTurbo · Pilot“ gespeichert, erneut freigegeben und gerendert. Nur wenn beide Dateien denselben Skript-Hash besitzen, zeigt die Weboberfläche sie nebeneinander. Laufzeit, Dateigröße und Codecs sind technische Hilfen; die Sichtprüfung auf passende Bilder, Stimme, sichtbare Fehler und Nachbearbeitungsaufwand bleibt erforderlich.

## Sprecherstimme und Qualitätsprüfung

Der lokale Standard bleibt Piper. Eine stumme Ersatzspur gilt nicht mehr als Erfolg: Fehlt die Stimme oder ist das Audio leer, bricht die Produktion ab. Optional kann die natürlichere, steuerbare Gemini-TTS-Stimme bewusst aktiviert werden:

```dotenv
TTS_PROVIDER=gemini
ALLOW_CLOUD_TTS=1
GEMINI_API_KEY=...
```

Gemini TTS besitzt derzeit ein Free Tier, aber übermittelte Inhalte dürfen dort zur Produktverbesserung verwendet werden; bei einem abrechenbaren Projekt können nach dem Freikontingent Kosten entstehen. Deshalb erfolgt kein automatischer Wechsel in diesen Modus.

Jeder Render erzeugt außerdem `voice-manifest.json`, `subtitles.srt` und `quality-report.json`. Erst wenn Sprecher-Audio nicht stumm ist, alle Sprachsegmente und visuellen Assets ihren Manifest-Hash erfüllen, Untertitel vorhanden sind und `ffprobe` Video-, Audio- und Laufzeitprüfung besteht, wechselt der Auftrag zu „Video prüfen“.

Unter Windows verwendet Remotion einen bereits installierten Chrome- oder Edge-Browser. Es lädt keinen Browser während des Renderns nach. Wird keiner gefunden, kann `REMOTION_BROWSER_EXECUTABLE` auf die lokale `chrome.exe` oder `msedge.exe` gesetzt werden. Fertige Auftragsvideos liegen bei lokalem Betrieb unter `data/jobs/<auftrags-id>/v<version>/video.mp4`; zusätzliche Formate liegen im Unterordner `formats/<seitenverhältnis>/`. Mit `DATA_DIR` lässt sich das Datenverzeichnis ändern.

## YouTube

Der Adapter ist implementiert, aber sicher deaktiviert. Ohne OAuth-Dateien speichert die zweite Freigabe nur `ready_to_publish`; es findet kein Upload statt. Für eine spätere Einrichtung werden die OAuth-Dateien unter `/data/secrets` erwartet und `YOUTUBE_ENABLED=1` gesetzt. Standard-Sichtbarkeit ist `private`.

## Mehrere Veröffentlichungsziele

Beim Anlegen eines Auftrags können mehrere Ziele gleichzeitig gewählt werden. Nach der zweiten, dateihashgebundenen Freigabe erhält jedes Ziel einen eigenen Status. Eingerichtete automatische Adapter werden gemeinsam eingereiht, aber bewusst einzeln und idempotent übertragen. Ein Fehler auf einer Plattform überschreibt nicht den Erfolg einer anderen; unterbrochene Uploads werden als „Status manuell prüfen“ markiert und nicht blind wiederholt.

Der Plattformkatalog umfasst YouTube/Shorts, Mastodon, TikTok, Instagram/Facebook Reels, LinkedIn, X, Bluesky, Podcast-RSS-Ziele, SoundCloud sowie Musik-Distributoren. Nur YouTube und Mastodon besitzen aktuell einen direkten Adapter. Andere Ziele zeigen ehrlich „Einrichtung nötig“, „RSS/Hosting erforderlich“ oder „Distributor erforderlich“.

Mastodon wird ausschließlich mit einer festen HTTPS-Instanz und lokalem Token aktiviert; die sichere Voreinstellung veröffentlicht privat:

```dotenv
MASTODON_ENABLED=1
MASTODON_BASE_URL=https://deine-instanz.example
MASTODON_ACCESS_TOKEN=...
MASTODON_VISIBILITY=private
```

Beim Rendern wird die Sprecher-Audiospur jetzt auf -16 LUFS mit -1,5 dB True-Peak-Reserve normalisiert. Das sorgt für gleichmäßigere Lautheit auf Video- und Podcastplattformen.

## Betrieb

```bash
docker compose logs -f
./scripts/doctor.sh
./scripts/smoke_test.sh
docker compose down
```

Nutzdaten liegen im benannten Docker-Volume `pipeline_data`. Ein Backup lässt sich später ohne Änderung an der Anwendung ergänzen. Die API-Dokumentation ist lokal unter <http://127.0.0.1:8080/api/docs> verfügbar.

## Architektur und Erweiterungen

- `backend/`: Workflow, SQLite, Freigabe-Invarianten, LLM-, Piper- und YouTube-Adapter
- `renderer/`: Remotion/React/SVG-Komposition und FFmpeg-Muxing
- `web/`: kleine lokale Bedienoberfläche
- `data/jobs/<id>/v<version>/`: versionsgebundene Render-Artefakte im Volume

Weitere Wege wie Blender, ComfyUI/Wan oder MoneyPrinterTurbo werden als neue Renderer hinter denselben Auftrag und dieselben Freigaben gesetzt. Sie sind bewusst nicht Voraussetzung für den ersten funktionierenden Produktionsweg.
