# Endvideos, Arbeitsdateien und Weiterbearbeitung

Stand: 16.10.2026. Nutzerentscheidung: **nur manuell aufräumen**. Die optionale
automatische Bereinigung ist standardmäßig deaktiviert; es läuft kein eigener
Hintergrunddienst dafür.

## In der Oberfläche

1. **Einstellungen → Endvideos und Arbeitsdateien getrennt speichern** öffnen.
   Einen lokalen Ordner für fertige Videos auswählen und speichern. Ohne eigene
   Auswahl verwendet die Pipeline `data/videos/`. Arbeitsmaterial bleibt in
   `data/jobs/<Auftrag>/v<Version>/`. Modell-Downloads und andere Projekte werden
   durch die Bereinigung nicht angetastet.
2. Neue Endvideos werden nach erfolgreicher Produktion geprüft, getrennt abgelegt
   und ihr Ort gespeichert. Erst nach verifizierter Kopie und gespeichertem Verweis
   wird die identische Arbeitskopie entfernt. Vorschau, Download, Discord und
   Veröffentlichung verwenden den gespeicherten Endvideoort. Bei Schreib-/Kopierfehler
   bleibt das Video im Arbeitsordner und die Pipeline meldet den Ablagefehler.
3. Ein vorhandenes Video über **Endvideo im Videoordner sichern** übernehmen.
   Alte externe Ablagen werden bei einem späteren Ordnerwechsel nicht automatisch
   gelöscht. Gleicher Inhalt ist wiederholbar; unterschiedliche Videodateien
   erhalten Namen mit Version, Format und Prüfsumme und werden nicht überschrieben.
4. **Arbeitsdateien jetzt bereinigen · Endvideo behalten** entfernt erzeugte
   Tonabschnitte, Zeichnungsdateien und dazugehörige Render-/Audio-Manifeste.
   Skriptversionen in der Datenbank, Endvideos, Qualitätsnachweise und unbekannte
   eigene Dateien bleiben erhalten. Andere, ältere MP4-Dateien im Arbeitsordner
   werden vorsichtshalber ebenfalls nicht von der Bereinigung gelöscht.
5. **Projekt behalten** schützt die Arbeitsdateien vor manueller und optionaler
   automatischer Bereinigung. Vor einem bewussten Aufräumen den Schutz ausschalten.

Laufende/vorgemerkte Produktion, aktive Discord-Überarbeitung und laufende,
unklare oder noch in TikTok zu bestätigende Übertragungen werden übersprungen.
Ein fehlender oder veränderter gespeicherter Endfilm verhindert die Bereinigung.
Pfadgrenzen werden geprüft; symbolischen Links und Windows-Verzeichnisverknüpfungen
wird bei der Bereinigung nicht gefolgt. Die Funktion arbeitet nur in den zum
Auftrag gehörenden Arbeitsverzeichnissen, nie in frei angegebenen Löschordnern.

## Später weiterbearbeiten

Beim vorhandenen Auftrag **Skript bearbeiten** wählen und einen KI-Änderungswunsch
angeben. Idee, Text, Zeichenplan und Versionsgeschichte bleiben gespeichert;
eine neue Bearbeitung muss nicht wieder mit einem leeren Prompt beginnen.

Vorhandene unveränderte Sprachabschnitte werden anhand von Inhalt, Stimme und
Einstellungen wiederverwendet. Änderungen an Text oder Stimme brauchen passende
neue Sprachdaten. Bilder, Animation und Schnitt werden für das neue Video erneut
zusammengesetzt; ein allgemeiner schnittweiser Videocache ist nicht implementiert.
Nach einer Arbeitsdatei-Bereinigung müssen entfernte Ton-/Bildmaterialien neu
erzeugt werden. Das alte getrennte Endvideo bleibt dabei erhalten. Die fertige
MP4 allein ersetzt kein vollständig erhaltenes Bearbeitungsprojekt.

Wer spätere Änderungen schnell und ohne erneute TTS-Erzeugung vornehmen möchte,
sollte **Projekt behalten** aktivieren und die Arbeitsdateien aufbewahren.

Optional sind in Einstellungen 30/90/180/365 Tage wählbar. Die Frist läuft ab
der letzten Auftragsänderung; frische Arbeitsdateien verlängern den Schutz.
Ein ungeschützter abgelaufener Auftrag wird dann nur bei geöffneter Anwendung,
im Leerlauf und unter denselben Sicherheitsbedingungen bereinigt. Die Voreinstellung
bleibt **Automatik aus**. Ein Rechenlauf, ein Kontologin oder ein Upload wird durch
die Bereinigung nicht gestartet.

## Nachweise

317 Backend-Tests (10 vorgesehene Skips), 60 JS-Tests und die native Windows-
Fensterprüfung bestanden. Neue Prüfungen: manuelle Voreinstellung, explizite
Bereinigung, optionale Frist, Schutzschalter, aktive Vorgänge, veraltete Version,
fehlender Endvideo-Datenträger, fehlgeschlagene Kopie, Erhalt anderer MP4s und
unbekannter Dateien sowie Wiedergabe nach Bereinigung und spätere Skriptbearbeitung.
Keine vorhandenen Nutzerdateien bereinigt und kein Testvideo erzeugt.
