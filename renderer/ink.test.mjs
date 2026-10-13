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
const {DrawingStage, actorMotion, actorState, directedProp, entryProgress, interactionCharacters, continuousScenes} = compiled.exports;
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
  const kinds = ['clock','laptop','desk','chair','bed','phone','book','tree','bush','fire','spear','basket','rock','sun','moon','cloud','house','food','water','gear','lightbulb','arrow','question','check','cross','heart','chart','carrier','pet_bed','bowl','litter_box','cat_tree','document'];
  for (const kind of kinds) assert.match(draw({characters:[],props:[{kind,x:50,y:70}]}),new RegExp(`data-prop="${kind}"`));
  assert.throws(()=>draw({characters:[],props:[{kind:'unknown',x:50,y:70}]}),/Unbekannte/);
});

test('animals are recognizable separate actors with animated movement and interaction targets', () => {
  const cat = {id:'luna',species:'cat',x:65,y:81,pose:'walk',end_x:45};
  const value = {characters:[{id:'mila',x:40,y:81,motion_cues:[{at:0,pose:'pet',target_character:'luna',duration:.6}]},cat],props:[{kind:'bowl',x:70,y:81}]};
  const svg = draw(value,10);
  assert.match(svg,/data-species="cat"/);
  assert.match(svg,/data-character="mila" data-pose="pet"/);
  assert.notEqual(svg,draw(value,20));
  assert.notEqual(svg,draw({...value,characters:[{...cat,species:'dog'}]},10));
  assert.notEqual(draw({...value,characters:[{...cat,pose:'sit'}]}),draw({...value,characters:[{...cat,pose:'sleep'}]}));
});

test('petting approaches the actual animal head and keeps its position after contact in both formats', () => {
  const value={characters:[{id:'human',x:20,y:82,motion_cues:[{at:1,pose:'pet',target_character:'cat',duration:.6},{at:2,pose:'stand',duration:.3}]},{id:'cat',species:'cat',x:56,y:82,pose:'sit',facing:'left'}],props:[]};
  for (const [w,h] of [[1000,600],[600,900]]) {
    const directed=interactionCharacters(value,6,w,h);
    const before=actorState(directed[0],1,6).x, after=actorState(directed[0],1.6,6).x;
    const head=56-33*h/600/w*100;
    assert.equal(before,20);
    assert.ok(Math.abs(head-after)*w/100/(h/600)<=100);
    assert.equal(actorState(directed[0],3,6).x,after);
    assert.equal(value.characters[0].motion_cues[0].move_to,undefined);
  }
  const leaving={characters:[{id:'cat',species:'cat',x:50,y:81,exit:.5}],props:[]};
  assert.match(draw(leaving,120),/data-species="cat"[^>]*opacity="0"/);
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
  assert.equal(actorState(value.characters[0],2.5,6).pose,'stand');
});

test('a new shot can place an object held in the preceding shot', () => {
  const prop = {kind:'phone',x:55,y:65};
  const value = {characters:[{x:40,y:80,motion_cues:[{at:1,pose:'place',target_prop:0,duration:.4}]}],props:[prop]};
  assert.ok(directedProp(prop,0,value,.5,6,1000,600).x<45);
  assert.deepEqual(directedProp(prop,0,value,1.5,6,1000,600),prop);
});

test('the rendered hand touches the prop grip throughout pickup, carry and placement', () => {
  for (const [w,h,portrait] of [[1000,600,false],[600,900,true]]) {
    for (const facing of ['left','right']) {
      const value = {characters:[{id:'holder',x:40,y:81,scale:1.2,facing,motion_cues:[
        {at:0,pose:'pick',target_prop:0,duration:.5},
        {at:1,pose:'carry',target_prop:0,duration:.4},
        {at:2,pose:'place',target_prop:0,duration:.5},
      ]}],props:[{kind:'book',x:44,y:70,scale:.7}]};
      for (const time of [.1,.3,.6,1.2,2.1,2.3]) {
        const prop = directedProp(value.props[0],0,value,time,6,w,h);
        const svg = draw(value,time*30,portrait);
        const hand = /data-hand-x="([^"]+)" data-hand-y="([^"]+)"/.exec(svg);
        assert.ok(hand,'actual drawing must expose the shared hand contact');
        assert.ok(Math.abs(Number(hand[1])-prop.x*w/100)<.001);
        assert.ok(Math.abs(Number(hand[2])-(prop.y*h/100-30*.7*h/600))<.001);
      }
    }
  }
});

test('changing posture while holding an object does not teleport it', () => {
  const value={characters:[{id:'reader',x:40,y:80,motion_cues:[
    {at:0,pose:'pick',target_prop:0,duration:.3},
    {at:1,pose:'carry',target_prop:0,duration:.3},
    {at:2,pose:'read',target_prop:0,duration:.3},
  ]}],props:[{kind:'book',x:42,y:65}]};
  for (const time of [1,2]) {
    const before=directedProp(value.props[0],0,value,time-.00001,6,1000,600);
    const after=directedProp(value.props[0],0,value,time+.00001,6,1000,600);
    assert.ok(Math.abs(after.y-before.y)<.01,'held object must not jump vertically');
  }
});

