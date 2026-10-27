"""Checks that every skill declared in ``registry.yaml`` ships a usable ``SKILL.md``."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml
from click.testing import CliRunner

from kedro_skills.cli import skills
from kedro_skills.installer import _resolve_skill_path
from kedro_skills.registry import RENAMED_SKILL_IDS, load_registry

if TYPE_CHECKING:
    from kedro_skills.registry import SkillMetadata

SKILLS = load_registry()
SKILL_IDS = {s.id for s in SKILLS}
SKILLS_DIR = Path(__file__).parents[1] / "skills"
IDES = ["cursor", "copilot", "claude"]


def test_every_skill_directory_is_registered() -> None:
    """``load_registry`` enforces the naming convention on registered ids only, so
    an unregistered directory would slip past it."""
    directories = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
    assert directories == SKILL_IDS


@pytest.mark.parametrize(("old_id", "new_id"), RENAMED_SKILL_IDS.items())
def test_renamed_id_points_at_registered_skill(old_id: str, new_id: str) -> None:
    assert new_id in SKILL_IDS
    assert old_id not in SKILL_IDS


def _split_frontmatter(skill_id: str) -> tuple[dict, str]:
    text = _resolve_skill_path(skill_id).read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{skill_id}: SKILL.md must open with frontmatter"
    end = text.index("\n---", 4)
    return yaml.safe_load(text[4:end]), text[end + 4 :]


def _frontmatter_of(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    end = text.index("\n---", 4)
    return yaml.safe_load(text[4:end])


@pytest.mark.parametrize("skill", SKILLS, ids=[s.id for s in SKILLS])
class TestPackagedSkill:
    def test_skill_md_exists(self, skill: SkillMetadata) -> None:
        assert _resolve_skill_path(skill.id).is_file()

    def test_frontmatter_name_matches_id(self, skill: SkillMetadata) -> None:
        frontmatter, _ = _split_frontmatter(skill.id)
        assert frontmatter["name"] == skill.id

    def test_frontmatter_description_matches_registry(
        self, skill: SkillMetadata
    ) -> None:
        """Claude activates on the SKILL.md description, Cursor and Copilot on the
        registry one; keeping them identical keeps activation consistent."""
        frontmatter, _ = _split_frontmatter(skill.id)
        assert " ".join(frontmatter["description"].split()) == " ".join(
            skill.description.split()
        )

    def test_frontmatter_has_no_paths(self, skill: SkillMetadata) -> None:
        frontmatter, _ = _split_frontmatter(skill.id)
        assert "paths" not in frontmatter

    def test_body_is_not_empty(self, skill: SkillMetadata) -> None:
        _, body = _split_frontmatter(skill.id)
        assert body.strip()

    def test_install_renders_every_ide(
        self, skill: SkillMetadata, kedro_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(kedro_project)
        result = CliRunner().invoke(
            skills, ["install", skill.id, "--ide", ",".join(IDES)]
        )
        assert result.exit_code == 0, result.output

        canonical = kedro_project / ".agents/skills" / skill.id / "SKILL.md"
        assert canonical.read_bytes() == _resolve_skill_path(skill.id).read_bytes()
        assert (kedro_project / ".claude/skills" / skill.id / "SKILL.md").is_file()

        agents_md = (kedro_project / "AGENTS.md").read_text(encoding="utf-8")
        assert f"<!-- kedro-skills:{skill.id}:start -->" in agents_md
        for glob in skill.paths:
            assert f"`{glob}`" in agents_md

        cursor = _frontmatter_of(kedro_project / ".cursor/rules" / f"{skill.id}.mdc")
        assert cursor["globs"] == ", ".join(skill.paths)
        assert cursor["description"]

        copilot = _frontmatter_of(
            kedro_project / ".github/instructions" / f"{skill.id}.instructions.md"
        )
        assert copilot["applyTo"] == ", ".join(skill.paths)
        assert copilot["description"]
