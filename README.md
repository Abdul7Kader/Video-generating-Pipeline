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

## KI-Skripterstellung

Die Pipeline erzeugt absichtlich **kein** allgemeines Vorlagenskript mehr. Ohne bewusst konfigurierten KI-Anbieter antwortet die Auftragserstellung mit einer klaren Konfigurationsmeldung. `SCRIPT_PROVIDER=auto` nutzt nur einen tatsächlich vorhandenen Schlüssel (Reihenfolge: Gemini, OpenAI, OpenRouter).

Kostenbewusster Einstieg mit begrenztem Gemini-Free-Tier:

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

Schlüssel gehören nur in `.env`; die Datei wird nicht versioniert. Ein ChatGPT-/Codex-Abo umfasst keine OpenAI-API-Nutzung. Beim Gemini-Free-Tier ist außerdem zu beachten, dass übermittelte Inhalte laut Anbieter zur Produktverbesserung verwendet werden können.

Der KI-Entwurf enthält neben dem Sprechertext einen konkreten Produktionsplan pro Szene (visueller Medientyp, sichtbare Einstellung, Asset-Prompt, Kamera, bewusste Texteinblendung und Übergang). Über das Feld „Änderungswunsch an die KI“ entsteht eine neue Skriptversion; alte Freigaben werden dabei ungültig.

Eine einzelne Szene kann separat gespeichert werden. Auch das erzeugt eine neue, hashgebundene Planversion. Beim nächsten Render werden unveränderte Stockmedien und Voiceover-Segmente nach Prüfung ihres SHA-256 wiederverwendet; nur betroffene Szenen werden neu beschafft beziehungsweise gesprochen. Der finale Film wird immer neu zusammengesetzt und als eigene Renderrevision geprüft.

Nicht verfügbare visuelle Typen werden bewusst gesperrt. Sie werden nicht mehr irreführend durch denselben Strichmännchenfilm ersetzt. Aktuell freigeschaltet sind der bestehende Strichmännchenpfad sowie echte Stockfotos/-videos bei konfiguriertem Pexels-Zugang.

## Reale Stockmedien

Für lizenzierte reale Fotos und Videos ist ein Pexels-Adapter vorhanden. Pexels stellt Inhalte und API kostenlos bereit, verlangt für API-Aufrufe aber einen Kontoschlüssel und eine sichtbare Verlinkung. Der Schlüssel bleibt ausschließlich in `.env`:

```dotenv
PEXELS_API_KEY=...
```

Jede Auswahl wird mit Suchbegriff, Pexels-Seite, Urheber, Lizenz-URL, lokaler Datei und SHA-256 im versionsgebundenen `asset-manifest.json` gespeichert. Fehlt der Schlüssel oder ein Asset, bricht der Renderauftrag ab; es erscheint kein Platzhalter als vermeintlich fertiges Video. Kostenpflichtige generative Medien bleiben zusätzlich durch `ALLOW_PAID_MEDIA=0` gesperrt.

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
