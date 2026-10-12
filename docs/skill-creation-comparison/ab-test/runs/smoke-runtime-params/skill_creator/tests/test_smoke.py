from pathlib import Path

import pytest
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

from spaceflights.pipelines.data_science import pipeline as ds_pipeline_module
from spaceflights.pipelines.data_science.nodes import split_data

PROJECT_PATH = Path(__file__).resolve().parents[1]


@pytest.fixture
def split_spy(monkeypatch):
    """Record the params and split sizes the real split_data node sees."""
    calls = []

    def spy(data, parameters):
        result = split_data(data, parameters)
        calls.append(
            {
                "params": dict(parameters),
                "n_rows": len(data),
                "n_test": len(result[1]),
            }
        )
        return result

    monkeypatch.setattr(ds_pipeline_module, "split_data", spy)
    return calls


def test_runtime_param_override_reaches_data_science(split_spy):
    bootstrap_project(PROJECT_PATH)
    with KedroSession.create(
        project_path=PROJECT_PATH,
        runtime_params={"model_options": {"test_size": 0.3}},
    ) as session:
        # Nested dict: a dotted key would be stored as a literal key.
        params = session.load_context().params["model_options"]
        assert params["test_size"] == 0.3
        # Other keys from conf/base are still present after the merge.
        assert params["random_state"] == 3
        assert "features" in params

        result = session.run(pipeline_names=["data_processing", "data_science"])

    assert "metrics" in result

    # The node actually received the override, not just the context.
    assert len(split_spy) == 1
    call = split_spy[0]
    assert call["params"]["test_size"] == 0.3
    # sklearn rounds the test set up: ceil(0.3 * n_rows), not ceil(0.2 * n_rows).
    n = call["n_rows"]
    assert call["n_test"] == -(-3 * n // 10)
    assert call["n_test"] != -(-n // 5)
