from pathlib import Path

import pandas as pd
import pytest
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from spaceflights.pipelines.data_science import create_pipeline
from spaceflights.pipelines.data_science.nodes import split_data

PROJECT_PATH = Path(__file__).resolve().parents[2]


@pytest.fixture
def model_input_table():
    return pd.DataFrame({"engines": [1, 2, 3, 4, 5], "crew": [4, 5, 6, 7, 8],
                         "passenger_capacity": [5, 6, 7, 8, 9], "price": [120, 290, 30, 40, 50]})


@pytest.fixture
def model_options():
    return {"test_size": 0.2, "random_state": 3, "features": ["engines", "passenger_capacity", "crew"]}


def test_split_data_holds_out_test_fraction():
    data = pd.DataFrame({"engines": [1, 2, 3, 4, 5], "price": [1, 2, 3, 4, 5]})
    params = {"test_size": 0.2, "random_state": 3, "features": ["engines"]}
    X_train, X_test, y_train, y_test = split_data(data, params)
    assert (len(X_train), len(X_test)) == (4, 1)


def test_data_science_pipeline_produces_metrics(model_input_table, model_options):
    catalog = DataCatalog({"model_input_table": MemoryDataset(model_input_table),
                           "params:model_options": MemoryDataset(model_options)})
    result = SequentialRunner().run(create_pipeline(), catalog)
    metrics = result["metrics"].load()
    assert set(metrics) == {"r2_score", "mae", "max_error"}


def test_to_outputs(model_input_table, model_options):
    catalog = DataCatalog()
    catalog["model_input_table"] = model_input_table
    catalog["params:model_options"] = model_options
    result = SequentialRunner().run(create_pipeline().to_outputs("X_train"), catalog)
    X_train = result["X_train"].load()
    assert len(X_train) == 4


def test_sliced_inputs():
    sliced = create_pipeline().from_nodes("train_model_node").to_nodes("evaluate_model_node")
    assert sliced.inputs() == {"X_train", "y_train", "X_test", "y_test"}


def test_data_processing_runs():
    bootstrap_project(PROJECT_PATH)
    with KedroSession.create(project_path=PROJECT_PATH) as session:
        session.run(pipeline_names=["data_processing"])


def test_env_kwargs():
    bootstrap_project(PROJECT_PATH)
    with KedroSession.create(project_path=PROJECT_PATH, env="test",
                             runtime_params={"model_options": {"test_size": 0.5}}) as s:
        assert s.load_context().params["model_options"]["test_size"] == 0.5


# --- iteration 2 (2026-10-13): new and changed snippets ---
# The fixtures above are the skill's new tests/conftest.py, byte for byte in
# values, so the pipeline example running green also covers that block.

TEST_ENV = PROJECT_PATH / "conf" / "test"
FULL_KEY = """model_options:
  test_size: 0.5
  random_state: 3
  features: [engines, passenger_capacity, crew]
"""


def _in_test_env(yaml_text, body):
    TEST_ENV.mkdir(exist_ok=True)
    (TEST_ENV / "parameters_data_science.yml").write_text(yaml_text)
    try:
        bootstrap_project(PROJECT_PATH)
        body()
    finally:
        (TEST_ENV / "parameters_data_science.yml").unlink()
        TEST_ENV.rmdir()


def test_assert_env_before_running():
    def body():
        with KedroSession.create(project_path=PROJECT_PATH, env="test") as session:
            assert session.load_context().params["model_options"]["test_size"] == 0.5
            session.run(pipeline_names=["data_science"])
    _in_test_env(FULL_KEY, body)


def test_partial_env_key_fails_with_keyerror_features():
    def body():
        with KedroSession.create(project_path=PROJECT_PATH, env="test") as session:
            with pytest.raises(KeyError, match="features"):
                session.run(pipeline_names=["data_science"])
    _in_test_env("model_options:\n  test_size: 0.5\n", body)


def test_misspelled_env_empty_params_and_missing_config():
    from kedro.config import MissingConfigException
    bootstrap_project(PROJECT_PATH)
    with KedroSession.create(project_path=PROJECT_PATH, env="tset") as session:
        with pytest.warns(UserWarning):
            assert session.load_context().params == {}
    with KedroSession.create(project_path=PROJECT_PATH, env="tset") as session:
        with pytest.raises(MissingConfigException):
            session.run(pipeline_names=["data_science"])


def test_indexing_run_result_fails_because_value_is_memorydataset(model_input_table, model_options):
    catalog = DataCatalog({"model_input_table": MemoryDataset(model_input_table),
                           "params:model_options": MemoryDataset(model_options)})
    result = SequentialRunner().run(create_pipeline(), catalog)
    assert isinstance(result["metrics"], MemoryDataset)
    with pytest.raises(TypeError):
        result["metrics"]["r2_score"]


def _mutate(df):
    df["engines"] = 0
    return df


def test_catalog_copy_vs_direct_call(model_input_table):
    from kedro.pipeline import Node, Pipeline
    before = model_input_table.copy()
    catalog = DataCatalog()
    catalog["model_input_table"] = model_input_table
    SequentialRunner().run(Pipeline([Node(_mutate, "model_input_table", "out")]), catalog)
    pd.testing.assert_frame_equal(model_input_table, before)
    _mutate(model_input_table)
    assert (model_input_table["engines"] == 0).all()
