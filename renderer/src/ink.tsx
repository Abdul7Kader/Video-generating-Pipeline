import React from 'react';

export type Character = {
  id?: string; x: number; y: number; scale?: number; pose?: string;
  expression?: string; outfit?: string; facing?: string; enter?: number; end_x?: number | null;
  speed?: number; motion_cues?: MotionCue[];
};
export type MotionCue = {at: number; pose: string; expression?: string | null; target_prop?: number | null; move_to?: number | null; duration: number};
export type Prop = {kind: string; x: number; y: number; scale?: number; enter?: number; exit?: number | null; label?: string};
export type Board = {
  setting?: string; framing?: string; camera_move?: string;
  characters: Character[]; props: Prop[];
};

const ink = '#22211f';
const blue = '#b6dce8';
const brown = '#b88d60';
const green = '#b2c49a';
const yellow = '#f0cf75';
const red = '#cf5e4f';
const pen = {stroke: ink, strokeWidth: 3.4, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none'};
const clamp = (value: number) => Math.max(0, Math.min(1, value));

export function entryProgress(frame: number, fps: number, duration: number, enter = 0) {
  if (enter === 0) return 1;
  return clamp((frame / fps - enter * duration) / .28);
}

export function actorState(c: Character, time: number, duration: number) {
  const travel = Math.min(1.8, Math.max(.25, Math.abs((c.end_x ?? c.x) - c.x) / (35 * (c.speed ?? 1.35))));
  let from = c.x;
  let goal = c.end_x ?? c.x;
  let at = (c.enter ?? 0) * duration;
  let seconds = travel;
  let pose = c.pose ?? 'stand';
  let expression = c.expression ?? 'neutral';
  let target_prop: number | null = null;
  // A shot starting with placement continues an object already held in the previous shot.
  const first = c.motion_cues?.[0];
  let held_prop: number | null = first?.pose === 'place' ? first.target_prop ?? null : null;
  let held_at = -1;
  let held_duration = .55;
  for (const cue of c.motion_cues ?? []) {
    if (cue.at > time) break;
    from += (goal - from) * clamp((cue.at - at) / seconds);
    goal = cue.move_to ?? from;
    at = cue.at;
    seconds = cue.duration;
    pose = cue.pose;
    expression = cue.expression ?? expression;
    target_prop = cue.target_prop ?? null;
    if (['pick', 'carry', 'read'].includes(pose) && target_prop !== null && held_prop !== target_prop) {
      held_prop = target_prop;
      held_at = at;
      held_duration = seconds;
    }
    if (pose === 'place' && time >= at + seconds) held_prop = null;
  }
  const progress = clamp((time - at) / seconds);
  const x = from + (goal - from) * progress;
  const action_pose = pose;
  if ((pose === 'walk' || pose === 'run') && goal !== from && progress === 1) pose = 'stand';
  return {x, pose, action_pose, expression, target_prop, held_prop, held_at, held_duration, at, progress};
}

// Feet anchor at (0, 0). Actions start at spoken text anchors, with no frame randomness.
export function actorMotion(character: Character, frame: number, fps: number, duration: number) {
  const time = frame / fps;
  const state = actorState(character, time, duration);
  const moving = state.pose === 'walk' || state.pose === 'run';
  const cycle = Math.sin((time - state.at) * (state.pose === 'run' ? 17 : 11) * (character.speed ?? 1.35));
  const bob = moving ? -Math.abs(cycle) * (state.pose === 'run' ? 8 : 4) : Math.sin(time * 3.5) * .7;
  return {...state, bob, stride: moving ? cycle * 23 : 0, gesture: Math.sin((time - state.at) * 10 * (character.speed ?? 1.35)) * 9};
}

const Face: React.FC<{expression: string; frame: number; fps: number}> = ({expression, frame, fps}) => {
  const blink = (frame % Math.round(fps * 4)) > fps * 3.88;
  const tired = expression === 'tired';
  return <g>
    {blink || tired
      ? <path d="M-16 -171 l8 1 M8 -170 l8 -1" strokeWidth="2.5"/>
      : <><ellipse cx="-12" cy="-171" rx="2.3" ry="3.5" fill={ink} stroke="none"/><ellipse cx="12" cy="-171" rx="2.3" ry="3.5" fill={ink} stroke="none"/></>}
    {(expression === 'worried' || expression === 'sad') && <path d="M-20 -182 l10 -4 M10 -186 l10 4" strokeWidth="2"/>}
    {(expression === 'angry' || expression === 'determined') && <path d="M-21 -186 l12 5 M10 -181 l12 -5" strokeWidth="2.4"/>}
    {expression === 'happy' ? <path d="M-12 -151 Q0 -137 13 -152" strokeWidth="2.5"/>
      : expression === 'surprised' ? <ellipse cx="0" cy="-150" rx="5" ry="7" strokeWidth="2.3"/>
      : expression === 'sad' || expression === 'worried' || tired ? <path d="M-10 -148 Q0 -159 10 -148" strokeWidth="2.3"/>
      : <path d="M-9 -149 Q0 -146 10 -150" strokeWidth="2.3"/>}
    <path d="M-2 -164 l-2 5 5 1" strokeWidth="1.5" opacity=".65"/>
  </g>;
};

export const InkActor: React.FC<{character: Character; props?: Prop[]; frame: number; fps: number; duration: number; stageWidth: number; stageHeight: number}> = ({character: c, props = [], frame, fps, duration, stageWidth, stageHeight}) => {
  const motion = actorMotion(c, frame, fps, duration);
  const {pose, expression} = motion;
  const entry = entryProgress(frame, fps, duration, c.enter);
  const scale = (c.scale ?? 1) * stageHeight / 600;
  const seated = pose === 'sit' || pose === 'work' || (['sit','work'].includes(c.pose ?? '') && ['talk','read','point','think','pick','place'].includes(pose));
  const bent = pose === 'gather';
  const headTilt = expression === 'sad' || expression === 'tired' ? -8 : bent ? 12 : pose === 'read' ? 9 : 0;
  const target = motion.target_prop == null ? undefined : props[motion.target_prop];
  const flip = c.facing === 'left' ? -1 : 1;
  const handX = target ? Math.max(-80, Math.min(80, (target.x - motion.x) * stageWidth / 100 / scale * flip)) : 45;
  const handY = target ? Math.max(-195, Math.min(-65, (target.y - c.y) * stageHeight / 100 / scale - 30)) : -95;
  const pointX = 29 + (handX - 29) * motion.progress;
  const pointY = -92 + ((target ? handY : -142 + motion.gesture) + 92) * motion.progress;
  const arms: Record<string, string> = {
    stand: 'M0 -127 Q-14 -105 -25 -89 M0 -127 Q15 -110 29 -92',
    point: `M0 -127 Q${pointX/2} -135 ${pointX} ${pointY} M0 -127 Q-13 -103 -26 -88`,
    think: 'M0 -127 Q21 -101 22 -137 L12 -150 M0 -125 Q-18 -110 -18 -90',
    shrug: `M0 -127 Q-21 -108 -46 ${-132 + motion.gesture} M0 -127 Q20 -108 46 ${-132 - motion.gesture}`,
    sit: 'M0 -127 Q-17 -111 -31 -100 M0 -127 Q16 -102 40 -99',
    sleep: 'M0 -127 Q-12 -112 -27 -101 M0 -126 Q21 -121 31 -144',
    work: `M0 -127 Q20 -100 58 ${-108 + motion.gesture} M0 -127 Q10 -90 40 -91`,
    gather: `M0 -127 Q12 -98 18 ${-66 + motion.gesture} M0 -127 Q32 -99 42 -64`,
    carry: 'M0 -127 Q-18 -114 -38 -127 M0 -127 Q24 -108 43 -127',
    pick: `M0 -127 Q24 -112 ${handX + (32-handX)*motion.progress} ${handY + (-90-handY)*motion.progress} M0 -127 Q-12 -110 -24 -95`,
    place: `M0 -127 Q24 -112 ${32 + (handX-32)*motion.progress} ${-90 + (handY+90)*motion.progress} M0 -127 Q-12 -110 -24 -95`,
    read: `M0 -127 Q-5 -105 8 -102 M0 -127 Q39 -116 48 ${-101 + motion.gesture * .15}`,
    celebrate: `M0 -127 Q-24 -154 -38 ${-180 + motion.gesture} M0 -127 Q22 -151 39 ${-178 - motion.gesture}`,
    talk: `M0 -127 Q-22 -112 -42 ${-127 + motion.gesture} M0 -127 Q20 -113 35 -89`,
    walk: `M0 -127 L${-22 - motion.stride} -98 M0 -127 L${24 + motion.stride} -99`,
    run: `M0 -127 l${-22 - motion.stride} 26 -12 -21 M0 -127 l${24 + motion.stride} 17 10 -25`,
  };
  if (target && pose === 'work') arms.work = `M0 -127 Q${handX/2} -110 ${handX} ${handY + motion.gesture * .4} M0 -127 Q10 -90 ${handX-15} ${handY + 4 - motion.gesture * .4}`;
  if (motion.held_prop != null) {
    if (['walk','run'].includes(motion.action_pose)) arms[pose] = `M0 -127 L${-22 - motion.stride} -98 M0 -127 Q39 -136 48 -126`;
    if (pose === 'carry') arms.carry = 'M0 -127 Q-5 -118 8 -126 M0 -127 Q39 -136 48 -126';
    if (pose === 'point') arms.point = `M0 -127 Q${pointX/2} -135 ${pointX} ${pointY} M0 -127 Q-5 -105 8 -102`;
    if (pose === 'think') arms.think = 'M0 -127 Q21 -101 22 -137 L12 -150 M0 -127 Q-5 -105 8 -102';
  }
  return <g data-character={c.id} data-pose={pose} data-target-prop={motion.target_prop ?? undefined} opacity={entry}
    transform={`translate(${motion.x * stageWidth / 100} ${c.y * stageHeight / 100 + motion.bob}) scale(${scale * (c.facing === 'left' ? -1 : 1)} ${scale})`}>
    <g {...pen} transform={pose === 'sleep' ? 'rotate(-75 0 -20)' : undefined}>
      <path d={seated ? 'M0 -66 L-33 -48 -32 0 M0 -66 L37 -45 42 0' : `M0 -66 Q${-14 - motion.stride / 2} -37 ${-24 - motion.stride} -2 l-9 0 M0 -66 Q${14 + motion.stride / 2} -34 ${23 + motion.stride} -2 l9 0`}/>
      <g transform={bent ? `rotate(${32 + motion.gesture * .8} 0 -66)` : pose === 'work' ? 'rotate(8 0 -66)' : undefined}>
      <path d="M-1 -143 Q4 -107 0 -66"/>
      {c.outfit === 'prehistoric' && <path d="M-18 -139 l15 -5 20 6 8 62 -12 -4 -5 10 -9 -8 -12 9 -11 -13 Z" fill={brown}/>}
      {c.outfit === 'office' && <><path d="M-17 -139 l17 -6 18 6 -1 52 -34 0 Z" fill={blue}/><path d="M-7 -143 l7 14 8 -14 M0 -129 l-5 21 5 9 5 -9 Z" fill={red} strokeWidth="2"/></>}
      {c.outfit === 'scientist' && <><path d="M-20 -140 l20 -5 20 5 5 62 -50 0 Z" fill="#fff"/><path d="M0 -140 v56 M-15 -111 h10 v13 h-10" strokeWidth="2"/></>}
      {c.outfit === 'casual' && <path d="M-17 -139 l17 -6 17 6 8 20 -10 2 -1 29 -29 0 -1 -29 -10 -2 Z" fill={green}/>}
      <path d={arms[pose] ?? arms.stand}/>
      <g transform={`rotate(${headTilt} 0 -166)`}>
        <path d="M-31 -176 C-37 -213 30 -215 33 -181 C41 -147 15 -133 -9 -140 C-26 -144 -35 -157 -31 -176 Z" fill="#fffdf8"/>
        <path d="M-30 -181 Q-35 -207 -4 -210 Q23 -211 32 -189" strokeWidth="1.2" opacity=".35"/>
        {c.outfit === 'prehistoric' && <path d="M-34 -180 l-3 -19 10 3 -4 -13 15 5 1 -14 12 8 12 -9 3 10 15 -2 -5 12 12 6 -9 9 -3 -6 -8 -15 -9 10 -9 -11 -10 13 -9 -2 Z" fill="#624a39" strokeWidth="2.3"/>}
        <Face expression={expression} frame={frame} fps={fps}/>
      </g>
      </g>
    </g>
    {expression === 'worried' && <path d="M42 -187 q-8 14 0 15 q8 -1 0 -15" fill={blue} stroke={ink} strokeWidth="1.8"/>}
    {pose === 'sleep' && <text x="44" y="-118" fill={ink} fontSize="22" fontFamily="cursive">z z</text>}
  </g>;
};

const Clock: React.FC<{time: number}> = ({time}) => <>
  <path d="M-27 -96 Q0 -115 26 -96 M-27 -9 l-9 10 M27 -9 l9 10"/>
  <path d="M-37 -85 Q-59 -101 -62 -76 L-35 -66 M37 -85 Q58 -101 62 -76 L35 -66" fill={red}/>
  <circle cy="-49" r="44" fill={red}/><circle cy="-49" r="35" fill="#fffdf8"/>
  {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map(angle => <path key={angle} d="M0 -79 v4" transform={`rotate(${angle} 0 -49)`} strokeWidth="2"/>)}
  <path d="M0 -49 v-23" transform={`rotate(${time * 12} 0 -49)`}/><path d="M0 -49 l-15 11"/>
  <circle cy="-49" r="3" fill={ink}/>
</>;

const PropArt: React.FC<{kind: string; time: number}> = ({kind, time}) => {
  switch (kind) {
    case 'clock': return <Clock time={time}/>;
    case 'laptop': return <><path d="M-43 -58 l77 0 6 48 -76 0 Z" fill={blue}/><path d="M-36 -10 l-19 12 106 0 -11 -12 Z" fill="#c4c5bc"/><path d="M-28 -46 h49 M-28 -36 h29" strokeWidth="2"/></>;
    case 'desk': return <><path d="M-85 -67 l170 0 0 13 -170 0 Z" fill={brown}/><path d="M-68 -54 v54 M67 -54 v54"/><path d="M-78 -60 h151" opacity=".35" strokeWidth="1.5"/></>;
    case 'chair': return <><path d="M-33 -88 h52 v50 h-52 Z" fill={brown}/><path d="M-33 -38 h66 v12 h-66 Z" fill={brown}/><path d="M-24 -26 v26 M24 -26 v26"/></>;
    case 'bed': return <><path d="M-83 -34 h164 v22 h-164 Z" fill={blue}/><path d="M-83 -71 v71 M81 -42 v42 M-74 -51 q20 -20 39 0 v14 h-39 Z" fill="#fffdf8"/></>;
    case 'phone': return <><rect x="-21" y="-75" width="42" height="74" rx="7" fill="#ddd"/><path d="M-15 -62 h30 v46 h-30 Z" fill={blue}/><circle cy="-9" r="2"/></>;
    case 'book': return <><path d="M0 -10 Q-28 -25 -48 -14 v-64 Q-23 -88 0 -70 Q24 -88 47 -78 v64 Q24 -25 0 -10 Z" fill="#fffdf8"/><path d="M0 -70 v60 M-37 -62 l24 6 M-37 -49 l24 6 M12 -56 l23 -6 M12 -43 l23 -6" strokeWidth="2"/></>;
    case 'tree': return <><path d="M-11 0 l4 -104 18 0 5 104" fill={brown}/><path d="M-7 -113 C-100 -72 -95 -180 -46 -173 C-61 -221 42 -237 43 -185 C109 -195 102 -107 35 -110 C10 -76 -15 -78 -7 -113 Z" fill={green}/><path d="M-33 -176 q-20 14 -16 29 M29 -182 q27 6 31 28" strokeWidth="2" opacity=".45"/></>;
    case 'bush': return <><path d="M-60 -6 C-92 -31 -55 -73 -29 -52 C-31 -95 27 -90 27 -54 C73 -76 86 -9 48 -6 Z" fill={green}/><circle cx="-25" cy="-34" r="5" fill={red}/><circle cx="20" cy="-46" r="5" fill={red}/><circle cx="36" cy="-21" r="5" fill={red}/></>;
    case 'fire': return <><path d="M-43 -3 l83 -12 M-37 -15 l73 13" stroke={brown} strokeWidth="12"/><path d={`M-29 -19 Q-46 -47 -16 -61 Q-19 -81 ${Math.sin(time * 8) * 5} -104 Q11 -72 22 -62 Q41 -49 27 -20 Z`} fill="#e89145"/><path d="M-12 -22 Q-20 -42 1 -65 Q24 -35 12 -22 Z" fill={yellow}/></>;
    case 'spear': return <><path d="M-50 0 L31 -136" stroke={brown} strokeWidth="5"/><path d="M24 -137 l29 -26 -11 35 Z" fill="#b8b4ab"/></>;
    case 'basket': return <><path d="M-44 -51 h88 l-10 49 h-68 Z" fill={brown}/><path d="M-29 -50 Q-34 -97 0 -96 Q34 -96 29 -50 M-36 -33 h72 M-34 -17 h67 M-20 -48 l4 45 M0 -48 v45 M20 -48 l-4 45" strokeWidth="2"/></>;
    case 'rock': return <path d="M-54 -6 l17 -34 35 -17 40 20 15 31 Z" fill="#c1beb3"/>;
    case 'sun': return <><circle cy="-40" r="28" fill={yellow}/>{[0,45,90,135,180,225,270,315].map(a => <path key={a} d="M0 -79 v-13" transform={`rotate(${a} 0 -40)`}/>)}</>;
    case 'moon': return <path d="M23 -81 C-45 -110 -64 -15 7 -8 C-20 -25 -20 -63 23 -81 Z" fill={yellow}/>;
    case 'cloud': return <path d="M-66 -16 C-98 -34 -70 -65 -47 -59 C-54 -110 21 -123 31 -77 C68 -92 98 -28 60 -17 Z" fill="#e8f1ef" strokeWidth="2"/>;
    case 'house': return <><path d="M-57 0 v-75 l57 -49 57 49 v75 Z" fill="#e7d5b5"/><path d="M-70 -70 L0 -135 70 -70" strokeWidth="7"/><path d="M-12 0 v-51 h25 v51 M-43 -66 h22 v25 h-22 M23 -66 h22 v25 h-22" fill={blue}/></>;
    case 'food': return <><ellipse cy="-8" rx="52" ry="13" fill="#fff"/><path d="M-38 -14 Q-44 -69 -8 -53 Q3 -92 37 -59 Q63 -20 25 -13 Z" fill={green}/><path d="M-9 -45 q25 -36 35 0" fill={red}/></>;
    case 'water': return <><path d="M0 -92 C-16 -57 -48 -29 -26 -9 C19 17 59 -22 0 -92 Z" fill={blue}/><path d="M-17 -33 q-10 17 7 22" stroke="#fff" strokeWidth="4"/></>;
    case 'gear': return <g transform={`rotate(${time * 18} 0 -42)`}><path d="M-12 -86 l24 0 5 12 14 -1 15 16 -7 13 7 13 -15 16 -14 -1 -5 12 -24 0 -5 -12 -14 1 -15 -16 7 -13 -7 -13 15 -16 14 1 Z" fill={blue}/><circle cy="-42" r="16" fill="#fff"/></g>;
    case 'lightbulb': return <><path d="M-16 -22 C-15 -44 -35 -44 -35 -67 C-36 -105 36 -105 35 -67 C35 -44 15 -44 16 -22 Z" fill={yellow}/><path d="M-16 -22 h32 M-14 -14 h28 M-9 -6 h18 M-4 -24 l-10 -33 13 4 12 -4 -8 33" strokeWidth="2.5"/></>;
    case 'arrow': return <path d="M-60 -33 Q-5 -48 41 -32 M24 -55 l24 24 -28 16" strokeWidth="5"/>;
    case 'question': return <><path d="M-19 -62 C-22 -103 40 -102 25 -66 Q5 -52 3 -35" strokeWidth="6"/><circle cx="3" cy="-15" r="4" fill={ink}/></>;
    case 'check': return <path d="M-29 -36 l22 24 45 -59" stroke="#628568" strokeWidth="8"/>;
    case 'cross': return <path d="M-27 -65 l54 54 M27 -65 l-54 54" stroke={red} strokeWidth="7"/>;
    case 'heart': return <path d="M0 -8 C-85 -58 -25 -112 0 -73 C25 -112 85 -58 0 -8 Z" fill={red}/>;
    case 'chart': return <><path d="M-53 -110 v110 h111"/><path d="M-38 -7 v-36 h20 v36 M-3 -7 v-68 h20 v68 M32 -7 v-95 h20 v95" fill={blue}/></>;
    default: throw new Error(`Unbekannte Zeichenrequisite: ${kind}`);
  }
};

export const InkProp: React.FC<{prop: Prop; frame: number; fps: number; duration: number; stageWidth: number; stageHeight: number}> = ({prop: p, frame, fps, duration, stageWidth, stageHeight}) => {
  const entry = entryProgress(frame, fps, duration, p.enter) *
    (p.exit == null ? 1 : clamp((p.exit * duration - frame / fps) / .28));
  return <g data-prop={p.kind} {...pen} opacity={entry} transform={`translate(${p.x * stageWidth / 100} ${p.y * stageHeight / 100 + (1-entry) * 12}) scale(${(p.scale ?? 1) * stageHeight / 600})`}>
    <PropArt kind={p.kind} time={frame / fps}/>
    {p.label && <text x="0" y="29" textAnchor="middle" stroke="none" fill={ink} fontSize="19" fontFamily="'Comic Sans MS', cursive">{p.label}</text>}
  </g>;
};

const Setting: React.FC<{kind: string; w: number; h: number}> = ({kind, w, h}) => {
  const ground = h * .81;
  return <g {...pen} strokeWidth="2.2">
    {kind !== 'white' && <path d={`M0 ${ground} Q${w*.3} ${ground-3} ${w*.5} ${ground+2} T${w} ${ground}`}/>}
    {(kind === 'nature' || kind === 'camp') && <>
      <path d={`M0 ${ground} Q${w*.2} ${ground-37} ${w*.4} ${ground} T${w} ${ground} L${w} ${h} H0 Z`} fill="#e2dec6" stroke="none"/>
      <path d={`M0 ${h*.38} Q${w*.2} ${h*.32} ${w*.4} ${h*.38} T${w} ${h*.36}`} stroke="#c6cdbb"/>
      {[.06,.12,.72,.79,.92].map(x => <path key={x} d={`M${w*x} ${ground+8} l-6 -20 8 13 5 -26 2 27 8 -15`} stroke="#8a9f78"/>) }
      {kind === 'camp' && <path d={`M${w*.76} ${ground} l${w*.09} ${-h*.22} ${w*.11} ${h*.22} Z M${w*.85} ${ground-h*.22} l${w*.03} ${h*.22}`} fill="#d5b994"/>}
    </>}
    {(kind === 'room' || kind === 'office' || kind === 'classroom') && <>
      <path d={`M${w*.08} ${ground} V${h*.14} H${w*.92} V${ground}`} stroke="#c4c0b7"/>
      <path d={`M${w*.71} ${h*.19} h${w*.14} v${h*.24} h${-w*.14} Z M${w*.78} ${h*.19} v${h*.24} M${w*.71} ${h*.31} h${w*.14}`} fill="#e2eff0" stroke="#b4c1bf"/>
      {kind === 'classroom' && <path d={`M${w*.14} ${h*.18} h${w*.41} v${h*.23} h${-w*.41} Z`} fill="#c4d4bf" stroke="#8a9582"/>}
    </>}
    {kind === 'city' && <path d={`M0 ${ground} V${h*.39} h${w*.11} v${-h*.18} h${w*.1} v${h*.28} h${w*.14} v${-h*.33} h${w*.13} v${h*.25} h${w*.18} v${-h*.12} h${w*.13} v${h*.13} h${w*.21} V${ground}`} stroke="#bbc5c5" fill="#f0f1ea"/>}
  </g>;
};

export function directedProp(prop: Prop, index: number, board: Board, time: number, duration: number, w: number, h: number): Prop {
  for (const c of board.characters) {
    const state = actorState(c, time, duration);
    if (state.held_prop !== index) continue;
    const scale = (c.scale ?? 1) * h / 600;
    const raised = state.pose === 'celebrate';
    const handX = state.x + (raised ? 39 : 32) * scale * (c.facing === 'left' ? -1 : 1) / w * 100;
    const handY = c.y - (raised ? 168 : ['carry','walk','run'].includes(state.action_pose) ? 116 : 90) * scale / h * 100;
    const holding = state.pose === 'place' ? 1 - state.progress : clamp((time - state.held_at) / state.held_duration);
    return {...prop, x: prop.x + (handX - prop.x) * holding, y: prop.y + (handY - prop.y) * holding};
  }
  return prop;
}

export const DrawingStage: React.FC<{board: Board; frame: number; fps: number; duration: number; portrait?: boolean}> = ({board, frame, fps, duration, portrait = false}) => {
  const w = portrait ? 600 : 1000;
  const h = portrait ? 900 : 600;
  const time = clamp(frame / fps / duration);
  const baseZoom = board.framing === 'closeup' ? 1.35 : board.framing === 'medium' ? 1.12 : 1;
  const zoom = baseZoom + (board.camera_move === 'push_in' ? time * .1 : 0);
  const pan = board.camera_move === 'pan_left' ? time * 24 : board.camera_move === 'pan_right' ? -time * 24 : 0;
  // Framing is centered on the chosen subjects so prop closeups stay in view.
  const subjects = [...board.characters, ...board.props];
  const focusX = (board.framing === 'closeup' || board.framing === 'medium') && subjects.length
    ? subjects.reduce((sum, subject) => sum + subject.x, 0) / subjects.length / 100 * w : w/2;
  const focusY = h * .51;
  const props = board.props.map((prop, i) => directedProp(prop, i, board, frame / fps, duration, w, h));
  return <svg width="100%" height="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="xMidYMid meet" style={{background:'#fffefa'}} aria-label="Gezeichnete Strichmenschen-Szene">
    <g transform={`translate(${w/2 + pan} ${h/2}) scale(${zoom}) translate(${-focusX} ${-focusY})`}>
      <Setting kind={board.setting ?? 'white'} w={w} h={h}/>
      {board.framing === 'split' && <path d={`M${w/2} ${h*.08} Q${w/2-3} ${h*.4} ${w/2} ${h*.83}`} stroke={ink} strokeWidth="2" strokeDasharray="9 9" fill="none"/>}
      {props.map((prop, i) => <InkProp key={i} prop={prop} frame={frame} fps={fps} duration={duration} stageWidth={w} stageHeight={h}/>)}
      {board.characters.map((character, i) => <InkActor key={character.id ?? i} character={character} props={props} frame={frame} fps={fps} duration={duration} stageWidth={w} stageHeight={h}/>)}
    </g>
  </svg>;
};
