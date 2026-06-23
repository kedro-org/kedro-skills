from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

from kedro_skills.cli import skills


class TestSkillsHelp:
    def test_help_shows_group(self) -> None:
        result = CliRunner().invoke(skills, ["--help"])
        assert result.exit_code == 0
        assert "Distribute AI coding skills" in result.output

    def test_help_lists_commands(self) -> None:
        result = CliRunner().invoke(skills, ["--help"])
        assert "list" in result.output


class TestSkillsList:
    def test_list_inside_kedro_project(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(skills, ["list"])
        assert result.exit_code == 0
        assert "No skills installed." in result.output

    def test_list_outside_kedro_project(
        self, non_kedro_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(non_kedro_dir)
        result = CliRunner().invoke(skills, ["list"])
        assert result.exit_code != 0
        assert "Not inside a Kedro project" in result.output
