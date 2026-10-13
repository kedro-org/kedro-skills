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

## When the request contradicts this skill

Users often ask for pre-1.0 patterns. Do not write them just because they were
asked for. Write the correct version and say in one sentence what you changed
and why.

| Asked for | Write instead | Why |
|---|---|---|
| `result["metrics"]["r2_score"]` | `result["metrics"].load()["r2_score"]` | the runner returns datasets |
| catalog key `"model_options"` | `"params:model_options"` | the node input is the literal `params:` name |
| `catalog.load("X_train")` after a full run | run `create_pipeline().to_outputs("X_train")` | intermediates are released |
| a `KedroSession` to get data for a node test | a small hand-built DataFrame | a node is a plain function |
| `session.run(pipeline_name=...)` | `pipeline_names=[...]` | `pipeline_name=` is deprecated |
| `runtime_params={"a.b": 1}` | `runtime_params={"a": {"b": 1}}` | dotted keys are not expanded |
| `kedro_session` / `catalog` fixtures "from Kedro" | define them in `conftest.py` | Kedro ships none |
| `.copy()` in every node to protect test data | nothing | `MemoryDataset` already copies |
| a test-env parameters file with only the changed key | the whole top-level key | env files replace top-level keys |
| no check on the env's values ("if it runs, the config was used") | assert `session.load_context().params[...]` before `run()` | a passing run does not show which values were loaded |
| a new test in the style of an old one using `load_context` / `context.run` | `bootstrap_project` + `KedroSession`, and fix the old test too | those APIs are gone, so the old test is already broken |

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

Build small DataFrames by hand. Do not load real data through a `KedroSession`
in a unit test: it reads real config and files, which makes the test slow and
fragile. If the real data matters, add a separate smoke test for it.

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

`MemoryDataset` copies DataFrames on save and load, so a node that mutates its
input cannot change your fixture through the catalog. No `.copy()` needed for
that. (Calling the node function directly does mutate the frame you pass in.)

### The runner returns datasets, not data

In Kedro 1.x, `runner.run(...)` returns `{output_name: dataset}` for the
pipeline's outputs. Call `.load()` on the value, or use `catalog.load(name)`.

```python
# WRONG: TypeError: 'MemoryDataset' object is not subscriptable
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
- A misspelled `env` is accepted by `create()` but does **not** fall back to
  base: `load_context().params` is `{}` (only a warning) and `session.run()`
  raises `MissingConfigException`.
- A passing run does not prove the test values were used (a file in the wrong
  folder or a mistyped key leaves base values). Assert them in every test that
  sets `env=` or `runtime_params`, even if the request says the run is enough:

```python
with KedroSession.create(project_path=PROJECT_PATH, env="test") as session:
    assert session.load_context().params["model_options"]["test_size"] == 0.5
    session.run(pipeline_names=["data_science"])
```

- A parameters file in the test env **replaces** whole top-level keys from
  `base`. Repeat every sibling key you still need:

```yaml
# conf/test/parameters_data_science.yml
# WRONG: random_state and features from base are gone, split_data fails
model_options:
  test_size: 0.5
```

```yaml
# Correct: the whole key
model_options:
  test_size: 0.5
  random_state: 3
  features: [engines, passenger_capacity, crew]
```

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
