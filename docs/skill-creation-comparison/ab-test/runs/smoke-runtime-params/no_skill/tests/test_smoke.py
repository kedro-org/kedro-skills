"""Smoke test: run data_processing + data_science through a KedroSession with a
runtime override of ``model_options.test_size`` and check the override is used."""
import math
from pathlib import Path

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

from spaceflights.pipelines.data_science import nodes as ds_nodes

PROJECT_PATH = Path(__file__).resolve().parents[1]


def test_runtime_override_of_test_size(monkeypatch):
    bootstrap_project(PROJECT_PATH)

    calls = []
    real_split = ds_nodes.train_test_split

    def spy(X, y, **kwargs):
        result = real_split(X, y, **kwargs)
        calls.append({"kwargs": kwargs, "n_total": len(X), "n_test": len(result[1])})
        return result

    monkeypatch.setattr(ds_nodes, "train_test_split", spy)

    with KedroSession.create(
        project_path=PROJECT_PATH,
        runtime_params={"model_options": {"test_size": 0.3}},
    ) as session:
        params = session.load_context().params["model_options"]
        assert params["test_size"] == 0.3
        assert params["random_state"] == 3  # sibling keys are preserved

        session.run(pipeline_names=["data_processing", "data_science"])

    # The node received the override, not the 0.2 from parameters.yml.
    assert len(calls) == 1
    call = calls[0]
    assert call["kwargs"]["test_size"] == 0.3
    # And the resulting split is really ~30% (sklearn uses ceil for test size).
    assert call["n_test"] == math.ceil(0.3 * call["n_total"])
