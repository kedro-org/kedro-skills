from pathlib import Path

import pytest
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

from spaceflights.pipelines.data_science import pipeline as ds_pipeline_module
from spaceflights.pipelines.data_science.nodes import split_data

PROJECT_PATH = Path(__file__).resolve().parents[1]


def test_runtime_param_override_takes_effect(monkeypatch):
    calls = []

    def recording_split_data(data, parameters):
        calls.append({"n_rows": len(data), "parameters": dict(parameters)})
        return split_data(data, parameters)

    # The pipeline is built when session.run() resolves it, so patching the
    # name used by data_science/pipeline.py is picked up by the run.
    monkeypatch.setattr(ds_pipeline_module, "split_data", recording_split_data)

    bootstrap_project(PROJECT_PATH)
    with KedroSession.create(
        project_path=PROJECT_PATH,
        runtime_params={"model_options": {"test_size": 0.3}},
    ) as session:
        # Config view: the override is merged over conf/base (0.2).
        params = session.load_context().params
        assert params["model_options"]["test_size"] == 0.3
        # Sibling keys of the nested dict are preserved.
        assert params["model_options"]["random_state"] == 3

        output = session.run(pipeline_names=["data_processing", "data_science"])

    assert output is not None
    # Runtime view: the node actually received the overridden value.
    assert len(calls) == 1
    assert calls[0]["parameters"]["test_size"] == 0.3
    assert calls[0]["parameters"]["random_state"] == 3
