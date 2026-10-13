"""Verification of testing-pipelines skill claims against Kedro 1.7.0.

Each test is named after the fact number in facts.md.
"""
import logging
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from kedro.config import MissingConfigException
from kedro.framework.context import KedroContext
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.io import DataCatalog, DatasetError, MemoryDataset
from kedro.pipeline import Node, Pipeline
from kedro.runner import SequentialRunner

from spaceflights.pipelines.data_processing import create_pipeline as dp_pipeline
from spaceflights.pipelines.data_processing.nodes import preprocess_companies
from spaceflights.pipelines.data_science import create_pipeline as ds_pipeline

PROJECT = Path(__file__).resolve().parents[2]


def _ds_inputs():
    df = pd.DataFrame(
        {
            "engines": [1, 2, 3, 4, 5],
            "crew": [4, 5, 6, 7, 8],
            "passenger_capacity": [5, 6, 7, 8, 9],
            "price": [120, 290, 30, 40, 50],
        }
    )
    params = {
        "test_size": 0.2,
        "random_state": 3,
        "features": ["engines", "passenger_capacity", "crew"],
    }
    return df, params


# 1 -------------------------------------------------------------------------
def test_f01_context_has_no_run():
    assert not hasattr(KedroContext, "run")


# 2 -------------------------------------------------------------------------
def test_f02_session_without_bootstrap_fails():
    code = (
        "from pathlib import Path\n"
        "from kedro.framework.session import KedroSession\n"
        f"with KedroSession.create(project_path=Path({str(PROJECT)!r})) as s:\n"
        "    s.run()\n"
    )
    r = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT, capture_output=True, text=True
    )
    print(r.stderr[-1500:])
    assert r.returncode != 0


# 3 -------------------------------------------------------------------------
@pytest.mark.parametrize(
    "stmt",
    [
        "from kedro.runner import KedroSession",
        "from kedro.io import KedroSession",
        "from kedro.framework.context import load_context",
    ],
)
def test_f03_wrong_imports_fail(stmt):
    with pytest.raises(ImportError):
        exec(stmt, {})


# 4 -------------------------------------------------------------------------
def test_f04_no_kedro_pytest_fixtures():
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "--fixtures", "-p", "no:cacheprovider",
         "-o", "addopts=", str(Path(__file__))],
        cwd=PROJECT, capture_output=True, text=True,
    )
    out = r.stdout
    for name in ("kedro_session", "kedro_context", "catalog ", "pipeline "):
        assert f"\n{name}" not in out, name


# 5 -------------------------------------------------------------------------
def test_f05_node_function_called_directly():
    companies = pd.DataFrame(
        {"id": [1], "iata_approved": ["t"], "company_rating": ["90%"]}
    )
    out = preprocess_companies(companies)
    assert out["iata_approved"].tolist() == [True]
    assert out["company_rating"].tolist() == [0.9]


# 6 -------------------------------------------------------------------------
def test_f06_runner_returns_datasets_not_data():
    df, params = _ds_inputs()
    catalog = DataCatalog(
        {"model_input_table": MemoryDataset(df),
         "params:model_options": MemoryDataset(params)}
    )
    result = SequentialRunner().run(ds_pipeline(), catalog)
    assert set(result) == {"metrics"}
    assert isinstance(result["metrics"], MemoryDataset)
    metrics = result["metrics"].load()
    assert set(metrics) == {"r2_score", "mae", "max_error"}
    # catalog.load works too for pipeline outputs
    assert catalog.load("metrics") == metrics
    # intermediates are RELEASED after their last consumer: not loadable
    with pytest.raises(DatasetError, match="has not been saved yet"):
        catalog.load("X_train")
    # free inputs are kept
    assert catalog.load("model_input_table").equals(df)


def test_f06d_slice_to_inspect_intermediate():
    df, params = _ds_inputs()
    catalog = DataCatalog()
    catalog["model_input_table"] = df
    catalog["params:model_options"] = params
    result = SequentialRunner().run(ds_pipeline().to_outputs("X_train"), catalog)
    assert len(result["X_train"].load()) == 4


def test_f06b_setitem_wraps_raw_data():
    df, params = _ds_inputs()
    catalog = DataCatalog()
    catalog["model_input_table"] = df
    catalog["params:model_options"] = params
    assert isinstance(catalog["model_input_table"], MemoryDataset)
    SequentialRunner().run(ds_pipeline(), catalog)


# 7 -------------------------------------------------------------------------
def test_f07_missing_free_input_raises_valueerror():
    df, _ = _ds_inputs()
    catalog = DataCatalog({"model_input_table": MemoryDataset(df)})
    with pytest.raises(ValueError, match="params:model_options"):
        SequentialRunner().run(ds_pipeline(), catalog)


