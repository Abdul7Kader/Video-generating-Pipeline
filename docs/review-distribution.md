# Videoabbruch, Discord-Abnahme und Verteilung

Auftrag vom 16.10.2026. Desktopabschluss ist gesichert; diese Erweiterung folgt.

1. Abbruch je Auftrag, schon während KI-Zeichenplanung, Stimme und Schnitt. Nur
   eigene Prozesse dieses Vorgangs enden. Skripte/fertige Videos bleiben erhalten;
   abgebrochene Teile werden nicht freigegeben oder veröffentlicht. Verspätete
   Ergebnisse dürfen einen Abbruch nicht überschreiben. Kein Film als Routinetest.
2. Einstellungen: Videoordner, Discord-Ziel und erlaubte Freigeber, Plattformkonten
   und API-Zugänge. Neue Geheimnisse im nativen Betriebssystem-Tresor, nie in
   API-Antworten/Logs/Git. Einstellungen nur über bestehenden lokalen Schutz.
3. Discord erhält die fertige Datei mit Video-/Versionsbindung und Knöpfen für
   Freigabe, Änderungswunsch und Ablehnung. Bot-Gateway ausschließlich ausgehend,
   keine öffentlichen Webhooks/Ports. Nur gewählte Server/Kanäle/Nutzer dürfen
   entscheiden. Alte/fremde/doppelte Freigaben dürfen nichts veröffentlichen.
4. Nach Freigabe genau die geprüften Dateien an ausgewählte eingerichtete Ziele
   übertragen. Vorhandene YouTube-/Mastodon-Dispatcher und Idempotenz weiterverwenden;
   Meta/TikTok über offizielle APIs und deren Rechte-/Consent-Voraussetzungen.
   Kein Ersetzen fehlender Anbieterfreigaben durch Login-/CAPTCHA-/Browsertricks.
5. Sichtbarer Zielstatus, Fehler/Fortsetzung ohne blinde Upload-Wiederholung.
   Ohne API-Zugang klares Exportpaket und reguläre Anbieter-Anmeldung. Keine
   Monetarisierungsgarantie; Freigaben und Einnahmeprogramme verwaltet der Anbieter.

Native Windows-Anwendung verwenden. Keine WSL-Chromium-Instanz, fremde Browser,
Portsuche oder Eingriffe in andere laufende Arbeiten. Bereits laufende Nutzer-
produktion erst bei nötigem Neustart berücksichtigen.

Abnahme: echte Prozess-Abbruchfixture ohne Modell/Video, Zustands-/Hash-/Rennfall-
Tests, negative Discord-Berechtigungsfälle, gemockte Hersteller-APIs, UI-Prüfung.
Live-Uploads/Anmeldungen erst nach Einrichtung der eigenen Zielkonten; kein
ungefragtes Veröffentlichen vorhandener Filme.

Stand: Umsetzung beginnt mit Punkt 1; weitere Punkte noch offen.
