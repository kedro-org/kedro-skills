// Run with: node --test evals/lib/*.test.js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { codeBlocks, forbid } = require('./blocks.js');

const paths = (output) => codeBlocks(output).map((b) => b.path);

test('File: line labels the next block', () => {
  assert.deepEqual(paths('File: `conf/base/parameters.yml`\n```yaml\na: 1\n```'), [
    'conf/base/parameters.yml',
  ]);
});

test('File: line wins over other paths mentioned in prose', () => {
  const out = 'File: conf/local/credentials.yml (not conf/base/credentials.yml)\n```yaml\nx\n```';
  assert.deepEqual(paths(out), ['conf/local/credentials.yml']);
});

test('heading label is used when there is no File: line', () => {
  const out = '#### conf/base/parameters.yml\nAdd it.\n```yaml\na: 1\n```\n**src/p/nodes.py**\n```python\nx\n```';
  assert.deepEqual(paths(out), ['conf/base/parameters.yml', 'src/p/nodes.py']);
});

test('label in its own fence applies to the following block', () => {
  const out = '```yaml\nFile: conf/base/credentials.yml\n```\n```yaml\ndb:\n  password: hunter2\n```';
  assert.deepEqual(paths(out), ['conf/base/credentials.yml']);
});

test('label does not carry over to later unlabelled blocks', () => {
  const out = 'File: a.py\n```python\nx\n```\nThen run:\n```bash\nkedro run\n```';
  assert.deepEqual(paths(out), ['a.py', null]);
});

test('forbid ignores patterns mentioned only in prose', () => {
  const out = 'Do not use `TemplatedConfigLoader`.\n```python\nfrom kedro.config import OmegaConfigLoader\n```';
  assert.equal(forbid(out, /TemplatedConfigLoader/, () => true, 'x').pass, true);
});

test('forbid reports the offending path', () => {
  const out = '#### conf/base/parameters.yml\n```yaml\nb: ${oc.env:X}\n```';
  const result = forbid(out, /oc\.env/, (b) => /parameters/.test(b.path || ''), 'oc.env');
  assert.equal(result.pass, false);
  assert.match(result.reason, /conf\/base\/parameters\.yml/);
});
