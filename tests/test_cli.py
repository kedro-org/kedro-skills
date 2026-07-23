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
    """Verify verbose vs concise install output."""

    def test_bare_install_shows_file_list_and_tip(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(skills, ["install", "catalog-config"])
        assert result.exit_code == 0
        assert ".agents/skills/catalog-config/SKILL.md" in result.output
        assert "AGENTS.md" in result.output
        assert ".cursor/rules/catalog-config.mdc" in result.output
        assert "--ide" in result.output

    def test_install_with_ide_flag_is_concise(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(
            skills, ["install", "catalog-config", "--ide", "cursor"]
        )
        assert result.exit_code == 0
        assert "3 files" in result.output
        assert "--ide" not in result.output

    def test_install_all_is_concise(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(skills, ["install", "--all"])
        assert result.exit_code == 0
        assert "5 files" in result.output
        assert "--ide" not in result.output
