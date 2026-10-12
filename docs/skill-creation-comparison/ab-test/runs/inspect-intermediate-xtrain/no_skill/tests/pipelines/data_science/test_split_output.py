import pandas as pd
import pytest
from kedro.framework.hooks import _create_hook_manager
from kedro.framework.hooks.markers import hook_impl
from kedro.io import DataCatalog
from kedro.runner import SequentialRunner
from spaceflights.pipelines.data_science import create_pipeline as create_ds_pipeline


class CaptureOutputs:
    """Hook that records the outputs of selected nodes, because the runner
    releases intermediate datasets such as X_train once they are consumed."""

    def __init__(self):
        self.outputs = {}

    @hook_impl
    def after_node_run(self, node, outputs):
        if node.name == "split_data_node":
            self.outputs.update(outputs)


@pytest.fixture
def model_options():
    return {
        "test_size": 0.2,
        "random_state": 3,
        "features": ["engines", "passenger_capacity", "crew"],
    }


@pytest.fixture
def model_input_table():
    # Extra columns that must NOT end up in X_train.
    return pd.DataFrame(
        {
            "engines": [1, 2, 3, 4, 5],
            "crew": [4, 5, 6, 7, 8],
            "passenger_capacity": [5, 6, 7, 8, 9],
            "company_rating": [0.1, 0.2, 0.3, 0.4, 0.5],
            "price": [120, 290, 30, 60, 90],
        }
    )


def test_x_train_only_contains_model_option_features(model_input_table, model_options):
    catalog = DataCatalog()
    catalog["model_input_table"] = model_input_table
    catalog["params:model_options"] = model_options

    capture = CaptureOutputs()
    hook_manager = _create_hook_manager()
    hook_manager.register(capture)

    SequentialRunner().run(create_ds_pipeline(), catalog, hook_manager=hook_manager)

    X_train = capture.outputs["X_train"]
    assert list(X_train.columns) == model_options["features"]
    assert "price" not in X_train.columns
    assert "company_rating" not in X_train.columns
