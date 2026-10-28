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

test('File: path keeps underscores and drops markdown wrappers', () => {
  const out =
    'File: `src/eval_project/settings.py`\n```python\nx\n```\n**File: conf/base/parameters_data_science.yml**\n```yaml\ny\n```';
  assert.deepEqual(paths(out), [
    'src/eval_project/settings.py',
    'conf/base/parameters_data_science.yml',
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

test('path comment on the first line labels the block', () => {
  const out = '```yaml\n# conf/base/parameters.yml\na: 1\n```\n```python\n// src/p/settings.py\nx = 1\n```';
  assert.deepEqual(paths(out), ['conf/base/parameters.yml', 'src/p/settings.py']);
});

test('path comment wins over a file only mentioned in prose', () => {
  const out =
    'Register it via `CONFIG_LOADER_ARGS` in `settings.py`.\n\n```yaml\n# conf/base/parameters.yml\nb: ${oc.env:X}\n```';
  assert.deepEqual(paths(out), ['conf/base/parameters.yml']);
});

test('ordinary first-line comment is not a label', () => {
  const out = 'File: src/p/nodes.py\n```python\n# Train the model\nx = 1\n```';
  assert.deepEqual(paths(out), ['src/p/nodes.py']);
});

test('label does not carry over to later unlabelled blocks', () => {
  const out = 'File: a.py\n```python\nx\n```\nThen run:\n```bash\nkedro run\n```';
  assert.deepEqual(paths(out), ['a.py', null]);
});

test('forbid ignores patterns mentioned only in prose', () => {
  const out = 'Do not use `TemplatedConfigLoader`.\n```python\nfrom kedro.config import OmegaConfigLoader\n```';
  assert.equal(forbid(out, /TemplatedConfigLoader/, () => true, 'x').pass, true);
});

test('forbid skips a block introduced as a counter-example', () => {
  const out =
    'Use OmegaConfigLoader.\n\nDo **not** use:\n\n```python\nfrom kedro.config import TemplatedConfigLoader\n```';
  assert.equal(forbid(out, /TemplatedConfigLoader/, () => true, 'x').pass, true);
});

test('"do not forget" does not make a block a counter-example', () => {
  const out = "Don't forget to add:\n```python\nfrom kedro.config import TemplatedConfigLoader\n```";
  assert.equal(forbid(out, /TemplatedConfigLoader/, () => true, 'x').pass, false);
});

test('a negative sentence earlier in the prose does not exempt the block', () => {
  const out =
    'Do not use ConfigLoader:\nit was removed. Instead, set this up:\n```python\nfrom kedro.config import TemplatedConfigLoader\n```';
  assert.equal(forbid(out, /TemplatedConfigLoader/, () => true, 'x').pass, false);
});

test('forbid reports the offending path', () => {
  const out = '#### conf/base/parameters.yml\n```yaml\nb: ${oc.env:X}\n```';
  const result = forbid(out, /oc\.env/, (b) => /parameters/.test(b.path || ''), 'oc.env');
  assert.equal(result.pass, false);
  assert.match(result.reason, /conf\/base\/parameters\.yml/);
});
