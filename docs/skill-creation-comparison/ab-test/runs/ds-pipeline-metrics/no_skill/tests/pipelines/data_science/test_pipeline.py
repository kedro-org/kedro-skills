import logging
import pandas as pd
import pytest
from kedro.io import DataCatalog
from kedro.runner import SequentialRunner
from spaceflights.pipelines.data_science import create_pipeline as create_ds_pipeline
from spaceflights.pipelines.data_science.nodes import split_data

@pytest.fixture
def dummy_data():
    return pd.DataFrame(
        {
            "engines": [1, 2, 3],
            "crew": [4, 5, 6],
            "passenger_capacity": [5, 6, 7],
            "price": [120, 290, 30],
        }
    )

@pytest.fixture
def dummy_parameters():
    parameters = {
        "model_options": {
            "test_size": 0.2,
            "random_state": 3,
            "features": ["engines", "passenger_capacity", "crew"],
        }
    }
    return parameters


def test_split_data(dummy_data, dummy_parameters):
    X_train, X_test, y_train, y_test = split_data(
        dummy_data, dummy_parameters["model_options"]
    )
    assert len(X_train) == 2
    assert len(y_train) == 2
    assert len(X_test) == 1
    assert len(y_test) == 1

def test_split_data_missing_price(dummy_data, dummy_parameters):
    dummy_data_missing_price = dummy_data.drop(columns="price")
    with pytest.raises(KeyError) as e_info:
        X_train, X_test, y_train, y_test = split_data(dummy_data_missing_price, dummy_parameters["model_options"])

    assert "price" in str(e_info.value)

def test_data_science_pipeline(caplog, dummy_data, dummy_parameters):
    pipeline = (
        create_ds_pipeline()
        .from_nodes("split_data_node")
        .to_nodes("evaluate_model_node")
    )
    catalog = DataCatalog()
    catalog["model_input_table"] = dummy_data
    catalog["params:model_options"] = dummy_parameters["model_options"]

    caplog.set_level(logging.DEBUG, logger="kedro")
    successful_run_msg = "Pipeline execution completed successfully"

    SequentialRunner().run(pipeline, catalog)

    assert successful_run_msg in caplog.text


def test_data_science_pipeline_metrics():
    # 10 rows so the 20% test split has 2 samples (r2 needs >= 2).
    data = pd.DataFrame(
        {
            "engines": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "crew": [2, 1, 4, 3, 6, 5, 8, 7, 10, 9],
            "passenger_capacity": [5, 6, 7, 9, 8, 11, 12, 10, 14, 13],
            "price": [100, 150, 210, 250, 310, 340, 420, 440, 520, 540],
        }
    )
    params = {
        "test_size": 0.2,
        "random_state": 3,
        "features": ["engines", "passenger_capacity", "crew"],
    }
    catalog = DataCatalog()
    catalog["model_input_table"] = data
    catalog["params:model_options"] = params

    SequentialRunner().run(create_ds_pipeline(), catalog)

    metrics = catalog.load("metrics")
    assert {"r2_score", "mae", "max_error"} <= set(metrics.keys())
