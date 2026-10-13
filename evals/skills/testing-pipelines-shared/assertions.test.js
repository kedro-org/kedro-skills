// Run with: node --test evals/skills/*/*.test.js (part of make eval-test)
const { test } = require('node:test');
const assert = require('node:assert/strict');
const a = require('./assertions.js');

const py = (code, path = 'tests/test_x.py') => `File: ${path}\n\`\`\`python\n${code}\n\`\`\`\n`;

test('runner result: indexing fails, .load() passes', () => {
  const bad = py('result = SequentialRunner().run(p, catalog)\nassert result["metrics"]["r2_score"]');
  const good = py('metrics = result["metrics"].load()\nassert metrics["r2_score"]');
  assert.equal(a.noIndexingRunResult(bad).pass, false);
  assert.equal(a.loadsRunOutput(bad).pass, false);
  assert.equal(a.noIndexingRunResult(good).pass, true);
  assert.equal(a.loadsRunOutput(good).pass, true);
});

test('params key: bare model_options fails, literal params: key passes', () => {
  assert.equal(a.noBareParamsCatalogKey(py('DataCatalog({"model_options": MemoryDataset(p)})')).pass, false);
  assert.equal(a.noBareParamsCatalogKey(py('catalog["model_options"] = p')).pass, false);
  const good = py('DataCatalog({"params:model_options": MemoryDataset(p)})');
  assert.equal(a.noBareParamsCatalogKey(good).pass, true);
  assert.equal(a.registersParamsKey(good).pass, true);
});

test('intermediate: slice or hook passes, plain catalog.load fails', () => {
  assert.equal(a.makesIntermediateObservable(py('run(create_pipeline(), c)\nc.load("X_train")')).pass, false);
  assert.equal(a.makesIntermediateObservable(py('run(create_pipeline().to_outputs("X_train"), c)')).pass, true);
});

test('bootstrap_project must come before KedroSession.create', () => {
  assert.equal(a.bootstrapsBeforeSession(py('KedroSession.create(project_path=P)')).pass, false);
  assert.equal(a.bootstrapsBeforeSession(py('bootstrap_project(P)\nKedroSession.create(project_path=P)')).pass, true);
  const viaConftest =
    py('bootstrap_project(P)', 'tests/conftest.py') + py('KedroSession.create(project_path=P)');
  assert.equal(a.bootstrapsBeforeSession(viaConftest).pass, true);
  assert.equal(a.bootstrapsBeforeSession('no code here').pass, false);
});

test('runtime_params: dotted key fails, nested passes', () => {
  assert.equal(a.noDottedRuntimeParams(py('runtime_params={"model_options.test_size": 0.3}')).pass, false);
  assert.equal(a.noDottedRuntimeParams(py('runtime_params={"model_options": {"test_size": 0.3}}')).pass, true);
});

test('removed APIs and deprecated pipeline_name are caught', () => {
  assert.equal(a.noRemovedApis(py('from kedro.framework.context import load_context')).pass, false);
  assert.equal(a.noRemovedApis(py('from kedro.io import KedroDataCatalog')).pass, false);
  assert.equal(a.noRemovedApis(py('session.load_context()')).pass, true);
  assert.equal(a.noDeprecatedPipelineName(py('session.run(pipeline_name="ds")')).pass, false);
  assert.equal(a.noDeprecatedPipelineName(py('session.run(pipeline_names=["ds"])')).pass, true);
});

test('a counter-example block does not fail forbid checks', () => {
  const out = "Don't write:\n```python\nfrom kedro.framework.context import load_context\n```";
  assert.equal(a.noRemovedApis(out).pass, true);
});

test('fixtures: requested but undefined fails, defined passes', () => {
  const uses = py('def test_ds(kedro_session, catalog):\n    pass');
  assert.equal(a.fixturesAreDefined(uses).pass, false);
  const defined = py('@pytest.fixture\ndef catalog():\n    return DataCatalog()\n@pytest.fixture\ndef kedro_session():\n    pass', 'tests/conftest.py');
  assert.equal(a.fixturesAreDefined(uses + defined).pass, true);
  assert.equal(a.fixturesAreDefined(py('def test_ds(tmp_path):\n    pass')).pass, true);
});

test('shared fixtures must be defined somewhere', () => {
  const uses = py('def test_split(model_options, model_input_table):\n    pass');
  assert.equal(a.sharedFixturesAreDefined(uses).pass, false);
  const conftest = py('def model_options():\n    return {}\ndef model_input_table():\n    return df', 'tests/conftest.py');
  assert.equal(a.sharedFixturesAreDefined(uses + conftest).pass, true);
});

test('unit test: session or runner fails, direct call passes', () => {
  assert.equal(a.noKedroMachineryInUnitTest(py('with KedroSession.create() as s:\n    pass')).pass, false);
  assert.equal(a.noKedroMachineryInUnitTest(py('out = preprocess_companies(df)')).pass, true);
  const sessionInUnit = py('with KedroSession.create() as s:\n    df = s.load_context().catalog.load("companies")\npreprocess_companies(df)', 'tests/pipelines/data_processing/test_nodes.py');
  assert.equal(a.noKedroMachineryInUnitTest(sessionInUnit).pass, false);
  const unitPlusSmoke =
    py('out = preprocess_companies(df)', 'tests/pipelines/data_processing/test_nodes.py') +
    py('with KedroSession.create(project_path=P) as s:\n    preprocess_companies(c.copy())', 'tests/test_run.py');
  assert.equal(a.noKedroMachineryInUnitTest(unitPlusSmoke).pass, true);
});

test('env params: reading test_size from context params passes, a bare run fails', () => {
  const good = py('with KedroSession.create(project_path=P, env="test") as s:\n    assert s.load_context().params["model_options"]["test_size"] == 0.5\n    s.run()');
  assert.equal(a.assertsEnvParams(good).pass, true);
  assert.equal(a.assertsEnvParams(py('with KedroSession.create(env="test") as s:\n    s.run()')).pass, false);
});

test('env file: full model_options block passes, test_size alone fails', () => {
  const y = (code) => `File: conf/test/parameters_data_science.yml\n\`\`\`yaml\n${code}\n\`\`\`\n`;
  assert.equal(a.writesFullEnvBlock(y('model_options:\n  test_size: 0.5')).pass, false);
  const full = y('model_options:\n  test_size: 0.5\n  random_state: 3\n  features:\n    - engines');
  assert.equal(a.writesFullEnvBlock(full).pass, true);
  assert.equal(a.writesFullEnvBlock(py('model_options: test_size random_state features')).pass, false);
});

test('old load_context test: rewritten with KedroSession passes, left alone fails', () => {
  const newOnly = py('def test_data_science_runs():\n    with KedroSession.create(project_path=P) as s:\n        s.run()');
  assert.equal(a.rewritesOldTest(newOnly).pass, false);
  const both = py('def test_data_processing_runs():\n    bootstrap_project(P)\n    with KedroSession.create(project_path=P) as s:\n        s.run()');
  assert.equal(a.rewritesOldTest(both).pass, true);
  const helper = py('def _run(n):\n    with KedroSession.create(project_path=P) as s:\n        s.run(pipeline_names=[n])\ndef test_data_processing_runs():\n    _run("data_processing")');
  assert.equal(a.rewritesOldTest(helper).pass, true);
});
