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
        assert "catalog-config" in result.output
        assert "not installed" in result.output

    def test_list_outside_kedro_project(
        self, non_kedro_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(non_kedro_dir)
        result = CliRunner().invoke(skills, ["list"])
        assert result.exit_code != 0
        assert "Not inside a Kedro project" in result.output


class TestInstallOutput:
    """Verify interactive prompt vs non-interactive install."""

    def test_bare_install_prompts_and_accepts_all(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(
            skills, ["install", "catalog-config"], input="all\n"
        )
        assert result.exit_code == 0
        assert "5 files" in result.output

    def test_bare_install_prompts_and_selects_one(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(
            skills, ["install", "catalog-config"], input="cursor\n"
        )
        assert result.exit_code == 0
        assert "3 files" in result.output

    def test_install_with_ide_flag_skips_prompt(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(
            skills, ["install", "catalog-config", "--ide", "cursor"]
        )
        assert result.exit_code == 0
        assert "3 files" in result.output
        assert "Available IDEs" not in result.output

    def test_install_all_skips_prompt(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(skills, ["install", "--all"])
        assert result.exit_code == 0
        assert "5 files" in result.output
        assert "Available IDEs" not in result.output
