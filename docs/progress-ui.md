# Wartezeiten in der Strichmännchen-UI

Hörproben, Stimmenvergleich, Sprecher-Skript, KI-Überarbeitungen, Bildplanung und
Videoproduktion zeigen einen Ladebalken und die vergangene Zeit. Nach dem Start
wird die Anzeige automatisch in den sichtbaren Bereich gescrollt.

Die Restzeit und der Balken sind ausdrücklich **Schätzungen**: Qwen-TTS und die
Skriptanbieter liefern bei diesen Aufrufen kein laufendes Fortschrittssignal.
Die Startwerte berücksichtigen Anbieter, Textlänge beziehungsweise Videolänge.
Erfolgreiche Hörproben und Skripte passen die nächsten Schätzungen an die
gemessene Laufzeit an. Dafür speichert der Browser ausschließlich Zahlen je
Vorgangsart in `pipeline-process-times-v1`, keine Sprechertexte oder Prompts.
Sprechertext und Bildplanung nach der Freigabe haben getrennte Zeitmessungen.
Schnelle Cache-Antworten und fehlgeschlagene Aufrufe fließen nicht ein.

100 % erscheint erst nach erfolgreicher Antwort. Bei Überschreitung der
Schätzung bleibt die Anzeige unter 100 % und erklärt, dass der Vorgang weiter
läuft. Ein Fehler stoppt die Uhr und gibt die Bedienelemente wieder frei.
Während einer Hörprobe oder Skripterstellung verhindert die UI doppelte Starts
und versehentliches Schließen des Dialogs.

Eine eingereihte Videoproduktion zeigt zunächst ihre bisherige Wartezeit.
Die Dauer vor dem Produktionsstart lässt sich nicht verlässlich vorhersagen.
Nach Start zählt die Uhr ab dem gespeicherten Serverereignis, auch nach einem
Neuladen. Beim regelmäßigen Aktualisieren des Auftrags bleibt der Balken
erhalten. Die Render-Schätzung berücksichtigt Szenen, Stimme und Videoformate;
vorhandene Tonspuren können den Vorgang deutlich verkürzen.

Prüfung der Zeitlogik ohne zusätzliche Pakete:

```text
node --test tests/process-progress.test.cjs
```

Die Browserprüfung verwendet eine separate lokale Datenbank und verzögerte
Testantworten für Hörprobe, Skript und Überarbeitung. Warteschlange und
Renderstatus lassen sich so prüfen, ohne einen echten Film zu erzeugen oder
bestehende Aufträge zu verändern. Neue Backend-Berechtigungen, Netzwerkdienste
oder kostenpflichtige Anbieter werden für die Anzeige nicht benötigt.
