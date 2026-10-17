# Technologiestech

Werkzeuge der Strichmännchen-Pipeline. Alternativen werden ausdrücklich ausgewählt.

| Tool / Technologie | Wofür wir es nutzen | Anmeldung / Abo |
|---|---|---|
| Cloudflare Workers AI + FLUX.1 schnell | KI-Bilder für Frame; Adapter und Einzelbildtest eingebaut. | Workers-Free-Konto, Account-ID und API-Token; Tageskontingent, Live-Einrichtung noch nötig. |
| Electron + native Prozessverwaltung | Eigenes Programmfenster; gemeinsamer Start/Stopp. Windows: Job Objects, Linux: systemd + Subreaper, macOS: launchd + Prozessregistrierung (Mac-Abnahme offen). | Kein Konto, kein Abo; lokale Desktop-Laufzeit herunterladen. |
| Antigravity + Gemini | Skripte überarbeiten und Szenarien planen; beim letzten Katzenvideo verwendet. | Eigenes berechtigtes Google-Konto nötig. Kostenloses begrenztes Basiskontingent, Pro-Abo optional; Zusatzcredits werden vor jedem Aufruf geprüft und müssen aus sein; Modelle und Limits hängen vom Konto ab. [Tarife](https://www.antigravity.google/docs/plans) |
| Web-KI (z. B. Gemini-Webversion) | Manueller Prompt-/Antwortimport für Text, Überarbeitung und Zeichenplan. | Anmeldung beim gewählten Anbieter; dessen Gratislimits/Tarife gelten. Kein automatischer Weblogin. |
| Ollama + Qwen 3.5 | Alternative für lokale Skripte und Szenarien. | Kein Konto, kein Abo; Modell herunterladen. |
| Qwen3-TTS + PyTorch | Natürlichere Erzählerstimme auf dem eigenen Rechner. | Kein Konto, kein Abo; Modell herunterladen. |
| Piper TTS | Schnellere, sparsame lokale Stimmalternative. | Kein Konto, kein Abo; Stimme herunterladen. |
| Eigener SVG-Code | Strichmännchen, Tiere, Gegenstände und Bewegungen zeichnen. | Kein Konto, kein Abo. |
| Remotion + React + TypeScript | Zeichnungen, Animation und Ton zum Video zusammensetzen. | Kein Konto für lokales Rendern. Remotion ist für Einzelpersonen und Firmen bis 3 Personen kostenlos; größere Firmen benötigen eine kostenpflichtige Lizenz. [Lizenz](https://github.com/remotion-dev/remotion/blob/main/packages/core/LICENSE.md) |
| Node.js | Führt die Video-Renderwerkzeuge aus. | Kein Konto, kein Abo. |
| Chrome / Edge / Chromium | Berechnet die einzelnen Videobilder. | Kein Konto, kein Abo. |
| FFmpeg / FFprobe | Audio verarbeiten, Videos kodieren und Mediendateien prüfen. | Kein Konto, kein Abo. |
| Python + FastAPI + Uvicorn | Steuert Aufträge und stellt die lokale Webseite bereit. | Kein Konto, kein Abo. |
| SQLite | Speichert Aufträge, Skriptversionen, Freigaben und dauerhafte Endvideoorte. | Kein Konto, kein Abo. |
| keyring + Betriebssystem-Tresor | Neue API-Schlüssel und Anmeldetokens geschützt speichern. | Kein Abo; Windows-Tresor, Mac-Schlüsselbund oder Linux Secret Service nötig. |
| Discord Bot API + WebSocket-Gateway | Videos zur Abnahme senden; Freigeben, Ändern, Ablehnen. | Discord-Konto, eigener Bot, Server-/Kanalrechte und erlaubte Nutzer-IDs. |
| YouTube Data API + Google OAuth | Freigegebene Videos hochladen. | Google-Konto/Kanal, Entwicklerprojekt, OAuth-Desktopclient; Anbieterquoten gelten. |
| Meta Graph APIs | Facebook-Seiten-Reels und Instagram-Reels veröffentlichen. | Entwickleranwendung, autorisierter Token und passende Konto-/Veröffentlichungsrechte; Instagram Professional. |
| TikTok Content Posting API | Video als Entwurf in die TikTok-Inbox übertragen, Status prüfen. | Entwickleranwendung, OAuth-Zugang mit video.upload; endgültig in TikTok posten. |
| HTML + CSS + JavaScript | Benutzeroberfläche mit Einstellungen und Videobedienung. | Kein Konto, kein Abo. |

Frame-Bilder: Cloudflare Workers AI / FLUX.1 schnell (Free-Konto, Account-ID und
API-Token nötig) oder vorhandenes Google-Abo über eingeschränkten Antigravity-CLI-
Bildadapter (Google-Einzelbild erfolgreich getestet). Keine separate Gemini-Bild-API.
Cloudflare-Live-/Serien-/Visionabnahme offen;
Skriptanmeldung allein bestätigt keine erfolgreiche Bilderzeugung.

ElevenLabs wird aktuell nicht verwendet. Codex wird für die Entwicklung genutzt; die fertige Pipeline benötigt keinen Coding-Agenten.
