import {strict as assert} from 'node:assert';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {createRequire, Module} from 'node:module';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';

// Render the real TSX with React server rendering; no browser or hook mocks.
const filename = fileURLToPath(new URL('./src/ink.tsx', import.meta.url));
const code = ts.transpileModule(readFileSync(filename, 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true},
}).outputText;
const compiled = new Module(filename);
compiled.filename = filename;
compiled.paths = Module._nodeModulePaths(filename.replace(/[/\\][^/\\]+$/, ''));
compiled.require = createRequire(import.meta.url);
compiled._compile(code, filename);
const {DrawingStage, actorMotion, entryProgress} = compiled.exports;
const board = {
  setting:'camp', framing:'split', camera_move:'static',
  characters:[{id:'modern',x:25,y:78,pose:'work',outfit:'office',expression:'tired'},
    {id:'hunter',x:75,y:78,pose:'gather',outfit:'prehistoric',expression:'happy'}],
  props:[{kind:'clock',x:20,y:35},{kind:'fire',x:65,y:79}],
};
const draw = (value, frame = 30, portrait = false) => renderToStaticMarkup(React.createElement(DrawingStage, {board:value,frame,fps:30,duration:6,portrait}));

test('real drawing contains directed actors, props and split staging', () => {
  const svg = draw(board);
  assert.match(svg, /data-character="modern"/);
  assert.match(svg, /data-pose="gather"/);
  assert.match(svg, /data-prop="clock"/);
  assert.match(svg, /stroke-dasharray="9 9"/);
  assert.doesNotMatch(svg, /Szene \d|radial-gradient|filter=/);
});
test('different actions and emotions produce different actual drawings', () => {
  assert.notEqual(draw(board), draw({...board,characters:[{...board.characters[0],pose:'sleep',expression:'happy'}]}));
  assert.notEqual(draw(board,30),draw(board,45));
  assert.equal(draw(board,30),draw(board,30));
});
test('walk arrives at destination and late reveals are invisible until their cue', () => {
  const character = {x:20,end_x:80,pose:'walk',enter:.25};
  assert.equal(actorMotion(character,0,30,8).x,20);
  assert.equal(actorMotion(character,240,30,8).x,80);
  assert.equal(entryProgress(0,30,8),1);
  assert.equal(entryProgress(45,30,8,.25),0);
  assert.equal(entryProgress(75,30,8,.25),1);
});
test('portrait stage retains drawing bounds and visible text is escaped', () => {
  const svg = draw({...board,props:[{kind:'book',x:50,y:65,label:'<script>alert(1)</script>'}]},30,true);
  assert.match(svg,/viewBox="0 0 600 900"/);
  assert.match(svg,/&lt;script&gt;/);
  assert.doesNotMatch(svg,/<script>/);
});
test('directed object disappears at its exit cue', () => {
  const value = {characters:[],props:[{kind:'phone',x:50,y:70,exit:.5}]};
  assert.match(draw(value,30),/data-prop="phone"[^>]*opacity="1"/);
  assert.match(draw(value,120),/data-prop="phone"[^>]*opacity="0"/);
});
test('every vocabulary prop draws and unknown assets fail clearly', () => {
  const kinds = ['clock','laptop','desk','chair','bed','phone','book','tree','bush','fire','spear','basket','rock','sun','moon','cloud','house','food','water','gear','lightbulb','arrow','question','check','cross','heart','chart'];
  for (const kind of kinds) assert.match(draw({characters:[],props:[{kind,x:50,y:70}]}),new RegExp(`data-prop="${kind}"`));
  assert.throws(()=>draw({characters:[],props:[{kind:'unknown',x:50,y:70}]}),/Unbekannte/);
});
