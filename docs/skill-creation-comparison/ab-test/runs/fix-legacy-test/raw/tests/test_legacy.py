from pathlib import Path

import pandas as pd
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner

from spaceflights.pipelines.data_science import create_pipeline


def test_project_runs():
    project_path = Path(__file__).resolve().parents[1]
    bootstrap_project(project_path)
    with KedroSession.create(project_path=project_path) as session:
        session.run(pipeline_names=["data_processing"])


def test_data_science_metrics_are_reasonable():
    data = pd.DataFrame(
        {
            "engines": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "crew": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
            "passenger_capacity": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
            "price": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        }
    )
    catalog = DataCatalog(
        {
            "model_input_table": MemoryDataset(data),
            "params:model_options": MemoryDataset(
                {"test_size": 0.2, "random_state": 3,
                 "features": ["engines", "passenger_capacity", "crew"]}
            ),
        }
    )
    result = SequentialRunner().run(create_pipeline(), catalog)
    assert result["metrics"].load()["mae"] < 1
