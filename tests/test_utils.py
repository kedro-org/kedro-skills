from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

from kedro_skills.utils import find_project_root


class TestFindProjectRoot:
    def test_returns_path_inside_project(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        assert find_project_root() == kedro_project

    def test_falls_back_to_cwd_outside_project(
        self,
        non_kedro_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(non_kedro_dir)
        assert find_project_root() == non_kedro_dir
        err = capsys.readouterr().err
        assert "Not inside a Kedro project" in err
        assert str(non_kedro_dir) in err
