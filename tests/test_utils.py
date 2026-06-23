from __future__ import annotations

from typing import TYPE_CHECKING

import click
import pytest

if TYPE_CHECKING:
    from pathlib import Path

from kedro_skills.utils import find_project_root


class TestFindProjectRoot:
    def test_returns_path_inside_project(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        assert find_project_root() == kedro_project

    def test_raises_outside_project(
        self, non_kedro_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(non_kedro_dir)
        with pytest.raises(click.UsageError, match="Not inside a Kedro project"):
            find_project_root()
