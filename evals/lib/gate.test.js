// Run with: node --test evals/lib/*.test.js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { gate } = require('./gate.js');

const result = (label, success, failureReason = success ? 0 : 1) => ({
  prompt: { label },
  provider: { id: 'p' },
  testCase: { description: 't' },
  success,
  failureReason,
});

test('baseline failures do not fail the gate', () => {
  const { failed } = gate([result('with-skill', true), result('baseline', false)]);
  assert.equal(failed.length, 0);
});

test('with-skill failures and errors fail the gate', () => {
  const { failed } = gate([result('with-skill', false), result('with-skill', false, 2)]);
  assert.equal(failed.length, 2);
});

test('baseline errors and passes are reported separately', () => {
  const { baselineErrors, baselinePassed } = gate([
    result('baseline', false, 2),
    result('baseline', true),
  ]);
  assert.equal(baselineErrors.length, 1);
  assert.equal(baselinePassed.length, 1);
});
