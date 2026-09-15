import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  interpolate,
  Sequence,
  Video as RemotionVideo,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

type Scene = {
  scene_id?: string;
  narration: string;
  visual: string;
  visual_type?: string;
  assetSrc?: string;
  asset_kind?: 'image' | 'video';
  on_screen_text?: string;
  action: string;
  accent: string;
  start: number;
  duration: number;
  captions?: {text: string; start: number; duration: number}[];
};

export type VideoProps = {
  title: string;
  scenes: Scene[];
  durationSeconds: number;
  aspectRatio: string;
  language: string;
  audioSrc?: string;
  scriptHash?: string;
};

const StickFigure: React.FC<{action: string; accent: string}> = ({action, accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 16, stiffness: 120}});
  const walk = action === 'walk' ? Math.sin(frame / 4) * 18 : 0;
  const point = action === 'point' ? interpolate(frame % 45, [0, 18, 45], [25, -30, 25], {easing: Easing.inOut(Easing.quad)}) : 16;
  const bounce = action === 'celebrate' ? Math.abs(Math.sin(frame / 5)) * -34 : 0;
  const think = action === 'think' ? Math.sin(frame / 14) * 7 : 0;
  return <svg width="100%" height="100%" viewBox="0 0 520 650" style={{transform: `translateY(${(1-enter)*180 + bounce}px) scale(${0.75 + enter*0.25})`}}>
    <defs><filter id="shadow"><feDropShadow dx="0" dy="12" stdDeviation="10" floodOpacity=".18"/></filter></defs>
    <g filter="url(#shadow)" transform={`translate(${walk + think} 0)`} stroke="#152238" strokeWidth="22" strokeLinecap="round" fill="none">
      <circle cx="260" cy="150" r="78" fill="#fffaf2"/>
      <path d="M260 230 L260 420"/>
      <path d="M260 285 L150 360" transform={`rotate(${action === 'celebrate' ? -45 : 0} 260 285)`}/>
      <path d="M260 285 L370 360" transform={`rotate(${point} 260 285)`}/>
      <path d="M260 420 L170 570" transform={`rotate(${action === 'walk' ? walk/2 : 0} 260 420)`}/>
      <path d="M260 420 L350 570" transform={`rotate(${action === 'walk' ? -walk/2 : 0} 260 420)`}/>
      <circle cx="230" cy="135" r="7" fill="#152238" stroke="none"/><circle cx="290" cy="135" r="7" fill="#152238" stroke="none"/>
      <path d={action === 'think' ? 'M225 180 Q260 162 295 180' : 'M225 172 Q260 205 295 172'} strokeWidth="10"/>
    </g>
    <circle cx="412" cy="345" r="34" fill={accent} opacity={.95}/>
  </svg>;
};

const Progress: React.FC<{accent: string; index: number; total: number; progress: number}> = ({accent, index, total, progress}) => (
  <div style={{position:'absolute', zIndex:4, top:50, left:70, right:70, height:7, borderRadius:8, background:'#ffffff3d', overflow:'hidden'}}>
    <div style={{width:`${((index+progress)/total)*100}%`, height:'100%', borderRadius:8, background:accent}}/>
  </div>
);

const Captions: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const time = frame / fps;
  const caption = (scene.captions ?? []).find(item => time >= item.start && time < item.start + item.duration);
  if (!caption) return null;
  return <div style={{position:'absolute', zIndex:5, left:'8%', right:'8%', bottom:55, display:'flex', justifyContent:'center', textAlign:'center'}}>
    <span style={{background:'rgba(0,0,0,.78)', color:'white', borderRadius:14, padding:'12px 20px', fontSize:width > 1200 ? 38 : 42, lineHeight:1.22, fontWeight:750, boxDecorationBreak:'clone', textShadow:'0 2px 4px #000'}}>{caption.text}</span>
  </div>;
};

