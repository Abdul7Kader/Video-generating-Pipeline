const {app, dialog} = require('electron');
const {startDesktop} = require('./main.cjs');

startDesktop().catch(() => {
  dialog.showErrorBox('Video Pipeline – Start fehlgeschlagen',
    'Die lokale Pipeline konnte nicht sicher gestartet werden. Prüfe die Einrichtung und data/desktop/backend.log.');
  app.exit(1);
});
