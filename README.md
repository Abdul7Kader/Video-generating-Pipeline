# Lokale Video Pipeline

Eine lokale, erweiterbare Videoproduktion für den vorhandenen Ubuntu-Rechner. Die erste Produktionsart erzeugt CPU-taugliche Strichmännchen-/Erklärvideos mit Remotion, SVG, Piper und FFmpeg. FastAPI und SQLite speichern Auftrag, Versionen, Fehler und beide verbindlichen Freigaben.

## Start

Direkt im Projektordner liegen zwei Starter:

- **Windows:** `Start-Pipeline.cmd` doppelklicken. Das sichtbare Konsolenfenster zeigt den Server; mit `Strg+C` wird er beendet. Die vorhandene `.runtime/windows-python`-Umgebung wird bevorzugt, andernfalls eine bereits eingerichtete System-Python-Umgebung. Es wird nichts automatisch installiert.
- **Linux:** im Terminal `./Start-Pipeline.sh` ausführen. Der Starter bevorzugt eine vorhandene lokale Python-/Node-Laufzeit und verwendet sonst Docker Compose, falls Docker läuft. Beim ersten Docker-Start werden die im Compose-Projekt festgelegten Images und das Qwen-Modell geladen.

Beide Starter binden die Weboberfläche ausschließlich an `127.0.0.1`. Im lokalen Python-Betrieb wird sie nach dem Gesundheitscheck im Browser geöffnet; ohne grafischen Browser steht die Adresse im Terminal. Eine bereits laufende Pipeline wird erkannt und nicht doppelt gestartet. Lokale Einstellungen können in einer nicht versionierten `.env` stehen. Für den Qwen-Fallback muss Ollama separat laufen; Antigravity benötigt keinen gestarteten Ollama-Dienst.

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

1. Thema, Sprache, Länge, Format, Videoart und Ziel angeben.
2. Skript und Szenenplan bearbeiten und **Skript freigeben**.
3. **Video erzeugen**. Der Rechner bearbeitet bewusst nur einen Renderauftrag gleichzeitig.
4. Video ansehen und herunterladen.
5. Erst **Veröffentlichung freigeben** speichert die zweite, versionsgebundene Freigabe.

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
OLLAMA_NUM_PREDICT=2048
OLLAMA_TIMEOUT_SECONDS=720
```

Das lokale Modell bearbeitet höchstens eine Skripterstellung gleichzeitig. Vor einem aufwendigen Render wird es aus dem Arbeitsspeicher entladen. Ist Ollama nicht erreichbar, liefert die Oberfläche einen verständlichen Fehler; es gibt weder einen Vorlagen- noch einen Cloud-Ersatzpfad.

Die vorhandenen Cloudadapter bleiben ausschließlich für eine spätere ausdrücklich gewählte Konfiguration erhalten. Sie werden nicht automatisch verwendet.

### Gemini CLI mit Google AI Pro

Wichtiger aktueller Produktstand: Google hat „Login with Google“ in Gemini CLI für private Gemini-Code-Assist-, Google-AI-Pro- und Google-AI-Ultra-Konten zum 18. Juni 2026 eingestellt. Der reale Login auf diesem Rechner endet deshalb mit `This client is no longer supported for Gemini Code Assist for individuals`. Gemini CLI bleibt laut Google nur mit Code Assist Standard/Enterprise unterstützt. Für Consumer-/Pro-Konten verweist Google auf Antigravity CLI. Quelle: <https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals>.

Die sichere Gemini-CLI-Integration bleibt daher standardmäßig deaktiviert. Sie ist für ein künftig unterstütztes CLI-Profil beziehungsweise Code Assist Standard/Enterprise vorbereitet. Jedes Konto erhält ein getrenntes `GEMINI_CLI_HOME`; die Pipeline speichert oder zeigt keine Tokens, Cookies oder Passwörter. Profilverzeichnisse werden mit folgendem Skript eingerichtet und interaktiv angemeldet:

```powershell
.\scripts\gemini_profile.ps1 -Profile primary -Action login
.\scripts\gemini_profile.ps1 -Profile secondary -Action login
```

Die Anmeldung erfolgt vollständig im offiziellen CLI-/Google-Dialog. Beim ersten Start wird der leere Profil-Arbeitsordner ausdrücklich als **nicht vertrauenswürdig** gewählt. Für Pipeline-Aufrufe sind alle Gemini-CLI-Tools per Policy gesperrt; Prompts werden über stdin übergeben und nicht als Kommandozeilenargument sichtbar. Der Pool zeigt keine erfundene Resttokenzahl. Raten-/Kontingentfehler führen zu einer Cooldown-Markierung und der aktuelle Schritt wird mit exakt derselben gespeicherten Eingabe über das nächste verfügbare Profil neu gestartet.

Die Profile werden nur nach einem erfolgreichen, offiziell unterstützten Einzeltest aktiviert. Mit den vorhandenen Google-AI-Pro-Konten darf diese Einstellung derzeit **nicht** aktiviert werden:

```dotenv
GEMINI_CLI_ENABLED=1
GEMINI_CLI_PROFILES=primary,secondary
```

Im Dialog **Neues Video** kann zwischen lokalem Qwen und der Gemini CLI gewählt werden. Der Gemini-Pfad speichert Themenbriefing, Struktur, vollständiges Sprecher-Skript, Szenenplan und Qualitätsprüfung einzeln mit Eingabe-/Ausgabehash, Modell, Profil und Prompt-Version. Nach einem Serverneustart werden abgeschlossene Schritte nicht erneut erzeugt. Die technische Spezifikation steht in `SPEC-gemini-cli-pool.md`.

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

Nicht verfügbare visuelle Typen werden bewusst gesperrt. Sie werden nicht mehr irreführend durch denselben Strichmännchenfilm ersetzt. Aktuell freigeschaltet sind der bestehende Strichmännchenpfad sowie echte Stockfotos/-videos bei konfiguriertem Pexels-Zugang.

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
