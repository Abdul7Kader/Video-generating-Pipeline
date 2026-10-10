// Drawing instructions remain data. All text is escaped before inserting HTML.
window.DrawingEditor = (() => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const settings = {white:'Weißes Zeichenblatt',room:'Zimmer',office:'Büro',nature:'Natur',camp:'Lager',city:'Stadt',classroom:'Klassenraum'};
  const frames = {wide:'Totale',medium:'Halbnah',closeup:'Nahaufnahme',split:'Gegenüberstellung'};
  const cameras = {static:'Ruhige Kamera',push_in:'Langsam näher kommen',pan_left:'Nach links schwenken',pan_right:'Nach rechts schwenken'};
  const poses = {stand:'Stehen',walk:'Gehen',run:'Laufen',point:'Zeigen',think:'Nachdenken',shrug:'Schultern zucken',sit:'Sitzen',sleep:'Schlafen',work:'Arbeiten',gather:'Sammeln',carry:'Tragen',pick:'Aufheben',place:'Ablegen',read:'Lesen',celebrate:'Freuen',talk:'Sprechen'};
  const expressions = {neutral:'Neutral',happy:'Fröhlich',sad:'Traurig',worried:'Besorgt',angry:'Wütend',surprised:'Überrascht',tired:'Müde',determined:'Entschlossen'};
  const outfits = {plain:'Ohne Kleidung',prehistoric:'Steinzeit',office:'Büro',scientist:'Laborkittel',casual:'Alltag'};
  const props = {clock:'Wecker',laptop:'Laptop',desk:'Tisch',chair:'Stuhl',bed:'Bett',phone:'Telefon',book:'Buch',tree:'Baum',bush:'Beerenstrauch',fire:'Lagerfeuer',spear:'Speer',basket:'Korb',rock:'Stein',sun:'Sonne',moon:'Mond',cloud:'Wolke',house:'Haus',food:'Essen',water:'Wasser',gear:'Zahnrad',lightbulb:'Glühbirne',arrow:'Pfeil',question:'Fragezeichen',check:'Haken',cross:'Kreuz',heart:'Herz',chart:'Diagramm'};
  const select = (key, label, choices, current) => `<label class="field"><span>${label}</span><select aria-label="${escape(label)}" data-drawing-field="${key}">${Object.entries(choices).map(([id,name])=>`<option value="${id}" ${id===current?'selected':''}>${name}</option>`).join('')}</select></label>`;
  const number = (key,label,value,min,max,step=1) => `<label class="field"><span>${label}</span><input data-drawing-field="${key}" type="number" min="${min}" max="${max}" step="${step}" value="${escape(value)}"></label>`;
  const text = (key,label,value,max=32) => `<label class="field"><span>${label}</span><input data-drawing-field="${key}" maxlength="${max}" value="${escape(value)}"></label>`;
  const cueRow = cue => `<div class="drawing-item" data-cue-row><div class="drawing-grid">${[
    text('on','Start bei diesen Sprecherworten',cue.on||'',100),
    select('pose','Handlung',poses,cue.pose||'point'),
    select('expression','Gesichtsausdruck',{'':'Beibehalten',...expressions},cue.expression||''),
    select('target_prop','Zielgegenstand',{'':'Keiner',...Object.fromEntries(Array.from({length:8},(_,i)=>[String(i),`Requisite ${i+1}`]))},cue.target_prop==null?'':String(cue.target_prop)),
    number('move_to','Gehen zu (%) · leer = bleiben',cue.move_to??'',8,92),
    number('duration','Bewegung dauert (Sekunden)',cue.duration??.55,.15,2.5,.05),
  ].join('').replaceAll('data-drawing-field','data-cue-field')}</div><button type="button" class="ghost drawing-remove-cue">Regieschritt entfernen</button></div>`;
  const characterRow = (c,i) => `<div class="drawing-item" data-character-row><h4>Figur ${i+1}</h4><div class="drawing-grid">${text('id','Figurenname',c.id||`figur-${i+1}`)}${select('pose','Anfangshaltung',poses,c.pose||'stand')}${select('expression','Gesichtsausdruck',expressions,c.expression||'neutral')}${select('outfit','Kleidung',outfits,c.outfit||'plain')}${select('facing','Blickrichtung',{left:'Links',right:'Rechts'},c.facing||'right')}${number('x','Position links → rechts (%)',c.x??40,8,92)}${number('y','Füße oben → unten (%)',c.y??78,40,84)}${number('scale','Größe',c.scale??1,.4,1.6,.1)}${number('speed','Bewegungstempo',c.speed??1.35,.6,2.5,.05)}${number('enter','Auftritt bei Szenenanteil',c.enter??0,0,.9,.05)}${number('end_x','Bewegungsziel (%) · leer = bleiben',c.end_x??'',8,92)}</div><p class="field-hint">Regieschritte folgen den Sprecherworten. Wörter wörtlich aus dem Text übernehmen, in derselben Reihenfolge. Requisiten werden von oben nach unten gezählt.</p><div data-cues>${(c.cues||[]).map(cueRow).join('')}</div><button type="button" class="ghost drawing-add-cue">＋ Regieschritt</button><button type="button" class="ghost drawing-remove">Figur entfernen</button></div>`;
  const propRow = (p,i) => `<div class="drawing-item" data-prop-row><h4>Requisite ${i+1}</h4><div class="drawing-grid">${select('kind','Gegenstand',props,p.kind||'book')}${number('x','Position links → rechts (%)',p.x??65,5,95)}${number('y','Unterkante oben → unten (%)',p.y??76,15,84)}${number('scale','Größe',p.scale??1,.3,2,.1)}${text('enter_on','Erscheint bei Sprecherworten · optional',p.enter_on||'',100)}${text('exit_on','Verschwindet bei Sprecherworten · optional',p.exit_on||'',100)}${number('enter','Sonst: erscheint bei Szenenanteil',p.enter??0,0,.9,.05)}${number('exit','Sonst: verschwindet bei Szenenanteil · optional',p.exit??'',.05,1,.05)}${text('label','Kurze sichtbare Beschriftung',p.label||'')}</div><button type="button" class="ghost drawing-remove">Requisite entfernen</button></div>`;
  function content(board) {
    if (!board) return `<p class="notice warn">Dieser ältere Entwurf enthält noch keinen ausführbaren Zeichenplan. Ergänze die Zeichenregie oder erzeuge das Skript neu.</p><button type="button" class="ghost drawing-start">Zeichenregie ergänzen</button>`;
    return `<p class="field-hint">Positionen beziehen sich auf das Zeichenblatt. Regieschritte starten an geschätzten Wortzeiten der erzeugten Stimme. 0,5 als Szenenanteil bedeutet die Hälfte der Szene.</p><div class="drawing-grid" data-board-settings>${select('setting','Schauplatz',settings,board.setting||'white')}${select('framing','Bildausschnitt',frames,board.framing||'wide')}${select('camera_move','Kamerabewegung',cameras,board.camera_move||'static')}</div><div data-characters>${(board.characters||[]).map(characterRow).join('')}</div><button type="button" class="ghost drawing-add-character">＋ Figur</button><div data-props>${(board.props||[]).map(propRow).join('')}</div><button type="button" class="ghost drawing-add-prop">＋ Requisite</button>`;
  }
  const render = board => `<details class="drawing-editor" ${board?'':'open'}><summary>Zeichenregie · Figuren, Schauplatz und Requisiten</summary><p class="notice warn drawing-notice" role="alert" hidden></p><div class="drawing-content">${content(board)}</div></details>`;
  function fields(root) {
    return Object.fromEntries([...root.querySelectorAll('[data-drawing-field]')].map(el => [el.dataset.drawingField,el.type==='number'?(el.value===''?null:Number(el.value)):el.value]));
  }
  function collect(scene) {
    const root = scene.querySelector('.drawing-editor');
    if (!root?.querySelector('[data-board-settings]')) return null;
    return {...fields(root.querySelector('[data-board-settings]')),
      characters:[...root.querySelectorAll('[data-character-row]')].map(row => ({...fields(row), cues:[...row.querySelectorAll('[data-cue-row]')].map(cue => {
        const values = Object.fromEntries([...cue.querySelectorAll('[data-cue-field]')].map(el => [el.dataset.cueField,el.type==='number'?(el.value===''?null:Number(el.value)):el.value]));
        values.target_prop = values.target_prop===''?null:Number(values.target_prop);
        values.expression = values.expression||null;
        return values;
      })})),
      props:[...root.querySelectorAll('[data-prop-row]')].map(row => {const p=fields(row);p.enter_on=p.enter_on||null;p.exit_on=p.exit_on||null;return p;})};
  }
  function bind() {
    document.querySelectorAll('.drawing-editor').forEach(root => {
      root.onclick = event => {
        const button = event.target.closest('button');
        if (!button) return;
        if (button.classList.contains('drawing-start')) root.querySelector('.drawing-content').innerHTML = content({characters:[],props:[]});
        if (button.classList.contains('drawing-add-character')) {
          const rows = root.querySelectorAll('[data-character-row]');
          if (rows.length < 4) root.querySelector('[data-characters]').insertAdjacentHTML('beforeend',characterRow({id:`figur-${crypto.randomUUID().slice(0,8)}`},rows.length));
        }
        if (button.classList.contains('drawing-add-prop')) {
          const rows = root.querySelectorAll('[data-prop-row]');
          if (rows.length < 8) root.querySelector('[data-props]').insertAdjacentHTML('beforeend',propRow({},rows.length));
        }
        if (button.classList.contains('drawing-add-cue')) {
          const row = button.closest('[data-character-row]');
          if (row.querySelectorAll('[data-cue-row]').length < 8) row.querySelector('[data-cues]').insertAdjacentHTML('beforeend',cueRow({}));
        }
        if (button.classList.contains('drawing-remove-cue')) button.closest('[data-cue-row]').remove();
        if (button.classList.contains('drawing-remove')) {
          const row = button.closest('.drawing-item');
          if (row.hasAttribute('data-prop-row')) {
            const index = [...root.querySelectorAll('[data-prop-row]')].indexOf(row);
            const targets = [...root.querySelectorAll('[data-cue-field="target_prop"]')];
            if (targets.some(target => target.value!=='' && Number(target.value)===index)) {
              const notice = root.querySelector('.drawing-notice');
              notice.textContent='Diese Requisite ist ein Zielgegenstand. Ändere zuerst die betreffenden Regieschritte.';
              notice.hidden=false;
              return;
            }
            targets.forEach(target => {if(target.value!=='' && Number(target.value)>index) target.value=String(Number(target.value)-1)});
          }
          row.remove();
          root.querySelectorAll('[data-prop-row] h4').forEach((heading,index)=>heading.textContent=`Requisite ${index+1}`);
        }
      };
    });
  }
  return {render,collect,bind};
})();
