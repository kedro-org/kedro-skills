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
        row = next(
            line for line in result.output.splitlines() if "catalog-config" in line
        )
        assert "not installed" not in row

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


class TestUninstallDrift:
    def test_drift_no_flags_prompts_and_defaults_to_keep(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No flags + drift → prompt, default 'keep' unmanages the file."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

        cursor_file = kedro_project / ".cursor/rules/catalog-config.mdc"
        cursor_file.write_text("user modified content", encoding="utf-8")

        result = runner.invoke(skills, ["uninstall", "catalog-config"], input="\n")
        assert result.exit_code == 0
        assert "modified" in result.output
        assert "Kept 1 modified file" in result.output
        assert cursor_file.is_file()

        from kedro_skills.state import read  # noqa: PLC0415

        installed = read(kedro_project)
        assert "catalog-config" not in installed.skills

    def test_drift_prompt_delete_removes_all(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Prompt answer 'delete' removes drifted files too."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

        cursor_file = kedro_project / ".cursor/rules/catalog-config.mdc"
        cursor_file.write_text("user modified content", encoding="utf-8")

        result = runner.invoke(
            skills, ["uninstall", "catalog-config"], input="delete\n"
        )
        assert result.exit_code == 0
        assert not cursor_file.is_file()

        from kedro_skills.state import read  # noqa: PLC0415

        installed = read(kedro_project)
        assert "catalog-config" not in installed.skills

    def test_keep_modified_flag(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--keep-modified skips prompt and unmanages drifted files."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

        cursor_file = kedro_project / ".cursor/rules/catalog-config.mdc"
        cursor_file.write_text("user modified content", encoding="utf-8")

        result = runner.invoke(
            skills, ["uninstall", "catalog-config", "--keep-modified"]
        )
        assert result.exit_code == 0
        assert "Kept 1 modified file" in result.output
        assert cursor_file.is_file()

        from kedro_skills.state import read  # noqa: PLC0415

        installed = read(kedro_project)
        assert "catalog-config" not in installed.skills

    def test_force_deletes_drifted_files(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force deletes all files including drifted ones."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

        cursor_file = kedro_project / ".cursor/rules/catalog-config.mdc"
        cursor_file.write_text("user modified content", encoding="utf-8")

        result = runner.invoke(skills, ["uninstall", "catalog-config", "--force"])
        assert result.exit_code == 0
        assert not cursor_file.is_file()

        from kedro_skills.state import read  # noqa: PLC0415

        installed = read(kedro_project)
        assert "catalog-config" not in installed.skills

    def test_force_and_keep_modified_mutually_exclusive(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        result = runner.invoke(
            skills, ["uninstall", "catalog-config", "--force", "--keep-modified"]
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_no_drift_does_not_prompt(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Clean uninstall never prompts."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

        result = runner.invoke(skills, ["uninstall", "catalog-config"])
        assert result.exit_code == 0
        assert "modified" not in result.output
        assert "Keep" not in result.output

    def test_reinstall_after_keep_modified_works(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After keep-modified, a fresh install succeeds without --force."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

        cursor_file = kedro_project / ".cursor/rules/catalog-config.mdc"
        cursor_file.write_text("user modified content", encoding="utf-8")

        runner.invoke(skills, ["uninstall", "catalog-config", "--keep-modified"])

        result = runner.invoke(skills, ["install", "catalog-config"], input="all\n")
        assert result.exit_code == 0
        assert "Installed" in result.output
        assert "refused" not in result.output.lower()

    def test_drift_does_not_delete_non_drifted_files(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without flags, no files are deleted when drift is detected."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

        cursor_file = kedro_project / ".cursor/rules/catalog-config.mdc"
        cursor_file.write_text("user modified content", encoding="utf-8")

        from kedro_skills.orchestrator import uninstall_skill  # noqa: PLC0415

        result = uninstall_skill("catalog-config", kedro_project)
        assert result.refused
        assert not result.written
        assert not result.kept

        assert (kedro_project / ".agents/skills/catalog-config/SKILL.md").is_file()
        assert (kedro_project / "AGENTS.md").is_file()
        assert (
            kedro_project / ".github/instructions/catalog-config.instructions.md"
        ).is_file()
        assert (kedro_project / ".claude/skills/catalog-config/SKILL.md").is_file()


class TestUninstallDriftEdgeCases:
    def test_keep_modified_no_drift_behaves_like_plain_uninstall(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--keep-modified with no drifted files is a normal uninstall."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

        from kedro_skills.orchestrator import uninstall_skill  # noqa: PLC0415

        result = uninstall_skill("catalog-config", kedro_project, keep_modified=True)
        assert result.written
        assert not result.kept
        assert not result.refused

        assert not (kedro_project / ".agents/skills/catalog-config/SKILL.md").is_file()
        assert not (kedro_project / ".cursor/rules/catalog-config.mdc").is_file()

    def test_agents_md_block_drift_keep_modified(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Drifted AGENTS.md block is kept with --keep-modified."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "catalog-config"], input="all\n")

        agents_md = kedro_project / "AGENTS.md"
        content = agents_md.read_text(encoding="utf-8")
        content = content.replace(
            "<!-- kedro-skills:catalog-config:end -->",
            "User edit inside block\n<!-- kedro-skills:catalog-config:end -->",
        )
        agents_md.write_text(content, encoding="utf-8")

        result = runner.invoke(
            skills, ["uninstall", "catalog-config", "--keep-modified"]
        )
        assert result.exit_code == 0
        assert agents_md.is_file()
        assert "Kept 1 modified file" in result.output
        assert not (kedro_project / ".cursor/rules/catalog-config.mdc").is_file()
        assert not (kedro_project / ".claude/skills/catalog-config/SKILL.md").is_file()
