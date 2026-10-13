// Deterministic checks for the testing-pipelines skill. Both variants
// (testing-pipelines-raw and testing-pipelines-skill-creator) are graded with
// the same checks; each one maps to a fact in
// docs/skill-creation-comparison/facts.md and only inspects code blocks.

const { codeBlocks, forbid, requireCode, isPython } = require('../../lib/blocks.js');

const proposedPython = (output) => codeBlocks(output).filter((b) => !b.antiExample && isPython(b));

// "The runner returns datasets, not data": result["metrics"]["r2_score"]
// indexes a MemoryDataset and raises TypeError.
function noIndexingRunResult(output) {
  return forbid(
    output,
    /\[\s*["']metrics["']\s*\]\s*\[/,
    isPython,
    'run result indexed without .load()',
  );
}

function loadsRunOutput(output) {
  return requireCode(output, /\.load\(/, isPython, '.load() on a run output or catalog entry');
}

// "params: inputs are registered under their literal name": a bare
// "model_options" key leaves "params:model_options" missing.
function noBareParamsCatalogKey(output) {
  return forbid(
    output,
    /["']model_options["']\s*:\s*MemoryDataset|\[\s*["']model_options["']\s*\]\s*=/,
    isPython,
    'model_options registered without the params: prefix',
  );
}

function registersParamsKey(output) {
  return requireCode(output, /["']params:model_options["']/, isPython, '"params:model_options" catalog key');
}

// "Intermediates are released after the run": X_train must be made a
// pipeline output (slice) or captured by a hook, not loaded afterwards.
function makesIntermediateObservable(output) {
  return requireCode(
    output,
    /\.(to_outputs|only_nodes|to_nodes)\(|after_node_run/,
    isPython,
    'a slice or hook that exposes X_train',
  );
}

// "bootstrap_project before KedroSession.create".
function bootstrapsBeforeSession(output) {
  for (const b of proposedPython(output)) {
    const create = b.code.indexOf('KedroSession.create');
    if (create === -1) continue;
    const boot = b.code.indexOf('bootstrap_project(');
    if (boot !== -1 && boot < create) {
      return { pass: true, score: 1, reason: `bootstrap_project precedes KedroSession.create in ${b.path || '<unlabelled block>'}` };
    }
    // A fixture defined in another block (e.g. conftest.py) may do it.
    if (proposedPython(output).some((o) => o !== b && /bootstrap_project\(/.test(o.code))) {
      return { pass: true, score: 1, reason: 'bootstrap_project called in another proposed file' };
    }
    return { pass: false, score: 0, reason: `KedroSession.create without bootstrap_project in ${b.path || '<unlabelled block>'}` };
  }
  return { pass: false, score: 0, reason: 'No KedroSession.create in the proposed code' };
}

// "runtime_params must be nested through the Python API".
function noDottedRuntimeParams(output) {
  return forbid(output, /["']model_options\.test_size["']\s*:/, isPython, 'dotted runtime_params key');
}

// "Removed APIs": load_context, context.run and KedroDataCatalog are gone in 1.x.
// session.load_context() (a method) still exists, so only the bare call fails.
function noRemovedApis(output) {
  return forbid(
    output,
    /(?<!\.)\bload_context\s*\(|from kedro\.framework\.context import load_context|\bcontext\.run\(|KedroDataCatalog/,
    isPython,
    'load_context, context.run or KedroDataCatalog',
  );
}

// "pipeline_name= is deprecated; use pipeline_names=[...]".
function noDeprecatedPipelineName(output) {
  return forbid(output, /\bpipeline_name\s*=/, isPython, 'deprecated pipeline_name=');
}

// "Kedro ships no pytest fixtures": a test that asks for kedro_session or
// catalog must come with a fixture that defines it.
function fixturesAreDefined(output) {
  const blocks = proposedPython(output);
  const used = new Set();
  for (const b of blocks) {
    for (const m of b.code.matchAll(/def test_\w*\(([^)]*)\)/g)) {
      for (const name of ['kedro_session', 'catalog']) {
        if (new RegExp(`\\b${name}\\b`).test(m[1])) used.add(name);
      }
    }
  }
  const missing = [...used].filter(
    (name) => !blocks.some((b) => new RegExp(`def ${name}\\s*\\(`).test(b.code)),
  );
  if (missing.length > 0) {
    return { pass: false, score: 0, reason: `Uses undefined fixture(s): ${missing.join(', ')}` };
  }
  return { pass: true, score: 1, reason: used.size ? `Defines ${[...used].join(', ')}` : 'Uses no Kedro fixtures' };
}

// Same rule, for project fixtures: every fixture a test requests must be
// defined somewhere in the proposed code (a conftest.py or the module itself).
function sharedFixturesAreDefined(output) {
  const blocks = proposedPython(output);
  const missing = ['model_options', 'model_input_table'].filter(
    (name) =>
      blocks.some((b) => new RegExp(`def test_\\w*\\([^)]*\\b${name}\\b`).test(b.code)) &&
      !blocks.some((b) => new RegExp(`def ${name}\\s*\\(`).test(b.code)),
  );
  if (missing.length > 0) {
    return { pass: false, score: 0, reason: `Uses undefined fixture(s): ${missing.join(', ')}` };
  }
  return { pass: true, score: 1, reason: 'Every requested fixture is defined' };
}

// "Check that the test env took effect": a passing run proves nothing about
// which parameter values were used.
function assertsEnvParams(output) {
  return requireCode(
    output,
    /\.params\b[\s\S]*test_size|test_size[\s\S]*\.params\b/,
    isPython,
    'an assertion on the loaded test_size parameter',
  );
}

// "An env parameters file replaces whole top-level keys": the test env's
// model_options must carry random_state and features as well as test_size.
const isYaml = (b) => b.lang === 'yaml' || b.lang === 'yml' || /\.ya?ml$/.test(b.path || '');

function writesFullEnvBlock(output) {
  return requireCode(
    output,
    /model_options\s*:(?=[\s\S]*\btest_size\s*:)(?=[\s\S]*\brandom_state\s*:)(?=[\s\S]*\bfeatures\s*:)/,
    isYaml,
    'a model_options YAML block with test_size, random_state and features',
  );
}

// "load_context and context.run are gone": the old test the request points
// at is broken too, so it should be rewritten alongside the new one (directly
// or through a shared helper in the same file).
function rewritesOldTest(output) {
  return requireCode(
    output,
    /^(?=[\s\S]*\bdef\s+test_data_processing_runs\b)(?=[\s\S]*KedroSession\.create)/,
    isPython,
    'test_data_processing_runs rewritten with KedroSession',
  );
}

// "Node unit tests call the function directly". A separate smoke test that
// uses a session (for the realistic-data goal) is fine, so the check needs one
// block that calls the node without Kedro machinery, and no machinery in the
// unit-test module itself (test_nodes.py).
const KEDRO_MACHINERY = /KedroSession|SequentialRunner|DataCatalog|bootstrap_project/;

function noKedroMachineryInUnitTest(output) {
  const blocks = proposedPython(output);
  const dirty = blocks.find((b) => /test_nodes\.py$/.test(b.path || '') && KEDRO_MACHINERY.test(b.code));
  if (dirty) {
    return { pass: false, score: 0, reason: `Found Kedro session, runner or catalog in the node unit test ${dirty.path}` };
  }
  const direct = blocks.find((b) => /preprocess_companies\(/.test(b.code) && !KEDRO_MACHINERY.test(b.code));
  if (!direct) {
    return { pass: false, score: 0, reason: 'No block calls preprocess_companies directly without a session, runner or catalog' };
  }
  return { pass: true, score: 1, reason: `preprocess_companies called directly in ${direct.path || '<unlabelled block>'}` };
}

module.exports = {
  noIndexingRunResult,
  loadsRunOutput,
  noBareParamsCatalogKey,
  registersParamsKey,
  makesIntermediateObservable,
  bootstrapsBeforeSession,
  noDottedRuntimeParams,
  noRemovedApis,
  noDeprecatedPipelineName,
  fixturesAreDefined,
  sharedFixturesAreDefined,
  noKedroMachineryInUnitTest,
  assertsEnvParams,
  writesFullEnvBlock,
  rewritesOldTest,
};
