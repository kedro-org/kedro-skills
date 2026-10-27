"""Integration tests for the full install/update/uninstall lifecycle."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from kedro_skills import installer, orchestrator
from kedro_skills.cli import skills
from kedro_skills.registry import RENAMED_SKILL_IDS, get_skill
from kedro_skills.state import read

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(params=["kedro_project", "non_kedro_dir"])
def install_dir(request: pytest.FixtureRequest) -> Path:
    """Run the test both inside a Kedro project and in a plain directory."""
    path: Path = request.getfixturevalue(request.param)
    return path


class TestInstallLifecycle:
    """Full install → list → idempotent → update → uninstall cycle."""

    def test_install_creates_all_files(
        self, install_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(install_dir)
        runner = CliRunner()
        result = runner.invoke(
            skills, ["install", "kedro-catalog-config"], input="all\n"
        )
        assert result.exit_code == 0, result.output
        assert "Installed" in result.output or "install" in result.output.lower()

        assert (install_dir / ".agents/skills/kedro-catalog-config/SKILL.md").is_file()
        assert (install_dir / "AGENTS.md").is_file()
        assert (install_dir / ".cursor/rules/kedro-catalog-config.mdc").is_file()
        assert (
            install_dir / ".github/instructions/kedro-catalog-config.instructions.md"
        ).is_file()
        assert (install_dir / ".claude/skills/kedro-catalog-config/SKILL.md").is_file()
        assert (install_dir / ".agents/skills/.installed.json").is_file()

    def test_list_shows_installed(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "kedro-catalog-config"], input="all\n")

        result = runner.invoke(skills, ["list"])
        assert result.exit_code == 0
        assert "kedro-catalog-config" in result.output
        # The kedro-catalog-config line should show as installed (✓), even though
        # other skills in the registry may still be "not installed".
        for line in result.output.splitlines():
            if "kedro-catalog-config" in line:
                assert "✓" in line
                assert "not installed" not in line

    def test_install_is_idempotent(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "kedro-catalog-config"], input="all\n")
        result = runner.invoke(
            skills, ["install", "kedro-catalog-config"], input="all\n"
        )
        assert result.exit_code == 0
        assert "refused" not in result.output.lower()

    def test_update_refuses_drifted_file(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "kedro-catalog-config"], input="all\n")

        cursor_rule = kedro_project / ".cursor/rules/kedro-catalog-config.mdc"
        cursor_rule.write_text("user edited content\n", encoding="utf-8")

        result = runner.invoke(skills, ["update"])
        assert result.exit_code == 0
        assert ".cursor/rules/kedro-catalog-config.mdc" in result.output
        assert "refused" in result.output.lower() or "--force" in result.output

    def test_update_force_overrides_drift(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "kedro-catalog-config"], input="all\n")

        cursor_rule = kedro_project / ".cursor/rules/kedro-catalog-config.mdc"
        cursor_rule.write_text("user edited content\n", encoding="utf-8")

        result = runner.invoke(skills, ["update", "--force"])
        assert result.exit_code == 0
        assert "refused" not in result.output.lower()

    def test_agents_md_user_edits_outside_markers_no_drift(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "kedro-catalog-config"], input="all\n")

        agents_md = kedro_project / "AGENTS.md"
        content = agents_md.read_text(encoding="utf-8")
        content += "\n## My custom section\n\nUser notes here.\n"
        agents_md.write_text(content, encoding="utf-8")

        result = runner.invoke(skills, ["update"])
        assert result.exit_code == 0
        assert "refused" not in result.output.lower()
        assert "--force" not in result.output

    def test_uninstall_removes_all_managed_files(
        self, install_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(install_dir)
        runner = CliRunner()
        runner.invoke(skills, ["install", "kedro-catalog-config"], input="all\n")
        result = runner.invoke(skills, ["uninstall", "kedro-catalog-config"])
        assert result.exit_code == 0

        assert not (
            install_dir / ".agents/skills/kedro-catalog-config/SKILL.md"
        ).is_file()
        assert not (install_dir / "AGENTS.md").is_file()
        assert not (install_dir / ".cursor/rules/kedro-catalog-config.mdc").is_file()
        assert not (
            install_dir / ".github/instructions/kedro-catalog-config.instructions.md"
        ).is_file()
        assert not (
            install_dir / ".claude/skills/kedro-catalog-config/SKILL.md"
        ).is_file()
        assert not (install_dir / ".agents/skills/.installed.json").is_file()

    def test_list_shows_not_installed_after_uninstall(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "kedro-catalog-config"], input="all\n")
        runner.invoke(skills, ["uninstall", "kedro-catalog-config"])

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

    def test_install_outside_kedro_project(
        self, non_kedro_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(non_kedro_dir)
        runner = CliRunner()
        result = runner.invoke(
            skills, ["install", "kedro-catalog-config"], input="all\n"
        )
        assert result.exit_code == 0, result.output
        assert "Not inside a Kedro project" in result.output


class TestErrorHandling:
    def test_uninstall_not_installed(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        result = runner.invoke(skills, ["uninstall", "kedro-catalog-config"])
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
        runner.invoke(skills, ["install", "kedro-catalog-config", "--ide", "cursor"])

        assert (kedro_project / ".cursor/rules/kedro-catalog-config.mdc").is_file()
        assert not (
            kedro_project / ".github/instructions/kedro-catalog-config.instructions.md"
        ).is_file()

        result = runner.invoke(skills, ["update"])
        assert result.exit_code == 0

        assert (kedro_project / ".cursor/rules/kedro-catalog-config.mdc").is_file()
        assert not (
            kedro_project / ".github/instructions/kedro-catalog-config.instructions.md"
        ).is_file()
        assert not (
            kedro_project / ".claude/skills/kedro-catalog-config/SKILL.md"
        ).is_file()


class TestPartialUninstall:
    def test_uninstall_drift_keeps_skill_in_state(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If files are drifted and --force is not used, skill stays in state."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "kedro-catalog-config"], input="all\n")

        cursor_file = kedro_project / ".cursor/rules/kedro-catalog-config.mdc"
        cursor_file.write_text("user modified content", encoding="utf-8")

        result = runner.invoke(skills, ["uninstall", "kedro-catalog-config"])
        assert result.exit_code == 0
        assert "refused" in result.output or "modified" in result.output

        from kedro_skills.state import read  # noqa: PLC0415

        installed = read(kedro_project)
        assert "kedro-catalog-config" in installed.skills


class TestParametersAndConfigSkill:
    """Install/uninstall lifecycle for the kedro-parameters-and-config skill."""

    def test_install_creates_all_files(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        result = runner.invoke(
            skills, ["install", "kedro-parameters-and-config"], input="all\n"
        )
        assert result.exit_code == 0, result.output

        assert (
            kedro_project / ".agents/skills/kedro-parameters-and-config/SKILL.md"
        ).is_file()
        assert (kedro_project / "AGENTS.md").is_file()
        assert (
            kedro_project / ".cursor/rules/kedro-parameters-and-config.mdc"
        ).is_file()
        assert (
            kedro_project
            / ".github/instructions/kedro-parameters-and-config.instructions.md"
        ).is_file()
        assert (
            kedro_project / ".claude/skills/kedro-parameters-and-config/SKILL.md"
        ).is_file()

    def test_uninstall_removes_all_files(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "kedro-parameters-and-config"], input="all\n")
        result = runner.invoke(skills, ["uninstall", "kedro-parameters-and-config"])
        assert result.exit_code == 0

        assert not (
            kedro_project / ".agents/skills/kedro-parameters-and-config/SKILL.md"
        ).is_file()
        assert not (
            kedro_project / ".cursor/rules/kedro-parameters-and-config.mdc"
        ).is_file()
        assert not (
            kedro_project
            / ".github/instructions/kedro-parameters-and-config.instructions.md"
        ).is_file()
        assert not (
            kedro_project / ".claude/skills/kedro-parameters-and-config/SKILL.md"
        ).is_file()

    def test_both_skills_coexist_in_agents_md(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Both skills can be installed and each gets its own AGENTS.md block."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "kedro-catalog-config"], input="all\n")
        runner.invoke(skills, ["install", "kedro-parameters-and-config"], input="all\n")

        agents_md = (kedro_project / "AGENTS.md").read_text(encoding="utf-8")
        assert "<!-- kedro-skills:kedro-catalog-config:start -->" in agents_md
        assert "<!-- kedro-skills:kedro-catalog-config:end -->" in agents_md
        assert "<!-- kedro-skills:kedro-parameters-and-config:start -->" in agents_md
        assert "<!-- kedro-skills:kedro-parameters-and-config:end -->" in agents_md

    def test_install_all_includes_both_skills(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        result = runner.invoke(skills, ["install", "--all"])
        assert result.exit_code == 0
        assert (
            kedro_project / ".agents/skills/kedro-catalog-config/SKILL.md"
        ).is_file()
        assert (
            kedro_project / ".agents/skills/kedro-parameters-and-config/SKILL.md"
        ).is_file()

    def test_uninstall_one_preserves_other(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Uninstalling one skill does not remove the other's files."""
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "--all"])
        runner.invoke(skills, ["uninstall", "kedro-parameters-and-config"])

        # kedro-catalog-config files still present
        assert (
            kedro_project / ".agents/skills/kedro-catalog-config/SKILL.md"
        ).is_file()
        assert (kedro_project / ".cursor/rules/kedro-catalog-config.mdc").is_file()
        # AGENTS.md still exists with kedro-catalog-config block
        agents_md = (kedro_project / "AGENTS.md").read_text(encoding="utf-8")
        assert "<!-- kedro-skills:kedro-catalog-config:start -->" in agents_md
        assert "kedro-parameters-and-config" not in agents_md


