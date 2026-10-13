import {strict as assert} from 'node:assert';
import {test} from 'node:test';
import http from 'node:http';
import {enforceLoopbackListeners, loopbackListenArguments} from './loopback.mjs';

test('renderer listeners normalize wildcard and omitted hosts without mutating options', () => {
  const options={port:3000,host:'::',backlog:10};
  assert.deepEqual(loopbackListenArguments([options]),[{...options,host:'127.0.0.1'}]);
  assert.equal(options.host,'::');
  const callback=()=>{};
  assert.deepEqual(loopbackListenArguments([0,callback]),[0,'127.0.0.1',callback]);
  for (const args of [[3000,'192.168.1.2'],[{port:3000,host:'example.org'}],['/tmp/socket'],[{fd:3}]]) {
    assert.throws(()=>loopbackListenArguments(args));
  }
});

test('the actual HTTP listener binds to loopback and closes after use', async () => {
  const restore=enforceLoopbackListeners();
  const server=http.createServer((_,res)=>res.end('ok'));
  try {
    await new Promise((resolve,reject)=>{server.once('error',reject);server.listen({port:0,host:'0.0.0.0'},resolve);});
    assert.equal(server.address().address,'127.0.0.1');
    await new Promise((resolve,reject)=>server.close(error=>error?reject(error):resolve()));
  } finally {
    if (server.listening) server.close();
    restore();
  }
});
