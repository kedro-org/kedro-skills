import pandas as pd
import pytest
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner

from spaceflights.pipelines.data_science import create_pipeline


@pytest.fixture
def model_input_table():
    return pd.DataFrame(
        {
            "engines": [1, 2, 3, 4, 5],
            "crew": [4, 5, 6, 7, 8],
            "passenger_capacity": [5, 6, 7, 8, 9],
            "d_check_complete": [0, 1, 0, 1, 0],
            "moon_clearance_complete": [1, 0, 1, 0, 1],
            "price": [120, 290, 30, 40, 50],
            "unused_column": [9, 9, 9, 9, 9],
        }
    )


@pytest.fixture
def model_options():
    return {
        "test_size": 0.2,
        "random_state": 3,
        "features": ["engines", "passenger_capacity", "crew"],
    }


def test_x_train_only_has_model_option_features(model_input_table, model_options):
    catalog = DataCatalog(
        {
            "model_input_table": MemoryDataset(model_input_table),
            "params:model_options": MemoryDataset(model_options),
        }
    )

    # X_train is an intermediate and is released after its consumers run,
    # so end the pipeline at it to make it a pipeline output.
    pipeline = create_pipeline().to_outputs("X_train")
    result = SequentialRunner().run(pipeline, catalog)

    X_train = result["X_train"].load()
    assert list(X_train.columns) == model_options["features"]
    assert "unused_column" not in X_train.columns
    assert "price" not in X_train.columns
