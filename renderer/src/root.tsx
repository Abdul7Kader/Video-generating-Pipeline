import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {Video, VideoProps} from './video';

const defaults: VideoProps = {
  title: 'Video Pipeline',
  durationSeconds: 60,
  aspectRatio: '9:16',
  language: 'de',
  audioSrc: '',
  scenes: [{narration: 'Ein neues Video beginnt.', visual: 'Eine Figur erscheint.', action: 'intro', accent: '#ff6b4a', start: 0, duration: 60}],
};

const calculateMetadata: CalculateMetadataFunction<VideoProps> = ({props}) => {
  const landscape = props.aspectRatio === '16:9';
  const square = props.aspectRatio === '1:1';
  return {
    durationInFrames: Math.max(30, Math.ceil(props.durationSeconds * 30)),
    width: landscape ? 1920 : square ? 1080 : 1080,
    height: landscape ? 1080 : square ? 1080 : 1920,
    props,
  };
};

export const Root: React.FC = () => (
  <Composition id="PipelineVideo" component={Video} durationInFrames={1800} fps={30} width={1080} height={1920} defaultProps={defaults} calculateMetadata={calculateMetadata} />
);
