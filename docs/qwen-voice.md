# Die ausgewählte Qwen-Erzählerstimme

Qwen3-TTS läuft hier lokal, ohne ElevenLabs, Konto, API-Schlüssel oder bezahlte
Cloud-Anfragen. Modell und Qwen-Software stehen unter Apache-2.0; kommerzielle
Nutzung ist möglich, die jeweiligen Lizenzhinweise bleiben zu beachten. Strom,
Speicher und Rechenzeit fallen auf dem eigenen Rechner an. Die öffentliche
Hugging-Face-Demo hat Warteschlangen und ist kein Produktionsdienst der Pipeline.

## In der Oberfläche

Nach Einrichtung und Neustart: **Neues Video → Stimmenstudio · lokal →
Qwen · tiefer Erzähler**. Diese Stimme wird bei neuen deutschen Aufträgen
vorausgewählt, sobald ihre Installation verfügbar ist. Zum Prüfen **Stimmen hören
und vergleichen → Ausgewählte Stimme anhören** verwenden; auf einer CPU dauert
eine neue Hörprobe deutlich länger als mit Piper. Identische Proben werden
zwischengespeichert. **Alle verfügbaren Stimmen vergleichen** erstellt auch die
Piper-Proben.

Bei bestehenden Aufträgen die Stimme auswählen, **Produktionskonfiguration
speichern**, Sprechertext und Zeichenregie prüfen, **Skript freigeben**, dann
**Video erzeugen**. Die gespeicherte Auswahl gilt für alle Szenen und Formate.
Pausenkürzung, Tempo, Wortzeiten und Bewegungsregie bleiben Teil der Produktion.
Neue Audioerzeugung kann geringfügig anders klingen als die ursprüngliche Demo;
die feste Referenz stabilisiert den Stimmcharakter.

## Einmalige Installation

Die Hauptanwendung braucht kein Torch. Qwen verwendet eine eigene Python-3.12-
Umgebung, weil die Windows-Hauptlaufzeit Python 3.14 verwendet. Unter Windows,
mit installiertem Python 3.12, im Projektverzeichnis:

```powershell
py -3.12 -m venv .runtime/qwen-python
.runtime/qwen-python/Scripts/python.exe -m pip install pip==26.2.1 setuptools==83.0.0 --index-url https://pypi.org/simple
.runtime/qwen-python/Scripts/python.exe -m pip install torch==2.9.1+cpu torchaudio==2.9.1+cpu --index-url https://download.pytorch.org/whl/cpu
.runtime/qwen-python/Scripts/python.exe -m pip install -r requirements-qwen-lock.txt --index-url https://pypi.org/simple
.runtime/qwen-python/Scripts/python.exe -m pip check
.runtime/qwen-python/Scripts/python.exe scripts/setup_qwen_voice.py
```

Der Lockstand ist für die getestete Windows-CPU-Laufzeit mit Python 3.12. Unter
Linux heißen die ausführbaren Dateien `.runtime/qwen-python/bin/python`; eine
entsprechende Installation ist separat zu prüfen. Kein FlashAttention oder CUDA
wird benötigt. Das Sprachmodell benötigt etwa 4,5 GB auf der Platte; die volle
FP32-Verarbeitung braucht zusätzlich mehrere GB Arbeitsspeicher. Auf dem
Entwicklungsrechner sind 32 GB RAM vorhanden. Das Skriptmodell wird vor neuen
Hörproben und dem Rendern aus Ollama entladen, um Speicher freizugeben.

Lokaler Ersttest am 2026-10-12: der 25-Wörter-Vergleichstext brauchte bei 1,1×
Tempo einschließlich Modellstart etwa **155 Sekunden** für 9,7 Sekunden Audio
vor der Pausenkürzung. Gemessener Arbeitsspeicher während der Erzeugung: etwa
8,4 GB. Das ist ein einzelner Messwert, keine garantierte Renderzeit. Längere
Filme dauern auf einer CPU entsprechend länger; identische Szenenspuren werden
bei weiteren Versionen und Formaten aus dem vorhandenen Cache übernommen.

Bei Downloadfehlern denselben Setup-Befehl erneut starten. Erst nach vollständig
abgeschlossenem Download wird die Stimme als eingerichtet angezeigt. Es werden
keine Modelle automatisch durch einen Renderauftrag heruntergeladen.

Optionale lokale Variablen:

| Variable | Standard |
|---|---|
| `QWEN_TTS_PYTHON` | Python im Projekt unter `.runtime/qwen-python` |
| `QWEN_TTS_MODEL_DIR` | `data/voices/qwen-model` |
| `QWEN_TTS_THREADS` | 4, begrenzt auf 1–8 |
| `QWEN_TTS_TIMEOUT_SECONDS` | 1800 pro Sprachsegment, begrenzt auf 60–3600 |

Diese Pfade werden vom Betreiber gesetzt. Die API akzeptiert ausschließlich die
feste Stimmen-ID `qwen_narrator`, deutschen Text und Tempo 0,85–1,25×.

## Referenz, Quellstand und Grenzen

