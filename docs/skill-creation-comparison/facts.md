# testing-pipelines: verified fact sheet

Shared input for both skill variants (`testing-pipelines-raw` and
`testing-pipelines-skill-creator`). Every claim was checked against
**Kedro 1.7.0** in a fresh `spaceflights-pandas` project (`kedro new --starter
spaceflights-pandas`). The evidence tests are in
[`verification/test_facts.py`](verification/test_facts.py); all 20 pass.

Starting point: the "what agents get wrong" list in the skill roadmap and the
source doc `kedro/docs/develop/automated_testing.md`. The source doc covers setup
and a single `KedroSession` smoke test, and says nothing about pipeline tests with
an in-memory catalog. Most facts below therefore come from source.

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | `KedroContext` has no `run()` method. Running goes through `KedroSession.run()` | ✅ True | `test_f01`; `kedro/framework/context/context.py` defines no `run` |
| 2 | `bootstrap_project(project_path)` must be called before `KedroSession.create` in a test | ✅ True | `test_f02`: without it, `ValueError: Package name not found. Make sure you have configured the project` |
| 3 | `KedroSession` comes from `kedro.framework.session` and `bootstrap_project` from `kedro.framework.startup`. `kedro.runner`/`kedro.io` do not export `KedroSession`, and `load_context` is gone | ✅ True | `test_f03` |
| 4 | Kedro registers no pytest fixtures (`kedro_session`, `kedro_context`, `catalog`, ...) and has no `pytest11` entry point. Fixtures go in your own `conftest.py` | ✅ True | `test_f04`; `kedro/pyproject.toml` has no pytest plugin |
| 5 | A node unit test calls the plain Python function directly, with no catalog, runner or session | ✅ True | `test_f05` |
| 6 | **`runner.run(pipeline, catalog)` returns `{output_name: dataset}`, which are dataset objects and not data.** Use `result["x"].load()` or `catalog.load("x")`. Pre-1.0 runners returned the data of free outputs | ✅ True (key gotcha) | `test_f06`; `kedro/runner/runner.py:123-126` |
| 6b | Intermediates not in the catalog are auto-created as `MemoryDataset`, but the runner **releases** them after their last consumer, so `catalog.load("X_train")` after the run raises `DatasetError: ... has not been saved yet`. Free inputs and pipeline outputs are kept. To inspect an intermediate, slice so it becomes an output: `pipeline.to_outputs("X_train")` | ❌ First draft was wrong; corrected | `test_f06`, `test_f06d`; `runner.py:347-360` `_release_datasets`. Caught when the raw skill's snippet failed under pytest |
| 6c | `catalog["name"] = raw_data` wraps raw data in a `MemoryDataset`. `DataCatalog({"name": MemoryDataset(data)})` is equivalent | ✅ True | `test_f06b`; `DataCatalog.__setitem__` docstring |
| 7 | Every free input of the pipeline must be in the catalog, otherwise `ValueError: Pipeline input(s) {...} not found in the DataCatalog`. `pipeline.inputs()` lists them | ✅ True | `test_f07`, `test_f09b`; `runner.py:100-105` |
| 8 | `params:` inputs are registered under the literal name `"params:model_options"`. Registering `"model_options"` does not satisfy them | ✅ True | `test_f08` |
| 9 | Slicing: `only_nodes`, `from_nodes`, `to_nodes`, `from_inputs`, `to_outputs`, `only_nodes_with_tags`, `filter`. The slice's own `.inputs()` is what the test catalog must provide | ✅ True | `test_f09` |
| 10 | `KedroSession.create(project_path, env=..., runtime_params=...)` exist as kwargs | ✅ True, with three caveats ↓ | `test_f10`; `session.py:129-136` |
| 10a | `runtime_params` through the Python API must be **nested** (`{"model_options": {"test_size": 0.5}}`). Dotted keys (`"model_options.test_size"`) are **not** expanded. They end up as a literal top-level key and the real value is unchanged. Only the CLI `--params` parses dots | ⚠️ New finding | `test_f10` |
| 10b | A non-existent `env` is accepted by `KedroSession.create()` and `load_context()`, but it does **not** fall back to base: parameters come back empty `{}` with only a `UserWarning` ("Parameters not found"), and the catalog, so `session.run()`, raises `MissingConfigException: ... conf/<env> does not exist` | ❌ First draft was wrong ("accepted silently, uses base"); corrected 2026-10-13 | `test_f10`. The first evidence stopped at `load_context()` not raising. Caught while verifying the iteration-2 skill fixes |
| 10c | A `parameters.yml` in a test env **replaces** the whole top-level key from `base`. `conf/test/parameters.yml` with only `model_options.test_size` drops `features` and `random_state` | ⚠️ New finding | `test_f10c` |
| 10d | A session runs once: a second `session.run()` raises `KedroSessionError: A run has already been completed`. `session.run()` also returns `{name: dataset}` | ✅ True | `test_f10b`; `session.py:337-342` |
| 10e | `session.run(pipeline_name=...)` is deprecated. Use `pipeline_names=[...]` | ✅ True | `session.py:330-335` |
| 10f | A full-session smoke test uses the real `conf/base/catalog.yml` and **writes real files** to `data/` | ✅ True | `test_f10b` wrote `data/02_intermediate/*.parquet` and `data/03_primary/model_input_table.parquet` |
| 11 | `tests/` at the project root mirrors `src/<package>/` (e.g. `tests/pipelines/data_science/test_pipeline.py`). The starter `test_run.py` docstring that says "`src/tests`" is stale. The starter's `test_run.py` uses `Path.cwd()`, so it only works when pytest runs from the project root | ✅ True | Starter layout; `automated_testing.md` |
| 12 | `DataCatalog`, `MemoryDataset` import from `kedro.io`. `KedroDataCatalog` no longer exists in 1.x | ✅ True | `test_f12` |
| 12b | `MemoryDataset` copies pandas DataFrames and numpy arrays on load/save, so mutating a loaded frame doesn't change the catalog | ✅ True | `test_f12b`; `memory_dataset.py` `_infer_copy_mode` |
| 12c | The runner logs `Pipeline execution completed successfully` at INFO on `kedro` loggers. The spaceflights starter test asserts on this through `caplog` | ✅ True | `test_f12c`; starter `tests/pipelines/data_science/test_pipeline.py` |

