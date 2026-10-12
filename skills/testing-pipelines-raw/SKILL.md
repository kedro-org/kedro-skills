---
name: testing-pipelines-raw
description: >-
  Kedro testing guidance for tests/**/*.py in a Kedro project. Use when writing
  unit tests for node functions, pipeline tests with DataCatalog, MemoryDataset
  and SequentialRunner, or KedroSession smoke tests. Adds nothing for tests
  that do not touch Kedro.
---
# Testing Kedro Nodes and Pipelines

Applies to Kedro 1.x. Kedro ships **no pytest plugin and no fixtures**. Every
fixture you use (`catalog`, `session`, sample data) must be defined in your own
test module or `conftest.py`.

## Pick the right kind of test

| What you are checking | Test type | Needs Kedro objects? |
|---|---|---|
| A node's logic | Unit test: call the function | No |
| Nodes wired together (names, `params:`, outputs) | Pipeline test: `DataCatalog` + `SequentialRunner` | Yes, in memory |
| The project boots and runs end to end | Smoke test: `KedroSession` | Yes, real config and data |

Prefer the first two. Never start a `KedroSession` to test a single node.

## Unit-testing a node

A node is a plain Python function. Call it directly.

```python
import pandas as pd
from spaceflights.pipelines.data_science.nodes import split_data


def test_split_data_returns_expected_sizes():
    data = pd.DataFrame(
        {"engines": [1, 2, 3, 4, 5], "crew": [4, 5, 6, 7, 8], "price": [1, 2, 3, 4, 5]}
    )
    params = {"test_size": 0.2, "random_state": 3, "features": ["engines", "crew"]}

    X_train, X_test, y_train, y_test = split_data(data, params)

    assert len(X_train) == 4
    assert len(X_test) == 1
```

Pass parameters as the plain dict the node receives. There is no `params:` here.

## Testing a pipeline in memory

Build a `DataCatalog` of `MemoryDataset`s and run with `SequentialRunner`.

```python
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from spaceflights.pipelines.data_science import create_pipeline


def test_data_science_pipeline(model_input_table, model_options):
    catalog = DataCatalog(
        {
            "model_input_table": MemoryDataset(model_input_table),
            "params:model_options": MemoryDataset(model_options),
        }
    )

    result = SequentialRunner().run(create_pipeline(), catalog)

    metrics = result["metrics"].load()  # result values are datasets
    assert set(metrics) == {"r2_score", "mae", "max_error"}
```

`catalog["model_input_table"] = df` is equivalent: raw data is wrapped in a
`MemoryDataset` for you.

### The runner returns datasets, not data

In Kedro 1.x, `runner.run(...)` returns `{output_name: dataset}` for the
pipeline's outputs. Call `.load()` on the value, or use `catalog.load(name)`.

```python
# WRONG: compares a MemoryDataset with a dict, always fails
assert result["metrics"]["r2_score"] > 0

# Correct
assert result["metrics"].load()["r2_score"] > 0
```

### Provide every free input, including `params:`

The runner raises `ValueError: Pipeline input(s) {...} not found in the
DataCatalog` for any free input not in the catalog. Use `pipeline.inputs()` to
list them. Register parameters under their **literal** input name:

```python
# Correct
catalog["params:model_options"] = {"test_size": 0.2, ...}

# WRONG: the node asks for "params:model_options", so this is a missing input
catalog["model_options"] = {"test_size": 0.2, ...}
```

Outputs and intermediates do not need registering. The runner creates
`MemoryDataset`s for them. It also **releases** intermediates once their last
consumer has run, so `catalog.load("X_train")` after the run raises
`DatasetError`. Only free inputs and pipeline outputs survive. To assert on an
intermediate, slice so that it becomes an output (next section).

### Testing part of a pipeline

Slice the pipeline, then provide the free inputs of **the slice**:

```python
pipeline = create_pipeline().from_nodes("train_model_node").to_nodes("evaluate_model_node")
# pipeline.inputs() == {"X_train", "y_train", "X_test", "y_test"}

# Make an intermediate inspectable by ending the slice there
result = SequentialRunner().run(create_pipeline().to_outputs("X_train"), catalog)
X_train = result["X_train"].load()
```

Available: `only_nodes`, `from_nodes`, `to_nodes`, `from_inputs`, `to_outputs`,
`only_nodes_with_tags`, `filter`.

## Smoke-testing the whole project

```python
from pathlib import Path

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

PROJECT_PATH = Path(__file__).resolve().parents[1]  # project root, not cwd


def test_project_runs():
    bootstrap_project(PROJECT_PATH)  # required, before KedroSession.create
    with KedroSession.create(project_path=PROJECT_PATH) as session:
        session.run(pipeline_names=["data_processing"])
```

- Without `bootstrap_project`, `create` fails with `ValueError: Package name not
  found`.
- This uses the real `conf/base/catalog.yml` and **writes real files** to
  `data/`. Keep these tests few, and point the catalog elsewhere through a test
  env if that matters.
- One session = one run. A second `session.run()` raises `KedroSessionError`.
- `pipeline_name=` is deprecated. Use `pipeline_names=[...]`.

### Test environments and runtime parameters

```python
KedroSession.create(
    project_path=PROJECT_PATH,
    env="test",                                          # conf/test/
    runtime_params={"model_options": {"test_size": 0.5}},  # nested dict
)
```

- `runtime_params` must be **nested**. A dotted key like
  `{"model_options.test_size": 0.5}` is not expanded. It becomes a literal key and
  the real value is unchanged. (Only the CLI `--params` parses dots.)
- A misspelled or missing `env` is **not** an error. Kedro silently uses base only.
- A `parameters.yml` in the test env **replaces** whole top-level keys from
  `base`. Repeat every sibling key you still need.

## Wrong APIs: do not generate these

```python
# WRONG: none of these exist in Kedro 1.x
context.run()                                      # KedroContext has no run()
from kedro.framework.context import load_context
from kedro.runner import KedroSession              # it's kedro.framework.session
from kedro.io import KedroDataCatalog              # it's kedro.io.DataCatalog
def test_x(kedro_session, catalog): ...            # no built-in fixtures
```

## Fixtures and layout

Write fixtures yourself, in `conftest.py` to share them:

```python
# tests/conftest.py
import pandas as pd
import pytest


@pytest.fixture
def model_input_table():
    return pd.DataFrame({"engines": [1, 2, 3, 4, 5], "crew": [4, 5, 6, 7, 8],
                         "passenger_capacity": [5, 6, 7, 8, 9],
                         "price": [120, 290, 30, 40, 50]})


@pytest.fixture
def model_options():
    return {"test_size": 0.2, "random_state": 3,
            "features": ["engines", "passenger_capacity", "crew"]}
```

`tests/` sits at the project root and mirrors `src/<package>/`:

```
src/<package>/pipelines/data_science/nodes.py
tests/pipelines/data_science/test_nodes.py
tests/pipelines/data_science/test_pipeline.py
tests/test_run.py
```

Install the project (`pip install -e .`) so tests can import it, and run
`pytest` from the project root. Coverage comes from `pytest-cov` through
`[tool.pytest.ini_options] addopts = "--cov src/<package>"` in `pyproject.toml`.
