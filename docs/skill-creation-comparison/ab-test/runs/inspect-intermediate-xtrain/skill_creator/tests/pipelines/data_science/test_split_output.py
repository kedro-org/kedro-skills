import pandas as pd
import pytest
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from spaceflights.pipelines.data_science import create_pipeline


@pytest.fixture
def model_options():
    return {
        "test_size": 0.25,
        "random_state": 3,
        "features": ["engines", "crew", "passenger_capacity"],
    }


@pytest.fixture
def model_input_table():
    # Includes extra columns that must not leak into X_train.
    return pd.DataFrame(
        {
            "engines": [1, 2, 3, 4, 5, 6, 7, 8],
            "crew": [1, 2, 3, 4, 5, 6, 7, 8],
            "passenger_capacity": [5, 6, 7, 8, 9, 10, 11, 12],
            "company_rating": [0.1] * 8,
            "price": [100, 200, 300, 400, 500, 600, 700, 800],
        }
    )


def test_x_train_only_contains_model_option_features(model_input_table, model_options):
    catalog = DataCatalog(
        {
            "model_input_table": MemoryDataset(model_input_table),
            "params:model_options": MemoryDataset(model_options),
        }
    )
    # X_train is an intermediate dataset and is released after its last consumer
    # runs, so end the pipeline at it to make it a pipeline output.
    pipeline = create_pipeline().to_outputs("X_train")

    result = SequentialRunner().run(pipeline, catalog)

    X_train = result["X_train"].load()
    assert list(X_train.columns) == model_options["features"]
    assert "price" not in X_train.columns
    assert "company_rating" not in X_train.columns
