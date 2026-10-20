// Deterministic checks for the discrimination tasks. Each task targets a fact that only
// one variant states in depth (see docs/skill-creation-comparison/README.md, "Static
// comparison"), so a difference in pass rate between the variants points at that fact.
// Only code blocks are inspected; no judge model.

const { codeBlocks, forbid, isPython } = require('../../lib/blocks.js');
const { noIndexingRunResult } = require('../testing-pipelines-shared/assertions.js');

const pathIs = (re) => (b) => re.test(b.path || '');

// "MemoryDataset copies DataFrames on load and save": a node does not need its own copy.
function noCopyInNodes(output) {
  return forbid(output, /\.copy\(\)/, pathIs(/nodes\.py$/), '.copy() added inside a node');
}

// "Share fixtures via conftest.py": both fixtures defined once, in conftest.py, and not
// repeated in the test modules.
function fixturesInConftest(output) {
  const blocks = codeBlocks(output).filter((b) => !b.antiExample && isPython(b));
  const conftest = blocks.filter((b) => /conftest\.py$/.test(b.path || ''));
  const names = ['model_options', 'model_input_table'];
  const inConftest = names.filter((n) => conftest.some((b) => new RegExp(`def ${n}\\s*\\(`).test(b.code)));
  const repeated = names.filter((n) =>
    blocks.some((b) => !/conftest\.py$/.test(b.path || '') && new RegExp(`def ${n}\\s*\\(`).test(b.code)),
  );
  if (inConftest.length === names.length && repeated.length === 0) {
    return { pass: true, score: 1, reason: 'Both fixtures defined once in conftest.py' };
  }
  return {
    pass: false,
    score: 0,
    reason: `conftest.py defines [${inConftest.join(', ')}]; repeated in test modules [${repeated.join(', ')}]`,
  };
}

// "Never start a KedroSession to test a single node": the node unit test calls the function.
function noSessionInNodeTest(output) {
  return forbid(output, /KedroSession/, pathIs(/test_nodes\.py$/), 'KedroSession in a node unit test');
}

// "One session = one run": two configurations need two sessions.
function twoSessionsForTwoRuns(output) {
  const count = codeBlocks(output)
    .filter((b) => !b.antiExample && isPython(b))
    .reduce((n, b) => n + (b.code.match(/KedroSession\.create\(/g) || []).length, 0);
  if (count >= 2) {
    return { pass: true, score: 1, reason: `${count} KedroSession.create calls` };
  }
  return { pass: false, score: 0, reason: `${count} KedroSession.create call(s); two runs need two sessions` };
}

module.exports = {
  noCopyInNodes,
  fixturesInConftest,
  noSessionInNodeTest,
  twoSessionsForTwoRuns,
  noIndexingRunResult,
};
