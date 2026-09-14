import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {createReadStream} from 'node:fs';
import http from 'node:http';

const [propsFile, outputLocation, concurrencyArg = '2', audioFile] = process.argv.slice(2);
if (!propsFile || !outputLocation) throw new Error('Usage: node render.mjs PROPS_JSON OUTPUT_MP4 [CONCURRENCY] [AUDIO_WAV]');
const inputProps = JSON.parse(await readFile(propsFile, 'utf8'));
let audioServer;
if (audioFile) {
  audioServer = http.createServer((request, response) => {
    if (request.url !== '/audio.wav') { response.writeHead(404).end(); return; }
    response.writeHead(200, {'Content-Type':'audio/wav', 'Access-Control-Allow-Origin':'*', 'Cache-Control':'no-store'});
    createReadStream(audioFile).pipe(response);
  });
  await new Promise((resolve) => audioServer.listen(0, '0.0.0.0', resolve));
  const address = audioServer.address();
  inputProps.audioSrc = `http://127.0.0.1:${address.port}/audio.wav`;
}
const require = createRequire(import.meta.url);
const serveUrl = await bundle({entryPoint: require.resolve('./src/index.ts'), webpackOverride: (config) => config});
const composition = await selectComposition({serveUrl, id: 'PipelineVideo', inputProps});
try { await renderMedia({
  codec: 'h264',
  composition,
  serveUrl,
  outputLocation,
  inputProps,
  concurrency: Number(concurrencyArg),
  crf: 20,
  imageFormat: 'jpeg',
  chromiumOptions: {enableMultiProcessOnLinux: true},
  logLevel: 'info',
}); } finally { if (audioServer) await new Promise((resolve) => audioServer.close(resolve)); }
console.log(JSON.stringify({ok: true, outputLocation, frames: composition.durationInFrames}));