## Roadmap claims, after verification

| Roadmap claim | Outcome |
|---|---|
| Old `KedroContext` / `context.run()` pattern | Confirmed (1) |
| Omitting `bootstrap_project()` | Confirmed, with the exact error (2) |
| Importing session objects from `kedro.runner` / `kedro.io` | Confirmed (3) |
| Inventing `pytest-kedro` fixtures | Confirmed (4) |
| Running a whole session to test one node | Confirmed as bad practice (5, 10f) |

Not in the roadmap, found during verification: 6 (runner returns datasets), 6b
(intermediates are released), 10a–c (runtime params, missing env, env merge), 10f
(smoke tests write real files).

**Process note:** 6b was first written as "intermediates stay loadable". The
evidence test only checked `"X_train" in catalog`, which is true but not enough.
Running the raw skill's snippet showed the claim was wrong. A fact is only
verified once a test exercises the behaviour the skill tells people to rely on.

**Process note 2 (2026-10-13):** 10b repeated the same mistake. Its evidence test
only checked that `load_context()` does not raise, and the fact sheet turned that into
"silently uses base config". Both skills shipped the claim, and the round 2 promptfoo
rubric for the misspelled-env test was written from it. Running a test that reads
`context.params` and calls `session.run()` with a bad env showed empty parameters and
a `MissingConfigException`. Same lesson as 6b: test the behaviour the skill describes,
not just that nothing raised.
