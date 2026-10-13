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


def test_split_data_returns_expected_sizes():
    data = pd.DataFrame(
        {"engines": [1, 2, 3, 4, 5], "crew": [4, 5, 6, 7, 8], "price": [1, 2, 3, 4, 5]}
    )
    params = {"test_size": 0.2, "random_state": 3, "features": ["engines", "crew"]}
    X_train, X_test, y_train, y_test = split_data(data, params)
    assert len(X_train) == 4
    assert len(X_test) == 1


def test_data_science_pipeline(model_input_table, model_options):
    catalog = DataCatalog(
        {
            "model_input_table": MemoryDataset(model_input_table),
            "params:model_options": MemoryDataset(model_options),
        }
    )
    result = SequentialRunner().run(create_pipeline(), catalog)
    metrics = result["metrics"].load()
    assert set(metrics) == {"r2_score", "mae", "max_error"}


def test_wrong_vs_correct(model_input_table, model_options):
    catalog = DataCatalog()
    catalog["model_input_table"] = model_input_table
    catalog["params:model_options"] = model_options
    result = SequentialRunner().run(create_pipeline(), catalog)
    # The WRONG line fails exactly as the skill's comment says.
    with pytest.raises(TypeError, match="'MemoryDataset' object is not subscriptable"):
        result["metrics"]["r2_score"] > 0
    assert "r2_score" in result["metrics"].load()


def test_wrong_params_name(model_input_table, model_options):
    catalog = DataCatalog()
    catalog["model_input_table"] = model_input_table
    catalog["model_options"] = model_options
    with pytest.raises(ValueError, match="not found in the DataCatalog"):
        SequentialRunner().run(create_pipeline(), catalog)


def test_slice_inputs():
    pipeline = create_pipeline().from_nodes("train_model_node").to_nodes("evaluate_model_node")
    assert pipeline.inputs() == {"X_train", "y_train", "X_test", "y_test"}


def test_project_runs():
    bootstrap_project(PROJECT_PATH)
    with KedroSession.create(project_path=PROJECT_PATH) as session:
        session.run(pipeline_names=["data_processing"])


def test_session_kwargs():
    bootstrap_project(PROJECT_PATH)
    with KedroSession.create(project_path=PROJECT_PATH, env="test",
                             runtime_params={"model_options": {"test_size": 0.5}}) as s:
        assert s.load_context().params["model_options"]["test_size"] == 0.5


def test_slice_to_intermediate(model_input_table, model_options):
    catalog = DataCatalog()
    catalog["model_input_table"] = model_input_table
    catalog["params:model_options"] = model_options
    result = SequentialRunner().run(create_pipeline().to_outputs("X_train"), catalog)
    X_train = result["X_train"].load()
    assert len(X_train) == 4


# --- iteration 2 (2026-10-13): new snippets, WRONG lines included ---

TEST_ENV = PROJECT_PATH / "conf" / "test"
CORRECT_YAML = """model_options:
  test_size: 0.5
  random_state: 3
  features: [engines, passenger_capacity, crew]
"""
WRONG_YAML = """model_options:
  test_size: 0.5
"""


def _with_test_env(yaml_text, body):
    TEST_ENV.mkdir(exist_ok=True)
    (TEST_ENV / "parameters_data_science.yml").write_text(yaml_text)
    try:
        bootstrap_project(PROJECT_PATH)
        body()
    finally:
        (TEST_ENV / "parameters_data_science.yml").unlink()
        TEST_ENV.rmdir()


def test_env_assert_snippet_with_correct_yaml():
    def body():
        with KedroSession.create(project_path=PROJECT_PATH, env="test") as session:
            assert session.load_context().params["model_options"]["test_size"] == 0.5
            session.run(pipeline_names=["data_science"])
    _with_test_env(CORRECT_YAML, body)


def test_env_wrong_yaml_drops_siblings_and_split_data_fails():
    def body():
        with KedroSession.create(project_path=PROJECT_PATH, env="test") as session:
            assert session.load_context().params["model_options"] == {"test_size": 0.5}
        with KedroSession.create(project_path=PROJECT_PATH, env="test") as session:
            with pytest.raises(KeyError, match="features"):  # split_data fails
                session.run(pipeline_names=["data_science"])
    _with_test_env(WRONG_YAML, body)


def test_misspelled_env_empty_params_and_run_raises():
    from kedro.config import MissingConfigException
    bootstrap_project(PROJECT_PATH)
    with KedroSession.create(project_path=PROJECT_PATH, env="tset") as session:
        with pytest.warns(UserWarning, match="Parameters not found"):
            assert session.load_context().params == {}
    with KedroSession.create(project_path=PROJECT_PATH, env="tset") as session:
        with pytest.raises(MissingConfigException):
            session.run(pipeline_names=["data_science"])


def _mutate(df):
    df["engines"] = 0
    return df


def test_memorydataset_copy_protects_fixture(model_input_table):
    from kedro.pipeline import Node, Pipeline
    before = model_input_table.copy()
    catalog = DataCatalog()
    catalog["model_input_table"] = model_input_table
    SequentialRunner().run(Pipeline([Node(_mutate, "model_input_table", "out")]), catalog)
    pd.testing.assert_frame_equal(model_input_table, before)
    _mutate(model_input_table)  # a direct call does mutate
    assert (model_input_table["engines"] == 0).all()
