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
const {DrawingStage, actorMotion, actorState, directedProp, entryProgress} = compiled.exports;
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

test('speech cues switch action at the spoken phrase and complete movement quickly', () => {
  const character = {x:20,y:80,pose:'stand',motion_cues:[
    {at:.4,pose:'walk',move_to:60,duration:.7},
    {at:2,pose:'gather',target_prop:0,duration:.4},
  ]};
  assert.equal(actorState(character,.2,6).pose,'stand');
  assert.equal(actorState(character,1.5,6).x,60);
  assert.equal(actorState(character,2.1,6).pose,'gather');
  assert.equal(actorMotion({x:20,end_x:80,pose:'walk'},60,30,8).x,80);
  const value = {characters:[character],props:[{kind:'bush',x:65,y:80}]};
  assert.match(draw(value,75),/data-pose="gather"/);
  assert.notEqual(draw(value,75),draw(value,80));
});

test('a carried prop follows its actor and points toward the narrative target', () => {
  const value = {characters:[{id:'reader',x:40,y:80,pose:'stand',motion_cues:[
    {at:0,pose:'pick',target_prop:0,duration:.4},
    {at:1,pose:'read',target_prop:0,duration:.3},
  ]}],props:[{kind:'book',x:60,y:80}]};
  assert.match(draw(value,45),/data-pose="read"/);
  assert.notEqual(draw(value,0),draw(value,45));
  assert.match(draw(value,45),/data-target-prop="0"/);
});

test('picked objects travel with the actor and return to the surface on place', () => {
  const prop = {kind:'book',x:30,y:65};
  const value = {characters:[{x:20,y:80,motion_cues:[
    {at:0,pose:'pick',target_prop:0,duration:.4},
    {at:1,pose:'walk',move_to:60,duration:.7},
    {at:2,pose:'place',target_prop:0,duration:.4},
  ]}],props:[prop]};
  assert.equal(directedProp(prop,0,value,0,6,1000,600).x,30);
  assert.ok(directedProp(prop,0,value,1.8,6,1000,600).x>60);
  assert.equal(actorMotion(value.characters[0],54,30,6).stride,0);
  assert.deepEqual(directedProp(prop,0,value,2.5,6,1000,600),prop);
});

test('a new shot can place an object held in the preceding shot', () => {
  const prop = {kind:'phone',x:55,y:65};
  const value = {characters:[{x:40,y:80,motion_cues:[{at:1,pose:'place',target_prop:0,duration:.4}]}],props:[prop]};
  assert.ok(directedProp(prop,0,value,.5,6,1000,600).x<45);
  assert.deepEqual(directedProp(prop,0,value,1.5,6,1000,600),prop);
});

test('walking eases in and out and overlapping cues preserve the current position', () => {
  const character = {x:20,motion_cues:[{at:1,pose:'walk',move_to:80,duration:1}]};
  assert.ok(actorState(character,1.1,6).x < 23);
  assert.equal(actorState(character,1.5,6).x,50);
  assert.ok(actorState(character,1.9,6).x > 77);
  const interrupted = {...character,motion_cues:[...character.motion_cues,
    {at:1.25,pose:'walk',move_to:10,duration:1}]};
  assert.equal(actorState(interrupted,1.25,6).x,actorState(character,1.25,6).x);
  assert.ok(Math.abs(actorState(interrupted,1.25001,6).x-actorState(character,1.25,6).x)<.001);
  assert.equal(actorMotion(character,30,30,6).stride,0);
  assert.ok(Math.abs(actorMotion(character,59,30,6).stride)<8);
});

test('direction changes turn the actor and its held prop together without a jump', () => {
  const prop = {kind:'book',x:30,y:65};
  const character = {id:'walker',x:20,y:80,facing:'right',motion_cues:[
    {at:0,pose:'carry',target_prop:0,duration:.2},
    {at:1,pose:'walk',move_to:60,duration:.8},
    {at:2,pose:'walk',move_to:20,duration:.8},
  ]};
  const value = {characters:[character],props:[prop]};
  const before = directedProp(prop,0,value,1.99999,6,1000,600);
  const after = directedProp(prop,0,value,2.00001,6,1000,600);
  assert.ok(Math.abs(before.x-after.x)<.001);
  assert.ok(directedProp(prop,0,value,2.5,6,1000,600).x<actorState(character,2.5,6).x);
  assert.match(draw(value,90),/data-facing="left"/);
  assert.equal(actorState(character,3,6).facing,-1);
  assert.equal(actorState({x:80,end_x:20,pose:'walk'},1,6).facing,-1);
  assert.equal(actorState({x:40,facing:'left'},1,6).facing,-1);
});

test('running settles onto the same standing drawing at arrival in both formats', () => {
  const character = {id:'runner',x:80,y:80,pose:'run',end_x:20};
  for (const portrait of [false,true]) {
    assert.equal(draw({characters:[character],props:[]},90,portrait),
      draw({characters:[{id:'runner',x:20,y:80,pose:'stand',facing:'left'}],props:[]},90,portrait));
  }
  assert.equal(actorMotion(character,0,30,6).stride,0);
  assert.ok(actorMotion(character,10,30,6).stride!==0);
});