def _install_under_old_id(project_root: Path, old_id: str, ides: list[str]) -> None:
    """Install a skill the way kedro-skills did before it was renamed."""
    skill = get_skill(RENAMED_SKILL_IDS[old_id])
    skill_md = installer._resolve_skill_path(skill.id)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(orchestrator, "get_skill", lambda _: replace(skill, id=old_id))
        mp.setattr(installer, "_resolve_skill_path", lambda _: skill_md)
        orchestrator.install_skill(old_id, project_root, ides=ides)


class TestRenamedSkills:
    """Skills installed under their old, pre-``kedro-`` id move to the new id."""

    def test_update_moves_skill_to_new_id(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_under_old_id(kedro_project, "catalog-config", ["cursor"])
        monkeypatch.chdir(kedro_project)

        result = CliRunner().invoke(skills, ["update"])
        assert result.exit_code == 0, result.output
        assert "Updated 'kedro-catalog-config'" in result.output

        assert not (kedro_project / ".agents/skills/catalog-config").exists()
        assert not (kedro_project / ".cursor/rules/catalog-config.mdc").exists()
        assert (
            kedro_project / ".agents/skills/kedro-catalog-config/SKILL.md"
        ).is_file()
        assert (kedro_project / ".cursor/rules/kedro-catalog-config.mdc").is_file()
        # Only for the IDEs it was installed for under the old id.
        assert not (kedro_project / ".claude/skills/kedro-catalog-config").exists()

        agents_md = (kedro_project / "AGENTS.md").read_text(encoding="utf-8")
        assert "kedro-skills:catalog-config:" not in agents_md
        assert "<!-- kedro-skills:kedro-catalog-config:start -->" in agents_md

        assert list(read(kedro_project).skills) == ["kedro-catalog-config"]

    def test_update_refuses_when_old_files_modified(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_under_old_id(kedro_project, "catalog-config", ["cursor"])
        old_rule = kedro_project / ".cursor/rules/catalog-config.mdc"
        old_rule.write_text("user edited content\n", encoding="utf-8")
        monkeypatch.chdir(kedro_project)

        result = CliRunner().invoke(skills, ["update"])
        assert result.exit_code == 0, result.output
        assert ".cursor/rules/catalog-config.mdc (modified)" in result.output
        assert "--force" in result.output

        assert old_rule.read_text(encoding="utf-8") == "user edited content\n"
        assert not (kedro_project / ".agents/skills/kedro-catalog-config").exists()
        assert list(read(kedro_project).skills) == ["catalog-config"]

    def test_update_force_replaces_modified_old_files(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_under_old_id(kedro_project, "catalog-config", ["cursor"])
        old_rule = kedro_project / ".cursor/rules/catalog-config.mdc"
        old_rule.write_text("user edited content\n", encoding="utf-8")
        monkeypatch.chdir(kedro_project)

        result = CliRunner().invoke(skills, ["update", "--force"])
        assert result.exit_code == 0, result.output

        assert not old_rule.exists()
        assert (kedro_project / ".cursor/rules/kedro-catalog-config.mdc").is_file()
        assert list(read(kedro_project).skills) == ["kedro-catalog-config"]

    def test_update_with_old_and_new_ids_installed(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        runner = CliRunner()
        runner.invoke(skills, ["install", "kedro-catalog-config", "--ide", "cursor"])
        _install_under_old_id(kedro_project, "catalog-config", ["cursor"])

        result = runner.invoke(skills, ["update"])
        assert result.exit_code == 0, result.output
        assert result.output.count("Updated") == 1

        assert not (kedro_project / ".cursor/rules/catalog-config.mdc").exists()
        assert (kedro_project / ".cursor/rules/kedro-catalog-config.mdc").is_file()
        assert list(read(kedro_project).skills) == ["kedro-catalog-config"]

    def test_install_replaces_old_install(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_under_old_id(kedro_project, "catalog-config", ["cursor"])
        monkeypatch.chdir(kedro_project)

        result = CliRunner().invoke(
            skills, ["install", "kedro-catalog-config", "--ide", "cursor"]
        )
        assert result.exit_code == 0, result.output

        assert not (kedro_project / ".cursor/rules/catalog-config.mdc").exists()
        assert (kedro_project / ".cursor/rules/kedro-catalog-config.mdc").is_file()
        agents_md = (kedro_project / "AGENTS.md").read_text(encoding="utf-8")
        assert agents_md.count(":start -->") == 1
        assert list(read(kedro_project).skills) == ["kedro-catalog-config"]

    def test_install_refuses_when_old_files_modified(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_under_old_id(kedro_project, "catalog-config", ["cursor"])
        old_rule = kedro_project / ".cursor/rules/catalog-config.mdc"
        old_rule.write_text("user edited content\n", encoding="utf-8")
        monkeypatch.chdir(kedro_project)

        result = CliRunner().invoke(
            skills, ["install", "kedro-catalog-config", "--ide", "cursor"]
        )
        assert result.exit_code == 0, result.output
        assert ".cursor/rules/catalog-config.mdc (modified)" in result.output

        assert old_rule.read_text(encoding="utf-8") == "user edited content\n"
        assert list(read(kedro_project).skills) == ["catalog-config"]

    def test_install_old_id_names_new_id(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(
            skills, ["install", "catalog-config", "--ide", "cursor"]
        )
        assert result.exit_code != 0
        assert "renamed to 'kedro-catalog-config'" in result.output

    def test_uninstall_old_id(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_under_old_id(kedro_project, "catalog-config", ["cursor"])
        monkeypatch.chdir(kedro_project)

        result = CliRunner().invoke(skills, ["uninstall", "catalog-config"])
        assert result.exit_code == 0, result.output

        assert not (kedro_project / ".agents/skills/catalog-config").exists()
        assert not (kedro_project / ".cursor/rules/catalog-config.mdc").exists()
        assert not (kedro_project / "AGENTS.md").exists()
        assert not (kedro_project / ".agents/skills/.installed.json").exists()

    def test_list_points_at_update(
        self, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_under_old_id(kedro_project, "catalog-config", ["cursor"])
        monkeypatch.chdir(kedro_project)

        result = CliRunner().invoke(skills, ["list"])
        assert result.exit_code == 0, result.output
        assert "catalog-config → kedro-catalog-config" in result.output
        assert "kedro skills update" in result.output
