from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

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


class TestTelemetryEvents:
    """The install/update/uninstall commands report anonymous usage events."""

    def test_install_sends_event(
        self,
        kedro_project: Path,
        monkeypatch: pytest.MonkeyPatch,
        sent_events: list[tuple[str, dict[str, Any]]],
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(
            skills, ["install", "catalog-config", "--ide", "cursor"]
        )
        assert result.exit_code == 0
        assert sent_events == [
            (
                "kedro_skills_install",
                {
                    "skill_id": "catalog-config",
                    "target_ides": "cursor",
                    "install_all": False,
                    "success": True,
                },
            )
        ]

    def test_install_all_sends_event_per_skill(
        self,
        kedro_project: Path,
        monkeypatch: pytest.MonkeyPatch,
        sent_events: list[tuple[str, dict[str, Any]]],
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(skills, ["install", "--all"])
        assert result.exit_code == 0
        assert len(sent_events) >= 1
        assert all(name == "kedro_skills_install" for name, _ in sent_events)
        assert all(props["install_all"] is True for _, props in sent_events)
        assert any(props["skill_id"] == "catalog-config" for _, props in sent_events)

    def test_install_unknown_skill_masks_id(
        self,
        kedro_project: Path,
        monkeypatch: pytest.MonkeyPatch,
        sent_events: list[tuple[str, dict[str, Any]]],
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(
            skills, ["install", "no-such-skill", "--ide", "cursor"]
        )
        assert result.exit_code != 0
        assert sent_events == [
            (
                "kedro_skills_install",
                {"skill_id": "unknown", "install_all": False, "success": False},
            )
        ]

    def test_update_sends_summary_event(
        self,
        kedro_project: Path,
        monkeypatch: pytest.MonkeyPatch,
        sent_events: list[tuple[str, dict[str, Any]]],
    ) -> None:
        monkeypatch.chdir(kedro_project)
        CliRunner().invoke(skills, ["install", "catalog-config", "--ide", "cursor"])
        sent_events.clear()

        result = CliRunner().invoke(skills, ["update"])
        assert result.exit_code == 0
        assert sent_events == [
            (
                "kedro_skills_update",
                {"skills_updated": 1, "drift_detected": False, "success": True},
            )
        ]

    def test_update_with_nothing_installed(
        self,
        kedro_project: Path,
        monkeypatch: pytest.MonkeyPatch,
        sent_events: list[tuple[str, dict[str, Any]]],
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(skills, ["update"])
        assert result.exit_code == 0
        assert sent_events == [
            (
                "kedro_skills_update",
                {"skills_updated": 0, "drift_detected": False, "success": True},
            )
        ]

    def test_uninstall_sends_event(
        self,
        kedro_project: Path,
        monkeypatch: pytest.MonkeyPatch,
        sent_events: list[tuple[str, dict[str, Any]]],
    ) -> None:
        monkeypatch.chdir(kedro_project)
        CliRunner().invoke(skills, ["install", "catalog-config", "--ide", "cursor"])
        sent_events.clear()

        result = CliRunner().invoke(skills, ["uninstall", "catalog-config"])
        assert result.exit_code == 0
        assert sent_events == [
            ("kedro_skills_uninstall", {"skill_id": "catalog-config"})
        ]

    def test_list_sends_no_event(
        self,
        kedro_project: Path,
        monkeypatch: pytest.MonkeyPatch,
        sent_events: list[tuple[str, dict[str, Any]]],
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(skills, ["list"])
        assert result.exit_code == 0
        assert sent_events == []

    def test_install_works_without_kedro_telemetry(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        monkeypatch.setitem(sys.modules, "kedro_telemetry", None)
        monkeypatch.setitem(sys.modules, "kedro_telemetry.api", None)
        result = CliRunner().invoke(
            skills, ["install", "catalog-config", "--ide", "cursor"]
        )
        assert result.exit_code == 0
