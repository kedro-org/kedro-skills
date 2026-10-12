---
name: testing-pipelines-skill-creator
description: >-
  How to write tests for a Kedro 1.x project in tests/**/*.py, covering unit tests for
  node functions, in-memory pipeline tests with DataCatalog, MemoryDataset and
  SequentialRunner, and KedroSession smoke tests. Use this whenever you write,
  fix or review a test that imports kedro or a Kedro project's nodes and
  pipelines, even when the request is just "add tests for this pipeline" or
  "why does my pipeline test fail". Kedro 1.x changed what runners return and
  how sessions start, and older examples get both wrong. Not needed for tests
  that never touch Kedro.
---
# Writing tests for a Kedro project

Kedro tests are ordinary pytest tests. What makes them Kedro-specific is a
small set of runtime behaviours that look reasonable to guess and are easy to
guess wrong. This skill covers those. Everything else is plain pytest.

Kedro ships no pytest plugin, so there are no `kedro_session`, `kedro_context`
or `catalog` fixtures. If a test needs one, define it in the test module or in
`tests/conftest.py`. A test that asks for a fixture nobody defined fails at
collection.

## Choose the smallest test that answers the question

Each layer up costs more and fails for more reasons, so test at the lowest
layer that can catch the bug:

1. **Node logic** → call the node function directly. Nodes are plain Python
   functions, so a unit test needs no catalog, runner or session.
2. **Wiring** (dataset names, `params:` inputs, which outputs exist) → run the
   pipeline in memory with `DataCatalog` + `SequentialRunner`.
3. **The project boots end to end** → `KedroSession` smoke test. It reads the
   real `conf/` and writes real files to `data/`, so keep it to one or two
   tests.

## 1. Node unit tests

```python
import pandas as pd
from my_project.pipelines.data_science.nodes import split_data


def test_split_data_holds_out_test_fraction():
    data = pd.DataFrame({"engines": [1, 2, 3, 4, 5], "price": [1, 2, 3, 4, 5]})
    params = {"test_size": 0.2, "random_state": 3, "features": ["engines"]}

    X_train, X_test, y_train, y_test = split_data(data, params)

    assert (len(X_train), len(X_test)) == (4, 1)
```

The node receives parameters as a plain dict, so pass a dict. The `params:`
prefix only exists in pipeline wiring.

## 2. In-memory pipeline tests

```python
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from my_project.pipelines.data_science import create_pipeline


def test_data_science_pipeline_produces_metrics(model_input_table, model_options):
    catalog = DataCatalog(
        {
            "model_input_table": MemoryDataset(model_input_table),
            "params:model_options": MemoryDataset(model_options),
        }
    )

    result = SequentialRunner().run(create_pipeline(), catalog)

    metrics = result["metrics"].load()
    assert set(metrics) == {"r2_score", "mae", "max_error"}
```

`catalog["model_input_table"] = df` also works. Raw data is wrapped in a
`MemoryDataset` for you.

Four behaviours shape these tests:

**The runner returns datasets, not data.** `runner.run()` returns
`{output_name: dataset}` for the pipeline's outputs. Call `.load()` on each
value (or use `catalog.load(name)`). Pre-1.0 runners returned the data itself,
so older examples index straight into the result, as in
`result["metrics"]["r2_score"]`. On 1.x that fails because the value is a
`MemoryDataset`.

**Every free input must be in the catalog.** Otherwise the run stops with
`ValueError: Pipeline input(s) {...} not found in the DataCatalog`.
`pipeline.inputs()` tells you exactly what to provide.

**Parameters are registered under their literal input name.** If a node
declares `"params:model_options"`, the catalog key is `"params:model_options"`.
Registering `"model_options"` leaves the input missing.

**Intermediates are released after use.** The runner creates `MemoryDataset`s
for intermediate outputs, then releases each one once its last consumer has
run. So `catalog.load("X_train")` after the run raises `DatasetError: ... has
not been saved yet`. Only free inputs and pipeline outputs survive. To check
an intermediate, end the pipeline there so it becomes an output:

```python
result = SequentialRunner().run(create_pipeline().to_outputs("X_train"), catalog)
X_train = result["X_train"].load()
```

### Running part of a pipeline

`only_nodes`, `from_nodes`, `to_nodes`, `from_inputs`, `to_outputs`,
`only_nodes_with_tags` and `filter` return a new `Pipeline`. The catalog must
satisfy the **slice's** `.inputs()`, not the full pipeline's:

```python
sliced = create_pipeline().from_nodes("train_model_node").to_nodes("evaluate_model_node")
assert sliced.inputs() == {"X_train", "y_train", "X_test", "y_test"}
```

`MemoryDataset` copies pandas DataFrames and numpy arrays on load and save, so
a node that mutates its input cannot corrupt the fixture between tests.

## 3. KedroSession smoke tests

```python
from pathlib import Path

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

PROJECT_PATH = Path(__file__).resolve().parents[1]


def test_data_processing_runs():
    bootstrap_project(PROJECT_PATH)
    with KedroSession.create(project_path=PROJECT_PATH) as session:
        session.run(pipeline_names=["data_processing"])
```

Why each line looks like this:

- `bootstrap_project` reads `pyproject.toml` and registers the project's
  package and settings. Without it, `KedroSession.create` fails with
  `ValueError: Package name not found`.
- Resolve the project root from `__file__`. The starter template uses
  `Path.cwd()`, which only works when pytest runs from the project root.
- Use `pipeline_names=[...]`. `pipeline_name=` is deprecated.
- A session runs once. A second `session.run()` raises `KedroSessionError`, so
  create a new session per run.
- `session.run()` also returns `{name: dataset}`, same as the runner.

### Test environments and runtime parameters

```python
KedroSession.create(
    project_path=PROJECT_PATH,
    env="test",
    runtime_params={"model_options": {"test_size": 0.5}},
)
```

Three traps:

- **`runtime_params` must be nested.** Through the Python API, a dotted key
  like `{"model_options.test_size": 0.5}` is stored as a literal key and the real
  value is unchanged. Only the CLI's `--params` splits on dots.
- **A missing env is silent.** `env="tset"` raises nothing and you get base
  config, so a typo turns a test-config test into a production-config test.
- **An env's parameters file replaces whole top-level keys.** If
  `conf/test/parameters.yml` sets only `model_options.test_size`, the other
  `model_options` keys from `base` are gone. Repeat the keys you need.

## Imports and APIs that do not exist in Kedro 1.x

Models trained on older Kedro code tend to produce these:

| Don't write | Write |
|---|---|
| `context.run()` / `KedroContext.run` | `KedroSession.create(...).run()` |
| `from kedro.framework.context import load_context` | `bootstrap_project` + `KedroSession.create` |
| `from kedro.runner import KedroSession`, `from kedro.io import KedroSession` | `from kedro.framework.session import KedroSession` |
| `from kedro.io import KedroDataCatalog` | `from kedro.io import DataCatalog` |
| `def test_x(kedro_session, catalog):` with no fixture defined | Define the fixtures in `conftest.py` |

## Project layout

`tests/` sits at the project root and mirrors `src/<package>/`, with files
named `test_<module>.py`:

```
tests/
├── conftest.py
├── pipelines/
│   └── data_science/
│       ├── test_nodes.py
│       └── test_pipeline.py
└── test_run.py
```

The project has to be installed (`pip install -e .`) for tests to import it.
For coverage, `pytest-cov` with `addopts = "--cov src/<package>"` under
`[tool.pytest.ini_options]` in `pyproject.toml`.
