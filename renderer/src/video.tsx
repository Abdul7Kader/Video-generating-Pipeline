import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  Sequence,
  Video as RemotionVideo,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {Board, DrawingStage} from './ink';

type Scene = {
  stickman?: Board | null;
  transition?: string;
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
  if (!scene.stickman) throw new Error('Ausführbarer Zeichenplan fehlt. Bitte Zeichenregie ergänzen.');
  const reveal = Math.min(1, frame / Math.max(1, fps * .3));
  const opacity = scene.transition === 'dissolve' ? reveal : 1;
  const zoom = scene.transition === 'zoom' ? 1.08 - reveal * .08 : 1;
  return <AbsoluteFill style={{background:'#fffefa', opacity, color:'#22211f', fontFamily:'"Noto Sans", Arial, sans-serif', clipPath:scene.transition === 'wipe' ? `inset(0 ${(1-reveal)*100}% 0 0)` : undefined}}>
    <AbsoluteFill style={{transform:`scale(${zoom})`}}>
      <DrawingStage board={scene.stickman} frame={frame} fps={fps} duration={scene.duration} portrait={height > width}/>
    </AbsoluteFill>
    {scene.on_screen_text ? <div style={{position:'absolute', top:'7%', left:'8%', right:'8%', textAlign:'center', fontSize:width>height?48:42, lineHeight:1.15, fontWeight:700}}>{scene.on_screen_text}</div> : null}
    <Captions scene={scene}/>
  </AbsoluteFill>;
};

const SceneView: React.FC<{scene: Scene; index: number; total: number}> = (props) => (
  props.scene.assetSrc ? <AssetScene {...props}/> : <StickmanScene {...props}/>
);

export const Video: React.FC<VideoProps> = ({scenes, audioSrc, durationSeconds}) => (
  <AbsoluteFill style={{background:'#fffefa'}}>
    {audioSrc ? <Audio src={audioSrc}/> : null}
    {scenes.map((scene, index) => (
      <Sequence key={scene.scene_id ?? `${index}-${scene.start}`} from={Math.round(scene.start*30)} durationInFrames={Math.max(1,(index===scenes.length-1?Math.ceil(durationSeconds*30):Math.round((scene.start+scene.duration)*30))-Math.round(scene.start*30))}>
        <SceneView scene={scene} index={index} total={scenes.length}/>
      </Sequence>
    ))}
  </AbsoluteFill>
);
