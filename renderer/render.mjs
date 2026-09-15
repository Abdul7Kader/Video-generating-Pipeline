import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {createReadStream, statSync} from 'node:fs';
import http from 'node:http';

const [propsFile, outputLocation, concurrencyArg = '2', audioFile] = process.argv.slice(2);
if (!propsFile || !outputLocation) throw new Error('Usage: node render.mjs PROPS_JSON OUTPUT_MP4 [CONCURRENCY] [AUDIO_WAV]');
const inputProps = JSON.parse(await readFile(propsFile, 'utf8'));
let audioServer;
const mediaFiles = new Map();
if (audioFile) mediaFiles.set('/audio.wav', {path: audioFile, contentType: 'audio/wav'});
for (const [index, scene] of inputProps.scenes.entries()) {
  if (!scene.asset_path) continue;
  const route = `/asset-${index}`;
  const contentType = scene.asset_kind === 'video' ? 'video/mp4' : 'image/jpeg';
  mediaFiles.set(route, {path: scene.asset_path, contentType});
  scene.__assetRoute = route;
}
const serveFile = (request, response, file) => {
  const size = statSync(file.path).size;
  const headers = {'Content-Type': file.contentType, 'Access-Control-Allow-Origin':'*', 'Cache-Control':'no-store', 'Accept-Ranges':'bytes'};
  const range = request.headers.range;
  if (range) {
    const match = /^bytes=(\d*)-(\d*)$/.exec(range);
    if (!match) { response.writeHead(416, {...headers, 'Content-Range':`bytes */${size}`}).end(); return; }
    const start = match[1] ? Number(match[1]) : 0;
    const end = match[2] ? Math.min(Number(match[2]), size - 1) : size - 1;
    if (start > end || start >= size) { response.writeHead(416, {...headers, 'Content-Range':`bytes */${size}`}).end(); return; }
    response.writeHead(206, {...headers, 'Content-Range':`bytes ${start}-${end}/${size}`, 'Content-Length':String(end-start+1)});
    if (request.method === 'HEAD') response.end(); else createReadStream(file.path, {start, end}).pipe(response);
    return;
  }
  response.writeHead(200, {...headers, 'Content-Length':String(size)});
  if (request.method === 'HEAD') response.end(); else createReadStream(file.path).pipe(response);
};
if (mediaFiles.size) {
  audioServer = http.createServer((request, response) => {
    const pathname = new URL(request.url ?? '/', 'http://127.0.0.1').pathname;
    const file = mediaFiles.get(pathname);
    if (!file) { response.writeHead(404).end(); return; }
    serveFile(request, response, file);
  });
  await new Promise((resolve) => audioServer.listen(0, '127.0.0.1', resolve));
  const address = audioServer.address();
  if (audioFile) inputProps.audioSrc = `http://127.0.0.1:${address.port}/audio.wav`;
  for (const scene of inputProps.scenes) {
    if (scene.__assetRoute) {
      scene.assetSrc = `http://127.0.0.1:${address.port}${scene.__assetRoute}`;
      delete scene.__assetRoute;
    }
  }
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
