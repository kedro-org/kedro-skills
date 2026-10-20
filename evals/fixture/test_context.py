"""Tests for the promptfoo var loader. Run with: pytest evals/fixture/test_context.py"""

from pathlib import Path

import pytest

import context


@pytest.fixture
def overlay(tmp_path: Path) -> Path:
    (tmp_path / "conf/local").mkdir(parents=True)
    (tmp_path / "conf/local/parameters.yml").write_text("model_options:\n  test_size: 0.3\n")
    (tmp_path / "conf/base").mkdir(parents=True)
    (tmp_path / "conf/base/catalog.yml").write_text("metrics:\n  type: json.JSONDataset\n")
    (tmp_path / "conf/local/credentials.yml.deleted").write_text("")
    return tmp_path


def test_without_overlay_reads_the_snapshot():
    out = context.build_context(["conf/base/catalog.yml"])
    assert out.startswith("### conf/base/catalog.yml\n```\n")
    assert "companies:" in out


def test_overlay_replaces_and_adds_files(overlay):
    out = context.build_context(["conf/base/catalog.yml", "conf/local/parameters.yml"], overlay)
    assert "json.JSONDataset" in out
    assert "companies:" not in out
    assert "test_size: 0.3" in out


def test_overlay_falls_back_to_the_snapshot(overlay):
    out = context.build_context(["conf/base/parameters_data_science.yml"], overlay)
    assert "model_options" in out


def test_deleted_marker_hides_a_file(overlay):
    with pytest.raises(FileNotFoundError, match="deleted"):
        context.build_context(["conf/local/credentials.yml"], overlay)
    tree = context.project_tree(overlay)
    assert "conf/local/credentials.yml" not in tree
    assert "conf/local/credentials.yml.deleted" not in tree
    assert "conf/local/parameters.yml" in tree


def test_tree_comes_first(overlay):
    out = context.build_context(["conf/base/catalog.yml"], overlay, tree=True)
    assert out.startswith("### Files in the project\n```\n")
    assert "src/eval_project/pipeline_registry.py" in out.split("### conf/base")[0]


def test_paths_outside_the_project_are_rejected(overlay):
    with pytest.raises(ValueError):
        context.build_context(["../context.py"])
    with pytest.raises(ValueError):
        context.build_context(["../../outside.txt"], overlay)


def test_get_var_reports_errors():
    missing = context.get_var("project_context", "", {"project_files": "nope.yml"})
    assert "error" in missing
    bad_overlay = context.get_var(
        "project_context", "", {"project_files": "", "fixture_overlay": "skills/does-not-exist"}
    )
    assert "Overlay not found" in bad_overlay["error"]


def test_get_var_with_overlay_and_tree():
    out = context.get_var(
        "project_context",
        "",
        {"project_files": "conf/base/catalog.yml", "fixture_overlay": "fixture/project", "project_tree": "yes"},
    )
    assert out["output"].startswith("### Files in the project")