const AssetScene: React.FC<{scene: Scene; index: number; total: number}> = ({scene, index, total}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const frames = Math.max(1, scene.duration * fps);
  const fade = interpolate(frame, [0, 10, Math.max(11, frames-12), frames], [0, 1, 1, 0], {extrapolateLeft:'clamp', extrapolateRight:'clamp'});
  const zoom = interpolate(frame, [0, frames], [1.03, 1.1], {extrapolateRight:'clamp'});
  const progress = Math.min(1, frame / frames);
  if (!scene.assetSrc) throw new Error(`Asset URL fehlt für ${scene.scene_id ?? 'Szene'}`);
  return <AbsoluteFill style={{background:'#080b12', opacity:fade, fontFamily:'"Noto Sans", Arial, sans-serif'}}>
    <AbsoluteFill style={{transform:`scale(${zoom})`}}>
      {scene.asset_kind === 'video'
        ? <RemotionVideo src={scene.assetSrc} muted loop style={{width:'100%', height:'100%', objectFit:'cover'}}/>
        : <Img src={scene.assetSrc} style={{width:'100%', height:'100%', objectFit:'cover'}}/>}
    </AbsoluteFill>
    <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(3,6,12,.12) 20%,rgba(3,6,12,.28) 55%,rgba(3,6,12,.9) 100%)'}}/>
    <Progress accent={scene.accent} index={index} total={total} progress={progress}/>
    {scene.on_screen_text ? <div style={{position:'absolute', zIndex:3, left:72, right:72, bottom:220, color:'white', fontSize:64, lineHeight:1.08, fontWeight:900, letterSpacing:-1.5, textShadow:'0 4px 24px #000'}}>{scene.on_screen_text}</div> : null}
    <Captions scene={scene}/>
  </AbsoluteFill>;
};

const StickmanScene: React.FC<{scene: Scene; index: number; total: number}> = ({scene, index, total}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const frames = Math.max(1, scene.duration * fps);
  const fade = interpolate(frame, [0, 10, Math.max(11, frames-12), frames], [0, 1, 1, 0], {extrapolateLeft:'clamp', extrapolateRight:'clamp'});
  const progress = Math.min(1, frame / frames);
  const compact = width > height;
  return <AbsoluteFill style={{opacity:fade, color:'#152238', fontFamily:'"Noto Sans", Arial, sans-serif', padding:compact?74:78}}>
    <div style={{position:'absolute', inset:0, background:`radial-gradient(circle at ${25+index*9}% 18%, ${scene.accent}33, transparent 35%), linear-gradient(145deg,#fffaf2 0%,#f2f7ff 100%)`}}/>
    <Progress accent={scene.accent} index={index} total={total} progress={progress}/>
    <div style={{zIndex:1, height:'100%', display:'flex', flexDirection:compact?'row':'column', alignItems:'center', justifyContent:'center', gap:compact?60:35}}>
      <div style={{width:compact?'42%':'88%', height:compact?'78%':'49%', maxHeight:720}}><StickFigure action={scene.action} accent={scene.accent}/></div>
      <div style={{width:compact?'50%':'100%', display:'flex', flexDirection:'column', gap:26}}>
        <div style={{fontSize:compact?24:28, fontWeight:800, letterSpacing:4, textTransform:'uppercase', color:scene.accent}}>Szene {index+1} / {total}</div>
        {scene.on_screen_text ? <div style={{fontSize:compact?55:64, lineHeight:1.12, fontWeight:900, letterSpacing:-2}}>{scene.on_screen_text}</div> : null}
      </div>
    </div>
    <Captions scene={scene}/>
  </AbsoluteFill>;
};

const SceneView: React.FC<{scene: Scene; index: number; total: number}> = (props) => (
  props.scene.assetSrc ? <AssetScene {...props}/> : <StickmanScene {...props}/>
);

export const Video: React.FC<VideoProps> = ({scenes, audioSrc}) => (
  <AbsoluteFill style={{background:'#080b12'}}>
    {audioSrc ? <Audio src={audioSrc}/> : null}
    {scenes.map((scene, index) => (
      <Sequence key={scene.scene_id ?? `${index}-${scene.start}`} from={Math.round(scene.start*30)} durationInFrames={Math.max(1,Math.round(scene.duration*30))}>
        <SceneView scene={scene} index={index} total={scenes.length}/>
      </Sequence>
    ))}
  </AbsoluteFill>
);