Die vom Nutzer am 2026-10-12 ausgewählte, künstlich erzeugte VoiceDesign-Probe
ist `examples/qwen-narrator-reference.wav` (24 kHz, 10,777 Sekunden). Sie stellt
keine nachgeahmte reale Person dar. Der Stilprompt lautete:

> A German male narrator in his early thirties with a naturally deep, rich,
> slightly textured voice. Native standard German pronunciation. Warm, confident
> and conversational, like a creator explaining a fascinating story to a friend.
> Lively emphasis, brisk flowing delivery, no long dramatic pauses, no announcer
> or advertising tone. Clean studio recording.

Das VoiceDesign-Modell erzeugte die Referenz in der offiziellen Qwen-Demo.
Für neue Sprechertexte nutzt die Pipeline **Qwen3-TTS-12Hz-1.7B-Base** mit dieser
Referenz und ihrem vollständigen Transkript. Es werden keine privaten
Stimmaufnahmen hochgeladen. Referenz, Modellstand und Erzeugungspolicy fließen
in den Audio-Cache ein. Manipulierte Referenzen werden abgewiesen; bei Fehlern
ersetzt die Pipeline Qwen weder durch Piper noch durch eine stumme Tonspur.

- Modellrevision: `fd4b254389122332181a7c3db7f27e918eec64e3`
- Referenz-SHA256: `866676d828cc7df2cdaf4723f167b6a530298ac72b2f49e7085358075e400ab4`
- Qwen-Paket: `qwen-tts==0.1.1`
- Offline-Verarbeitung: lokales Modell, `local_files_only`, kein Remote-Code,
  SafeTensors, getrennte Laufzeit ohne User-Site/PYTHONPATH; feste Prozessargumente
  und JSON über stdin. API-Schlüssel werden nicht in seine Umgebung übernommen;
  ein Zeitlimit beendet den eigenen Prozessbaum einschließlich Windows-Launcher.
  Der Prozess läuft mit den normalen Benutzerrechten,
  die separate Python-Umgebung ist keine Betriebssystem-Sandbox.

## Abhängigkeitsprüfung und Sicherheitsgrenzen

`pip check` besteht. `pip-audit` vom 2026-10-12 meldet nach Aktualisierung von
pip und setuptools weiterhin zehn Einträge in zwei Paketen (teils doppelte
Meldungen). Das offizielle Qwen-Paket legt `transformers==4.57.3` und
`accelerate==1.12.0` fest; eine inkompatible Version wird nicht erzwungen.

Die verbleibenden Meldungen betreffen Trainer-Checkpoint-Deserialisierung,
X-CLIP-Konvertierung, LightGlue, externe Attention-Kernels, Custom-Generate,
Tokenizer-Speichern und manipulierte Shard-Indizes. Unsere Inferenz trainiert
nicht, konvertiert keine Checkpoints, speichert keine Tokenizer und verwendet
keine Custom-Generate-Funktion. Sie lädt ausschließlich den festgelegten
offiziellen Qwen-Stand als SafeTensors, explizit mit PyTorch-SDPA und im
Offline-Modus. Die API erlaubt keine Modellpfade, Konfigurationen, Uploads
oder URLs. Der Modellstand enthält keine Shard-Indexdatei.

Das begrenzt die betreffenden Angriffswege dieser Integration, beseitigt jedoch
keine Schwachstelle in den Bibliotheken selbst. Eine Funktion für fremde Modelle,
Training oder frei hochgeladene Referenzen braucht vor Freigabe eine erneute
Bewertung und gepflegte kompatible Abhängigkeiten. Die isolierte Laufzeit darf
nicht für solche fremden Modelle wiederverwendet werden. Der Prüfbericht liegt
lokal unter `data/qwen-dependency-audit.json`.

Die Gewichte werden nur beim Setup von Hugging Face geladen. Bei der
Spracherzeugung sind Hugging-Face-Netzwerkzugriff, implizite Tokens und Telemetrie
deaktiviert. Das Tempo wird mit FFmpeg `atempo` ohne Tonhöhenänderung angepasst.
Wortzeiten für die Zeichnungen sind weiterhin Näherungen, keine genaue ASR.

Für eine lokale Filmprobe ohne Skript-KI:

```powershell
.runtime/windows-python/Scripts/python.exe scripts/render_stickman_demo.py --voice qwen_tts --script examples/stickman-motion-demo.json --output data/qwen-motion-preview
```

Der lokale Test mit drei neuen Szenentexten erzeugte einen Film von etwa
14,5 Sekunden. Alle neun Prüfungen in `quality-report.json` bestanden, darunter
Sprachsegmente, Bindung an das Skript, Untertitel, Audio-/Videospur und Dauer.
Stimmenwahl, Speichern und der Audio-Player wurden zusätzlich im Browser mit
einer separaten Testdatenbank geprüft. Ein echter Windows-Timeout-Test beendete
alle eigenen Unterprozesse nach etwa 3,5 Sekunden.

Offizielle Quellen:
[Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS),
[Modellkarte](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base),
[Apache-2.0-Lizenz](https://github.com/QwenLM/Qwen3-TTS/blob/main/LICENSE),
[Qwen-Paket](https://pypi.org/project/qwen-tts/0.1.1/).
