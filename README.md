# Lokale Video Pipeline

Eine lokale, erweiterbare Videoproduktion für den vorhandenen Ubuntu-Rechner. Die erste Produktionsart erzeugt CPU-taugliche Strichmännchen-/Erklärvideos mit Remotion, SVG, Piper und FFmpeg. FastAPI und SQLite speichern Auftrag, Versionen, Fehler und beide verbindlichen Freigaben.

## Start

```bash
cp .env.example .env
docker compose up --build -d
```

Danach ist die Oberfläche ausschließlich lokal unter <http://127.0.0.1:8080> erreichbar. Beim ersten Start wird das Piper-Stimmenmodell `de_DE-thorsten-high` in das Docker-Volume geladen. Falls der Download vorübergehend nicht klappt, erzeugt die Pipeline ein prüfbares Video mit stummer Ersatzspur und weist in der Oberfläche darauf hin.

Auf diesem Rechner liegt zusätzlich eine verifizierte projektlokale Testlaufzeit unter `.runtime`. Solange Docker wegen fehlender Socket-Berechtigung noch nicht nutzbar ist, startet die bereits installierte Fassung so im Vordergrund:

```bash
./scripts/run_local.sh
```

## Bedienung

1. Thema, Sprache, Länge, Format, Videoart und Ziel angeben.
2. Skript und Szenenplan bearbeiten und **Skript freigeben**.
3. **Video erzeugen**. Der Rechner bearbeitet bewusst nur einen Renderauftrag gleichzeitig.
4. Video ansehen und herunterladen.
5. Erst **Veröffentlichung freigeben** speichert die zweite, versionsgebundene Freigabe.

Änderungen am Skript erzeugen eine neue Version und löschen automatisch alte Skript-, Render- und Veröffentlichungsfreigaben. Wiederholte Renderaufrufe derselben Version werden nicht doppelt gestartet. Die Weboberfläche ist zunächst an `127.0.0.1` gebunden.

## Automatische Skripterstellung

Ohne Schlüssel läuft ein lokaler Vorlagenplaner (`SCRIPT_PROVIDER=template`). Für höhere Textqualität kann in `.env` genau einer der vorgesehenen Adapter aktiviert werden:

```dotenv
SCRIPT_PROVIDER=gemini
GEMINI_API_KEY=...
```

oder:

```dotenv
SCRIPT_PROVIDER=openrouter
OPENROUTER_API_KEY=...
```

Schlüssel gehören nur in `.env`; die Datei wird nicht versioniert.

## YouTube

Der Adapter ist implementiert, aber sicher deaktiviert. Ohne OAuth-Dateien speichert die zweite Freigabe nur `ready_to_publish`; es findet kein Upload statt. Für eine spätere Einrichtung werden die OAuth-Dateien unter `/data/secrets` erwartet und `YOUTUBE_ENABLED=1` gesetzt. Standard-Sichtbarkeit ist `private`.

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
