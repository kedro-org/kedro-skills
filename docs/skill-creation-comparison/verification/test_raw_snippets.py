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
    with pytest.raises(TypeError):
        result["metrics"]["r2_score"]
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