# 8 -------------------------------------------------------------------------
def test_f08_params_registered_by_literal_name():
    df, params = _ds_inputs()
    catalog = DataCatalog({"model_input_table": MemoryDataset(df),
                           "model_options": MemoryDataset(params)})
    with pytest.raises(ValueError):
        SequentialRunner().run(ds_pipeline(), catalog)


# 9 -------------------------------------------------------------------------
def test_f09_slicing():
    p = ds_pipeline()
    assert {n.name for n in p.only_nodes("split_data_node").nodes} == {"split_data_node"}
    assert p.from_inputs("X_train").inputs() >= {"X_train"}
    assert {n.name for n in p.to_outputs("regressor").nodes} == {
        "split_data_node", "train_model_node"}
    sliced = p.from_nodes("train_model_node").to_nodes("evaluate_model_node")
    assert sliced.inputs() == {"X_train", "y_train", "X_test", "y_test"}
    tagged = Pipeline([Node(lambda x: x, "a", "b", name="n", tags="t")])
    assert len(tagged.only_nodes_with_tags("t").nodes) == 1


def test_f09b_free_inputs_of_slice():
    # dp pipeline free inputs: what the catalog must provide
    assert dp_pipeline().inputs() == {"companies", "shuttles", "reviews"}


# 10 ------------------------------------------------------------------------
def test_f10_session_env_and_runtime_params(tmp_path):
    bootstrap_project(PROJECT)
    # nested dict works and keeps sibling keys
    with KedroSession.create(
        project_path=PROJECT,
        runtime_params={"model_options": {"test_size": 0.5}},
    ) as session:
        mo = session.load_context().params["model_options"]
        assert mo["test_size"] == 0.5 and "random_state" in mo
    # dotted keys are NOT expanded via the Python API (only the CLI parses them)
    with KedroSession.create(
        project_path=PROJECT, runtime_params={"model_options.test_size": 0.5}
    ) as session:
        params = session.load_context().params
        assert params["model_options"]["test_size"] == 0.2
        assert "model_options.test_size" in params
    # a non-existent env is accepted by create() and load_context(), but it does
    # NOT fall back to base: parameters come back empty (with a UserWarning) and
    # the catalog, and so session.run(), raise MissingConfigException.
    # (The first version of this test stopped at load_context() and so "proved"
    # a silent fallback to base that does not happen.)
    with KedroSession.create(project_path=PROJECT, env="does_not_exist") as s:
        with pytest.warns(UserWarning, match="Parameters not found"):
            ctx = s.load_context()
            assert ctx.params == {}
    with KedroSession.create(project_path=PROJECT, env="does_not_exist") as s:
        with pytest.raises(MissingConfigException, match="does not exist"):
            s.run(pipeline_names=["data_processing"])


def test_f10c_env_params_replace_top_level_key(tmp_path):
    test_env = PROJECT / "conf" / "test"
    test_env.mkdir()
    try:
        (test_env / "parameters.yml").write_text("model_options:\n  test_size: 0.4\n")
        bootstrap_project(PROJECT)
        with KedroSession.create(project_path=PROJECT, env="test") as s:
            assert s.load_context().params["model_options"] == {"test_size": 0.4}
    finally:
        (test_env / "parameters.yml").unlink()
        test_env.rmdir()


def test_f10b_session_runs_once_and_returns_datasets():
    bootstrap_project(PROJECT)
    with KedroSession.create(project_path=PROJECT) as session:
        result = session.run(pipeline_names=["data_processing"])
        assert isinstance(result, dict)
        print({k: type(v).__name__ for k, v in result.items()})
        with pytest.raises(Exception, match="already been completed"):
            session.run(pipeline_names=["data_processing"])


# 12 ------------------------------------------------------------------------
def test_f12_kedrodatacatalog_gone():
    with pytest.raises(ImportError):
        exec("from kedro.io import KedroDataCatalog", {})


def test_f12b_memorydataset_copies_dataframes():
    df = pd.DataFrame({"a": [1]})
    ds = MemoryDataset(df)
    loaded = ds.load()
    loaded.loc[0, "a"] = 99
    assert ds.load().loc[0, "a"] == 1


def test_f12c_runner_logs_success(caplog):
    df, params = _ds_inputs()
    catalog = DataCatalog()
    catalog["model_input_table"] = df
    catalog["params:model_options"] = params
    caplog.set_level(logging.INFO, logger="kedro")
    SequentialRunner().run(ds_pipeline(), catalog)
    assert "Pipeline execution completed successfully" in caplog.text
