"""Integration tests for the full install/update/uninstall lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from kedro_skills.cli import skills

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class TestInstallLifecycle:
    """Full install → list → idempotent → update → uninstall cycle."""

    def test_install_creates_all_files(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        result = runner.invoke(skills, ["install", "catalog-config"])
        assert result.exit_code == 0, result.output
        assert "Installed" in result.output or "install" in result.output.lower()

        assert (kedro_project / ".agents/skills/catalog-config/SKILL.md").is_file()
        assert (kedro_project / "AGENTS.md").is_file()
        assert (kedro_project / ".cursor/rules/catalog-config.mdc").is_file()
        assert (
            kedro_project / ".github/instructions/catalog-config.instructions.md"
        ).is_file()
        assert (kedro_project / ".claude/skills/catalog-config/SKILL.md").is_file()
        assert (kedro_project / ".agents/skills/.installed.json").is_file()

    def test_list_shows_installed(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"])

        result = runner.invoke(skills, ["list"])
        assert result.exit_code == 0
        assert "catalog-config" in result.output
        assert "not installed" not in result.output

    def test_install_is_idempotent(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"])
        result = runner.invoke(skills, ["install", "catalog-config"])
        assert result.exit_code == 0
        assert "refused" not in result.output.lower()

    def test_update_refuses_drifted_file(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"])

        cursor_rule = kedro_project / ".cursor/rules/catalog-config.mdc"
        cursor_rule.write_text("user edited content\n", encoding="utf-8")

        result = runner.invoke(skills, ["update"])
        assert result.exit_code == 0
        assert ".cursor/rules/catalog-config.mdc" in result.output
        assert "refused" in result.output.lower() or "--force" in result.output

    def test_update_force_overrides_drift(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"])

        cursor_rule = kedro_project / ".cursor/rules/catalog-config.mdc"
        cursor_rule.write_text("user edited content\n", encoding="utf-8")

        result = runner.invoke(skills, ["update", "--force"])
        assert result.exit_code == 0
        assert "refused" not in result.output.lower()

    def test_agents_md_user_edits_outside_markers_no_drift(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"])

        agents_md = kedro_project / "AGENTS.md"
        content = agents_md.read_text(encoding="utf-8")
        content += "\n## My custom section\n\nUser notes here.\n"
        agents_md.write_text(content, encoding="utf-8")

        result = runner.invoke(skills, ["update"])
        assert result.exit_code == 0
        assert "refused" not in result.output.lower()
        assert "--force" not in result.output

    def test_uninstall_removes_all_managed_files(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"])
        result = runner.invoke(skills, ["uninstall", "catalog-config"])
        assert result.exit_code == 0

        assert not (kedro_project / ".agents/skills/catalog-config/SKILL.md").is_file()
        assert not (kedro_project / "AGENTS.md").is_file()
        assert not (kedro_project / ".cursor/rules/catalog-config.mdc").is_file()
        assert not (
            kedro_project / ".github/instructions/catalog-config.instructions.md"
        ).is_file()
        assert not (kedro_project / ".claude/skills/catalog-config/SKILL.md").is_file()
        assert not (kedro_project / ".agents/skills/.installed.json").is_file()

    def test_list_shows_not_installed_after_uninstall(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"])
        runner.invoke(skills, ["uninstall", "catalog-config"])

        result = runner.invoke(skills, ["list"])
        assert result.exit_code == 0
        assert "not installed" in result.output

    def test_install_all(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        result = runner.invoke(skills, ["install", "--all"])
        assert result.exit_code == 0
        assert (kedro_project / ".agents/skills/catalog-config/SKILL.md").is_file()


class TestErrorHandling:
    def test_install_outside_kedro_project(
        self, non_kedro_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(non_kedro_dir)
        runner = CliRunner()
        result = runner.invoke(skills, ["install", "catalog-config"])
        assert result.exit_code != 0
        assert "Not inside a Kedro project" in result.output

    def test_uninstall_not_installed(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        result = runner.invoke(skills, ["uninstall", "catalog-config"])
        assert result.exit_code != 0
        assert "not installed" in result.output.lower()

    def test_install_unknown_skill(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        result = runner.invoke(skills, ["install", "nonexistent-skill"])
        assert result.exit_code != 0
        assert "Unknown skill" in result.output or "nonexistent-skill" in result.output