test('placement keeps its new destination and the next owner picks up there', () => {
  const prop={kind:'phone',x:25,y:67};
  const value={characters:[
    {id:'a',x:20,y:80,motion_cues:[{at:0,pose:'pick',target_prop:0,duration:.3},
      {at:1,pose:'place',target_prop:0,place_x:65,place_y:63,duration:.4},
      {at:1.5,pose:'stand',duration:.3}]},
    {id:'b',x:70,y:80,motion_cues:[{at:3,pose:'pick',target_prop:0,duration:.4}]},
  ],props:[prop]};
  for (const [w,h] of [[1000,600],[600,900]]) {
    const placed=directedProp(prop,0,value,2,6,w,h);
    assert.equal(placed.x,65); assert.equal(placed.y,63);
    assert.deepEqual(directedProp(prop,0,value,3,6,w,h),placed);
    assert.equal(directedProp(prop,0,value,3.5,6,w,h).x,70+32*h/600/w*100);
    assert.deepEqual(value.props[0],prop);
  }
});

test('placing on a desk aligns the drawn book bottom with the tabletop', () => {
  const prop={kind:'book',x:30,y:65,scale:.7}, desk={kind:'desk',x:66,y:81,scale:1};
  const value={characters:[{id:'lead',x:60,y:81,motion_cues:[{at:1,pose:'place',target_prop:0,place_surface:1,duration:.4}]}],props:[prop,desk]};
  for (const [w,h] of [[1000,600],[600,900]]) {
    const placed=directedProp(prop,0,value,2,6,w,h);
    assert.equal(placed.x,desk.x);
    assert.ok(Math.abs((placed.y*h/100-10*.7*h/600)-(desk.y*h/100-67*h/600))<.001);
  }
});

test('spoken gestures settle and walking without a destination does not march forever', () => {
  const c={x:40,y:80,motion_cues:[{at:1,pose:'talk',duration:.4,active_until:1.7}]};
  assert.equal(actorState(c,.9,6).pose,'stand');
  assert.notEqual(actorMotion(c,36,30,6).gesture,0);
  assert.equal(actorMotion(c,60,30,6).gesture,0);
  assert.equal(actorState({x:40,y:80,pose:'walk'},3,6).pose,'stand');
});

test('a carried object and actor keep their actual contact position across cuts in both formats', () => {
  for (const [w,h] of [[1000,600],[600,900]]) {
    const input=[{start:0,duration:2,stickman:{setting:'room',characters:[{id:'mila',x:20,y:81,motion_cues:[{at:.2,pose:'pick',target_prop:0,duration:.5}]}],props:[{id:'b',kind:'book',x:70,y:65}]}},
      {start:2,duration:2,stickman:{setting:'room',characters:[{id:'mila',x:15,y:81,initial_prop:1}],props:[{kind:'desk',x:70,y:81},{id:'b',kind:'book',x:50,y:65}]}}];
    const before=JSON.stringify(input), [first,next]=continuousScenes(input,w,h);
    assert.equal(actorState(first.stickman.characters[0],2,2).x,next.stickman.characters[0].x);
    const a=directedProp(first.stickman.props[0],0,first.stickman,2,2,w,h);
    const b=directedProp(next.stickman.props[1],1,next.stickman,0,2,w,h);
    assert.ok(Math.abs(a.x-b.x)<.001); assert.ok(Math.abs(a.y-b.y)<.001);
    assert.equal(actorState(next.stickman.characters[0],0,2).held_prop,1);
    assert.equal(JSON.stringify(input),before);
  }
});

test('a held object leaves the frame together with its owner', () => {
  const board={characters:[{id:'mila',x:40,y:81,initial_prop:0,exit:.5}],props:[{kind:'phone',x:50,y:65}]};
  assert.equal(directedProp(board.props[0],0,board,1,6,1000,600).exit,.5);
  assert.match(draw(board,120),/data-prop="phone"[^>]*opacity="0"/);
});

test('distant pickup approaches the object and preserves the achieved position', () => {
  const value={characters:[{id:'lead',x:15,y:81,motion_cues:[
    {at:1,pose:'pick',target_prop:0,duration:.7},{at:2,pose:'carry',target_prop:0,duration:.3},
  ]}],props:[{kind:'book',x:80,y:65}]};
  for (const [w,h] of [[1000,600],[600,900]]) {
    const [actor]=interactionCharacters(value,6,w,h);
    const end=actorState(actor,1.7,6).x;
    assert.ok((80-end)*w/100/(h/600)<=100);
    assert.equal(actorState(actor,3,6).x,end);
    assert.equal(actorState(actor,.5,6).x,15);
    assert.equal(value.characters[0].motion_cues[0].move_to,undefined);
  }
});

test('the petting hand rests on the actual animated animal head', () => {
  for (const [w,h,portrait] of [[1000,600,false],[600,900,true]]) {
    const cat={id:'cat',species:'cat',x:55,y:81,pose:'sit',scale:.8,facing:'left'};
    const value={characters:[{id:'human',x:45,y:81,scale:1.1,motion_cues:[{at:0,pose:'pet',target_character:'cat',duration:.5}]},cat],props:[]};
    for (const time of [.6,1,1.4]) {
      const hand=/data-pet-hand-x="([^"]+)" data-pet-hand-y="([^"]+)"/.exec(draw(value,time*30,portrait));
      const motion=actorMotion(cat,time*30,30,6), scale=.8*h/600;
      assert.ok(hand);
      assert.ok(Math.abs(Number(hand[1])-(55*w/100-33*scale))<3*h/600);
      assert.ok(Math.abs(Number(hand[2])-(81*h/100+motion.bob*.4-105*scale))<.001);
    }
  }
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
