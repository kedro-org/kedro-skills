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
        result = runner.invoke(skills, ["install", "catalog-config"], input="all\n")
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
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

        result = runner.invoke(skills, ["list"])
        assert result.exit_code == 0
        assert "catalog-config" in result.output
        # The catalog-config line should show as installed (✓), even though
        # other skills in the registry may still be "not installed".
        for line in result.output.splitlines():
            if "catalog-config" in line:
                assert "✓" in line
                assert "not installed" not in line

    def test_install_is_idempotent(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")
        result = runner.invoke(skills, ["install", "catalog-config"], input="all\n")
        assert result.exit_code == 0
        assert "refused" not in result.output.lower()

    def test_update_refuses_drifted_file(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

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
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

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
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

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
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")
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
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")
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

        from kedro_skills.registry import load_registry  # noqa: PLC0415

        for skill in load_registry():
            assert (kedro_project / ".agents/skills" / skill.id / "SKILL.md").is_file()


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


class TestUpdatePreservesIdes:
    def test_update_does_not_expand_ides(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Update should re-install only the originally selected IDEs."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config", "--ide", "cursor"])

        assert (kedro_project / ".cursor/rules/catalog-config.mdc").is_file()
        assert not (
            kedro_project / ".github/instructions/catalog-config.instructions.md"
        ).is_file()

        result = runner.invoke(skills, ["update"])
        assert result.exit_code == 0

        assert (kedro_project / ".cursor/rules/catalog-config.mdc").is_file()
        assert not (
            kedro_project / ".github/instructions/catalog-config.instructions.md"
        ).is_file()
        assert not (kedro_project / ".claude/skills/catalog-config/SKILL.md").is_file()


class TestPartialUninstall:
    def test_uninstall_drift_keeps_skill_in_state(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If files are drifted and --force is not used, skill stays in state."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

        cursor_file = kedro_project / ".cursor/rules/catalog-config.mdc"
        cursor_file.write_text("user modified content", encoding="utf-8")

        result = runner.invoke(skills, ["uninstall", "catalog-config"])
        assert result.exit_code == 0
        assert "refused" in result.output or "modified" in result.output

        from kedro_skills.state import read  # noqa: PLC0415

        installed = read(kedro_project)
        assert "catalog-config" in installed.skills


class TestParametersAndConfigSkill:
    """Install/uninstall lifecycle for the parameters-and-config skill."""

    def test_install_creates_all_files(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        result = runner.invoke(
            skills, ["install", "parameters-and-config"], input="all\n"
        )
        assert result.exit_code == 0, result.output

        assert (
            kedro_project / ".agents/skills/parameters-and-config/SKILL.md"
        ).is_file()
        assert (kedro_project / "AGENTS.md").is_file()
        assert (kedro_project / ".cursor/rules/parameters-and-config.mdc").is_file()
        assert (
            kedro_project / ".github/instructions/parameters-and-config.instructions.md"
        ).is_file()
        assert (
            kedro_project / ".claude/skills/parameters-and-config/SKILL.md"
        ).is_file()

    def test_uninstall_removes_all_files(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "parameters-and-config"], input="all\n")
        result = runner.invoke(skills, ["uninstall", "parameters-and-config"])
        assert result.exit_code == 0

        assert not (
            kedro_project / ".agents/skills/parameters-and-config/SKILL.md"
        ).is_file()
        assert not (kedro_project / ".cursor/rules/parameters-and-config.mdc").is_file()
        assert not (
            kedro_project / ".github/instructions/parameters-and-config.instructions.md"
        ).is_file()
        assert not (
            kedro_project / ".claude/skills/parameters-and-config/SKILL.md"
        ).is_file()

    def test_both_skills_coexist_in_agents_md(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Both skills can be installed and each gets its own AGENTS.md block."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")
        runner.invoke(skills, ["install", "parameters-and-config"], input="all\n")

        agents_md = (kedro_project / "AGENTS.md").read_text(encoding="utf-8")
        assert "<!-- kedro-skills:catalog-config:start -->" in agents_md
        assert "<!-- kedro-skills:catalog-config:end -->" in agents_md
        assert "<!-- kedro-skills:parameters-and-config:start -->" in agents_md
        assert "<!-- kedro-skills:parameters-and-config:end -->" in agents_md

    def test_install_all_includes_both_skills(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        result = runner.invoke(skills, ["install", "--all"])
        assert result.exit_code == 0
        assert (kedro_project / ".agents/skills/catalog-config/SKILL.md").is_file()
        assert (
            kedro_project / ".agents/skills/parameters-and-config/SKILL.md"
        ).is_file()

    def test_uninstall_one_preserves_other(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Uninstalling one skill does not remove the other's files."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "--all"])
        runner.invoke(skills, ["uninstall", "parameters-and-config"])

        # catalog-config files still present
        assert (kedro_project / ".agents/skills/catalog-config/SKILL.md").is_file()
        assert (kedro_project / ".cursor/rules/catalog-config.mdc").is_file()
        # AGENTS.md still exists with catalog-config block
        agents_md = (kedro_project / "AGENTS.md").read_text(encoding="utf-8")
        assert "<!-- kedro-skills:catalog-config:start -->" in agents_md
        assert "parameters-and-config" not in agents_md
