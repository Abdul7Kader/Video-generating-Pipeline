const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

test('cancel is available during planning and calls only the selected job endpoint', async () => {
  const buttons = [], requests = [];
  const host = {append: button => buttons.push(button)};
  const context = {document: {getElementById: () => null, querySelector: () => host,
    createElement: () => ({})}, fetch: async (url, options) => {
      requests.push({url, method: options.method});
      return {ok: true, json: async () => ({status: 'cancelling'})};
    }};
  vm.runInNewContext(fs.readFileSync('web/production-controls.js', 'utf8'), context);
  context.ProductionControls.mount({id: 'chosen-job', status: 'render_planning'});
  assert.equal(buttons[0].disabled, false);
  await buttons[0].onclick();
  assert.deepEqual(requests, [{url: '/api/jobs/chosen-job/cancel', method: 'POST'}]);
  assert.equal(buttons[0].disabled, true);
  context.ProductionControls.mount({id: 'finished-job', status: 'video_review'});
  assert.equal(buttons.length, 1);
});
