import pandas as pd
import pytest
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from spaceflights.pipelines.data_science import create_pipeline


@pytest.fixture
def model_input_table():
    return pd.DataFrame(
        {
            "engines": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "crew": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
            "passenger_capacity": [5, 6, 8, 7, 9, 11, 10, 12, 14, 13],
            "price": [120, 290, 30, 40, 50, 60, 170, 80, 210, 100],
        }
    )


@pytest.fixture
def model_options():
    return {
        "test_size": 0.3,
        "random_state": 3,
        "features": ["engines", "passenger_capacity", "crew"],
    }


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
